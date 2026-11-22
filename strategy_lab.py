"""
🧪 BIST Strateji Laboratuvarı (Çoklu Sanal Portföy & Öz-Denetim Motoru)
- Kısa (3 iş günü), Orta (7 iş günü), Uzun (21 iş günü) vadelerde 9 farklı strateji portföyü
- Her portföy 2.000 TL sanal sermaye ile başlar
- Vade/döngü sonunda Öz-Denetim Ajanı (Self-Audit) kaybedilen kuralları teşhis edip
  güvenli sınırlar (guardrails) içinde parametreleri evrimleştirir (v1 -> v2)
"""

import json
import re
from datetime import datetime
import yfinance as yf

from database import (
    upsert_lab_portfolio,
    get_all_lab_portfolios,
    get_lab_portfolio_by_code,
    update_lab_portfolio_state,
    add_lab_position,
    get_lab_positions,
    update_lab_position,
    save_lab_audit_log,
    get_all_stock_data
)
from agent_engine import LLMAdapter
from day_trader_engine import format_bist_symbol, clean_bist_symbol

DEFAULT_PORTFOLIO_BLUEPRINTS = [
    # --- KISA VADE (3 İŞ GÜNÜ) ---
    {
        "code": "K1",
        "name": "Kısa Vade Kırılım (Breakout)",
        "horizon_days": 3,
        "initial_capital": 2000.0,
        "params": {
            "max_positions": 3,
            "min_rsi": 45.0,
            "max_rsi": 72.0,
            "min_tm_wr": 45.0,
            "stop_atr_mult": 1.3,
            "target_atr_mult": 2.2,
            "require_uptrend": 0
        },
        "bounds": {
            "max_positions": [2, 4],
            "min_rsi": [35.0, 55.0],
            "max_rsi": [58.0, 78.0],
            "min_tm_wr": [35.0, 65.0],
            "stop_atr_mult": [1.0, 2.5],
            "target_atr_mult": [1.5, 4.0]
        }
    },
    {
        "code": "K2",
        "name": "Kısa Vade Aşırı Satım Tepkisi",
        "horizon_days": 3,
        "initial_capital": 2000.0,
        "params": {
            "max_positions": 3,
            "min_rsi": 20.0,
            "max_rsi": 42.0,
            "min_tm_wr": 35.0,
            "stop_atr_mult": 1.5,
            "target_atr_mult": 2.0,
            "require_uptrend": 0
        },
        "bounds": {
            "max_positions": [2, 4],
            "min_rsi": [15.0, 35.0],
            "max_rsi": [32.0, 52.0],
            "min_tm_wr": [30.0, 60.0],
            "stop_atr_mult": [1.0, 2.5],
            "target_atr_mult": [1.5, 3.5]
        }
    },
    {
        "code": "K3",
        "name": "Kısa Vade Sıkı Stop Momentum",
        "horizon_days": 3,
        "initial_capital": 2000.0,
        "params": {
            "max_positions": 2,
            "min_rsi": 48.0,
            "max_rsi": 68.0,
            "min_tm_wr": 40.0,
            "stop_atr_mult": 1.2,
            "target_atr_mult": 2.4,
            "require_uptrend": 1
        },
        "bounds": {
            "max_positions": [2, 4],
            "min_rsi": [40.0, 58.0],
            "max_rsi": [60.0, 75.0],
            "min_tm_wr": [35.0, 65.0],
            "stop_atr_mult": [1.0, 2.0],
            "target_atr_mult": [1.8, 3.5]
        }
    },
    # --- ORTA VADE (7 İŞ GÜNÜ) ---
    {
        "code": "O1",
        "name": "Orta Vade Komite Konsensüs",
        "horizon_days": 7,
        "initial_capital": 2000.0,
        "params": {
            "max_positions": 3,
            "min_rsi": 35.0,
            "max_rsi": 65.0,
            "max_pe": 18.0,
            "min_tm_wr": 42.0,
            "stop_atr_mult": 1.6,
            "target_atr_mult": 2.8,
            "require_uptrend": 0
        },
        "bounds": {
            "max_positions": [2, 4],
            "min_rsi": [25.0, 45.0],
            "max_rsi": [55.0, 75.0],
            "max_pe": [8.0, 30.0],
            "min_tm_wr": [35.0, 65.0],
            "stop_atr_mult": [1.2, 2.8],
            "target_atr_mult": [2.0, 4.5]
        }
    },
    {
        "code": "O2",
        "name": "Orta Vade Trend Takip",
        "horizon_days": 7,
        "initial_capital": 2000.0,
        "params": {
            "max_positions": 3,
            "min_rsi": 45.0,
            "max_rsi": 70.0,
            "min_tm_wr": 40.0,
            "stop_atr_mult": 1.8,
            "target_atr_mult": 3.0,
            "require_uptrend": 1
        },
        "bounds": {
            "max_positions": [2, 4],
            "min_rsi": [35.0, 55.0],
            "max_rsi": [60.0, 78.0],
            "min_tm_wr": [30.0, 65.0],
            "stop_atr_mult": [1.2, 2.8],
            "target_atr_mult": [2.0, 5.0]
        }
    },
    {
        "code": "O3",
        "name": "Orta Vade Dengeli Düşük Risk",
        "horizon_days": 7,
        "initial_capital": 2000.0,
        "params": {
            "max_positions": 3,
            "min_rsi": 35.0,
            "max_rsi": 62.0,
            "max_pb": 3.0,
            "stop_atr_mult": 2.0,
            "target_atr_mult": 2.6,
            "require_uptrend": 0
        },
        "bounds": {
            "max_positions": [2, 4],
            "min_rsi": [25.0, 45.0],
            "max_rsi": [52.0, 70.0],
            "max_pb": [1.2, 5.0],
            "stop_atr_mult": [1.5, 3.0],
            "target_atr_mult": [2.0, 4.0]
        }
    },
    # --- UZUN VADE (21 İŞ GÜNÜ) ---
    {
        "code": "U1",
        "name": "Uzun Vade Değer Avcısı (Graham)",
        "horizon_days": 21,
        "initial_capital": 2000.0,
        "params": {
            "max_positions": 3,
            "min_rsi": 25.0,
            "max_rsi": 65.0,
            "max_pe": 10.0,
            "max_pb": 1.8,
            "stop_atr_mult": 2.2,
            "target_atr_mult": 4.0,
            "require_uptrend": 0
        },
        "bounds": {
            "max_positions": [2, 4],
            "max_rsi": [50.0, 75.0],
            "max_pe": [5.0, 18.0],
            "max_pb": [0.8, 3.5],
            "stop_atr_mult": [1.5, 3.2],
            "target_atr_mult": [2.5, 6.0]
        }
    },
    {
        "code": "U2",
        "name": "Uzun Vade Temettü Kalesi",
        "horizon_days": 21,
        "initial_capital": 2000.0,
        "params": {
            "max_positions": 3,
            "min_rsi": 30.0,
            "max_rsi": 68.0,
            "min_div_yield": 2.0,
            "max_pe": 15.0,
            "stop_atr_mult": 2.2,
            "target_atr_mult": 3.5,
            "require_uptrend": 0
        },
        "bounds": {
            "max_positions": [2, 4],
            "min_div_yield": [1.0, 6.0],
            "max_pe": [8.0, 25.0],
            "stop_atr_mult": [1.5, 3.2],
            "target_atr_mult": [2.5, 5.5]
        }
    },
    {
        "code": "U3",
        "name": "Uzun Vade Bileşik Büyüme",
        "horizon_days": 21,
        "initial_capital": 2000.0,
        "params": {
            "max_positions": 3,
            "min_rsi": 40.0,
            "max_rsi": 72.0,
            "max_pe": 22.0,
            "stop_atr_mult": 2.0,
            "target_atr_mult": 4.2,
            "require_uptrend": 1
        },
        "bounds": {
            "max_positions": [2, 4],
            "min_rsi": [30.0, 50.0],
            "max_rsi": [60.0, 78.0],
            "max_pe": [12.0, 35.0],
            "stop_atr_mult": [1.5, 3.0],
            "target_atr_mult": [3.0, 6.0]
        }
    }
]

