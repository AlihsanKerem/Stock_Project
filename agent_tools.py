"""
🤖 AI Agent Tools (Araç Takımı)
Mevcut analitik, portföy, backtest ve duygu analizi motorlarını
AI Ajanı için standart JSON şemalı ve deterministik fonksiyonlara dönüştürür.
"""

import json
import yfinance as yf
from database import (
    get_portfolio_positions, get_monthly_target_stats, 
    get_backtest_results, get_signal_backtest_map,
    get_signals, add_alert, get_active_alerts, get_tracked_stocks,
    get_all_stock_data
)
from analyzer import analyze_stock, run_analysis
from sentiment import analyze_sentiment
from day_trader_engine import run_time_machine_simulation, detect_chart_setups, calculate_trade_brackets, calculate_atr

def format_symbol(symbol: str) -> str:
    """Sembolü temizler ve BIST için .IS uzantısı ekler."""
    sym = symbol.strip().upper()
    if not sym.endswith(".IS"):
        sym = f"{sym}.IS"
    return sym

def clean_symbol(symbol: str) -> str:
    """Görüntüleme için .IS uzantısını kaldırır."""
    return symbol.replace(".IS", "").strip().upper()

# ==========================================
# 🛠️ Deterministik Araç Fonksiyonları
# ==========================================

def tool_get_portfolio_summary() -> dict:
    """
    Kullanıcının canlı portföy durumunu, açık pozisyonlarını,
    maliyetlerini, güncel kâr/zararını ve bu ayki gerçekleşen kârını döner.
    """
    try:
        raw_positions = get_portfolio_positions()
        target_stats = get_monthly_target_stats()
        
        if not raw_positions:
            return {
                "status": "empty",
                "message": "Portföyde açık hisse senedi pozisyonu bulunmuyor.",
                "total_cost": 0.0,
                "total_value": 0.0,
                "total_unrealized_pnl": 0.0,
                "monthly_realized_pnl": target_stats.get("realized_pnl", 0.0),
                "monthly_target": target_stats.get("target_profit", 0.0),
                "positions": []
            }

        positions_summary = []
        total_cost = 0.0
        total_value = 0.0

        for p in raw_positions:
            sym = p['symbol']
            lot = int(p['lot'])
            buy_price = float(p['buy_price'])
            cost = lot * buy_price

            cur_price = buy_price
            try:
                ticker = yf.Ticker(format_symbol(sym))
                hist = ticker.history(period="3d")
                if not hist.empty:
                    cur_price = float(hist.iloc[-1]['Close'])
            except Exception:
                pass

            val = lot * cur_price
            pnl = val - cost
            pnl_pct = ((cur_price - buy_price) / buy_price * 100) if buy_price > 0 else 0.0

            total_cost += cost
            total_value += val

            positions_summary.append({
                "symbol": clean_symbol(sym),
                "lot": lot,
                "buy_price": round(buy_price, 2),
                "current_price": round(cur_price, 2),
                "cost": round(cost, 2),
                "market_value": round(val, 2),
                "pnl_tl": round(pnl, 2),
                "pnl_pct": f"%{pnl_pct:+.2f}",
                "notes": p.get('notes', '')
            })

        total_pnl = total_value - total_cost
        total_pnl_pct = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0.0

        return {
            "status": "success",
            "total_portfolio_cost": round(total_cost, 2),
            "total_portfolio_value": round(total_value, 2),
            "total_unrealized_pnl": round(total_pnl, 2),
            "total_unrealized_pnl_pct": f"%{total_pnl_pct:+.2f}",
            "monthly_realized_pnl": round(target_stats.get("realized_pnl", 0.0), 2),
            "monthly_target_tl": round(target_stats.get("target_profit", 0.0), 2),
            "monthly_target_progress": f"%{target_stats.get('progress_pct', 0.0):.1f}",
            "positions_count": len(positions_summary),
            "positions": positions_summary
        }
    except Exception as e:
        return {"status": "error", "message": f"Portföy verisi alınırken hata: {str(e)}"}

def tool_analyze_stock(symbol: str) -> dict:
    """
    Belirtilen hissenin güncel teknik göstergelerini (RSI, ATR, Volatilite),
    çarpanlarını (F/K, PD/DD), Stop-Loss seviyesini ve tetiklenen sinyallerini döner.
    """
    try:
        formatted = format_symbol(symbol)
        clean = clean_symbol(symbol)
        data = analyze_stock(formatted)
        
        if not data:
            return {"status": "error", "message": f"{clean} hissesi için analiz verisi bulunamadı."}

        signals_info = []
        for s in data.get("signals", []):
            signals_info.append({
                "signal_name": s.get("name"),
                "timeframe": s.get("timeframe"),
                "horizon": s.get("horizon"),
                "action": s.get("action", "BUY"),
                "message": s.get("message")
            })

        return {
            "status": "success",
            "symbol": clean,
            "current_price": data.get("price"),
            "stop_loss_atr": data.get("stop_loss"),
            "atr": data.get("atr"),
            "risk_level": data.get("risk_level"),
            "volatility": data.get("volatility"),
            "rsi_14": data.get("rsi"),
            "pe_ratio": data.get("pe_ratio"),
            "pb_ratio": data.get("pb_ratio"),
            "dividend_yield": data.get("div_yield"),
            "active_signals_count": len(signals_info),
            "active_signals": signals_info
        }
    except Exception as e:
        return {"status": "error", "message": f"{symbol} analiz edilirken hata: {str(e)}"}

