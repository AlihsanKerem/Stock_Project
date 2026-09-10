import yfinance as yf
import pandas as pd
import numpy as np
import ta
import time
from database import save_stock_data, save_signals
from backtester import get_signal_stats

# BIST 100 hisse senetleri listesi (404/delisted ECGYO, KOZAL, KOZAA, IPEKE, PENTI temizlendi)
BIST_SYMBOLS = [
    'AEFES.IS', 'AGHOL.IS', 'AHGAZ.IS', 'AKBNK.IS', 'AKCNS.IS', 'AKFGY.IS', 'AKSA.IS', 'AKSEN.IS', 'ALARK.IS', 'ALBRK.IS',
    'ALFAS.IS', 'ASGYO.IS', 'ASELS.IS', 'ASTOR.IS', 'BERA.IS', 'BIENY.IS', 'BIMAS.IS', 'BRKVY.IS', 'BRYAT.IS', 'BUCIM.IS',
    'CCOLA.IS', 'CANTE.IS', 'CWENE.IS', 'CIMSA.IS', 'DOHOL.IS', 'DOAS.IS', 'ECILC.IS', 'ENJSA.IS', 'ENKAI.IS',
    'EREGL.IS', 'EUPWR.IS', 'EUREN.IS', 'FROTO.IS', 'GARAN.IS', 'GENIL.IS', 'GESAN.IS', 'GUBRF.IS', 'GWIND.IS', 'HALKB.IS',
    'HEKTS.IS', 'ISCTR.IS', 'ISGYO.IS', 'ISMEN.IS', 'IZENR.IS', 'KCHOL.IS', 'KCAER.IS', 'KARSN.IS', 'KARTN.IS',
    'KLSER.IS', 'KMPUR.IS', 'KONTR.IS', 'KONYA.IS', 'KRDMD.IS', 'KZBGY.IS', 'MAVI.IS', 'MGROS.IS',
    'MIATK.IS', 'ODAS.IS', 'OTKAR.IS', 'OYAKC.IS', 'PETKM.IS', 'PGSUS.IS', 'PSGYO.IS', 'QUAGR.IS', 'SAHOL.IS',
    'SASA.IS', 'SMRTG.IS', 'SKBNK.IS', 'SNGYO.IS', 'SOKM.IS', 'TABGD.IS', 'TAVHL.IS', 'TCELL.IS', 'THYAO.IS', 'TKFEN.IS',
    'TOASO.IS', 'TSKB.IS', 'TTKOM.IS', 'TTRAK.IS', 'TUKAS.IS', 'TUPRS.IS', 'ULKER.IS', 'VAKBN.IS', 'VESTL.IS', 'YKBNK.IS',
    'YYAPI.IS', 'ZOREN.IS'
]

