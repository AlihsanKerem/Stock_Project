"""
🎯 Prediction Tracker, BIST Market Hours Guard & Smart Funnel Digest
- Hafta içi / Seans saati kontrolü (Cumartesi-Pazar ve gece gereksiz veri çekimini engeller)
- Akıllı Huni (Funnel): En güçlü 3-5 adayı Yatırım Komitesi ve Time Machine'den geçirir
- Kısa & Okunabilir Telegram Yönetici Özeti üretir
- Gün içi 3 kez (10:30, 14:00, 18:15) açık AI tahminlerini canlı fiyatla doğrular
"""

from datetime import datetime, time as dt_time
import yfinance as yf

from database import (
    save_ai_prediction,
    get_open_ai_predictions,
    update_ai_prediction_status,
    get_ai_prediction_stats
)
from committee_engine import BistInvestmentCommittee
from day_trader_engine import run_time_machine_simulation, format_bist_symbol, clean_bist_symbol

def is_weekday(now: datetime = None) -> bool:
    """Pazartesi (0) - Cuma (4) arası True, Cumartesi (5) - Pazar (6) False döner."""
    dt = now or datetime.now()
    return dt.weekday() < 5

def is_bist_market_open(now: datetime = None) -> bool:
    """
    BIST Pay Piyasası seans saatlerinde (Hafta içi 09:55 - 18:20) True döner.
    Hafta sonu ve gece yarısı gereksiz Yahoo Finance sorgularını engeller.
    """
    dt = now or datetime.now()
    if not is_weekday(dt):
        return False
    cur_t = dt.time()
    return dt_time(9, 55) <= cur_t <= dt_time(18, 20)

def select_top_candidates(signals: list, max_candidates: int = 5) -> list:
    """
    Tarama motorundan çıkan sinyaller arasından çelişkisiz, doğrulanmış
    en güçlü AL adaylarını seçer ve sembol bazında tekilleştirir.
    """
    if not signals:
        return []

    # 1. Öncelik: Çelişkisiz ve doğrulanmış BUY sinyalleri
    filtered = [
        s for s in signals
        if str(s.get("action", "BUY")).upper() == "BUY"
        and not s.get("is_conflict", 0)
        and s.get("is_validated", 1)
    ]

    # Eğer hiç doğrulanmış yoksa sadece çelişkisiz BUY sinyallerini al
    if not filtered:
        filtered = [
            s for s in signals
            if str(s.get("action", "BUY")).upper() == "BUY"
            and not s.get("is_conflict", 0)
        ]

    # Kazanma oranı ve ortalama getiriye göre sırala
    def _score(sig):
        wr = float(sig.get("win_rate") or 50.0)
        ar = float(sig.get("avg_return") or 0.0)
        return wr + (ar * 5.0)

    filtered.sort(key=_score, reverse=True)

    top_symbols = []
    seen = set()
    for s in filtered:
        sym = clean_bist_symbol(s.get("symbol", ""))
        if sym and sym not in seen:
            seen.add(sym)
            top_symbols.append(sym)
        if len(top_symbols) >= max_candidates:
            break

    return top_symbols