def tool_get_backtest_stats(signal_type: str = None) -> dict:
    """
    Sinyallerin 5 yıllık tarihsel BIST simülasyon ve Out-of-Sample doğrulama sonuçlarını döner.
    signal_type verilmezse en başarılı sinyallerin özet listesini döner.
    """
    try:
        results = get_backtest_results(signal_type=signal_type)
        if not results:
            return {
                "status": "not_found",
                "message": f"Backtest sonucu bulunamadı. Lütfen önce backtest motorunu çalıştırın."
            }
        
        if isinstance(results, dict):
            # Tekil sinyal detayı
            return {
                "status": "success",
                "signal_type": results.get("signal_type"),
                "signal_name": results.get("signal_name"),
                "horizon_days": results.get("horizon_days"),
                "sample_size": results.get("sample_size"),
                "win_rate": f"%{results.get('win_rate', 0.0):.1f}",
                "avg_return": f"%{results.get('avg_return', 0.0):.2f}",
                "benchmark_bist_return": f"%{results.get('benchmark_return', 0.0):.2f}",
                "excess_alpha": f"%{results.get('excess_return', 0.0):.2f}",
                "is_validated": bool(results.get("is_validated")),
                "alpha_label": results.get("alpha_label"),
                "test_win_rate": f"%{results.get('test_win_rate', 0.0):.1f}" if results.get("test_win_rate") else None
            }
        else:
            # Liste
            summary_list = []
            for r in results[:8]:
                summary_list.append({
                    "signal_type": r.get("signal_type"),
                    "signal_name": r.get("signal_name"),
                    "win_rate": f"%{r.get('win_rate', 0.0):.1f}",
                    "avg_return": f"%{r.get('avg_return', 0.0):.2f}",
                    "excess_alpha": f"%{r.get('excess_return', 0.0):.2f}",
                    "is_validated": bool(r.get("is_validated"))
                })
            return {
                "status": "success",
                "total_signals": len(results),
                "signals": summary_list
            }
    except Exception as e:
        return {"status": "error", "message": f"Backtest verisi alınırken hata: {str(e)}"}

def tool_get_news_and_sentiment(symbol: str) -> dict:
    """
    Hisse senedi hakkında en güncel haber başlığını ve duygu analizini (OLUMLU / OLUMSUZ / NÖTR) döner.
    """
    try:
        clean = clean_symbol(symbol)
        formatted = format_symbol(symbol)
        result = analyze_sentiment(formatted)
        
        if not result or result.get("status") == "error":
            return {
                "status": "no_news",
                "symbol": clean,
                "message": result.get("message", "Güncel haber bulunamadı.") if result else "Haber bulunamadı."
            }
        
        return {
            "status": "success",
            "symbol": clean,
            "sentiment": result.get("status"),
            "news_title": result.get("title"),
            "news_link": result.get("link")
        }
    except Exception as e:
        return {"status": "error", "message": f"Haber analizi hatası ({symbol}): {str(e)}"}

def tool_create_price_alert(symbol: str, target_price: float, condition: str = "ABOVE") -> dict:
    """
    Belirli bir hisse için sisteme fiyat alarmı ekler.
    condition: 'ABOVE' (fiyat hedefin üstüne çıkarsa) veya 'BELOW' (fiyat hedefin altına düşerse).
    """
    try:
        clean = clean_symbol(symbol)
        formatted = format_symbol(symbol)
        
        # Anlık fiyatı al
        ticker = yf.Ticker(formatted)
        hist = ticker.history(period="1d")
        if hist.empty:
            return {"status": "error", "message": f"{clean} hissesi için güncel fiyat alınamadı."}
            
        cur_price = float(hist.iloc[-1]['Close'])
        direction = "YUKARI" if condition.upper() in ["ABOVE", "YUKARI"] else "ASAGI"
        pct_diff = ((target_price - cur_price) / cur_price) * 100

        add_alert(
            symbol=clean,
            reference_price=round(cur_price, 2),
            target_percentage=round(pct_diff, 2),
            target_price=round(target_price, 2),
            direction=direction,
            notes=f"AI Ajanı tarafından oluşturuldu (Referans: {round(cur_price, 2)} ₺)"
        )

        return {
            "status": "success",
            "message": f"{clean} için {round(target_price, 2)} ₺ ({direction}) alarmı başarıyla kuruldu.",
            "reference_price": round(cur_price, 2),
            "target_price": round(target_price, 2),
            "direction": direction
        }
    except Exception as e:
        return {"status": "error", "message": f"Alarm oluşturulurken hata: {str(e)}"}