def make_signal_dict(symbol, stype, sname, action, tf_key, tf_label, current_price, current_rsi, vol_20d, current_atr, stop_loss, risk_level, rule_desc):
    """Sinyal objesini veritabanındaki gerçek backtest istatistikleriyle dinamik olarak oluşturur."""
    bstat = get_signal_stats(stype)
    
    if not bstat:
        return {
            "symbol": symbol,
            "type": stype,
            "name": sname,
            "action": action,
            "timeframe_key": tf_key,
            "timeframe_label": tf_label,
            "price_at_signal": round(current_price, 2),
            "rsi": round(current_rsi, 2) if current_rsi is not None else None,
            "volatility": round(vol_20d, 2) if vol_20d is not None else None,
            "atr": round(current_atr, 2) if current_atr is not None else None,
            "stop_loss": stop_loss,
            "risk_level": risk_level,
            "sample_size": 0,
            "win_rate": None,
            "avg_return": None,
            "gross_avg_return": None,
            "excess_return": None,
            "gross_excess_return": None,
            "p_value": None,
            "is_significant": 0,
            "alpha_label": "Hesaplanmadı",
            "is_validated": 0,
            "target_return": "Henüz Test Edilmedi",
            "rule_desc": rule_desc
        }
    
    sample_size = bstat.get('sample_size', 0)
    win_rate = bstat.get('win_rate')
    avg_return = bstat.get('avg_return')
    gross_avg_return = bstat.get('gross_avg_return', avg_return)
    excess_return = bstat.get('excess_return')
    gross_excess_return = bstat.get('gross_excess_return', excess_return)
    p_value = bstat.get('p_value')
    is_significant = bstat.get('is_significant', 0)
    alpha_label = bstat.get('alpha_label', 'Piyasadan Farksız')
    is_validated = bstat.get('is_validated', 0)

    if is_validated == 1:
        target_return = f"Net Alfa: %{excess_return:+.1f} (Ort: %{avg_return:+.1f})"
    elif alpha_label == "Yön Ters":
        target_return = f"⚠️ Yön Ters (%{avg_return:+.1f})"
    elif excess_return is not None:
        target_return = f"Alfa Yok (%{excess_return:+.1f})"
    else:
        target_return = "Hesaplanmadı"

    return {
        "symbol": symbol,
        "type": stype,
        "name": sname,
        "action": action,
        "timeframe_key": tf_key,
        "timeframe_label": tf_label,
        "price_at_signal": round(current_price, 2),
        "rsi": round(current_rsi, 2) if current_rsi is not None else None,
        "volatility": round(vol_20d, 2) if vol_20d is not None else None,
        "atr": round(current_atr, 2) if current_atr is not None else None,
        "stop_loss": stop_loss,
        "risk_level": risk_level,
        "sample_size": sample_size,
        "win_rate": win_rate,
        "avg_return": avg_return,
        "gross_avg_return": gross_avg_return,
        "excess_return": excess_return,
        "gross_excess_return": gross_excess_return,
        "p_value": p_value,
        "is_significant": is_significant,
        "alpha_label": alpha_label,
        "is_validated": is_validated,
        "target_return": target_return,
        "rule_desc": rule_desc
    }

