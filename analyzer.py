import yfinance as yf
import pandas as pd
import ta
import time

# BIST 100 hisse senetleri listesi
BIST_SYMBOLS = [
    'AEFES.IS', 'AGHOL.IS', 'AHGAZ.IS', 'AKBNK.IS', 'AKCNS.IS', 'AKFGY.IS', 'AKSA.IS', 'AKSEN.IS', 'ALARK.IS', 'ALBRK.IS',
    'ALFAS.IS', 'ASGYO.IS', 'ASELS.IS', 'ASTOR.IS', 'BERA.IS', 'BIENY.IS', 'BIMAS.IS', 'BRKVY.IS', 'BRYAT.IS', 'BUCIM.IS',
    'CCOLA.IS', 'CANTE.IS', 'CWENE.IS', 'CIMSA.IS', 'DOHOL.IS', 'DOAS.IS', 'ECILC.IS', 'ECGYO.IS', 'ENJSA.IS', 'ENKAI.IS',
    'EREGL.IS', 'EUPWR.IS', 'EUREN.IS', 'FROTO.IS', 'GARAN.IS', 'GENIL.IS', 'GESAN.IS', 'GUBRF.IS', 'GWIND.IS', 'HALKB.IS',
    'HEKTS.IS', 'IPEKE.IS', 'ISCTR.IS', 'ISGYO.IS', 'ISMEN.IS', 'IZENR.IS', 'KCHOL.IS', 'KCAER.IS', 'KARSN.IS', 'KARTN.IS',
    'KLSER.IS', 'KMPUR.IS', 'KONTR.IS', 'KONYA.IS', 'KOZAL.IS', 'KOZAA.IS', 'KRDMD.IS', 'KZBGY.IS', 'MAVI.IS', 'MGROS.IS',
    'MIATK.IS', 'ODAS.IS', 'OTKAR.IS', 'OYAKC.IS', 'PENTI.IS', 'PETKM.IS', 'PGSUS.IS', 'PSGYO.IS', 'QUAGR.IS', 'SAHOL.IS',
    'SASA.IS', 'SMRTG.IS', 'SKBNK.IS', 'SNGYO.IS', 'SOKM.IS', 'TABGD.IS', 'TAVHL.IS', 'TCELL.IS', 'THYAO.IS', 'TKFEN.IS',
    'TOASO.IS', 'TSKB.IS', 'TTKOM.IS', 'TTRAK.IS', 'TUKAS.IS', 'TUPRS.IS', 'ULKER.IS', 'VAKBN.IS', 'VESTL.IS', 'YKBNK.IS',
    'YYAPI.IS', 'ZOREN.IS'
]