def clamp_param(value, bounds):
    """Parametreyi [min, max] güvenlik sınırları içinde tutar."""
    low, high = bounds[0], bounds[1]
    if isinstance(low, int) and isinstance(high, int):
        return int(max(low, min(high, round(float(value)))))
    return round(max(float(low), min(float(high), float(value))), 2)

def initialize_lab_portfolios():
    """9 strateji portföyünü veritabanında oluşturur (zaten varsa korur)."""
    for bp in DEFAULT_PORTFOLIO_BLUEPRINTS:
        upsert_lab_portfolio(
            code=bp["code"],
            name=bp["name"],
            horizon_days=bp["horizon_days"],
            initial_capital=bp["initial_capital"],
            cash_balance=bp["initial_capital"],
            version=1,
            params_json=bp["params"],
            param_bounds_json=bp["bounds"]
        )

def build_market_candidates_from_db():
    """
    Veritabanındaki (stocks.db -> stock_data) güncel BIST verilerini portföy seçim havuzuna dönüştürür.
    """
    rows = get_all_stock_data()
    candidates = []
    for r in rows:
        price = float(r.get("price") or 0.0)
        if price <= 0:
            continue
        rsi = float(r.get("rsi") or 50.0)
        pe = float(r["pe_ratio"]) if r.get("pe_ratio") is not None else None
        pb = float(r["pb_ratio"]) if r.get("pb_ratio") is not None else None
        div_y = float(r.get("div_yield") or 0.0)
        atr = float(r.get("atr") or (price * 0.03))
        signals_str = str(r.get("signals") or "")

        # Sinyal metinlerinden basit trend tahmini
        trend = "YUKARI" if ("trend" in signals_str.lower() or rsi >= 52) and "trend_kirilimi" not in signals_str.lower() else "AŞAĞI" if rsi < 42 else "NÖTR"

        candidates.append({
            "symbol": clean_bist_symbol(r["symbol"]),
            "price": price,
            "rsi": rsi,
            "pe_ratio": pe,
            "pb_ratio": pb,
            "div_yield": div_y,
            "atr": atr,
            "trend": trend,
            "tm_wr": 50.0,
            "committee_score": 65 if signals_str else 50
        })
    return candidates