def tool_get_active_signals() -> dict:
    """
    Sistemin son taramasında tespit ettiği en güncel hisse sinyallerini döner.
    """
    try:
        recent_signals = get_signals(limit=15)
        if not recent_signals:
            return {
                "status": "empty",
                "message": "Henüz kaydedilmiş aktif sinyal bulunmuyor veya tarama yapılmadı.",
                "signals": []
            }

        formatted_signals = []
        for s in recent_signals:
            formatted_signals.append({
                "symbol": clean_symbol(s.get("symbol", "")),
                "signal_name": s.get("signal_name"),
                "timeframe": s.get("timeframe_label"),
                "action": s.get("action", "BUY"),
                "price": s.get("price_at_signal"),
                "stop_loss": s.get("stop_loss"),
                "win_rate": f"%{s.get('win_rate', 0.0):.1f}" if s.get("win_rate") else None,
                "is_conflict": bool(s.get("is_conflict")),
                "message": s.get("message")
            })

        return {
            "status": "success",
            "total_signals": len(formatted_signals),
            "signals": formatted_signals
        }
    except Exception as e:
        return {"status": "error", "message": f"Sinyaller alınırken hata: {str(e)}"}

def tool_get_tracked_watchlist() -> dict:
    """
    Kullanıcının takip listesindeki (Watchlist) hisseleri ve son fiyatlarını döner.
    """
    try:
        stocks = get_tracked_stocks()
        return {
            "status": "success",
            "watchlist": [clean_symbol(s) for s in stocks]
        }
    except Exception as e:
        return {"status": "error", "message": f"Takip listesi alınırken hata: {str(e)}"}

def tool_run_time_machine(symbol: str, target_pct: float = 4.0, stop_pct: float = 2.5) -> dict:
    """
    Belirli bir BIST hissesi için Time Machine geçmiş bar tekrar simülasyonunu çalıştırır.
    Kazanma oranı (win rate), beklenti (expectancy) ve kâr faktörünü döner.
    """
    return run_time_machine_simulation(symbol, target_pct=float(target_pct), stop_pct=float(stop_pct))

def tool_get_day_trading_setups(symbol: str) -> dict:
    """
    Hisse için gün içi formasyon kırılımlarını (Boğa Flaması, Aşırı Satım Tepkisi, Destek Dönüşü)
    ve kesin Stop-Loss/Hedef braketlerini döner.
    """
    try:
        clean_sym = clean_symbol(symbol)
        ticker = yf.Ticker(format_symbol(symbol))
        df = ticker.history(period="60d")
        if df.empty or len(df) < 15:
            return {"status": "error", "message": f"{clean_sym} için grafik verisi alınamadı."}
        
        cur_price = float(df['Close'].iloc[-1])
        atr_series = calculate_atr(df)
        cur_atr = float(atr_series.iloc[-1]) if not atr_series.empty else cur_price * 0.03
        
        brackets = calculate_trade_brackets(cur_price, cur_atr)
        setups = detect_chart_setups(df)
        
        return {
            "status": "success",
            "symbol": clean_sym,
            "current_price": cur_price,
            "brackets": brackets,
            "setups": setups
        }
    except Exception as e:
        return {"status": "error", "message": f"Day-trading tarama hatası: {str(e)}"}

def tool_get_committee_review(symbol: str) -> dict:
    """
    Hisse senedi hakkında 4 uzman ajanın (Değer, Momentum, Risk, Baş Portföy Yöneticisi)
    ortak komite müzakeresini ve nihai kararını döner.
    """
    try:
        from committee_engine import BistInvestmentCommittee
        committee = BistInvestmentCommittee()
        return committee.evaluate_stock(symbol)
    except Exception as e:
        return {"status": "error", "message": f"Komite değerlendirme hatası: {str(e)}"}

# ==========================================
# 📋 Standart Araç Şemaları (Tool Schemas)
# ==========================================

