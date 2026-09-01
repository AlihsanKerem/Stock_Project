from flask import Flask, render_template, jsonify, request
from database import get_all_stock_data, init_db, get_tracked_stocks, add_tracked_stock, remove_tracked_stock
from analyzer import analyze_stock
from sentiment import analyze_sentiment
import os
import yfinance as yf

app = Flask(__name__)

# Veritabanını hazırla
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hisse-analiz')
def hisse_analiz():
    return render_template('detail.html')

@app.route('/takip')
def takip_listesi():
    return render_template('tracked.html')

@app.route('/api/data')
def api_data():
    try:
        data = get_all_stock_data()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/analyze/<symbol>')
def api_analyze(symbol):
    try:
        # ".IS" eklentisi yoksa ekle (Kullanıcı "THYAO" girecektir)
        symbol = symbol.upper()
        if not symbol.endswith('.IS'):
            symbol = symbol + '.IS'
            
        result = analyze_stock(symbol)
        if result:
            # Haberleri bul ve LLM (Ollama/Gemini) ile analiz et
            sentiment_result = analyze_sentiment(symbol)
            result['sentiment'] = sentiment_result
            
            return jsonify({"status": "success", "data": result})
        else:
            return jsonify({"status": "error", "message": "Veri bulunamadı. Lütfen geçerli bir hisse kodu girin."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/tracked')
def api_get_tracked():
    try:
        data = get_tracked_stocks()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/tracked/add', methods=['POST'])
def api_add_tracked():
    try:
        data = request.json
        symbol = data.get('symbol', '').upper()
        if not symbol:
            return jsonify({"status": "error", "message": "Sembol boş olamaz."})
            
        # Check if it exists and fetch current price
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="5d")
        
        if history.empty:
            return jsonify({"status": "error", "message": f"'{symbol}' sembolü bulunamadı veya veri alınamadı. Uzantıyı (örn: BIST) doğru seçtiğinizden emin olun."})
            
        last_price = history.iloc[-1]['Close']
        add_tracked_stock(symbol, last_price)
        return jsonify({"status": "success", "message": f"{symbol} başarıyla listeye eklendi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/tracked/remove', methods=['POST'])
def api_remove_tracked():
    try:
        data = request.json
        symbol = data.get('symbol', '').upper()
        if not symbol:
            return jsonify({"status": "error", "message": "Sembol boş olamaz."})
            
        remove_tracked_stock(symbol)
        return jsonify({"status": "success", "message": f"{symbol} listeden çıkarıldı."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    # Flask sunucusunu başlat
    app.run(debug=True, host='0.0.0.0', port=5000)