def select_stocks_for_portfolio(portfolio: dict, candidates: list) -> list:
    """
    Portföyün güncel parametrelerine (params) ve 2.000 TL bütçe sınırına göre
    en uygun hisseleri seçer.
    """
    params = portfolio["params"]
    cash = float(portfolio.get("cash_balance") or 0.0)
    max_pos = int(params.get("max_positions", 3))
    if cash <= 0 or max_pos <= 0:
        return []

    per_stock_budget = cash / max_pos
    min_rsi = float(params.get("min_rsi", 0.0))
    max_rsi = float(params.get("max_rsi", 100.0))
    max_pe = params.get("max_pe")
    max_pb = params.get("max_pb")
    min_div = params.get("min_div_yield")
    min_tm = params.get("min_tm_wr")
    req_uptrend = int(params.get("require_uptrend", 0))

    matching = []
    for c in candidates:
        price = float(c.get("price") or 0.0)
        if price <= 0 or price > per_stock_budget:
            # 1 lot bile bütçeye sığmıyorsa atla
            continue

        rsi = float(c.get("rsi") or 50.0)
        if not (min_rsi <= rsi <= max_rsi):
            continue

        if req_uptrend and c.get("trend") != "YUKARI":
            continue

        pe = c.get("pe_ratio")
        if max_pe is not None and (pe is None or pe <= 0 or pe > float(max_pe)):
            continue

        pb = c.get("pb_ratio")
        if max_pb is not None and (pb is None or pb <= 0 or pb > float(max_pb)):
            continue

        div_y = float(c.get("div_yield") or 0.0)
        if min_div is not None and div_y < float(min_div):
            continue

        tm_wr = float(c.get("tm_wr") or 50.0)
        if min_tm is not None and tm_wr < float(min_tm):
            continue

        matching.append(c)

    # Stratejiye göre sırala
    code = portfolio.get("code", "")
    if code.startswith("U"):
        # Uzun vade: düşük F/K ve yüksek temettü öncelikli
        matching.sort(key=lambda x: ((x.get("div_yield") or 0.0) * 3.0) - (x.get("pe_ratio") or 15.0), reverse=True)
    elif code == "K2":
        # Tepki: en düşük RSI
        matching.sort(key=lambda x: x.get("rsi") or 50.0)
    else:
        # Kırılım/Momentum/Orta Vade: yüksek komite skoru + TM
        matching.sort(key=lambda x: (x.get("committee_score") or 50) + (x.get("tm_wr") or 50), reverse=True)

    return matching[:max_pos]

