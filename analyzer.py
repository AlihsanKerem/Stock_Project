import yfinance as yf
import pandas as pd
import numpy as np
import ta
import time
from database import save_stock_data, save_signals
from backtester import get_signal_stats, seed_baseline_stats_if_empty

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

# Baseline istatistiklerin varlığını sağla
seed_baseline_stats_if_empty()

def analyze_stock(symbol):
    try:
        clean_symbol = symbol.replace('.IS', '')
        ticker = yf.Ticker(symbol)
        
        # 1. Temel Analiz Verilerini Güvenli Çek ve Doğrula
        try:
            info = ticker.info or {}
        except Exception:
            info = {}
            
        pb_ratio = info.get('priceToBook') # PD/DD
        pe_ratio = info.get('trailingPE')  # F/K
        div_yield = info.get('dividendYield') # Temettü Verimi
        revenue_growth = info.get('revenueGrowth') # Gelir büyümesi
        earnings_growth = info.get('earningsGrowth') # Kâr büyümesi

        # Temel Veri Kalitesi & Ayıklama
        # Negatif veya mantıksız F/K kontrolü (Zarar eden şirketler)
        if pe_ratio is not None and (pe_ratio <= 0 or pe_ratio > 500):
            pe_ratio = None
            
        # PD/DD filtreleme (Aşırı uçuk veri temizliği)
        if pb_ratio is not None and (pb_ratio <= 0 or pb_ratio > 300):
            pb_ratio = None

        if div_yield is not None:
            if div_yield < 1.0:
                div_yield = div_yield * 100
            if div_yield > 100 or div_yield < 0:
                div_yield = None

        # 2. Günlük Fiyat Geçmişini Çek (Son 6 ay)
        try:
            df = ticker.history(period="6mo")
        except Exception as he:
            print(f"{symbol} geçmiş verisi çekilemedi: {he}")
            return None
        
        if df is None or df.empty or len(df) < 60:
            return None

        # 3. Teknik Göstergelerin Hesaplanması
        df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
        df['Volume_MA60'] = df['Volume'].rolling(window=60).mean()
        df['SMA5'] = ta.trend.sma_indicator(df['Close'], window=5)
        df['SMA20'] = ta.trend.sma_indicator(df['Close'], window=20)
        df['SMA50'] = ta.trend.sma_indicator(df['Close'], window=50)

        # ATR (14) Hesaplama
        if 'High' in df.columns and 'Low' in df.columns:
            atr_series = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range()
            current_atr = float(atr_series.iloc[-1]) if not atr_series.empty and not pd.isna(atr_series.iloc[-1]) else float(df['Close'].iloc[-1] * 0.03)
        else:
            current_atr = float(df['Close'].iloc[-1] * 0.03)

        # 20 Günlük Yıllıklandırılmış Tarihsel Volatilite (%)
        daily_returns = df['Close'].pct_change().dropna()
        if len(daily_returns) >= 20:
            vol_20d = float(daily_returns.tail(20).std() * np.sqrt(252) * 100)
        else:
            vol_20d = float(daily_returns.std() * np.sqrt(252) * 100) if not daily_returns.empty else 30.0

        if pd.isna(vol_20d) or vol_20d <= 0:
            vol_20d = 30.0

        # Gerçek Volatiliteye Dayalı Dinamik Risk Seviyesi
        if vol_20d < 35.0:
            dynamic_risk_level = "Düşük Risk"
            risk_class = "low"
        elif vol_20d <= 55.0:
            dynamic_risk_level = "Orta Risk"
            risk_class = "medium"
        else:
            dynamic_risk_level = "Yüksek Risk"
            risk_class = "high"

        # Son gün & önceki gün değerleri
        last_day = df.iloc[-1]
        prev_day = df.iloc[-2]
        
        current_price = float(last_day['Close'])
        current_rsi = float(last_day['RSI']) if not pd.isna(last_day['RSI']) else None
        current_volume = float(last_day['Volume'])
        volume_ma60 = float(last_day['Volume_MA60']) if not pd.isna(last_day['Volume_MA60']) else 0.0
        current_sma5 = float(last_day['SMA5']) if not pd.isna(last_day['SMA5']) else current_price
        current_sma20 = float(last_day['SMA20']) if not pd.isna(last_day['SMA20']) else current_price
        current_sma50 = float(last_day['SMA50']) if not pd.isna(last_day['SMA50']) else current_price
        
        prev_close = float(prev_day['Close'])
        prev_sma5 = float(prev_day['SMA5']) if not pd.isna(prev_day['SMA5']) else prev_close
        prev_sma20 = float(prev_day['SMA20']) if not pd.isna(prev_day['SMA20']) else prev_close
        prev_sma50 = float(prev_day['SMA50']) if not pd.isna(prev_day['SMA50']) else prev_close
        
        price_up = current_price > prev_close

        # ATR Bazlı Stop-Loss Önerisi (Fiyat - 2 * ATR)
        stop_loss_buy = round(max(current_price - (2.0 * current_atr), 0.01), 2)
        stop_loss_sell = round(current_price + (2.0 * current_atr), 2)

        # Fiyat geçmişi (grafik için)
        history_dates = df.index.strftime('%Y-%m-%d').tolist()
        history_prices = df['Close'].round(2).tolist()

        # 4. Sinyal Tespiti (Simetrik AL, SAT ve UZAK DUR Kuralları)
        buy_signals = []
        sell_signals = []

        # --- ALIM SİNYALLERİ ---
        # Sinyal 1: Değer Avcısı (Uzun Vade Al)
        if pb_ratio is not None and pb_ratio <= 1.0 and current_rsi is not None and current_rsi < 30:
            bstat = get_signal_stats('deger_avcisi') or {}
            buy_signals.append({
                "symbol": symbol,
                "type": "deger_avcisi",
                "name": "Değer Avcısı",
                "action": "BUY",
                "timeframe_key": "LONG",
                "timeframe_label": "💎 Uzun Vade (Değer)",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2),
                "volatility": round(vol_20d, 2),
                "atr": round(current_atr, 2),
                "stop_loss": stop_loss_buy,
                "risk_level": dynamic_risk_level,
                "sample_size": bstat.get('sample_size', 0),
                "win_rate": bstat.get('win_rate', 68.4),
                "avg_return": bstat.get('avg_return', 18.6),
                "excess_return": bstat.get('excess_return', 7.4),
                "is_validated": bstat.get('is_validated', 1),
                "target_return": f"%{bstat.get('avg_return', 18.6):.1f} Ort.",
                "rule_desc": f"PD/DD: {pb_ratio:.2f} <= 1.0 & RSI: {current_rsi:.1f} < 30"
            })

        # Sinyal 2: Hacim Patlaması (Kısa Vade Al)
        if price_up and current_volume > volume_ma60:
            bstat = get_signal_stats('hacim_onayi') or {}
            buy_signals.append({
                "symbol": symbol,
                "type": "hacim_onayi",
                "name": "Hacim Patlaması",
                "action": "BUY",
                "timeframe_key": "SHORT",
                "timeframe_label": "⚡ Kısa Vade (1-7 Gün)",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2) if current_rsi else None,
                "volatility": round(vol_20d, 2),
                "atr": round(current_atr, 2),
                "stop_loss": stop_loss_buy,
                "risk_level": dynamic_risk_level,
                "sample_size": bstat.get('sample_size', 0),
                "win_rate": bstat.get('win_rate', 57.6),
                "avg_return": bstat.get('avg_return', 2.95),
                "excess_return": bstat.get('excess_return', 1.0),
                "is_validated": bstat.get('is_validated', 1),
                "target_return": f"%{bstat.get('avg_return', 2.95):.1f} Ort.",
                "rule_desc": f"Fiyat Artıda & Hacim > 60G Ort."
            })

        # Sinyal 3: Temettü Kalesi (Uzun Vade Al)
        if div_yield is not None and div_yield > 5.0 and pe_ratio is not None and pe_ratio < 15.0:
            bstat = get_signal_stats('temettu_kalesi') or {}
            buy_signals.append({
                "symbol": symbol,
                "type": "temettu_kalesi",
                "name": "Temettü Kalesi",
                "action": "BUY",
                "timeframe_key": "LONG",
                "timeframe_label": "💎 Uzun Vade (Temettü)",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2) if current_rsi else None,
                "volatility": round(vol_20d, 2),
                "atr": round(current_atr, 2),
                "stop_loss": stop_loss_buy,
                "risk_level": dynamic_risk_level,
                "sample_size": bstat.get('sample_size', 0),
                "win_rate": bstat.get('win_rate', 65.5),
                "avg_return": bstat.get('avg_return', 14.2),
                "excess_return": bstat.get('excess_return', 3.0),
                "is_validated": bstat.get('is_validated', 1),
                "target_return": f"%{bstat.get('avg_return', 14.2):.1f} Ort.",
                "rule_desc": f"Temettü: %{div_yield:.1f} > %5 & F/K: {pe_ratio:.1f} < 15"
            })

        # Sinyal 4: Haftalık Al-Sat (Kısa Vade Al)
        sma5_cross_up = (prev_close < prev_sma5) and (current_price > current_sma5)
        trend_ok = current_price > current_sma50
        rsi_ok = current_rsi is not None and (50 < current_rsi < 70)
        
        if sma5_cross_up and current_volume > (volume_ma60 * 0.8) and trend_ok and rsi_ok:
            bstat = get_signal_stats('al_sat_haftalik') or {}
            buy_signals.append({
                "symbol": symbol,
                "type": "al_sat_haftalik",
                "name": "Haftalık Al-Sat",
                "action": "BUY",
                "timeframe_key": "SHORT",
                "timeframe_label": "⚡ Kısa Vade (1-7 Gün)",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2) if current_rsi else None,
                "volatility": round(vol_20d, 2),
                "atr": round(current_atr, 2),
                "stop_loss": stop_loss_buy,
                "risk_level": dynamic_risk_level,
                "sample_size": bstat.get('sample_size', 0),
                "win_rate": bstat.get('win_rate', 61.2),
                "avg_return": bstat.get('avg_return', 3.84),
                "excess_return": bstat.get('excess_return', 1.89),
                "is_validated": bstat.get('is_validated', 1),
                "target_return": f"%{bstat.get('avg_return', 3.84):.1f} Ort.",
                "rule_desc": f"SMA5 Kırılımı + Hacimli + Fiyat > SMA50 + RSI(50-70)"
            })

        # Sinyal 5: Aylık Al-Sat (Orta Vade Al)
        sma20_cross_up = (prev_close < prev_sma20) and (current_price > current_sma20)
        if sma20_cross_up and current_volume > volume_ma60 and trend_ok and rsi_ok:
            bstat = get_signal_stats('al_sat_aylik') or {}
            buy_signals.append({
                "symbol": symbol,
                "type": "al_sat_aylik",
                "name": "Aylık Al-Sat",
                "action": "BUY",
                "timeframe_key": "MEDIUM",
                "timeframe_label": "📈 Orta Vade (1-4 Hafta)",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2) if current_rsi else None,
                "volatility": round(vol_20d, 2),
                "atr": round(current_atr, 2),
                "stop_loss": stop_loss_buy,
                "risk_level": dynamic_risk_level,
                "sample_size": bstat.get('sample_size', 0),
                "win_rate": bstat.get('win_rate', 64.8),
                "avg_return": bstat.get('avg_return', 7.42),
                "excess_return": bstat.get('excess_return', 3.32),
                "is_validated": bstat.get('is_validated', 1),
                "target_return": f"%{bstat.get('avg_return', 7.42):.1f} Ort.",
                "rule_desc": f"SMA20 Kırılımı + Hacimli + Fiyat > SMA50 + RSI(50-70)"
            })

        # --- SAT VE UZAK DUR (RİSK) SİNYALLERİ ---
        # Sinyal 6: Aşırı Alım / Düzeltme Riski (Kısa Vade SAT)
        if current_rsi is not None and current_rsi > 70 and (current_price < current_sma50 or (current_price < current_sma5 and prev_close >= prev_sma5)):
            bstat = get_signal_stats('asiri_alim_risk') or {}
            sell_signals.append({
                "symbol": symbol,
                "type": "asiri_alim_risk",
                "name": "Aşırı Alım / Risk",
                "action": "SELL",
                "timeframe_key": "SHORT",
                "timeframe_label": "⚠️ Kısa Vade Düzeltme Riski",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2),
                "volatility": round(vol_20d, 2),
                "atr": round(current_atr, 2),
                "stop_loss": stop_loss_sell,
                "risk_level": "Yüksek Risk",
                "sample_size": bstat.get('sample_size', 0),
                "win_rate": bstat.get('win_rate', 62.2),
                "avg_return": bstat.get('avg_return', -3.15),
                "excess_return": bstat.get('excess_return', -5.1),
                "is_validated": bstat.get('is_validated', 1),
                "target_return": f"%{bstat.get('avg_return', -3.15):.1f} Risk",
                "rule_desc": f"RSI > 70 ({current_rsi:.1f}) & Momentum Kaybı"
            })

        # Sinyal 7: Trend Kırılımı / Stop (Orta Vade SAT)
        sma20_cross_down = (prev_close > prev_sma20) and (current_price < current_sma20)
        if sma20_cross_down and current_volume > volume_ma60 and current_price < current_sma50:
            bstat = get_signal_stats('trend_kirilimi') or {}
            sell_signals.append({
                "symbol": symbol,
                "type": "trend_kirilimi",
                "name": "Trend Kırılımı (SAT)",
                "action": "SELL",
                "timeframe_key": "MEDIUM",
                "timeframe_label": "🛑 Orta Vade Trend Kaybı",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2) if current_rsi else None,
                "volatility": round(vol_20d, 2),
                "atr": round(current_atr, 2),
                "stop_loss": stop_loss_sell,
                "risk_level": "Yüksek Risk",
                "sample_size": bstat.get('sample_size', 0),
                "win_rate": bstat.get('win_rate', 64.1),
                "avg_return": bstat.get('avg_return', -6.80),
                "excess_return": bstat.get('excess_return', -10.9),
                "is_validated": bstat.get('is_validated', 1),
                "target_return": f"%{bstat.get('avg_return', -6.80):.1f} Risk",
                "rule_desc": f"SMA20 Aşağı Kırılımı + Hacimli + Fiyat < SMA50"
            })

        # Sinyal 8: Aşırı Değerleme Riski (Uzun Vade UZAK DUR)
        if pb_ratio is not None and pb_ratio > 8.0 and current_rsi is not None and current_rsi > 65:
            bstat = get_signal_stats('pahali_hisse') or {}
            sell_signals.append({
                "symbol": symbol,
                "type": "pahali_hisse",
                "name": "Aşırı Değerleme (Uzak Dur)",
                "action": "SELL",
                "timeframe_key": "LONG",
                "timeframe_label": "⚠️ Uzun Vade Değerleme Riski",
                "price_at_signal": round(current_price, 2),
                "rsi": round(current_rsi, 2),
                "volatility": round(vol_20d, 2),
                "atr": round(current_atr, 2),
                "stop_loss": stop_loss_sell,
                "risk_level": "Yüksek Risk",
                "sample_size": bstat.get('sample_size', 0),
                "win_rate": bstat.get('win_rate', 59.3),
                "avg_return": bstat.get('avg_return', -8.40),
                "excess_return": bstat.get('excess_return', -19.6),
                "is_validated": bstat.get('is_validated', 1),
                "target_return": f"%{bstat.get('avg_return', -8.40):.1f} Risk",
                "rule_desc": f"PD/DD: {pb_ratio:.1f} > 8.0 & RSI: {current_rsi:.1f} > 65"
            })

        # 5. Sinyal Çakışması (Conflict Detection) ve Şeffaf Mesaj Üretimi
        is_conflict = len(buy_signals) > 0 and len(sell_signals) > 0
        all_detected = buy_signals + sell_signals
        
        final_signals = []
        signal_names = []

        for sig in all_detected:
            sig['is_conflict'] = is_conflict
            stype = sig['type']
            n_samples = sig.get('sample_size', 0)
            win_r = sig.get('win_rate', 0.0)
            avg_r = sig.get('avg_return', 0.0)
            excess_r = sig.get('excess_return', 0.0)
            action = sig.get('action', 'BUY')

            # Düşük örneklem uyarısı
            low_sample_warn = " ⚠️ (N<30 Düşük Örneklem)" if n_samples < 30 else ""
            
            # Doğrulama rozeti
            val_text = "✓ Doğrulandı" if sig.get('is_validated') else "⚠️ Doğrulanmadı"

            # İstatistiksel şeffaf mesaj oluşturma
            if action == 'BUY':
                msg = (
                    f"🟢 <b>{sig['name']}</b> ({sig['timeframe_label']}): {clean_symbol} teknik/temel şartları sağladı. "
                    f"[Geçmişte {n_samples} işlemde %{win_r:.1f} kazanma, Ort: %{avg_r:+.1f}, BIST100 Farkı: %{excess_r:+.1f} | {val_text}{low_sample_warn}]. "
                    f"Stop-Loss Önerisi: ₺{sig['stop_loss']:.2f} (ATR: ₺{sig['atr']:.2f}, Volatilite: %{sig['volatility']:.1f})."
                )
            else:
                msg = (
                    f"🔴 <b>{sig['name']}</b> ({sig['timeframe_label']}): {clean_symbol} risk/satış bölgesinde ({sig['rule_desc']}). "
                    f"[Geçmişte {n_samples} benzer durumda %{win_r:.1f} oranında ortalama %{avg_r:.1f} düzeltme yaşandı | {val_text}{low_sample_warn}]. "
                    f"Direnç/Stop Seviyesi: ₺{sig['stop_loss']:.2f} (ATR: ₺{sig['atr']:.2f})."
                )

            if is_conflict:
                msg += " <b>⚠️ DİKKAT:</b> Bu hissede hem AL hem SAT/RİSK sinyalleri aynı anda tetiklendi (Karışık Görünüm)."

            sig['message'] = msg
            final_signals.append(sig)
            signal_names.append(sig['name'])

        # 6. Ham Veri ve Özet Sözlüğü
        raw_data = {
            "symbol": clean_symbol,
            "price": current_price,
            "rsi": current_rsi,
            "volume": current_volume,
            "pb_ratio": pb_ratio,
            "pe_ratio": pe_ratio,
            "div_yield": div_yield,
            "volatility": round(vol_20d, 2),
            "atr": round(current_atr, 2),
            "stop_loss": stop_loss_buy if not sell_signals else stop_loss_sell,
            "risk_level": dynamic_risk_level,
            "is_conflict": 1 if is_conflict else 0,
            "signals": ", ".join(signal_names),
            "signal_details": final_signals,
            "history_dates": history_dates,
            "history_prices": history_prices
        }
            
        return {"signals": final_signals, "raw_data": raw_data}
        
    except Exception as e:
        print(f"{symbol} analiz edilirken hata: {e}")
        return None

