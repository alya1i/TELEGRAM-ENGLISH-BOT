import json, os, random, re, requests

#here to save all the words add by user to file
DATA_FILE = "words.json"
# this for Gemini 
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
API_KEY = os.getenv("GEMINI_API_KEY") 


def load_words():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_words(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clean_response(text):
    text = re.sub(r"```(?:json)?", "", text)
    text = text.replace("```", "")
    return text.strip()
# for this code go gemini and take the responed based on the structure o give 
def call_gemini_api(prompt_text):
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt_text}]}]}
    full_url = f"{API_URL}?key={API_KEY}"
    
    try:
        response = requests.post(full_url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            return parts[0]["text"] if parts and isinstance(parts[0], dict) and "text" in parts[0] else ""
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return ""
    except requests.RequestException as e:
        print(f"Request Error: {e}")
        return ""

def get_word_data(word: str):
    word = word.strip().lower()
    prompt = f"""
You are a bilingual English-Arabic dictionary assistant.
For the English word "{word}", respond ONLY with a JSON object in this format:
{{
  "word": "{word}",
  "meaning_arabic": "معنى الكلمة بالعربية (كلمة أو اثنتين)",
  "synonyms": ["synonym1", "synonym2", "synonym3"],
  "example": "An English sentence using the word."
}}
"""
    answer = call_gemini_api(prompt)
    cleaned = clean_response(answer)

    try:
        data = json.loads(cleaned)
        if not data.get("meaning_arabic") or "كلمة أو كلمتين" in data.get("meaning_arabic", ""):
            return None
        return {
            "word": word,
            "meaning": data.get("meaning_arabic", ""),
            "synonyms": data.get("synonyms", []),
            "example": data.get("example", "")
        }
    except json.JSONDecodeError:
        return None