def run_funnel_committee_digest(signals: list, max_candidates: int = 5) -> dict:
    """
    En iyi adayları Yatırım Komitesi ve Time Machine'den geçirir,
    AL kararlarını veritabanına tahmin olarak kaydeder ve
    Telegram için kısa, okunabilir bir Yönetici Özeti üretir.
    """
    top_symbols = select_top_candidates(signals, max_candidates=max_candidates)
    if not top_symbols:
        return {
            "evaluated": [],
            "digest_message": "ℹ️ <b>GÜNLÜK BIST ÖZETİ</b>\n\nBugün kriterlere uyan öne çıkan bir AL adayı bulunamadı. Tüm detaylar Web Dashboard'da."
        }

    committee = BistInvestmentCommittee()
    evaluated = []

    for sym in top_symbols:
        comm_rep = committee.evaluate_stock(sym)
        tm_rep = run_time_machine_simulation(sym)

        cur_price = float(comm_rep.get("current_price") or tm_rep.get("current_price") or 0.0)
        brackets = tm_rep.get("brackets", {})
        sim = tm_rep.get("simulation", {})

        entry_p = float(brackets.get("entry_price") or cur_price)
        stop_l = float(brackets.get("stop_loss") or (comm_rep.get("risk_officer", {}).get("stop_loss_level")) or round(entry_p * 0.95, 2))
        target_p = float(brackets.get("target_1") or round(entry_p * 1.05, 2))

        decision = str(comm_rep.get("final_decision", "TUT / İZLE"))
        score = int(comm_rep.get("consensus_score", 50))
        win_rate = float(sim.get("win_rate_percent", 0.0))

        # Sadece AL yönlü kararları tahmin takip sistemine kaydet
        is_buy_decision = ("AL" in decision.upper()) and ("UZAK DUR" not in decision.upper()) and ("SAT" not in decision.upper())
        if is_buy_decision and entry_p > 0:
            save_ai_prediction(sym, decision, score, entry_p, target_p, stop_l)

        evaluated.append({
            "symbol": sym,
            "decision": decision,
            "score": score,
            "entry_price": entry_p,
            "target_price": target_p,
            "stop_loss": stop_l,
            "win_rate": win_rate,
            "summary": comm_rep.get("executive_summary", "")
        })

    # Konsensüs skoruna göre sırala
    evaluated.sort(key=lambda x: x["score"], reverse=True)

    lines = [
        f"<b>🏛️ GÜNLÜK AI YATIRIM KOMİTESİ ÖZETİ</b>",
        f"<i>{len(signals)} ham sinyal elendi → En güçlü {len(evaluated)} aday seçildi:</i>\n"
    ]

    for item in evaluated:
        emoji = "🟢" if "GÜÇLÜ AL" in item["decision"] else "🟡" if "AL" in item["decision"] else "⚪"
        lines.append(
            f"{emoji} <b>{item['symbol']}</b> — <b>{item['decision']}</b> (Skor: {item['score']}/100)\n"
            f"   Giriş: <code>{item['entry_price']:.2f}₺</code> | Hedef: <code>{item['target_price']:.2f}₺</code> | Stop: <code>{item['stop_loss']:.2f}₺</code>\n"
            f"   ⏱️ Time Machine Başarısı: <b>%{item['win_rate']:.1f}</b>"
        )

    lines.append("\n🌐 <i>Tüm ham tarama listesi ve grafikler Web Dashboard'da kayıtlıdır.</i>")

    return {
        "evaluated": evaluated,
        "digest_message": "\n".join(lines)
    }

def _default_price_fetcher(symbol: str):
    """Yahoo Finance'tan son kapanış/anlık fiyatı çeker."""
    try:
        ticker = yf.Ticker(format_bist_symbol(symbol))
        hist = ticker.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None

def evaluate_open_predictions(price_fetcher=None) -> dict:
    """
    Veritabanındaki açık AI tahminlerini canlı piyasa fiyatlarıyla karşılaştırır,
    hedef/stop durumunu günceller ve Telegram için 'AI Tahmin Karnesi' oluşturur.
    """
    fetcher = price_fetcher or _default_price_fetcher
    open_preds = get_open_ai_predictions()

    if not open_preds:
        return {
            "checked_count": 0,
            "report_message": None
        }

    lines = ["<b>🎯 AI TAHMİN DOĞRULAMA KARNESİ</b>\n"]
    checked = 0

    for pred in open_preds:
        sym = pred["symbol"]
        cur_p = fetcher(sym)
        if cur_p is None or cur_p <= 0:
            continue

        entry_p = float(pred["entry_price"])
        target_p = float(pred["target_price"])
        stop_l = float(pred["stop_loss"])
        pnl_pct = round(((cur_p - entry_p) / entry_p) * 100.0, 2) if entry_p > 0 else 0.0

        if cur_p >= target_p:
            new_status = "HIT_TARGET"
            status_label = "🎯 Hedefe Ulaştı!"
        elif cur_p <= stop_l:
            new_status = "HIT_STOP"
            status_label = "🛑 Stop Oldu"
        else:
            new_status = "OPEN"
            status_label = "📈 Doğru Yönde (Kârda)" if pnl_pct > 0 else "📉 Ekside (İzleniyor)"

        update_ai_prediction_status(pred["id"], cur_p, pnl_pct, new_status)
        checked += 1

        sign = "+" if pnl_pct > 0 else ""
        lines.append(
            f"• <b>{sym}</b> ({pred['decision']}): <code>{entry_p:.2f}₺</code> → <code>{cur_p:.2f}₺</code> (<b>{sign}{pnl_pct:.2f}%</b>)\n"
            f"  Durum: {status_label}"
        )

    if checked == 0:
        return {"checked_count": 0, "report_message": None}

    stats = get_ai_prediction_stats()
    lines.append(
        f"\n📊 <b>Genel Başarı:</b> {stats['wins']}/{stats['total']} İsabet (<b>%{stats['accuracy_pct']}</b>)"
    )

    return {
        "checked_count": checked,
        "report_message": "\n".join(lines)
    }