def analyze_stock(symbol):
    try:
        # Hisse senedini yfinance üzerinden çek
        ticker = yf.Ticker(symbol)
        try:
            info = ticker.info or {}
        except Exception:
            info = {}
        
        # Günlük fiyat geçmişini çek (Son 6 ay, hacim ortalaması için yeterli)
        try:
            df = ticker.history(period="6mo")
        except Exception as he:
            print(f"{symbol} geçmiş verisi çekilemedi: {he}")
            return None
        
        if df is None or df.empty or len(df) < 60:
            return None
            
        # 1. Teknik Analiz (RSI ve Hacim)
        # RSI hesaplama
        df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
        
        # 60 günlük hacim ortalaması (yaklaşık 3 ay)
        df['Volume_MA60'] = df['Volume'].rolling(window=60).mean()
        
        # 5, 20 ve 50 günlük basit hareketli ortalamalar (Haftalık, Aylık ve Ana Trend için)
        df['SMA5'] = ta.trend.sma_indicator(df['Close'], window=5)
        df['SMA20'] = ta.trend.sma_indicator(df['Close'], window=20)
        df['SMA50'] = ta.trend.sma_indicator(df['Close'], window=50)
        
        # Son günün verilerini al
        last_day = df.iloc[-1]
        prev_day = df.iloc[-2]
        
        current_price = last_day['Close']
        current_rsi = last_day['RSI']
        current_volume = last_day['Volume']
        volume_ma60 = last_day['Volume_MA60']
        current_sma5 = last_day['SMA5']
        current_sma20 = last_day['SMA20']
        current_sma50 = last_day['SMA50']
        price_up = current_price > prev_day['Close']
        prev_sma5 = prev_day['SMA5']
        prev_sma20 = prev_day['SMA20']
        
        # 2. Temel Analiz Verileri
        # yfinance'den temel rasyoları güvenli bir şekilde al
        pb_ratio = info.get('priceToBook') # PD/DD
        pe_ratio = info.get('trailingPE')  # F/K
        div_yield = info.get('dividendYield') # Temettü Verimi (0.1 = %10)
        
        if div_yield is not None:
            # yfinance bazen 0.14 (yani %14) bazen de direkt 14.0 döndürebiliyor.
            if div_yield < 1.0:
                div_yield = div_yield * 100
            
        # Fiyat geçmişini grafik için hazırla
        history_dates = df.index.strftime('%Y-%m-%d').tolist()
        history_prices = df['Close'].round(2).tolist()

        # Tüm analiz sonuçlarını tek bir sözlükte (dict) topla
        raw_data = {
            "symbol": symbol.replace('.IS', ''),
            "price": current_price,
            "rsi": current_rsi,
            "volume": current_volume,
            "pb_ratio": pb_ratio,
            "pe_ratio": pe_ratio,
            "div_yield": div_yield,
            "signals": "", # Aşağıda doldurulacak
            "history_dates": history_dates,
            "history_prices": history_prices
        }
        
        # 3. Sinyal Şartlarını Kontrol Et
        signals = []
        signal_names = []
        
        # Sinyal 1: Değer (Ucuzluk) Avcısı Sinyali (Uzun Vade)
        # PD/DD <= 1 VE RSI < 30
        if pb_ratio is not None and pb_ratio <= 1.0 and current_rsi is not None and current_rsi < 30:
            sig = {
                "symbol": symbol,
                "type": "deger_avcisi",
                "name": "Değer Avcısı",
                "timeframe_key": "LONG",
                "timeframe_label": "💎 Uzun Vade (Değer)",
                "target_return": "%15 - %30+",
                "risk_level": "Düşük / Orta",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2) if current_rsi else None,
                "message": f"🚨 Değer Avcısı: {symbol.replace('.IS', '')} temel olarak ucuz (PD/DD: {pb_ratio:.2f}) ve teknik olarak aşırı satım bölgesinde (RSI: {current_rsi:.2f}). İncelemeye değer!"
            }
            signals.append(sig)
            signal_names.append("Değer Avcısı")
            
        # Sinyal 2: Dönüş ve Hacim Onayı Sinyali (Kısa Vade)
        # Kapanış artıda VE işlem hacmi 3 aylık ortalamanın üzerinde
        if price_up and current_volume > volume_ma60:
            sig = {
                "symbol": symbol,
                "type": "hacim_onayi",
                "name": "Hacim Patlaması",
                "timeframe_key": "SHORT",
                "timeframe_label": "⚡ Kısa Vade (1-7 Gün)",
                "target_return": "%3 - %7",
                "risk_level": "Orta",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2) if current_rsi else None,
                "message": f"🔥 Hacim Patlaması: {symbol.replace('.IS', '')} artan hacimle yükselişe geçti. Olası bir trend dönüşü (onayı) olabilir."
            }
            signals.append(sig)
            signal_names.append("Hacim Patlaması")
            
        # Sinyal 3: Uzun Vadeli Temettü Kalesi Sinyali (Uzun Vade)
        # Temettü > %5 VE F/K < 15
        if div_yield is not None and div_yield > 5.0 and pe_ratio is not None and pe_ratio < 15.0:
            sig = {
                "symbol": symbol,
                "type": "temettu_kalesi",
                "name": "Temettü Kalesi",
                "timeframe_key": "LONG",
                "timeframe_label": "💎 Uzun Vade (Temettü)",
                "target_return": "%10 - %25+",
                "risk_level": "Düşük",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2) if current_rsi else None,
                "message": f"🏦 Temettü Kalesi: {symbol.replace('.IS', '')} yüksek temettü verimine sahip (%{div_yield:.2f}) ve F/K oranı makul ({pe_ratio:.2f})."
            }
            signals.append(sig)
            signal_names.append("Temettü Kalesi")
            
        # Sinyal 4: Haftalık Al-Sat (Kısa Vade: 1-7 Gün)
        # Şartlar: SMA 5 kırılımı + Hacim onayı + RSI (50-70 arası) + Ana Trend (Fiyat > SMA50)
        sma5_cross_up = (prev_day['Close'] < prev_sma5) and (current_price > current_sma5)
        trend_ok = current_price > current_sma50
        rsi_ok = current_rsi is not None and (50 < current_rsi < 70)
        
        if sma5_cross_up and current_volume > (volume_ma60 * 0.8) and trend_ok and rsi_ok:
            sig = {
                "symbol": symbol,
                "type": "al_sat_haftalik",
                "name": "Haftalık Al-Sat",
                "timeframe_key": "SHORT",
                "timeframe_label": "⚡ Kısa Vade (1-7 Gün)",
                "target_return": "%2.5 - %5",
                "risk_level": "Orta / Yüksek",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2) if current_rsi else None,
                "message": f"⚡ Haftalık Al-Sat: {symbol.replace('.IS', '')} fiyatı 5 günlük ortalamasını hacimli kesti (RSI: {current_rsi:.1f}, Ana Trend: Pozitif). Hedef: %2.5 - %5."
            }
            signals.append(sig)
            signal_names.append("Haftalık Al-Sat")
            
        # Sinyal 5: Aylık Al-Sat (Orta Vade: 1-4 Hafta)
        # Şartlar: SMA 20 kırılımı + Hacim onayı + RSI (50-70 arası) + Ana Trend (Fiyat > SMA50)
        sma20_cross_up = (prev_day['Close'] < prev_sma20) and (current_price > current_sma20)
        if sma20_cross_up and current_volume > volume_ma60 and trend_ok and rsi_ok:
            sig = {
                "symbol": symbol,
                "type": "al_sat_aylik",
                "name": "Aylık Al-Sat",
                "timeframe_key": "MEDIUM",
                "timeframe_label": "📈 Orta Vade (1-4 Hafta)",
                "target_return": "%5 - %12",
                "risk_level": "Orta",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2) if current_rsi else None,
                "message": f"🚀 Aylık Al-Sat: {symbol.replace('.IS', '')} fiyatı 20 günlük ortalamasını kırarak yükselişe geçti (RSI: {current_rsi:.1f}, Ana Trend: Pozitif). Hedef: %5 - %12."
            }
            signals.append(sig)
            signal_names.append("Aylık Al-Sat")
            
        raw_data['signals'] = ", ".join(signal_names)
        raw_data['signal_details'] = signals
            
        return {"signals": signals, "raw_data": raw_data}
        
    except Exception as e:
        print(f"{symbol} analiz edilirken hata: {e}")
        return None

