"""
⚡ Day-Trader Engine (jakeschincariol/day-trader-skill BIST Adaptasyonu)
- Gün içi ve swing formasyon tarayıcısı (ORB, Boğa Flaması, Aşırı Satım Tepkisi)
- Kesin Giriş, Stop-Loss ve Hedef Kâr (Trade Brackets) hesaplayıcısı
- "Time Machine" Geçmiş Bar Replay & Monte Carlo benzeri olasılık simülatörü
"""

import math
import numpy as np
import pandas as pd
import yfinance as yf

def format_bist_symbol(symbol: str) -> str:
    sym = symbol.strip().upper()
    if not sym.endswith(".IS"):
        sym = f"{sym}.IS"
    return sym

def clean_bist_symbol(symbol: str) -> str:
    return symbol.replace(".IS", "").strip().upper()

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range (ATR) hesaplar."""
    high = df['High']
    low = df['Low']
    close = df['Close']
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Göreceli Güç Endeksi (RSI) hesaplar."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_trade_brackets(entry_price: float, atr: float, risk_reward_ratio: float = 2.0, 
                             user_capital: float = None, risk_per_trade_pct: float = 2.0) -> dict:
    """
    Kullanıcı pozisyona girmeden önce matematiksel Giriş, Stop-Loss ve Hedef seviyelerini hesaplar.
    """
    atr = max(atr, 0.05)
    risk_amount = round(1.5 * atr, 2)
    stop_loss = round(max(entry_price - risk_amount, 0.01), 2)
    stop_pct = round(((entry_price - stop_loss) / entry_price) * 100, 2)
    
    target_1 = round(entry_price + risk_amount, 2)
    target_1_pct = round(((target_1 - entry_price) / entry_price) * 100, 2)
    
    target_2 = round(entry_price + (risk_amount * risk_reward_ratio), 2)
    target_2_pct = round(((target_2 - entry_price) / entry_price) * 100, 2)
    
    actual_rr = round((target_2 - entry_price) / max((entry_price - stop_loss), 0.01), 2)
    
    res = {
        "entry_price": round(entry_price, 2),
        "atr_14": round(atr, 2),
        "stop_loss": stop_loss,
        "stop_loss_pct": f"-{stop_pct}%",
        "target_1": target_1,
        "target_1_pct": f"+{target_1_pct}%",
        "target_2": target_2,
        "target_2_pct": f"+{target_2_pct}%",
        "risk_reward_ratio": actual_rr,
        "recommended_lots": None
    }
    
    if user_capital and user_capital > 0:
        max_risk_tl = user_capital * (risk_per_trade_pct / 100.0)
        risk_per_share = entry_price - stop_loss
        if risk_per_share > 0:
            rec_lots = int(max_risk_tl / risk_per_share)
            res["recommended_lots"] = max(rec_lots, 1)
            res["max_risk_capital_tl"] = round(max_risk_tl, 2)
            
    return res

def detect_chart_setups(df: pd.DataFrame) -> list:
    """
    DataFrame üzerinde Day-Trader setup'larını tarar:
    - Aşırı Satım Tepkisi (Oversold Bounce)
    - Boğa Flaması / Sıkışma Kırılımı (Bull Flag Breakout)
    - Trend Desteğinden Tepki (SMA20 Bounce)
    - Hacimli Kırılım (Volume Breakout)
    """
    if len(df) < 25:
        return []
    
    setups = []
    close = df['Close']
    open_p = df['Open']
    high = df['High']
    low = df['Low']
    vol = df['Volume']
    
    rsi = calculate_rsi(close)
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean() if len(df) >= 50 else sma20
    vol_ma20 = vol.rolling(20).mean()
    
    cur_idx = -1
    cur_c = close.iloc[cur_idx]
    cur_o = open_p.iloc[cur_idx]
    cur_h = high.iloc[cur_idx]
    cur_l = low.iloc[cur_idx]
    cur_v = vol.iloc[cur_idx]
    cur_rsi = rsi.iloc[cur_idx]
    cur_sma20 = sma20.iloc[cur_idx]
    cur_vol_ma = vol_ma20.iloc[cur_idx]
    
    # 1. Aşırı Satım Tepkisi (Oversold Bounce)
    if cur_rsi < 36 and cur_c >= cur_o:
        setups.append({
            "setup_type": "AŞIRI_SATIM_TEPKİSİ",
            "direction": "LONG",
            "confidence": 75 if cur_rsi < 30 else 65,
            "description": f"RSI ({cur_rsi:.1f}) aşırı satım bölgesinden yeşil mumla tepki veriyor."
        })
        
    # 2. Hacimli Kırılım (Volume Breakout)
    recent_highest = high.iloc[-10:-1].max() if len(high) >= 10 else high.iloc[:-1].max()
    if cur_c > recent_highest and cur_v > (cur_vol_ma * 1.4):
        setups.append({
            "setup_type": "HACİMLİ_DİRENÇ_KIRILIMI",
            "direction": "LONG",
            "confidence": 85,
            "description": f"Fiyat son 10 günün zirvesini ({recent_highest:.2f} TL) ortalama üzeri hacimle kırdı."
        })
        
    # 3. SMA20 Trend Desteğinden Dönüş
    if not math.isnan(cur_sma20) and cur_sma20 > 0:
        dist_to_sma = abs(cur_l - cur_sma20) / cur_sma20
        if dist_to_sma < 0.015 and cur_c > cur_sma20 and cur_c > cur_o:
            setups.append({
                "setup_type": "SMA20_TREND_DESTEĞİ",
                "direction": "LONG",
                "confidence": 70,
                "description": f"Fiyat 20 günlük hareketli ortalamayı ({cur_sma20:.2f} TL) test edip yukarı sekti."
            })
            
    # 4. Boğa Flaması / Sıkışma Kırılımı (Bull Flag)
    if len(close) >= 15:
        ten_day_change = (close.iloc[-4] - close.iloc[-14]) / close.iloc[-14]
        consolidation_range = (high.iloc[-4:-1].max() - low.iloc[-4:-1].min()) / close.iloc[-4]
        if ten_day_change > 0.05 and consolidation_range < 0.035 and cur_c > high.iloc[-4:-1].max():
            setups.append({
                "setup_type": "BOĞA_FLAMASI_KIRILIMI",
                "direction": "LONG",
                "confidence": 80,
                "description": "Güçlü yükseliş sonrası daralan konsolidasyon yukarı yönlü kırıldı."
            })
            
    if not setups:
        setups.append({
            "setup_type": "STANDART_İZLEME",
            "direction": "NÖTR",
            "confidence": 50,
            "description": "Belirgin bir formasyon kırılımı yok, fiyat standart bantta hareket ediyor."
        })
        
    return setups

def simulate_time_machine_from_df(df: pd.DataFrame, target_pct: float = 3.0, 
                                  stop_pct: float = 2.0, max_holding_bars: int = 5) -> dict:
    """
    Time Machine Replay Simülatörü:
    Geçmiş barlar üzerinde Monte Carlo benzeri bir geriye sarma simülasyonu çalıştırır.
    Her pozitif dönüş/momentum barında sanal pozisyon açıp Hedef vs Stop başarısını kaydeder.
    """
    if len(df) < 30:
        return {
            "status": "insufficient_data",
            "sample_size": 0,
            "win_rate_percent": 0.0,
            "expectancy_percent": 0.0,
            "profit_factor": 0.0,
            "verdict": "YETERSİZ VERİ"
        }
        
    close = df['Close']
    high = df['High']
    low = df['Low']
    rsi = calculate_rsi(close)
    
    wins = 0
    losses = 0
    timeouts = 0
    gain_pcts = []
    
    # Tarihsel barlar üzerinde setup oluşum anlarını tara
    # Örneğin: RSI 40-60 arası veya yeşil kırılım barlarında işleme girilseydi ne olurdu?
    for i in range(20, len(df) - max_holding_bars):
        c_bar = close.iloc[i]
        h_bar = high.iloc[i]
        l_bar = low.iloc[i]
        rsi_bar = rsi.iloc[i]
        
        # Giriş koşulu: Pozitif momentum veya aşırı satım sıçraması
        is_entry = (rsi_bar < 45 and close.iloc[i] > close.iloc[i-1]) or (close.iloc[i] > high.iloc[i-5:i].max() * 0.99)
        if not is_entry:
            continue
            
        entry_price = c_bar
        target_price = entry_price * (1 + (target_pct / 100.0))
        stop_price = entry_price * (1 - (stop_pct / 100.0))
        
        resolved = False
        for f in range(1, max_holding_bars + 1):
            future_idx = i + f
            fut_h = high.iloc[future_idx]
            fut_l = low.iloc[future_idx]
            
            # Aynı barda hem stop hem hedef olduysa temkinli yaklaş: Stop say
            if fut_l <= stop_price and fut_h >= target_price:
                losses += 1
                gain_pcts.append(-stop_pct)
                resolved = True
                break
            elif fut_h >= target_price:
                wins += 1
                gain_pcts.append(target_pct)
                resolved = True
                break
            elif fut_l <= stop_price:
                losses += 1
                gain_pcts.append(-stop_pct)
                resolved = True
                break
                
        if not resolved:
            # Süre doldu, kapanış fiyatından çık
            exit_price = close.iloc[i + max_holding_bars]
            realized = ((exit_price - entry_price) / entry_price) * 100.0
            gain_pcts.append(realized)
            timeouts += 1
            if realized > 0:
                wins += 1
            else:
                losses += 1
                
    total_trades = wins + losses
    if total_trades == 0:
        return {
            "status": "no_signals_found",
            "sample_size": 0,
            "win_rate_percent": 0.0,
            "expectancy_percent": 0.0,
            "profit_factor": 0.0,
            "verdict": "SİNYAL OLUŞMADI"
        }
        
    win_rate = round((wins / total_trades) * 100, 1)
    avg_gain = np.mean(gain_pcts) if gain_pcts else 0.0
    
    total_wins_val = sum([g for g in gain_pcts if g > 0])
    total_losses_val = abs(sum([g for g in gain_pcts if g < 0]))
    profit_factor = round(total_wins_val / total_losses_val, 2) if total_losses_val > 0 else 9.99
    
    # Beklenti (Expectancy) = (Kazanma Oranı * Ortalama Kazanç) - (Kayıp Oranı * Ortalama Kayıp)
    win_p = win_rate / 100.0
    loss_p = 1.0 - win_p
    win_avg = np.mean([g for g in gain_pcts if g > 0]) if any(g > 0 for g in gain_pcts) else target_pct
    loss_avg = abs(np.mean([g for g in gain_pcts if g <= 0])) if any(g <= 0 for g in gain_pcts) else stop_pct
    expectancy = round((win_p * win_avg) - (loss_p * loss_avg), 2)
    
    if win_rate >= 60 and profit_factor >= 1.5:
        verdict = "🟢 YÜKSEK BAŞARI OLASILIĞI"
    elif win_rate >= 48 and profit_factor >= 1.1:
        verdict = "🟡 DENGELİ İSTATİSTİKSEL SETUP"
    else:
        verdict = "🔴 DÜŞÜK BEKLENTİ / RİSKLİ"
        
    return {
        "status": "success",
        "sample_size": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate_percent": win_rate,
        "expectancy_percent": expectancy,
        "profit_factor": profit_factor,
        "avg_trade_gain_pct": round(avg_gain, 2),
        "target_pct_tested": target_pct,
        "stop_pct_tested": stop_pct,
        "max_holding_bars": max_holding_bars,
        "verdict": verdict
    }

def run_time_machine_simulation(symbol: str, target_pct: float = 4.0, stop_pct: float = 2.5, 
                                lookback_period: str = "1y") -> dict:
    """
    Belirli bir BIST hissesi için Yahoo Finance'tan geçmiş barları çeker ve
    Time Machine Replay simülasyonunu çalıştırır.
    """
    clean_sym = clean_bist_symbol(symbol)
    full_sym = format_bist_symbol(symbol)
    
    try:
        ticker = yf.Ticker(full_sym)
        df = ticker.history(period=lookback_period)
        if df.empty or len(df) < 30:
            return {
                "symbol": clean_sym,
                "status": "error",
                "message": f"{clean_sym} için yeterli geçmiş veri bulunamadı."
            }
            
        cur_price = float(df['Close'].iloc[-1])
        atr_series = calculate_atr(df)
        cur_atr = float(atr_series.iloc[-1]) if not atr_series.empty and not math.isnan(atr_series.iloc[-1]) else cur_price * 0.03
        
        brackets = calculate_trade_brackets(cur_price, cur_atr)
        setups = detect_chart_setups(df)
        sim_res = simulate_time_machine_from_df(df, target_pct=target_pct, stop_pct=stop_pct)
        
        return {
            "symbol": clean_sym,
            "status": "success",
            "current_price": cur_price,
            "brackets": brackets,
            "detected_setups": setups,
            "simulation": sim_res
        }
    except Exception as e:
        return {
            "symbol": clean_sym,
            "status": "error",
            "message": f"Time Machine simülasyon hatası ({clean_sym}): {str(e)}"
        }