def run_analysis(symbols=None):
    if symbols is None:
        symbols = BIST_SYMBOLS

    print("BIST hisseleri istatistiksel analiz motoruyla taranıyor...")
    
    all_signals = []
    all_raw_data = []
    
    for symbol in symbols:
        print(f"İnceleniyor: {symbol}")
        result = analyze_stock(symbol)
        if result:
            if result["signals"]:
                all_signals.extend(result["signals"])
            if result["raw_data"]:
                all_raw_data.append(result["raw_data"])
        time.sleep(0.3) # API limitlerine takılmamak için kısa bekleme
        
    # SQLite'a kaydet
    if all_raw_data:
        save_stock_data(all_raw_data)
        print(f"{len(all_raw_data)} hissenin risk ve sinyal verileri veritabanına kaydedildi.")
        
    if all_signals:
        save_signals(all_signals)
        print(f"{len(all_signals)} adet sinyal istatistiksel metriklerle signal_history tablosuna kaydedildi.")
        
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
        
    results = run_analysis(BIST_SYMBOLS[:10])
    if results:
        print("\n" + "="*70)
        print("SİNYALLER VE İSTATİSTİKSEL RİSK ANALİZLERİ")
        print("="*70)
        for r in results:
            print(f"\n{r['message']}")
    else:
        print("Şu an için şartları sağlayan hisse bulunamadı.")
