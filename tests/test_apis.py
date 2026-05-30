import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

print("--- STARTING API CONNECTION TESTS ---")

# 1. Test Gemini
if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("your_"):
    print("\n[TEST 1] Testing Gemini API (gemini-2.5-flash)...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Reply with 'Gemini is working fine'")
        print(f"Gemini Response: {response.text.strip()}")
    except Exception as e:
        print(f"Gemini Failed: {e}")
else:
    print("\n[TEST 1] Gemini Key is missing or default placeholder.")

# Helper for OpenRouter test
def test_openrouter(model_name, label):
    print(f"\n[TEST] Testing OpenRouter model {label} ({model_name})...")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://127.0.0.1:5000",
        "X-Title": "Personal Hub Test"
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": f"Reply with '{label} is working fine'"}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            result = response.json()
            print(f"{label} Response: {result['choices'][0]['message']['content'].strip()}")
        else:
            print(f"{label} Failed (Status {response.status_code}): {response.text}")
    except Exception as e:
        print(f"{label} Failed: {e}")

# 2. Test OpenRouter
if OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith("your_"):
    test_openrouter("deepseek/deepseek-v4-flash:free", "DeepSeek Free")
    test_openrouter("qwen/qwen3-next-80b-a3b-instruct:free", "Qwen Free")
else:
    print("\n[TEST 2] OpenRouter Key is missing or default placeholder.")

# 3. Test DeepSeek Official API
if DEEPSEEK_API_KEY and not DEEPSEEK_API_KEY.startswith("your_"):
    print("\n[TEST 3] Testing Official DeepSeek API (deepseek-chat)...")
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "Reply with 'DeepSeek Official is working fine'"}
        ],
        "max_tokens": 50
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            result = response.json()
            print(f"DeepSeek Official Response: {result['choices'][0]['message']['content'].strip()}")
        else:
            print(f"DeepSeek Official Failed (Status {response.status_code}): {response.text}")
    except Exception as e:
        print(f"DeepSeek Official Failed: {e}")
else:
    print("\n[TEST 3] DeepSeek Official Key is missing or default placeholder.")

print("\n--- API CONNECTION TESTS FINISHED ---")

