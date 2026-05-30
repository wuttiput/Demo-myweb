import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


# --- Configure Gemini ---
gemini_model = None
if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("your_"):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # ใช้โมเดล gemini-2.5-flash ที่เสถียรสำหรับคุยแชท
        gemini_model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        print(f"Error configuring Gemini: {e}")

# --- Check Model Availability ---
def is_model_available(provider):
    """ตรวจสอบว่าโมเดลของค่ายที่เลือกเปิดใช้งานและมี API Key หรือไม่"""
    if provider == 'gemini':
        return gemini_model is not None
    elif provider == 'deepseek':
        # พร้อมใช้ถ้ามีคีย์ตรงของ DeepSeek หรือคีย์ OpenRouter
        has_direct = bool(DEEPSEEK_API_KEY and not DEEPSEEK_API_KEY.startswith("your_") and DEEPSEEK_API_KEY != "")
        has_or = bool(OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith("your_") and OPENROUTER_API_KEY != "")
        return has_direct or has_or
    elif provider == 'qwen':
        return bool(OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith("your_") and OPENROUTER_API_KEY != "")
    return False

def get_available_models():
    """คืนค่ารายการโมเดลที่พร้อมใช้งาน"""
    available = []
    if is_model_available('gemini'):
        available.append({'id': 'gemini', 'name': 'Gemini 2.5 Flash (Google)', 'free': True})
    if is_model_available('deepseek'):
        # แสดงชื่อตามประเภทคีย์ที่ตั้งไว้
        if DEEPSEEK_API_KEY and not DEEPSEEK_API_KEY.startswith("your_"):
            available.append({'id': 'deepseek', 'name': 'DeepSeek Chat (Official API)', 'free': False})
        else:
            available.append({'id': 'deepseek', 'name': 'DeepSeek V4 Flash (Free on OpenRouter)', 'free': True})
    if is_model_available('qwen'):
        available.append({'id': 'qwen', 'name': 'Qwen 3 Next 80B (Free on OpenRouter)', 'free': True})
    return available

# --- Send Message to Gemini ---
def _chat_gemini(message_text, history_messages):
    """ส่งคำถามไปหา Gemini โดยรักษาประวัติการสนทนา"""
    if not gemini_model:
        return "Gemini API ยังไม่พร้อมใช้งาน กรุณาตั้งค่า GEMINI_API_KEY"
    
    # แปลงประวัติแชทของ SQLite เป็นโครงสร้างที่ Gemini ต้องการ
    contents = []
    for msg in history_messages:
        role = "user" if msg['sender'] == 'user' else "model"
        contents.append({
            "role": role,
            "parts": [msg['message']]
        })
        
    # เพิ่มข้อความปัจจุบันเข้าไป
    contents.append({
        "role": "user",
        "parts": [message_text]
    })
    
    try:
        response = gemini_model.generate_content(contents)
        return response.text.strip()
    except Exception as e:
        return f"Gemini API Error: {e}"

# --- Send Message to OpenRouter (DeepSeek / Qwen) ---
def _chat_openrouter(model_id, message_text, history_messages):
    """ส่งคำถามไปหา OpenRouter (DeepSeek / Qwen รุ่นฟรี)"""
    if not OPENROUTER_API_KEY:
        return "OpenRouter API Key ยังไม่พร้อมใช้งาน กรุณาตั้งค่า OPENROUTER_API_KEY ในไฟล์ .env"
        
    # เลือกรุ่นโมเดลฟรีที่เหมาะสม
    model_name = "deepseek/deepseek-v4-flash:free"
    if model_id == 'qwen':
        model_name = "qwen/qwen3-next-80b-a3b-instruct:free"
        
    # แปลงประวัติเป็นฟอร์แมต OpenAI-compatible
    messages = []
    
    # เพิ่ม System Prompt เพื่อกำหนดพฤติกรรม
    messages.append({
        "role": "system",
        "content": "You are a helpful and intelligent personal assistant. Answer the user clearly and friendly in the language they use (defaulting to Thai)."
    })
    
    for msg in history_messages:
        role = "user" if msg['sender'] == 'user' else "assistant"
        messages.append({"role": role, "content": msg['message']})
        
    messages.append({"role": "user", "content": message_text})
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://127.0.0.1:5000",
        "X-Title": "Personal Hub Chat"
    }
    
    payload = {
        "model": model_name,
        "messages": messages
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            return f"OpenRouter API Error (Status {response.status_code}): {response.text}"
    except Exception as e:
        return f"Request Error: {e}"

# --- Send Message to DeepSeek Official API ---
def _chat_deepseek_official(message_text, history_messages):
    """ส่งคำถามตรงไปยัง DeepSeek API (เสถียรและเร็วมากสำหรับผู้ใช้ที่มีคีย์ตรง)"""
    if not DEEPSEEK_API_KEY:
        return "DeepSeek API Key ไม่ถูกต้อง"
        
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = []
    messages.append({
        "role": "system",
        "content": "You are a helpful and intelligent personal assistant. Answer the user clearly and friendly in the language they use (defaulting to Thai)."
    })
    
    for msg in history_messages:
        role = "user" if msg['sender'] == 'user' else "assistant"
        messages.append({"role": role, "content": msg['message']})
        
    messages.append({"role": "user", "content": message_text})
    
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            return f"DeepSeek API Error (Status {response.status_code}): {response.text}"
    except Exception as e:
        return f"Request Error: {e}"

# --- Main Entry Point for Routing ---
def generate_ai_response(model_id, message_text, history_messages):
    """ฟังก์ชันหลักสำหรับเลือกส่งข้อมูลไปประมวลผลตามโมเดลที่เลือก"""
    if model_id == 'gemini':
        return _chat_gemini(message_text, history_messages)
    elif model_id == 'deepseek':
        # หากมีคีย์ตรงของ DeepSeek ให้วิ่งเข้าเซิร์ฟเวอร์หลักเพื่อความเสถียรสูงสุด
        if DEEPSEEK_API_KEY and not DEEPSEEK_API_KEY.startswith("your_"):
            return _chat_deepseek_official(message_text, history_messages)
        else:
            return _chat_openrouter(model_id, message_text, history_messages)
    elif model_id == 'qwen':
        return _chat_openrouter(model_id, message_text, history_messages)
    else:
        return f"ไม่รองรับโมเดลรหัส {model_id}"
