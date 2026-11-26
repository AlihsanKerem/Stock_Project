import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

def get_latest_news(symbol):
    """
    yfinance kullanarak hisse senedi hakkında en son haberleri çeker.
    """
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        if not news:
            return None
        
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
    Hissenin son haberini alır ve .env üzerinden yapılandırılmış Evrensel LLM (Gemini, Groq, Ollama vb.)
    ile duygu analizi yapar.
    """
    news_item = get_latest_news(symbol)
    if not news_item:
        return {"status": "neutral", "message": "Son haber bulunamadı."}

    prompt = (
        f"Sen uzman bir borsa analistisin.\n"
        f"Aşağıda {symbol} hissesiyle ilgili çıkan en son haberin başlığı yer alıyor.\n"
        f"Bu haberin hisse fiyatı üzerinde kısa ve orta vadede nasıl bir etki yaratmasını beklersin?\n"
        f"Sadece 3 kelimeden biriyle cevap ver: 'OLUMLU', 'OLUMSUZ', 'NÖTR'. Başka hiçbir kelime kullanma.\n\n"
        f"Haber Başlığı: {news_item['title']}\n"
        f"Yayıncı: {news_item['publisher']}\n"
        f"Cevap:"
    )

    try:
        from agent_engine import LLMAdapter
        adapter = LLMAdapter()
        raw_res = adapter.call_llm([{"role": "user", "content": prompt}])

        if not raw_res or "Sistem Bildirimi" in raw_res:
            return {"status": "error", "message": "LLM sağlayıcısı yapılandırılmamış veya yanıt vermedi."}

        sentiment = raw_res.strip().upper()
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
    print("THYAO.IS için duygu analizi testi...")
    result = analyze_sentiment("THYAO.IS")
    print(result)
