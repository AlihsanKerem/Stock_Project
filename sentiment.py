import os
import google.generativeai as genai
import yfinance as yf
import requests
from dotenv import load_dotenv

# .env dosyasından API anahtarlarını yükle
load_dotenv()

# Ayarları Al
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

model = None
if GEMINI_API_KEY and GEMINI_API_KEY != "your_google_gemini_api_key_here":
    genai.configure(api_key=GEMINI_API_KEY)
    # Model oluştur
    model = genai.GenerativeModel('gemini-1.5-flash')

def get_latest_news(symbol):
    """
    yfinance kullanarak hisse senedi hakkında en son haberleri çeker.
    """
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        if not news:
            return None
        
        # En son haberi al
        latest = news[0]
        return {
            "title": latest.get('title', ''),
            "publisher": latest.get('publisher', ''),
            "link": latest.get('link', '')
        }
    except Exception as e:
        print(f"Haberler çekilirken hata oluştu ({symbol}): {e}")
        return None

def analyze_sentiment(symbol):
    """
    Hissenin son haberini alır ve Lokal Model (Ollama) veya Gemini kullanarak duygu analizi yapar.
    """
    if not OLLAMA_API_URL and not model:
        return {"status": "error", "message": "Ne lokal LLM URL'i ne de Gemini API anahtarı ayarlanmamış."}

    news_item = get_latest_news(symbol)
    if not news_item:
        return {"status": "neutral", "message": "Son haber bulunamadı."}

    prompt = f"""
    Sen uzman bir borsa analistisin. 
    Aşağıda {symbol} hissesiyle ilgili çıkan en son haberin başlığı yer alıyor. 
    Bu haberin hisse fiyatı üzerinde kısa ve orta vadede nasıl bir etki yaratmasını beklersin? 
    Sadece 3 kelimeden biriyle cevap ver: 'OLUMLU', 'OLUMSUZ', 'NÖTR'. Başka hiçbir kelime kullanma.
    
    Haber Başlığı: {news_item['title']}
    Yayıncı: {news_item['publisher']}
    Cevap:"""

    try:
        sentiment = "NÖTR"
        
        # Eğer Ollama aktifse onu kullan (Öncelikli)
        if OLLAMA_API_URL:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
            # Lokal modellerin ilk cevap süresi (özellikle CPU'da) 10 saniyeyi geçebildiği için süreyi uzattık.
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=45)
            if response.status_code == 200:
                sentiment = response.json().get("response", "").strip().upper()
            else:
                return {"status": "error", "message": f"Ollama API Hatası: {response.status_code}"}
        
        # Ollama yoksa Gemini'yi kullan
        elif model:
            response = model.generate_content(prompt)
            sentiment = response.text.strip().upper()
        
        # Çıktı Temizleme ve Eşleme
        if "OLUMLU" in sentiment or "POSITIVE" in sentiment:
            sentiment = "OLUMLU"
        elif "OLUMSUZ" in sentiment or "NEGATIVE" in sentiment:
            sentiment = "OLUMSUZ"
        else:
            sentiment = "NÖTR"
            
        return {
            "status": sentiment, 
            "title": news_item['title'],
            "link": news_item['link']
        }
    except Exception as e:
        print(f"LLM API hatası: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Test
    print("THYAO.IS için duygu analizi testi...")
    result = analyze_sentiment("THYAO.IS")
    print(result)
