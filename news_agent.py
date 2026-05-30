import os
import time
import sqlite3
import feedparser
from dotenv import load_dotenv
import google.generativeai as genai
import database

# Load environment variables from .env if present
load_dotenv()

# Configure Gemini API if key is present
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # ค้นหาโมเดล Flash ที่ดีที่สุดและพร้อมใช้งานจาก API key นี้แบบไดนามิก
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        preferred_models = [
            'models/gemini-2.5-flash',
            'models/gemini-2.0-flash',
            'models/gemini-1.5-flash',
            'models/gemini-3.5-flash',
        ]
        selected_model = 'gemini-2.5-flash' # ค่าเริ่มต้นกรณีหาตัวโปรดไม่เจอ
        for pref in preferred_models:
            if pref in available_models:
                selected_model = pref.replace('models/', '')
                break
        print(f"Selected Gemini Model: {selected_model}")
        model = genai.GenerativeModel(selected_model)
    except Exception as e:
        print(f"Error checking models, fallback to gemini-2.5-flash: {e}")
        model = genai.GenerativeModel('gemini-2.5-flash')
else:
    model = None


# Tech RSS Feeds to aggregate
RSS_FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "Wired": "https://www.wired.com/feed/rss",
    "The Verge": "https://www.theverge.com/rss/index.xml"
}

def clean_html(text):
    """Helper to remove simple HTML tags from RSS description if any"""
    import re
    if not text:
        return ""
    # Remove HTML tags
    clean = re.compile('<.*?>')
    cleaned = re.sub(clean, '', text)
    # Decode XML entities if any
    cleaned = cleaned.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    return cleaned.strip()

def rule_based_filter(title, description):
    """Fallback rule-based relevance checker for Tech/AI keywords"""
    keywords = [
        'ai', 'artificial intelligence', 'machine learning', 'tech', 'software', 
        'hardware', 'chip', 'nvidia', 'intel', 'amd', 'apple', 'google', 
        'microsoft', 'openai', 'claude', 'gemini', 'chatgpt', 'robot', 
        'semiconductor', 'quantum', 'cybersecurity', 'mobile', 'app', 'startup'
    ]
    text = (title + " " + description).lower()
    for kw in keywords:
        if kw in text:
            # Simple category detection
            if any(x in text for x in ['ai', 'artificial intelligence', 'openai', 'claude', 'gemini', 'chatgpt', 'llm', 'neural']):
                return True, "AI"
            return True, "Tech"
    return False, None

def ask_gemini_to_summarize(title, description):
    """Uses Gemini API to filter, categorize and summarize the news item in 1 short Thai sentence"""
    if not model:
        return None
    
    prompt = f"""
    Analyze the following news item:
    Title: {title}
    Description: {description}

    Rules:
    1. Is this news relevant to Artificial Intelligence (AI) or general Technology? 
       - If NO, reply with only the word "SKIP".
       - If YES:
         a) Translate and summarize the news into a single, very short Thai sentence (maximum 20 words). Keep it highly concise and simple.
         b) Categorize it as "AI" or "Tech".
         c) Format the output EXACTLY as:
            RELEVANT: [Yes/No]
            CATEGORY: [AI/Tech]
            SUMMARY: [Your short Thai summary]
    
    Do not add any markdown formatting, thoughts, or extra characters.
    """
    try:
        response = model.generate_content(prompt)
        text_resp = response.text.strip()
        
        if "SKIP" in text_resp or "RELEVANT: No" in text_resp:
            return None
        
        # Parse response
        lines = text_resp.split('\n')
        category = "Tech"
        summary = ""
        
        for line in lines:
            if line.startswith("CATEGORY:"):
                category = line.replace("CATEGORY:", "").strip()
            elif line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
                
        if summary:
            return {"category": category, "summary": summary}
        return None
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

def update_news_data():
    """Fetches RSS feeds, filters/summarizes using AI (or rules), and stores in DB"""
    print("Starting news aggregation and update...")
    
    # Establish a fresh connection with a 30s timeout for Thread-safety and lock prevention
    conn = sqlite3.connect(database.DATABASE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    new_articles_count = 0
    
    for source, url in RSS_FEEDS.items():
        print(f"Fetching from {source}: {url}")
        try:
            feed = feedparser.parse(url)
            # ดึงข่าวล่าสุด 2 ข่าวต่อหนึ่งแหล่งเพื่อประหยัดโควตาและโทเคนสูงสุด (รวมไม่เกิน 6 ข่าวต่อรอบ)
            entries = feed.entries[:2]
            
            for entry in entries:
                title = entry.get('title', 'No Title')
                link = entry.get('link', '')
                raw_desc = entry.get('description', '') or entry.get('summary', '')
                desc = clean_html(raw_desc)
                pub_date = entry.get('published', '') or entry.get('updated', '')
                
                if not link:
                    continue
                
                # Check if already exists in DB to avoid reprocessing
                cursor.execute("SELECT id FROM news WHERE url = ?", (link,))
                if cursor.fetchone():
                    # Article already parsed and saved before
                    continue
                
                # Process with Gemini AI or fallback
                ai_result = None
                if model:
                    print(f"Processing with Gemini API: {title[:50]}...")
                    ai_result = ask_gemini_to_summarize(title, desc)
                    # หน่วงเวลา 12 วินาทีเพื่อให้ไม่เกินลิมิต 5 requests/minute ของรุ่นฟรียุคใหม่
                    time.sleep(12)

                
                if ai_result:
                    # AI verified relevant
                    category = ai_result['category']
                    summary = ai_result['summary']
                else:
                    # Fallback or API skipped/failed
                    # Perform rule-based filter
                    is_rel, cat = rule_based_filter(title, desc)
                    if not is_rel:
                        # Skip if not tech/AI related
                        continue
                    category = cat
                    # Limit summary to 120 chars for fallback English display
                    summary = desc[:150] + "..." if len(desc) > 150 else desc
                    if not summary:
                        summary = title
                
                # Insert new article
                try:
                    cursor.execute("""
                        INSERT INTO news (title, summary, url, published_date, source, category)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (title, summary, link, pub_date, source, category))
                    new_articles_count += 1
                except sqlite3.IntegrityError:
                    # Prevent duplicate URLs just in case
                    pass
                    
        except Exception as e:
            print(f"Error parsing feed {source}: {e}")
            
    # Update last_updated_time metadata
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        INSERT OR REPLACE INTO news_metadata (key, value)
        VALUES ('last_updated_time', ?)
    """, (current_time,))
    
    conn.commit()
    conn.close()
    
    print(f"News update completed. Added {new_articles_count} new articles.")
    return new_articles_count

if __name__ == "__main__":
    # Test script locally
    import sys
    print("Testing News Agent...")
    added = update_news_data()
    print(f"Done. Added {added} news.")