AVAILABLE_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "tool_get_portfolio_summary",
            "description": "Kullanıcının canlı portföyünü, açık hisse pozisyonlarını, lot adetlerini, maliyetlerini, anlık kâr/zararını ve aylık hedefini döner. Portföy ile ilgili sorularda ilk çağrılması gereken araçtır.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_analyze_stock",
            "description": "Belirli bir BIST hissesi için teknik analizi, RSI, ATR bazlı Stop-Loss seviyesini, volatilite riskini ve sistemin ürettiği aktif AL/SAT sinyallerini çeker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Hisse senedi sembolü (Örn: THYAO, EREGL, ASELS, GARAN)"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_backtest_stats",
            "description": "Stratejilerin geçmiş 5 yıllık BIST backtest başarı oranlarını (kazanma oranı, BIST endeksine kıyasla alfa getirisi, doğrulama durumu) sorgular. Sinyallerin güvenilirliğini test etmek için kullanılır.",
            "parameters": {
                "type": "object",
                "properties": {
                    "signal_type": {
                        "type": "string",
                        "description": "Sorgulanacak sinyal tipi (Örn: hacim_onayi, deger_avcisi, temettu_kalesi, al_sat_haftalik). Boş bırakılırsa tüm sinyallerin başarı sıralamasını döner."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_news_and_sentiment",
            "description": "Belirtilen hisse hakkında en son KAP ve piyasa haber başlığını çekip duygu analizini (OLUMLU/OLUMSUZ/NÖTR) döner.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Hisse senedi sembolü (Örn: THYAO, SASA)"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_create_price_alert",
            "description": "Kullanıcı için belirli bir hisseye hedef fiyat alarmı kurar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Hisse senedi kodu (Örn: THYAO)"
                    },
                    "target_price": {
                        "type": "number",
                        "description": "Alarm kurulacak hedef fiyat (TL)"
                    },
                    "condition": {
                        "type": "string",
                        "enum": ["ABOVE", "BELOW"],
                        "description": "Fiyat hedefin üstüne çıkınca mı (ABOVE) yoksa altına düşünce mi (BELOW) tetiklenecek."
                    }
                },
                "required": ["symbol", "target_price"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_active_signals",
            "description": "Piyasa taramasından çıkan güncel AL ve SAT sinyallerini listeler.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_tracked_watchlist",
            "description": "Kullanıcının takip listesindeki hisse senetlerini listeler.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_run_time_machine",
            "description": "Hissenin teknik setup'ını geçmiş 1 yıllık barlarda geriye sarıp simüle eder. Kazanma oranı (win rate %), beklenti oranı ve kâr faktörünü hesaplar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Hisse senedi sembolü (Örn: THYAO, EREGL)"
                    },
                    "target_pct": {
                        "type": "number",
                        "description": "Test edilecek hedef kâr yüzdesi (Varsayılan: 4.0)"
                    },
                    "stop_pct": {
                        "type": "number",
                        "description": "Test edilecek zarar durdurma yüzdesi (Varsayılan: 2.5)"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_day_trading_setups",
            "description": "Hisse için gün içi ve kısa vadeli formasyon kırılımlarını (Boğa Flaması, Aşırı Satım Tepkisi vb.) ve matematiksel Stop-Loss/Hedef fiyat seviyelerini döner.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Hisse senedi sembolü (Örn: THYAO, ASELS)"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_committee_review",
            "description": "virattt/ai-hedge-fund mimarisiyle hisseyi 4 rollü (Değer Analisti, Momentum Analisti, Risk Yöneticisi ve Baş Portföy Yöneticisi) BIST Yatırım Komitesine sunar ve çelişkileri uzlaştırılmış nihai kurumsal kararı (GÜÇLÜ AL, KADEMELİ AL, TUT vb.) döner.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Hisse senedi sembolü (Örn: THYAO, EREGL, GARAN)"
                    }
                },
                "required": ["symbol"]
            }
        }
    }
]

# Fonksiyon eşleme tablosu
TOOLS_MAP = {
    "tool_get_portfolio_summary": tool_get_portfolio_summary,
    "tool_analyze_stock": tool_analyze_stock,
    "tool_get_backtest_stats": tool_get_backtest_stats,
    "tool_get_news_and_sentiment": tool_get_news_and_sentiment,
    "tool_create_price_alert": tool_create_price_alert,
    "tool_get_active_signals": tool_get_active_signals,
    "tool_get_tracked_watchlist": tool_get_tracked_watchlist,
    "tool_run_time_machine": tool_run_time_machine,
    "tool_get_day_trading_setups": tool_get_day_trading_setups,
    "tool_get_committee_review": tool_get_committee_review
}

def execute_agent_tool(tool_name: str, arguments: dict) -> dict:
    """
    Ajan tarafından talep edilen aracı çalıştırır ve sonucunu döner.
    """
    if tool_name not in TOOLS_MAP:
        return {"status": "error", "message": f"'{tool_name}' adında bir araç bulunamadı."}
    
    try:
        func = TOOLS_MAP[tool_name]
        if arguments:
            return func(**arguments)
        else:
            return func()
    except Exception as e:
        return {"status": "error", "message": f"Araç çalıştırma hatası ({tool_name}): {str(e)}"}

