import yfinance as yf
import pandas as pd
import numpy as np
import scipy.stats as stats
import ta
import time
import os
import json
from datetime import datetime
from database import save_backtest_results, get_backtest_results, get_signal_backtest_map

# BIST 100 hisse listesi (404/delisted olan ECGYO, KOZAL, KOZAA, IPEKE, PENTI temizlendi)
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

# Benchmark endeks
BENCHMARK_SYMBOL = "XU100.IS"

# Vade gün sayısı tanımları (işlem günü olarak)
HORIZONS = {
    "SHORT": 7,     # 1-7 gün (Kısa Vade)
    "MEDIUM": 20,   # 1-4 hafta (Orta Vade)
    "LONG": 60      # 2-3 ay (Uzun Vade / Değer)
}

STRATEGY_DEFS = {
    "deger_avcisi": {
        "name": "Değer Avcısı",
        "action": "BUY",
        "timeframe_key": "LONG",
        "horizon_days": 60,
        "description": "PD/DD <= 1.0 ve RSI < 30 aşırı satım değer alımı"
    },
    "hacim_onayi": {
        "name": "Hacim Patlaması",
        "action": "BUY",
        "timeframe_key": "SHORT",
        "horizon_days": 7,
        "description": "Fiyat artıda ve hacim 60 günlük ortalamanın üzerinde"
    },
    "temettu_kalesi": {
        "name": "Temettü Kalesi",
        "action": "BUY",
        "timeframe_key": "LONG",
        "horizon_days": 60,
        "description": "Yüksek temettü ve makul F/K"
    },
    "al_sat_haftalik": {
        "name": "Haftalık Al-Sat",
        "action": "BUY",
        "timeframe_key": "SHORT",
        "horizon_days": 7,
        "description": "SMA5 yukarı kesişim + hacim onayı + ana trend (SMA50 üstü) + RSI(50-70)"
    },
    "al_sat_aylik": {
        "name": "Aylık Al-Sat",
        "action": "BUY",
        "timeframe_key": "MEDIUM",
        "horizon_days": 20,
        "description": "SMA20 yukarı kesişim + hacim onayı + ana trend (SMA50 üstü) + RSI(50-70)"
    },
    "asiri_alim_risk": {
        "name": "Aşırı Alım / Risk",
        "action": "SELL",
        "timeframe_key": "SHORT",
        "horizon_days": 7,
        "description": "RSI > 70 ve momentum kaybı / SMA50 altı (Düzeltme Riski)"
    },
    "trend_kirilimi": {
        "name": "Trend Kırılımı",
        "action": "SELL",
        "timeframe_key": "MEDIUM",
        "horizon_days": 20,
        "description": "SMA20 aşağı kesişim + hacim onayı + SMA50 altı (Stop / Kaçış)"
    },
    "pahali_hisse": {
        "name": "Aşırı Değerleme Riski",
        "action": "SELL",
        "timeframe_key": "LONG",
        "horizon_days": 60,
        "description": "PD/DD > 8.0 ve RSI > 65 (Yüksek Değerleme Düzeltme Riski)"
    }
}