def run_analysis():
    print("BIST hisseleri analiz ediliyor...")
    from database import save_stock_data, save_signals
    
    all_signals = []
    all_raw_data = []
    
    for symbol in BIST_SYMBOLS:
        print(f"İnceleniyor: {symbol}")
        result = analyze_stock(symbol)
        if result:
            if result["signals"]:
                all_signals.extend(result["signals"])
            if result["raw_data"]:
                all_raw_data.append(result["raw_data"])
        time.sleep(1) # API limitlerine takılmamak için kısa bekleme
        
    # SQLite'a kaydet
    if all_raw_data:
        save_stock_data(all_raw_data)
        print(f"{len(all_raw_data)} hissenin verileri SQLite veritabanına kaydedildi.")
        
    if all_signals:
        save_signals(all_signals)
        print(f"{len(all_signals)} adet sinyal geçmişe kaydedildi.")
        
    return all_signals

if __name__ == "__main__":
    import sys
    import io
    
    # Haber analizi için import
    try:
        from sentiment import analyze_sentiment
    except ImportError:
        analyze_sentiment = None

    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        
    results = run_analysis()
    if results:
        print("\n" + "="*50)
        print("SİNYALLER VE YAPAY ZEKA HABER ANALİZLERİ")
        print("="*50)
        for r in results:
            print(f"\n{r['message']}")
            
            # Eğer sentiment modülü yüklüyse ve çalışıyorsa analiz yap
            if analyze_sentiment:
                sent = analyze_sentiment(r['symbol'])
                if sent and sent.get('status') not in ['error', 'neutral']:
                    color = "\033[92m" if sent['status'] == 'OLUMLU' else "\033[91m" if sent['status'] == 'OLUMSUZ' else "\033[0m"
                    reset = "\033[0m"
                    print(f"🤖 Yapay Zeka Haber Yorumu: {color}{sent['status']}{reset}")
                    print(f"📰 Haber: {sent.get('title')}")
        print("\n" + "="*50)
    else:
        print("Şu an için şartları sağlayan hisse bulunamadı.")