def open_positions_for_portfolio(portfolio: dict, picks: list) -> list:
    """Seçilen hisseler için sanal lot hesabı yapıp lab_positions tablosuna kaydeder."""
    if not picks:
        return []

    cash = float(portfolio["cash_balance"])
    params = portfolio["params"]
    stop_mult = float(params.get("stop_atr_mult", 1.5))
    target_mult = float(params.get("target_atr_mult", 2.5))

    alloc_per_stock = cash / len(picks)
    opened = []
    spent_total = 0.0

    for item in picks:
        price = float(item["price"])
        lots = int(alloc_per_stock // price)
        if lots < 1:
            continue

        cost = lots * price
        if spent_total + cost > cash:
            continue

        atr = float(item.get("atr") or (price * 0.03))
        stop_loss = round(max(price - (stop_mult * atr), 0.01), 2)
        target_price = round(price + (target_mult * atr), 2)

        pos_id = add_lab_position(
            portfolio_id=portfolio["id"],
            symbol=item["symbol"],
            lots=lots,
            entry_price=price,
            target_price=target_price,
            stop_loss=stop_loss
        )
        spent_total += cost
        opened.append({"pos_id": pos_id, "symbol": item["symbol"], "lots": lots, "entry_price": price})

    if spent_total > 0:
        new_cash = round(cash - spent_total, 2)
        update_lab_portfolio_state(portfolio["id"], new_cash, portfolio["version"], params)

    return opened

def _default_price_fetcher(symbol: str):
    try:
        ticker = yf.Ticker(format_bist_symbol(symbol))
        hist = ticker.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None

def evaluate_portfolio_positions(portfolio: dict, price_fetcher=None, now: datetime = None) -> dict:
    """
    Portföyün açık pozisyonlarını canlı fiyatla günceller;
    Hedef, Stop veya Vade Sonu (EXPIRED) koşuluna ulaşılanları kapatıp nakdi geri ekler.
    """
    fetcher = price_fetcher or _default_price_fetcher
    cur_dt = now or datetime.now()
    open_pos = get_lab_positions(portfolio["id"], status="OPEN")

    if not open_pos:
        return {"closed_count": 0, "open_count": 0}

    cash = float(portfolio["cash_balance"])
    horizon_days = int(portfolio["horizon_days"])
    closed_count = 0
    wins_inc = 0
    remaining_open = 0

    for pos in open_pos:
        cur_p = fetcher(pos["symbol"])
        if cur_p is None or cur_p <= 0:
            remaining_open += 1
            continue

        entry_p = float(pos["entry_price"])
        lots = int(pos["lots"])
        pnl_tl = round((cur_p - entry_p) * lots, 2)
        pnl_pct = round(((cur_p - entry_p) / entry_p) * 100.0, 2) if entry_p > 0 else 0.0

        # Vade doldu mu kontrolü
        opened_str = str(pos.get("opened_at") or "")
        age_days = 0
        try:
            opened_dt = datetime.fromisoformat(opened_str.replace("Z", ""))
            age_days = (cur_dt - opened_dt).days
        except Exception:
            age_days = 0

        if cur_p >= float(pos["target_price"]):
            new_status = "HIT_TARGET"
        elif cur_p <= float(pos["stop_loss"]):
            new_status = "HIT_STOP"
        elif age_days >= horizon_days:
            new_status = "EXPIRED"
        else:
            new_status = "OPEN"

        update_lab_position(pos["id"], cur_p, pnl_tl, pnl_pct, new_status)

        if new_status != "OPEN":
            closed_count += 1
            cash += round(lots * cur_p, 2)
            if pnl_tl > 0:
                wins_inc += 1
        else:
            remaining_open += 1

    if closed_count > 0:
        update_lab_portfolio_state(
            portfolio["id"], round(cash, 2), portfolio["version"],
            portfolio["params"], total_trades_inc=closed_count, win_trades_inc=wins_inc
        )

    return {"closed_count": closed_count, "open_count": remaining_open}

def run_portfolio_self_audit(portfolio: dict) -> dict:
    """
    Öz-Denetim Ajanı (Self-Audit):
    Portföyün kapanan işlemlerini inceler, neden kaybettiğini/kazandığını teşhis eder,
    güvenli sınırlar (param_bounds) içinde parametreleri günceller ve loglar.
    """
    all_pos = get_lab_positions(portfolio["id"])
    closed_pos = [p for p in all_pos if p["status"] != "OPEN"][:10]
    if not closed_pos:
        return None

    avg_pnl_pct = round(sum(float(p["pnl_pct"]) for p in closed_pos) / len(closed_pos), 2)
    old_params = dict(portfolio["params"])
    bounds = portfolio["bounds"]
    old_ver = int(portfolio["version"])
    new_ver = old_ver + 1

    # LLM'den teşhis ve JSON parametre önerisi iste
    trades_summary = "\n".join([
        f"- {p['symbol']}: Giriş {p['entry_price']}₺ -> Çıkış {p['current_price']}₺ ({p['pnl_pct']}%, {p['status']})"
        for p in closed_pos
    ])

    prompt = (
        f"Sen Strateji Laboratuvarı Öz-Denetim Mühendisisin.\n"
        f"Portföy: {portfolio['code']} - {portfolio['name']} (Vade: {portfolio['horizon_days']} gün)\n"
        f"Mevcut Parametreler: {json.dumps(old_params, ensure_ascii=False)}\n"
        f"İzin Verilen Güvenli Sınırlar: {json.dumps(bounds, ensure_ascii=False)}\n"
        f"Son Kapanan İşlemler (Ortalama %{avg_pnl_pct}):\n{trades_summary}\n\n"
        f"GÖREV: Hangi kural yüzünden kaybettik/kazandık teşhis et ve en fazla 2 parametreyi güvenli sınırlar içinde iyileştir.\n"
        f"Sadece şu JSON formatında yanıt ver:\n"
        f'{{"diagnosis": "Kısa Türkçe teşhis cümlesi", "changes": {{"param_adi": yeni_sayi}}}}'
    )

    diagnosis = None
    suggested_changes = {}

    try:
        llm = LLMAdapter()
        raw_res = llm.call_llm([
            {"role": "system", "content": "Sadece geçerli JSON döndür. Kod veya markdown dışı gereksiz metin yazma."},
            {"role": "user", "content": prompt}
        ])
        match = re.search(r"\{.*\}", raw_res, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            diagnosis = parsed.get("diagnosis")
            suggested_changes = parsed.get("changes", {})
    except Exception:
        pass

    # LLM yanıt veremezse veya boş dönerse deterministik kural tabanlı evrim uygula
    if not diagnosis or not isinstance(suggested_changes, dict) or not suggested_changes:
        stops = sum(1 for p in closed_pos if p["status"] == "HIT_STOP")
        if avg_pnl_pct < 0:
            if stops > 0 and "stop_atr_mult" in bounds:
                new_stop = clamp_param(float(old_params.get("stop_atr_mult", 1.5)) + 0.2, bounds["stop_atr_mult"])
                suggested_changes["stop_atr_mult"] = new_stop
                diagnosis = f"Son döngüde ortalama %{avg_pnl_pct} kayıp ve {stops} stop gerçekleşti; gürültüye takılmamak için ATR stop çarpanı esnetildi."
            elif "max_rsi" in bounds:
                new_rsi = clamp_param(float(old_params.get("max_rsi", 65)) - 3.0, bounds["max_rsi"])
                suggested_changes["max_rsi"] = new_rsi
                diagnosis = f"Ortalama %{avg_pnl_pct} getiri nedeniyle aşırı alım riskini azaltmak için RSI tavanı düşürüldü."
            else:
                diagnosis = f"Ortalama %{avg_pnl_pct} performans sonrası parametreler korundu."
        else:
            diagnosis = f"Döngü ortalama +%{avg_pnl_pct} kârla tamamlandı; başarılı kurallar bir sonraki tura taşındı."

    # Değişiklikleri güvenli sınırlar (guardrails) içinde uygula
    new_params = dict(old_params)
    applied_diff = {}
    for k, v in suggested_changes.items():
        if k in bounds and k in old_params:
            clamped_val = clamp_param(v, bounds[k])
            if clamped_val != old_params[k]:
                applied_diff[k] = {"old": old_params[k], "new": clamped_val}
                new_params[k] = clamped_val

    update_lab_portfolio_state(portfolio["id"], portfolio["cash_balance"], new_ver, new_params)
    save_lab_audit_log(portfolio["id"], old_ver, new_ver, avg_pnl_pct, diagnosis, applied_diff)

    return {
        "portfolio_code": portfolio["code"],
        "version_from": old_ver,
        "version_to": new_ver,
        "cycle_pnl_pct": avg_pnl_pct,
        "diagnosis": diagnosis,
        "applied_diff": applied_diff
    }

def run_lab_daily_cycle(price_fetcher=None) -> dict:
    """
    Tüm 9 Strateji Portföyünü günlük olarak günceller:
    1. Eksik portföyleri kurar (2.000 TL)
    2. Açık pozisyonları günceller / kapatır
    3. Boşalan portföylerde Öz-Denetim çalıştırır ve yeni tura geçer
    """
    initialize_lab_portfolios()
    portfolios = get_all_lab_portfolios()
    candidates = build_market_candidates_from_db()

    audit_events = []
    opened_total = 0

    for p in portfolios:
        eval_res = evaluate_portfolio_positions(p, price_fetcher=price_fetcher)
        # Güncel portföyü yeniden oku
        p = get_lab_portfolio_by_code(p["code"])

        if eval_res["open_count"] == 0:
            # Eğer daha önce kapanmış işlemi varsa Öz-Denetim yap
            closed_hist = [pos for pos in get_lab_positions(p["id"]) if pos["status"] != "OPEN"]
            if closed_hist and eval_res["closed_count"] > 0:
                audit_res = run_portfolio_self_audit(p)
                if audit_res:
                    audit_events.append(audit_res)
                p = get_lab_portfolio_by_code(p["code"])

            # Yeni tura hisse seçip sanal alım yap
            if candidates:
                picks = select_stocks_for_portfolio(p, candidates)
                opened = open_positions_for_portfolio(p, picks)
                opened_total += len(opened)

    telegram_msg = None
    if audit_events:
        lines = ["<b>🧪 STRATEJİ LAB ÖZ-DENETİM & EVRİM RAPORU</b>\n"]
        for ev in audit_events:
            diff_str = ", ".join([f"{k}: {v['old']}→{v['new']}" for k, v in ev["applied_diff"].items()]) or "Parametreler korundu"
            lines.append(
                f"• <b>{ev['portfolio_code']}</b> (v{ev['version_from']}→v{ev['version_to']}, Döngü: %{ev['cycle_pnl_pct']})\n"
                f"  Teşhis: <i>{ev['diagnosis']}</i>\n"
                f"  Ayar: <code>{diff_str}</code>"
            )
        telegram_msg = "\n".join(lines)

    return {
        "portfolios_count": len(portfolios),
        "opened_positions": opened_total,
        "audit_events": audit_events,
        "telegram_message": telegram_msg
    }