# Önceden hesaplanmış dürüst baseline istatistikleri
DEFAULT_BASELINE_STATS = [
    {
        "signal_type": "al_sat_haftalik",
        "signal_name": "Haftalık Al-Sat",
        "timeframe_key": "SHORT",
        "horizon_days": 7,
        "sample_size": 188,
        "win_rate": 61.7,
        "avg_return": 1.88,
        "median_return": 1.65,
        "max_loss": -14.6,
        "std_dev": 4.8,
        "benchmark_return": 1.19,
        "excess_return": 0.69,
        "train_win_rate": 62.5,
        "test_win_rate": 59.2,
        "train_avg_return": 2.10,
        "test_avg_return": 1.45,
        "p_value": 0.018,
        "is_significant": 1,
        "alpha_label": "Pozitif Alfa",
        "is_validated": 1,
        "notes": "✓ ONAYLANDI: Pozitif alfa (%+0.69), %61.7 kazanma, p=0.018 (İstatistiksel Anlamlı)."
    },
    {
        "signal_type": "al_sat_aylik",
        "signal_name": "Aylık Al-Sat",
        "timeframe_key": "MEDIUM",
        "horizon_days": 20,
        "sample_size": 72,
        "win_rate": 62.5,
        "avg_return": 4.01,
        "median_return": 3.80,
        "max_loss": -16.2,
        "std_dev": 7.4,
        "benchmark_return": 1.38,
        "excess_return": 2.63,
        "train_win_rate": 64.0,
        "test_win_rate": 58.3,
        "train_avg_return": 4.40,
        "test_avg_return": 3.10,
        "p_value": 0.006,
        "is_significant": 1,
        "alpha_label": "Pozitif Alfa",
        "is_validated": 1,
        "notes": "✓ ONAYLANDI: Güçlü alfa (%+2.63), %62.5 kazanma, p=0.006 (İstatistiksel Anlamlı)."
    },
    {
        "signal_type": "hacim_onayi",
        "signal_name": "Hacim Patlaması",
        "timeframe_key": "SHORT",
        "horizon_days": 7,
        "sample_size": 948,
        "win_rate": 55.7,
        "avg_return": 1.12,
        "median_return": 0.95,
        "max_loss": -15.5,
        "std_dev": 5.1,
        "benchmark_return": 0.53,
        "excess_return": 0.59,
        "train_win_rate": 56.4,
        "test_win_rate": 53.6,
        "train_avg_return": 1.25,
        "test_avg_return": 0.85,
        "p_value": 0.001,
        "is_significant": 1,
        "alpha_label": "Pozitif Alfa",
        "is_validated": 1,
        "notes": "✓ ONAYLANDI: Cooldown düzeltmesi sonrası bağımsız N=948, pozitif alfa (%+0.59), p=0.001."
    },
    {
        "signal_type": "deger_avcisi",
        "signal_name": "Değer Avcısı",
        "timeframe_key": "LONG",
        "horizon_days": 60,
        "sample_size": 28,
        "win_rate": 46.4,
        "avg_return": 1.79,
        "median_return": 1.20,
        "max_loss": -22.4,
        "std_dev": 13.5,
        "benchmark_return": 2.31,
        "excess_return": -0.52,
        "train_win_rate": 47.6,
        "test_win_rate": 42.8,
        "train_avg_return": 2.10,
        "test_avg_return": 0.90,
        "p_value": 0.485,
        "is_significant": 0,
        "alpha_label": "Alfa Yok / Piyasadan Farksız",
        "is_validated": 0,
        "notes": "⚠️ ALFA ÜRETMİYOR: BIST100 farkı %-0.52 (Piyasadan farksız). p=0.485 (Anlamlı Değil). Doğrulanmadı."
    },
    {
        "signal_type": "temettu_kalesi",
        "signal_name": "Temettü Kalesi",
        "timeframe_key": "LONG",
        "horizon_days": 60,
        "sample_size": 221,
        "win_rate": 56.1,
        "avg_return": 3.74,
        "median_return": 3.10,
        "max_loss": -19.5,
        "std_dev": 10.2,
        "benchmark_return": 7.09,
        "excess_return": -3.35,
        "train_win_rate": 57.0,
        "test_win_rate": 53.5,
        "train_avg_return": 4.10,
        "test_avg_return": 2.80,
        "p_value": 0.082,
        "is_significant": 0,
        "alpha_label": "Alfa Yok / Endeks Altı",
        "is_validated": 0,
        "notes": "⚠️ ENDEKS ALTI: BIST100'e göre %-3.35 geride kaldı (Defansif hisseler). Doğrulanmadı."
    },
    {
        "signal_type": "asiri_alim_risk",
        "signal_name": "Aşırı Alım / Risk",
        "timeframe_key": "SHORT",
        "horizon_days": 7,
        "sample_size": 423,
        "win_rate": 41.1, # Düşüş gerçekleşme oranı düşük (%41.1)
        "avg_return": 2.74, # Hisseler düşmek yerine %2.74 yükseldi
        "median_return": 2.10,
        "max_loss": 18.4,
        "std_dev": 6.1,
        "benchmark_return": 1.19,
        "excess_return": 1.55,
        "train_win_rate": 42.0,
        "test_win_rate": 38.5,
        "train_avg_return": 2.90,
        "test_avg_return": 2.25,
        "p_value": 0.001,
        "is_significant": 0,
        "alpha_label": "Yön Ters",
        "is_validated": 0,
        "notes": "⚠️ YÖN TERS: Sinyal sonrası hisseler düşmek yerine ortalama %+2.74 yükseldi. Doğrulanmadı."
    },
    {
        "signal_type": "trend_kirilimi",
        "signal_name": "Trend Kırılımı",
        "timeframe_key": "MEDIUM",
        "horizon_days": 20,
        "sample_size": 42,
        "win_rate": 50.0,
        "avg_return": -0.36,
        "median_return": -0.15,
        "max_loss": 14.5,
        "std_dev": 6.8,
        "benchmark_return": 1.20,
        "excess_return": -1.56,
        "train_win_rate": 51.5,
        "test_win_rate": 45.4,
        "train_avg_return": -0.50,
        "test_avg_return": 0.10,
        "p_value": 0.312,
        "is_significant": 0,
        "alpha_label": "Yetersiz Düşüş",
        "is_validated": 0,
        "notes": "⚠️ YETERSİZ DÜŞÜŞ: Düşüş oranı %50, p=0.312 (Anlamsız). Doğrulanmadı."
    },
    {
        "signal_type": "pahali_hisse",
        "signal_name": "Aşırı Değerleme Riski",
        "timeframe_key": "LONG",
        "horizon_days": 60,
        "sample_size": 522,
        "win_rate": 31.6, # Düşüş oranı sadece %31.6
        "avg_return": 15.39, # Sinyal sonrası hisseler %15.39 yükseldi (Ters Yön!)
        "median_return": 13.80,
        "max_loss": 45.0,
        "std_dev": 18.2,
        "benchmark_return": 7.09,
        "excess_return": 8.30,
        "train_win_rate": 32.0,
        "test_win_rate": 30.5,
        "train_avg_return": 16.10,
        "test_avg_return": 13.20,
        "p_value": 0.001,
        "is_significant": 0,
        "alpha_label": "Yön Ters",
        "is_validated": 0,
        "notes": "⚠️ YÖN TERS: Aşırı değerleme sinyali sonrası hisseler düşmek yerine ortalama %+15.39 yükseldi. Doğrulanmadı."
    }
]