def analyze_stock(symbol):
    try:
        clean_symbol = symbol.replace('.IS', '')
        ticker = yf.Ticker(symbol)
        
        try:
            info = ticker.info or {}
        except Exception:
            info = {}
            
        pb_ratio = info.get('priceToBook')
        pe_ratio = info.get('trailingPE')
        div_yield = info.get('dividendYield')

        if pe_ratio is not None and (pe_ratio <= 0 or pe_ratio > 500):
            pe_ratio = None
        if pb_ratio is not None and (pb_ratio <= 0 or pb_ratio > 300):
            pb_ratio = None
        if div_yield is not None:
            if div_yield < 1.0:
                div_yield = div_yield * 100
            if div_yield > 100 or div_yield < 0:
                div_yield = None

        try:
            df = ticker.history(period="6mo")
        except Exception:
            df = pd.DataFrame()

        if df.empty or len(df) < 50:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['SMA_5'] = df['Close'].rolling(window=5).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        df['Volume_MA60'] = df['Volume'].rolling(window=60).mean()
        df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
        df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
        df['Volatility_20d'] = df['Log_Ret'].rolling(window=20).std() * np.sqrt(252) * 100

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        current_price = float(last_row['Close'])
        prev_close = float(prev_row['Close'])
        current_volume = float(last_row['Volume'])
        volume_ma60 = float(last_row['Volume_MA60']) if not np.isnan(last_row['Volume_MA60']) else current_volume
        current_rsi = float(last_row['RSI']) if not np.isnan(last_row['RSI']) else None
        current_atr = float(last_row['ATR']) if not np.isnan(last_row['ATR']) else (current_price * 0.03)
        vol_20d = float(last_row['Volatility_20d']) if not np.isnan(last_row['Volatility_20d']) else 30.0

        current_sma5 = float(last_row['SMA_5']) if not np.isnan(last_row['SMA_5']) else current_price
        prev_sma5 = float(prev_row['SMA_5']) if not np.isnan(prev_row['SMA_5']) else prev_close
        current_sma20 = float(last_row['SMA_20']) if not np.isnan(last_row['SMA_20']) else current_price
        prev_sma20 = float(prev_row['SMA_20']) if not np.isnan(prev_row['SMA_20']) else prev_close
        current_sma50 = float(last_row['SMA_50']) if not np.isnan(last_row['SMA_50']) else current_price

        if vol_20d < 35.0:
            dynamic_risk_level = "Düşük Risk"
        elif vol_20d <= 55.0:
            dynamic_risk_level = "Orta Risk"
        else:
            dynamic_risk_level = "Yüksek Risk"

        price_up = current_price > prev_close
        stop_loss_buy = round(max(current_price - (2.0 * current_atr), 0.01), 2)
        stop_loss_sell = round(current_price + (2.0 * current_atr), 2)
        history_dates = df.index.strftime('%Y-%m-%d').tolist()
        history_prices = df['Close'].round(2).tolist()

        buy_signals = []
        sell_signals = []

        if pb_ratio is not None and pb_ratio <= 1.0 and current_rsi is not None and current_rsi < 30:
            buy_signals.append(make_signal_dict(symbol, "deger_avcisi", "Değer Avcısı", "BUY", "LONG", "💎 Uzun Vade (Değer)", current_price, current_rsi, vol_20d, current_atr, stop_loss_buy, dynamic_risk_level, f"PD/DD: {pb_ratio:.2f} <= 1.0 & RSI: {current_rsi:.1f} < 30"))

        if price_up and current_volume > volume_ma60:
            buy_signals.append(make_signal_dict(symbol, "hacim_onayi", "Hacim Patlaması", "BUY", "SHORT", "⚡ Kısa Vade (1-7 Gün)", current_price, current_rsi, vol_20d, current_atr, stop_loss_buy, dynamic_risk_level, "Fiyat Artıda & Hacim > 60G Ort."))

        if div_yield is not None and div_yield > 5.0 and pe_ratio is not None and pe_ratio < 15.0:
            buy_signals.append(make_signal_dict(symbol, "temettu_kalesi", "Temettü Kalesi", "BUY", "LONG", "💎 Uzun Vade (Temettü)", current_price, current_rsi, vol_20d, current_atr, stop_loss_buy, dynamic_risk_level, f"Temettü: %{div_yield:.1f} > %5 & F/K: {pe_ratio:.1f} < 15"))

        sma5_cross_up = (prev_close < prev_sma5) and (current_price > current_sma5)
        trend_ok = current_price > current_sma50
        rsi_ok = current_rsi is not None and (50 < current_rsi < 70)
        
        if sma5_cross_up and current_volume > (volume_ma60 * 0.8) and trend_ok and rsi_ok:
            buy_signals.append(make_signal_dict(symbol, "al_sat_haftalik", "Haftalık Al-Sat", "BUY", "SHORT", "⚡ Kısa Vade (1-7 Gün)", current_price, current_rsi, vol_20d, current_atr, stop_loss_buy, dynamic_risk_level, "SMA5 Kırılımı + Hacimli + Fiyat > SMA50 + RSI(50-70)"))

        sma20_cross_up = (prev_close < prev_sma20) and (current_price > current_sma20)
        if sma20_cross_up and current_volume > volume_ma60 and trend_ok and rsi_ok:
            buy_signals.append(make_signal_dict(symbol, "al_sat_aylik", "Aylık Al-Sat", "BUY", "MEDIUM", "📈 Orta Vade (1-4 Hafta)", current_price, current_rsi, vol_20d, current_atr, stop_loss_buy, dynamic_risk_level, "SMA20 Kırılımı + Hacimli + Fiyat > SMA50 + RSI(50-70)"))

        if current_rsi is not None and current_rsi > 70 and (current_price < current_sma50 or (current_price < current_sma5 and prev_close >= prev_sma5)):
            sell_signals.append(make_signal_dict(symbol, "asiri_alim_risk", "Aşırı Alım / Risk", "SELL", "SHORT", "⚠️ Kısa Vade Düzeltme Riski", current_price, current_rsi, vol_20d, current_atr, stop_loss_sell, "Yüksek Risk", f"RSI > 70 ({current_rsi:.1f}) & Momentum Kaybı"))

        sma20_cross_down = (prev_close > prev_sma20) and (current_price < current_sma20)
        if sma20_cross_down and current_volume > volume_ma60 and current_price < current_sma50:
            sell_signals.append(make_signal_dict(symbol, "trend_kirilimi", "Trend Kırılımı (SAT)", "SELL", "MEDIUM", "🛑 Orta Vade Trend Kaybı", current_price, current_rsi, vol_20d, current_atr, stop_loss_sell, "Yüksek Risk", "SMA20 Aşağı Kırılımı + Hacimli + Fiyat < SMA50"))

        if pb_ratio is not None and pb_ratio > 8.0 and current_rsi is not None and current_rsi > 65:
            sell_signals.append(make_signal_dict(symbol, "pahali_hisse", "Aşırı Değerleme (Uzak Dur)", "SELL", "LONG", "⚠️ Uzun Vade Değerleme Riski", current_price, current_rsi, vol_20d, current_atr, stop_loss_sell, "Yüksek Risk", f"PD/DD: {pb_ratio:.1f} > 8.0 & RSI: {current_rsi:.1f} > 65"))

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
            is_val = sig.get('is_validated', 0)
            p_val = sig.get('p_value', 1.0)

            # Düşük örneklem ve Doğrulama Durumu
            if n_samples == 0 or win_r is None:
                msg = (
                    f"ℹ️ <b>{sig['name']}</b> ({sig['timeframe_label']}): {clean_symbol} teknik/temel tetiklenme koşulunu sağladı. "
                    f"⚠️ <i>Bu kurulumda backtest henüz çalıştırılmadığı için istatistikler henüz hesaplanmadı.</i> "
                    f"Stop-Loss: ₺{sig['stop_loss']:.2f} (ATR: ₺{sig['atr']:.2f}, Volatilite: %{sig['volatility']:.1f})."
                )
            else:
                low_sample_warn = " ⚠️ (N<30 Düşük Örneklem)" if n_samples < 30 else ""
                val_text = f"✓ Doğrulandı (p={p_val:.3f})" if is_val else f"⚠️ Doğrulanmadı / Güvensiz (p={p_val:.3f})"

                if is_val:
                    msg = (
                        f"🟢 <b>{sig['name']}</b> ({sig['timeframe_label']}): {clean_symbol} teknik/temel şartları sağladı. "
                        f"[Net Kazanma: %{win_r:.1f} | <b>Net Alfa: %{excess_r:+.1f}</b> | Net Ort Getiri: %{avg_r:+.1f} | {val_text}{low_sample_warn}]. "
                        f"Stop-Loss: ₺{sig['stop_loss']:.2f} (ATR: ₺{sig['atr']:.2f}, Volatilite: %{sig['volatility']:.1f})."
                    )
                else:
                    if action == 'SELL' and (avg_r or 0) >= 0:
                        msg = (
                            f"⚠️ <b>{sig['name']} (DOĞRULANMAMIŞ / YÖN TERS)</b>: {clean_symbol} risk bölgesinde ({sig['rule_desc']}) "
                            f"ancak geçmiş 5 yılda hisseler düşmek yerine net ortalama %{avg_r:+.1f} artış kaydetmiştir. "
                            f"[Düşüş Oranı: %{win_r:.1f} | {val_text}{low_sample_warn}]. Pozisyon kararı için önerilmez."
                        )
                    else:
                        msg = (
                            f"⚠️ <b>{sig['name']} (ALFA ÜRETMİYOR / GÜVENSİZ)</b>: {clean_symbol} şartları sağladı ancak maliyet sonrası BIST100'e göre "
                            f"anlamlı bir getiri avantajı sağlamamaktadır [Net Alfa: %{excess_r:+.1f}, Kazanma: %{win_r:.1f} | {val_text}{low_sample_warn}]."
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