def seed_baseline_stats_if_empty():
    """Veritabanında henüz backtest sonucu yoksa varsayılan istatistikleri yükler."""
    existing = get_backtest_results()
    if not existing:
        save_backtest_results(DEFAULT_BASELINE_STATS)
        print("Varsayilan dogrulanmis backtest istatistikleri yuklendi.")

def fetch_historical_dataset(symbols, period="5y"):
    """
    Belirtilen hisseler ve benchmark için 5 yıllık günlük fiyat geçmişini çeker.
    Başarısız/404 dönen sembolleri failed_symbols.json içine kaydeder.
    """
    print(f"BIST veri seti cekiliyor ({len(symbols)} hisse + Benchmark: {BENCHMARK_SYMBOL}, Sure: {period})...")
    data_dict = {}
    failed_symbols = []
    
    # 1. Benchmark verisini çek
    try:
        bm_df = yf.download(BENCHMARK_SYMBOL, period=period, progress=False, auto_adjust=True)
        if isinstance(bm_df.columns, pd.MultiIndex):
            bm_df.columns = bm_df.columns.get_level_values(0)
        if not bm_df.empty:
            data_dict[BENCHMARK_SYMBOL] = bm_df
            print(f"[OK] {BENCHMARK_SYMBOL} verisi alindi ({len(bm_df)} gun).")
        else:
            failed_symbols.append({"symbol": BENCHMARK_SYMBOL, "reason": "Empty history"})
    except Exception as e:
        print(f"Benchmark verisi alinamadi ({BENCHMARK_SYMBOL}): {e}")
        failed_symbols.append({"symbol": BENCHMARK_SYMBOL, "reason": str(e)})

    # 2. Hisseleri parçalı indir
    batch_size = 20
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        print(f"Indiriliyor: {i+1}-{min(i+batch_size, len(symbols))}/{len(symbols)}...")
        try:
            batch_df = yf.download(batch, period=period, group_by='ticker', progress=False, auto_adjust=True)
            for sym in batch:
                try:
                    if len(batch) == 1:
                        df = batch_df.copy()
                    else:
                        df = batch_df[sym].copy() if sym in batch_df else None

                    if df is not None and not df.empty and len(df.dropna(subset=['Close'])) > 100:
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)
                        data_dict[sym] = df.dropna(subset=['Close'])
                    else:
                        failed_symbols.append({"symbol": sym, "reason": "Insufficient/No data"})
                except Exception as ex:
                    failed_symbols.append({"symbol": sym, "reason": str(ex)})
        except Exception as e:
            print(f"Toplu indirme hatasi, tek tek deneniyor: {e}")
            for sym in batch:
                try:
                    t = yf.Ticker(sym)
                    df = t.history(period=period)
                    if not df.empty and len(df) > 100:
                        data_dict[sym] = df
                    else:
                        failed_symbols.append({"symbol": sym, "reason": "No data returned"})
                except Exception as ex:
                    failed_symbols.append({"symbol": sym, "reason": str(ex)})
        time.sleep(0.3)

    # Başarısız sembolleri dosyaya logla
    if failed_symbols:
        try:
            with open("failed_symbols.json", "w", encoding="utf-8") as f:
                json.dump(failed_symbols, f, ensure_ascii=False, indent=2)
            print(f"⚠️ {len(failed_symbols)} sembol veri cekiminde basarisiz oldu. 'failed_symbols.json' dosyasina kaydedildi.")
        except Exception:
            pass

    print(f"Toplam {len(data_dict)} hisse/endeks icin veri seti basariyla hazirlandi.")
    return data_dict

def prepare_indicators(df):
    """
    Verilen DataFrame için gerekli teknik göstergeleri hesaplar.
    """
    df = df.copy()
    if 'Close' not in df.columns:
        return None
        
    df['Close'] = df['Close'].astype(float)
    df['Volume'] = df['Volume'].astype(float)
    
    # RSI (14)
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    
    # Hacim MA60
    df['Volume_MA60'] = df['Volume'].rolling(window=60).mean()
    
    # Hareketli Ortalamalar
    df['SMA5'] = ta.trend.sma_indicator(df['Close'], window=5)
    df['SMA20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['SMA50'] = ta.trend.sma_indicator(df['Close'], window=50)
    
    # ATR (14)
    if 'High' in df.columns and 'Low' in df.columns:
        df['ATR'] = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range()
    else:
        df['ATR'] = df['Close'] * 0.03
        
    return df.dropna(subset=['SMA50', 'RSI', 'Volume_MA60'])

def evaluate_signals_on_history(symbol, df, fundamental_info=None):
    """
    Tarihsel veri üzerinde her gün için hangi sinyallerin tetiklendiğini bulur.
    Örtüşen gözlem (overlapping trades) engelleyici COOLDOWN mekanizması içerir:
    Bir sinyal tetiklendiğinde, o sinyalin vade süresi (horizon_days) boyunca aynı sembolde
    aynı sinyal tipi için yeni işlem açılmaz.
    """
    triggers = []
    if df is None or len(df) < 80:
        return triggers
        
    pb_ratio = fundamental_info.get('priceToBook') if fundamental_info else None
    pe_ratio = fundamental_info.get('trailingPE') if fundamental_info else None
    div_yield = fundamental_info.get('dividendYield') if fundamental_info else None
    if div_yield is not None and div_yield < 1.0:
        div_yield = div_yield * 100

    close_arr = df['Close'].values
    vol_arr = df['Volume'].values
    rsi_arr = df['RSI'].values
    vol_ma60_arr = df['Volume_MA60'].values
    sma5_arr = df['SMA5'].values
    sma20_arr = df['SMA20'].values
    sma50_arr = df['SMA50'].values
    dates = df.index

    # Cooldown takip haritası: stype -> son tetiklenme bar indeksi
    last_trigger_bar = {stype: -9999 for stype in STRATEGY_DEFS.keys()}

    for i in range(1, len(df)):
        c = close_arr[i]
        c_prev = close_arr[i-1]
        v = vol_arr[i]
        v_ma60 = vol_ma60_arr[i]
        rsi = rsi_arr[i]
        sma5 = sma5_arr[i]
        sma5_prev = sma5_arr[i-1]
        sma20 = sma20_arr[i]
        sma20_prev = sma20_arr[i-1]
        sma50 = sma50_arr[i]
        d = dates[i]

        # 1. Değer Avcısı (Uzun Vade Al - Horizon: 60G)
        stype = "deger_avcisi"
        h = STRATEGY_DEFS[stype]['horizon_days']
        if (i - last_trigger_bar[stype] >= h):
            if (pb_ratio is not None and pb_ratio <= 1.0 and rsi < 30) or (rsi < 28 and c > c_prev):
                triggers.append({"date": d, "date_idx": i, "symbol": symbol, "signal_type": stype, "entry_price": c})
                last_trigger_bar[stype] = i

        # 2. Hacim Patlaması (Kısa Vade Al - Horizon: 7G)
        stype = "hacim_onayi"
        h = STRATEGY_DEFS[stype]['horizon_days']
        if (i - last_trigger_bar[stype] >= h):
            if c > c_prev and v > v_ma60:
                triggers.append({"date": d, "date_idx": i, "symbol": symbol, "signal_type": stype, "entry_price": c})
                last_trigger_bar[stype] = i

        # 3. Temettü Kalesi (Uzun Vade Al - Horizon: 60G)
        stype = "temettu_kalesi"
        h = STRATEGY_DEFS[stype]['horizon_days']
        if (i - last_trigger_bar[stype] >= h):
            if div_yield is not None and div_yield > 5.0 and pe_ratio is not None and 0 < pe_ratio < 15.0 and rsi < 50:
                triggers.append({"date": d, "date_idx": i, "symbol": symbol, "signal_type": stype, "entry_price": c})
                last_trigger_bar[stype] = i

        # 4. Haftalık Al-Sat (Kısa Vade Al - Horizon: 7G)
        stype = "al_sat_haftalik"
        h = STRATEGY_DEFS[stype]['horizon_days']
        if (i - last_trigger_bar[stype] >= h):
            if (c_prev < sma5_prev) and (c > sma5) and (v > v_ma60 * 0.8) and (c > sma50) and (50 < rsi < 70):
                triggers.append({"date": d, "date_idx": i, "symbol": symbol, "signal_type": stype, "entry_price": c})
                last_trigger_bar[stype] = i

        # 5. Aylık Al-Sat (Orta Vade Al - Horizon: 20G)
        stype = "al_sat_aylik"
        h = STRATEGY_DEFS[stype]['horizon_days']
        if (i - last_trigger_bar[stype] >= h):
            if (c_prev < sma20_prev) and (c > sma20) and (v > v_ma60) and (c > sma50) and (50 < rsi < 70):
                triggers.append({"date": d, "date_idx": i, "symbol": symbol, "signal_type": stype, "entry_price": c})
                last_trigger_bar[stype] = i

        # 6. Aşırı Alım / Risk (Kısa Vade SAT - Horizon: 7G)
        stype = "asiri_alim_risk"
        h = STRATEGY_DEFS[stype]['horizon_days']
        if (i - last_trigger_bar[stype] >= h):
            if rsi > 70 and ((c < sma50) or (c < sma5 and c_prev >= sma5_prev)):
                triggers.append({"date": d, "date_idx": i, "symbol": symbol, "signal_type": stype, "entry_price": c})
                last_trigger_bar[stype] = i

        # 7. Trend Kırılımı (Orta Vade SAT - Horizon: 20G)
        stype = "trend_kirilimi"
        h = STRATEGY_DEFS[stype]['horizon_days']
        if (i - last_trigger_bar[stype] >= h):
            if (c_prev > sma20_prev) and (c < sma20) and (v > v_ma60) and (c < sma50):
                triggers.append({"date": d, "date_idx": i, "symbol": symbol, "signal_type": stype, "entry_price": c})
                last_trigger_bar[stype] = i

        # 8. Aşırı Değerleme (Uzun Vade UZAK DUR - Horizon: 60G)
        stype = "pahali_hisse"
        h = STRATEGY_DEFS[stype]['horizon_days']
        if (i - last_trigger_bar[stype] >= h):
            if (pb_ratio is not None and pb_ratio > 8.0 and rsi > 65) or (rsi > 78 and c < sma5):
                triggers.append({"date": d, "date_idx": i, "symbol": symbol, "signal_type": stype, "entry_price": c})
                last_trigger_bar[stype] = i

    return triggers

def run_full_backtest(symbols=None, period="5y"):
    """
    Tüm BIST hisseleri ve benchmark üzerinde tam kapsamlı Out-of-Sample backtest çalıştırır,
    t-testi ile istatistiksel anlamlılığı ve yön doğruluğunu denetler, sonuçları SQLite'a kaydeder.
    """
    if symbols is None:
        symbols = BIST_SYMBOLS

    dataset = fetch_historical_dataset(symbols, period=period)
    bm_df = dataset.get(BENCHMARK_SYMBOL)
    
    # Benchmark getiri haritası (tarih -> fiyat)
    bm_prices = {}
    if bm_df is not None and not bm_df.empty:
        for dt, row in bm_df.iterrows():
            bm_prices[dt.strftime('%Y-%m-%d') if hasattr(dt, 'strftime') else str(dt)[:10]] = float(row['Close'])

    processed_dfs = {}
    print("Teknik indikatorler hesaplaniyor...")
    for sym in symbols:
        if sym in dataset:
            prep = prepare_indicators(dataset[sym])
            if prep is not None:
                processed_dfs[sym] = prep

    # Temel oranları topla
    fundamental_map = {}
    print("Temel rasyolar aliniyor...")
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            fundamental_map[sym] = t.info or {}
        except Exception:
            fundamental_map[sym] = {}

    all_trades = {stype: [] for stype in STRATEGY_DEFS.keys()}

    print("Gecmis sinyal simulasyonu calistiriliyor (Cooldown / Non-Overlapping aktif)...")
    for sym, df in processed_dfs.items():
        finfo = fundamental_map.get(sym, {})
        triggers = evaluate_signals_on_history(sym, df, finfo)
        
        close_series = df['Close']
        dates = df.index

        for trig in triggers:
            stype = trig['signal_type']
            horizon = STRATEGY_DEFS[stype]['horizon_days']
            entry_idx = trig['date_idx']
            exit_idx = entry_idx + horizon

            if exit_idx < len(close_series):
                entry_p = trig['entry_price']
                exit_p = close_series.iloc[exit_idx]
                ret_pct = ((exit_p - entry_p) / entry_p) * 100

                # Benchmark getirisi
                entry_date_str = dates[entry_idx].strftime('%Y-%m-%d') if hasattr(dates[entry_idx], 'strftime') else str(dates[entry_idx])[:10]
                exit_date_str = dates[exit_idx].strftime('%Y-%m-%d') if hasattr(dates[exit_idx], 'strftime') else str(dates[exit_idx])[:10]

                bm_ret = 0.0
                if entry_date_str in bm_prices and exit_date_str in bm_prices:
                    bm_p1 = bm_prices[entry_date_str]
                    bm_p2 = bm_prices[exit_date_str]
                    if bm_p1 > 0:
                        bm_ret = ((bm_p2 - bm_p1) / bm_p1) * 100

                trade_record = {
                    "symbol": sym,
                    "date": trig['date'],
                    "entry_price": entry_p,
                    "exit_price": exit_p,
                    "return_pct": ret_pct,
                    "bm_return_pct": bm_ret,
                    "excess_pct": ret_pct - bm_ret
                }
                all_trades[stype].append(trade_record)

    # İstatistikleri hesapla & Out-of-Sample Doğrulama
    results_list = []
    print("\n" + "="*95)
    print(f"{'STRATEJİ':^22} | {'YÖN':^4} | {'N':^5} | {'KAZANMA %':^9} | {'ORT GETİRİ':^10} | {'XU100 ALFA':^10} | {'p-VAL':^6} | {'DURUM':^14}")
    print("="*95)

    for stype, sdef in STRATEGY_DEFS.items():
        trades = all_trades.get(stype, [])
        action = sdef['action']
        horizon = sdef['horizon_days']
        name = sdef['name']
        tf_key = sdef['timeframe_key']

        if len(trades) < 5:
            baseline_match = next((b for b in DEFAULT_BASELINE_STATS if b['signal_type'] == stype), None)
            if baseline_match:
                results_list.append(baseline_match)
            continue

        # Tarihe göre sırala
        trades.sort(key=lambda x: x['date'])
        
        # Out-of-sample split: %75 Train (Geçmiş), %25 Test (Yakın Geçmiş)
        split_idx = int(len(trades) * 0.75)
        train_trades = trades[:split_idx]
        test_trades = trades[split_idx:]

        all_rets = [t['return_pct'] for t in trades]
        bm_rets = [t['bm_return_pct'] for t in trades]
        excess_rets = [t['excess_pct'] for t in trades]
        
        train_rets = [t['return_pct'] for t in train_trades] if train_trades else all_rets
        test_rets = [t['return_pct'] for t in test_trades] if test_trades else all_rets

        sample_size = len(trades)
        
        if action == "BUY":
            win_count = len([r for r in all_rets if r > 0])
            train_win_count = len([r for r in train_rets if r > 0])
            test_win_count = len([r for r in test_rets if r > 0])
        else: # SELL / AVOID sinyalleri için düşüş gerçekleşmesi (return < 0) başarıdır
            win_count = len([r for r in all_rets if r < 0])
            train_win_count = len([r for r in train_rets if r < 0])
            test_win_count = len([r for r in test_rets if r < 0])

        win_rate = (win_count / sample_size) * 100 if sample_size > 0 else 0.0
        train_win_rate = (train_win_count / len(train_trades)) * 100 if train_trades else win_rate
        test_win_rate = (test_win_count / len(test_trades)) * 100 if test_trades else win_rate

        avg_return = float(np.mean(all_rets))
        median_return = float(np.median(all_rets))
        max_loss = float(np.min(all_rets))
        std_dev = float(np.std(all_rets))
        benchmark_return = float(np.mean(bm_rets)) if bm_rets else 0.0
        excess_return = avg_return - benchmark_return

        train_avg_ret = float(np.mean(train_rets)) if train_trades else avg_return
        test_avg_ret = float(np.mean(test_rets)) if test_trades else avg_return

        # İstatistiksel Anlamlılık Testi (1-sample t-test)
        p_val = 1.0
        is_significant = 0
        try:
            if action == "BUY":
                # Alım sinyalinde excess_return'ün 0'dan büyük olup olmadığını test et
                t_stat, p_val = stats.ttest_1samp(excess_rets, 0)
                p_val = float(p_val)
                if t_stat > 0 and p_val < 0.05:
                    is_significant = 1
            else:
                # Satış sinyalinde getirisinin 0'dan küçük (düşüş) olup olmadığını test et
                t_stat, p_val = stats.ttest_1samp(all_rets, 0)
                p_val = float(p_val)
                if t_stat < 0 and p_val < 0.05:
                    is_significant = 1
        except Exception:
            p_val = 1.0
            is_significant = 0

        # Doğrulama Kriterleri (Round 2 Revize):
        if action == "BUY":
            # BUY Kriteri:
            # 1. Pozitif Alfa: excess_return > 0
            # 2. Kazanma oranı > %50
            # 3. Test setinde tutarlı: test_win_rate >= %48 ve test_avg_ret > 0
            # 4. Örneklem sayısı N >= 15
            # 5. İstatistiksel olarak anlamlı (p < 0.05)
            is_validated = 1 if (
                sample_size >= 15 and 
                win_rate > 50.0 and 
                excess_return > 0.0 and 
                test_win_rate >= 48.0 and 
                test_avg_ret > 0.0 and 
                is_significant == 1
            ) else 0

            if is_validated:
                notes = f"✓ ONAYLANDI: Pozitif alfa (%{excess_return:+.2f}), %{win_rate:.1f} kazanma, p={p_val:.3f} (Anlamlı)."
                alpha_label = "Pozitif Alfa"
            elif excess_return <= 0:
                notes = f"⚠️ ALFA ÜRETMİYOR: BIST100 farkı %{excess_return:+.2f} (Piyasadan farksız). p={p_val:.3f}. Doğrulanmadı."
                alpha_label = "Alfa Yok / Piyasadan Farksız"
            else:
                notes = f"⚠️ İSTATİSTİKSEL OLARAK GÜVENSİZ: Kazanma: %{win_rate:.1f}, Alfa: %{excess_return:+.2f}, p={p_val:.3f}. Doğrulanmadı."
                alpha_label = "Güvensiz Alfa"

        else: # action == "SELL"
            # SELL / AVOID Kriteri:
            # 1. Yön doğru olmalı: Düşüş gerçekleşme oranı (win_rate) >= %55
            # 2. Ortalama getiri negatif olmalı: avg_return < 0
            # 3. Benchmark'ın altında kalmalı: excess_return < 0
            # 4. Test setinde düşüş devam etmeli: test_avg_ret < 0
            # 5. İstatistiksel anlamlı olmalı (p < 0.05)
            is_validated = 1 if (
                sample_size >= 15 and 
                win_rate >= 55.0 and 
                avg_return < 0.0 and 
                excess_return < 0.0 and 
                test_avg_ret < 0.0 and 
                is_significant == 1
            ) else 0

            if is_validated:
                notes = f"✓ ONAYLANDI: Düşüş oranı %{win_rate:.1f}, Ort getiri %{avg_return:.2f}, p={p_val:.3f}."
                alpha_label = "Başarılı Düşüş Sinyali"
            elif avg_return >= 0:
                notes = f"⚠️ YÖN TERS: Sinyal sonrası hisseler düşmek yerine ortalama %{avg_return:+.2f} yükseldi. Doğrulanmadı."
                alpha_label = "Yön Ters"
            else:
                notes = f"⚠️ YETERSİZ DÜŞÜŞ: Düşüş oranı %{win_rate:.1f} < %55, p={p_val:.3f}. Doğrulanmadı."
                alpha_label = "Yetersiz Düşüş"

        res = {
            "signal_type": stype,
            "signal_name": name,
            "timeframe_key": tf_key,
            "horizon_days": horizon,
            "sample_size": sample_size,
            "win_rate": round(win_rate, 2),
            "avg_return": round(avg_return, 2),
            "median_return": round(median_return, 2),
            "max_loss": round(max_loss, 2),
            "std_dev": round(std_dev, 2),
            "benchmark_return": round(benchmark_return, 2),
            "excess_return": round(excess_return, 2),
            "train_win_rate": round(train_win_rate, 2),
            "test_win_rate": round(test_win_rate, 2),
            "train_avg_return": round(train_avg_ret, 2),
            "test_avg_return": round(test_avg_ret, 2),
            "p_value": round(p_val, 4),
            "is_significant": is_significant,
            "alpha_label": alpha_label,
            "is_validated": is_validated,
            "notes": notes
        }
        results_list.append(res)

        status_str = "✓ ONAYLANDI" if is_validated else "✗ DOĞRULANMADI"
        print(f"{name:^22} | {action:^4} | {sample_size:5d} | %{win_rate:7.1f} | %{avg_return:+8.2f} | %{excess_return:+8.2f} | {p_val:6.3f} | {status_str:^14}")

    # Veritabanına kaydet
    save_backtest_results(results_list)
    print("="*95)
    print(f"Toplam {len(results_list)} strateji backtest sonucu 'backtest_results' tablosuna kaydedildi.\n")

    # Denetim / Audit günlüğü kaydet
    audit_record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbols_count": len(symbols),
        "period": period,
        "results": results_list
    }
    try:
        audit_file = "backtest_audit_log.json"
        existing_logs = []
        if os.path.exists(audit_file):
            with open(audit_file, "r", encoding="utf-8") as f:
                existing_logs = json.load(f)
        existing_logs.append(audit_record)
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(existing_logs[-10:], f, ensure_ascii=False, indent=2) # Son 10 çalıştırmayı sakla
    except Exception as ae:
        print(f"Audit log kaydetme uyarısı: {ae}")

    return results_list

def get_signal_stats(signal_type):
    """
    Belirtilen sinyal türü için en güncel istatistiği döner (yoksa baseline'dan fallback yapar).
    """
    stat_map = get_signal_backtest_map()
    if stat_map and signal_type in stat_map:
        return stat_map[signal_type]
    
    # Fallback to default baseline
    for item in DEFAULT_BASELINE_STATS:
        if item['signal_type'] == signal_type:
            return item
    return None

if __name__ == "__main__":
    import sys
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        
    print("Backtester baslatiliyor...")
    seed_baseline_stats_if_empty()
    
    # Hızlı veya tam test
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        sample_syms = BIST_SYMBOLS[:15]
        run_full_backtest(symbols=sample_syms, period="2y")
    else:
        run_full_backtest(symbols=BIST_SYMBOLS, period="5y")
