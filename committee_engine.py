"""
🏛️ BIST Investment Committee Engine (virattt/ai-hedge-fund BIST Adaptasyonu)
Çoklu Ajan Hiyerarşisi:
1. Değer Analisti (Value & Fundamentals - Graham/Buffett Ekolü)
2. Momentum & Teknik Analist (Trend, RSI, Volume, Day-Trader Formasyonları)
3. Baş Risk Yöneticisi (Risk Officer - ATR Stop, Volatilite, Sermaye Koruma)
4. Baş Portföy Yöneticisi (Chief Portfolio Manager - Çelişki Uzlaştırma & Nihai Karar)
"""

import os
import re
import json
import yfinance as yf
from agent_engine import LLMAdapter
from day_trader_engine import (
    format_bist_symbol, clean_bist_symbol, calculate_atr, 
    detect_chart_setups, calculate_trade_brackets
)
from database import get_stock_data, get_portfolio_positions

def reconcile_committee_views(symbol: str, value_rep: dict, momentum_rep: dict, risk_rep: dict) -> dict:
    """
    ai-hedge-fund felsefesindeki 'Signal Reconciliation' mekanizması:
    Analistlerin (örneğin ucuz diyen Değer Analisti ile düşüş trendi diyen Momentum Analisti)
    çelişkilerini matematiksel ve mantıksal olarak dengeler.
    """
    val_score = float(value_rep.get("score", 50))
    mom_score = float(momentum_rep.get("score", 50))
    risk_score = float(risk_rep.get("risk_score", 50))
    
    val_stance = value_rep.get("stance", "NEUTRAL").upper()
    mom_stance = momentum_rep.get("stance", "NEUTRAL").upper()
    
    # Ağırlıklı Konsensüs Skoru: Değer %35, Momentum %35, Risk Sağlığı %30
    consensus_score = int(round((val_score * 0.35) + (mom_score * 0.35) + (risk_score * 0.30)))
    consensus_score = max(5, min(95, consensus_score))
    
    # Çelişki ve Karar Matrisi
    if val_stance == "BULLISH" and mom_stance == "BULLISH" and risk_score >= 50:
        decision = "GÜÇLÜ AL"
        summary = (
            f"{symbol} için hem temel rasyolar hem de teknik momentum güçlü bir alım fırsatına işaret ediyor. "
            f"Risk parametreleri kabul edilebilir seviyede, portföyde ağırlık artırılabilir."
        )
    elif val_stance == "BULLISH" and mom_stance in ["BEARISH", "NEUTRAL"]:
        decision = "KADEMELİ AL"
        summary = (
            f"{symbol} temel rasyolarıyla cazip ve iskontolu görünse de, kısa vadeli teknik göstergeler henüz dip dönüşünü "
            f"tamamlamamış olabilir. Risk yöneticisi tek seferde girmek yerine zamana yayılı 'kademeli alım' öneriyor."
        )
    elif val_stance in ["BEARISH", "NEUTRAL"] and mom_stance == "BULLISH":
        decision = "KISA VADELİ İZLE / AL-SAT"
        summary = (
            f"{symbol} üzerinde kısa vadeli kuvvetli bir hacim ve momentum var, ancak temel çarpanlar iskontolu değil. "
            f"Sıkı ATR stop seviyesine sadık kalınarak kısa vadeli swing işlemler değerlendirilebilir."
        )
    elif val_stance == "BEARISH" and mom_stance == "BEARISH":
        decision = "RİSKLİ / UZAK DUR"
        summary = (
            f"{symbol} hem yüksek çarpanları hem de negatif teknik trendi nedeniyle komite tarafından yüksek riskli "
            f"değerlendirildi. Yeni pozisyon açılması önerilmemektedir."
        )
    else:
        decision = "TUT / İZLE"
        summary = (
            f"{symbol} mevcut piyasa koşullarında dengeli/nötr bir bölgede fiyatlanıyor. "
            f"Mevcut pozisyonlar korunabilir, yeni giriş için net bir formasyon kırılımı beklenmeli."
        )
        
    return {
        "final_decision": decision,
        "consensus_score": consensus_score,
        "executive_summary": summary,
        "recommended_allocation_pct": risk_rep.get("max_allocation_pct", 10.0)
    }

def build_deterministic_committee_report(metrics: dict) -> dict:
    """
    LLM yanıt veremediğinde veya API anahtarı girilmediğinde deterministik
    kantitatif kurallarla eksiksiz bir yatırım komitesi raporu üretir.
    """
    sym = metrics.get("symbol", "BIST")
    cur_p = metrics.get("current_price", 0.0)
    pe = metrics.get("pe_ratio")
    pb = metrics.get("pb_ratio")
    rsi = metrics.get("rsi", 50.0)
    trend = metrics.get("trend", "NÖTR")
    atr = metrics.get("atr_14", cur_p * 0.03)
    stop_l = metrics.get("stop_loss", round(cur_p - (1.5 * atr), 2))
    setups = metrics.get("setups", [])
    
    # 1. Değer Analisti Hesaplaması
    val_score = 50
    val_points = []
    if pe is not None and pe > 0:
        if pe < 7.0:
            val_score += 25
            val_points.append(f"F/K ({pe:.1f}) BIST ortalamasının belirgin altında, derin iskonto var.")
        elif pe < 12.0:
            val_score += 10
            val_points.append(f"F/K ({pe:.1f}) makul ve dengeli seviyede.")
        else:
            val_score -= 15
            val_points.append(f"F/K ({pe:.1f}) tarihsel ortalamaların üzerinde, çarpan pahalı.")
            
    if pb is not None and pb > 0:
        if pb < 1.5:
            val_score += 15
            val_points.append(f"PD/DD ({pb:.2f}) defter değerine yakın işlem görüyor.")
        elif pb > 4.5:
            val_score -= 15
            val_points.append(f"PD/DD ({pb:.2f}) defter değerinin oldukça üzerinde.")
            
    val_score = max(10, min(95, val_score))
    val_stance = "BULLISH" if val_score >= 65 else "BEARISH" if val_score <= 40 else "NEUTRAL"
    val_thesis = " ".join(val_points) if val_points else f"{sym} temel rasyoları sektör ortalamaları ile uyumlu."
    
    # 2. Momentum Analisti Hesaplaması
    mom_score = 50
    mom_points = []
    if trend == "YUKARI":
        mom_score += 20
        mom_points.append("Fiyat orta vadeli yükselen ana trend kanalında ilerliyor.")
    elif trend == "AŞAĞI":
        mom_score -= 20
        mom_points.append("Fiyat düşen trend baskısı altında.")
        
    if rsi < 35:
        mom_score += 15
        mom_points.append(f"RSI ({rsi:.1f}) aşırı satım bölgesinde, yukarı yönlü teknik tepki bekleniyor.")
    elif rsi > 70:
        mom_score -= 15
        mom_points.append(f"RSI ({rsi:.1f}) aşırı alım bölgesinde, kâr realizasyonu riski yüksek.")
        
    for s in setups:
        if s.get("direction") == "LONG":
            mom_score += 10
            mom_points.append(f"Aktif Formasyon: {s.get('setup_type')} ({s.get('description', '')})")
            
    mom_score = max(10, min(95, mom_score))
    mom_stance = "BULLISH" if mom_score >= 65 else "BEARISH" if mom_score <= 40 else "NEUTRAL"
    mom_thesis = " ".join(mom_points) if mom_points else "Teknik göstergeler nötr bantta konsolide oluyor."
    
    # 3. Risk Yöneticisi Hesaplaması
    stop_distance_pct = round(((cur_p - stop_l) / cur_p) * 100, 2) if cur_p > 0 else 5.0
    risk_score = 70
    if stop_distance_pct > 8.0:
        risk_score -= 25
        max_alloc = 5.0
        risk_warning = f"ATR oynaklığı yüksek (Stop mesafesi %{stop_distance_pct:.1f}). Pozisyon boyutu küçük tutulmalı."
    elif stop_distance_pct < 4.0:
        risk_score += 15
        max_alloc = 15.0
        risk_warning = f"Düşük volatilite ve yakın stop seviyesi (%{stop_distance_pct:.1f}). Sermaye riski kontrollü."
    else:
        max_alloc = 10.0
        risk_warning = f"Normal BIST volatilitesi. Standart portföy ağırlığı (%{max_alloc}) uygulanabilir."
        
    value_rep = {"stance": val_stance, "score": val_score, "thesis": val_thesis}
    momentum_rep = {"stance": mom_stance, "score": mom_score, "thesis": mom_thesis}
    risk_rep = {
        "risk_score": risk_score, 
        "max_allocation_pct": max_alloc, 
        "stop_loss_level": stop_l, 
        "stop_distance_pct": stop_distance_pct,
        "warning": risk_warning
    }
    
    reconciliation = reconcile_committee_views(sym, value_rep, momentum_rep, risk_rep)
    
    return {
        "symbol": sym,
        "current_price": cur_p,
        "consensus_score": reconciliation["consensus_score"],
        "final_decision": reconciliation["final_decision"],
        "executive_summary": reconciliation["executive_summary"],
        "recommended_allocation_pct": reconciliation["recommended_allocation_pct"],
        "value_analyst": value_rep,
        "momentum_analyst": momentum_rep,
        "risk_officer": risk_rep,
        "chief_portfolio_manager": {
            "verdict": reconciliation["final_decision"],
            "consensus_score": reconciliation["consensus_score"],
            "summary": reconciliation["executive_summary"]
        }
    }

class BistInvestmentCommittee:
    """
    BIST hisseleri için 4 uzman ajanın komite değerlendirmesini yürüten orkestratör.
    """
    def __init__(self):
        self.llm = LLMAdapter()

    def fetch_metrics(self, symbol: str) -> dict:
        """Hisse verilerini ve teknik rasyolarını toplar."""
        clean_sym = clean_bist_symbol(symbol)
        full_sym = format_bist_symbol(symbol)
        
        # 1. SQLite veritabanı önceliği
        db_data = get_stock_data(clean_sym)
        cur_p = 0.0
        pe = None
        pb = None
        rsi = 50.0
        trend = "NÖTR"
        
        if db_data:
            cur_p = float(db_data.get('price', 0.0))
            pe_val = db_data.get('pe_ratio') if db_data.get('pe_ratio') is not None else db_data.get('pe')
            pe = float(pe_val) if pe_val is not None else None
            pb_val = db_data.get('pb_ratio') if db_data.get('pb_ratio') is not None else db_data.get('pb')
            pb = float(pb_val) if pb_val is not None else None
            rsi = float(db_data.get('rsi', 50.0))
            trend = db_data.get('trend', 'NÖTR')
            if db_data.get('atr'):
                cur_atr = float(db_data.get('atr'))
            if db_data.get('stop_loss'):
                stop_l = float(db_data.get('stop_loss'))
            
        # 2. yfinance üzerinden barları çek
        setups = []
        cur_atr = cur_p * 0.03
        try:
            ticker = yf.Ticker(full_sym)
            df = ticker.history(period="60d")
            if not df.empty:
                cur_p = float(df['Close'].iloc[-1])
                atr_s = calculate_atr(df)
                if not atr_s.empty:
                    cur_atr = float(atr_s.iloc[-1])
                setups = detect_chart_setups(df)
                
                # yfinance fundamentals
                info = getattr(ticker, 'info', {}) or {}
                if pe is None:
                    pe = info.get('trailingPE')
                if pb is None:
                    pb = info.get('priceToBook')
        except Exception:
            pass
            
        brackets = calculate_trade_brackets(cur_p, cur_atr)
        
        return {
            "symbol": clean_sym,
            "current_price": cur_p,
            "pe_ratio": pe,
            "pb_ratio": pb,
            "rsi": rsi,
            "trend": trend,
            "atr_14": cur_atr,
            "stop_loss": brackets.get("stop_loss", round(cur_p - (1.5 * cur_atr), 2)),
            "brackets": brackets,
            "setups": setups
        }

    def evaluate_stock(self, symbol: str, sample_metrics: dict = None) -> dict:
        """
        Komiteyi toplar ve hisse senedi hakkında nihai fon kararını üretir.
        """
        metrics = sample_metrics if sample_metrics else self.fetch_metrics(symbol)
        clean_sym = metrics.get("symbol", clean_bist_symbol(symbol))
        
        # Temel deterministik raporu hesapla
        deterministic_rep = build_deterministic_committee_report(metrics)
        
        # Eğer aktif bir LLM sağlayıcısı varsa, raporu profesyonel LLM sentezi ile zenginleştir
        prompt = (
            f"Sen bir Kurumsal BIST Portföy Yönetim Fonunun Baş Portföy Yöneticisisin (CIO).\n"
            f"Aşağıdaki analist raporlarını ve piyasa verilerini sentezle:\n"
            f"Hisse: {clean_sym}\n"
            f"Fiyat: {metrics.get('current_price')} TL\n"
            f"Değer Analisti: Skor {deterministic_rep['value_analyst']['score']}/100, Görüş: {deterministic_rep['value_analyst']['stance']}. Tez: {deterministic_rep['value_analyst']['thesis']}\n"
            f"Momentum Analisti: Skor {deterministic_rep['momentum_analyst']['score']}/100, Görüş: {deterministic_rep['momentum_analyst']['stance']}. Tez: {deterministic_rep['momentum_analyst']['thesis']}\n"
            f"Risk Yöneticisi: Risk Puanı {deterministic_rep['risk_officer']['risk_score']}/100. Stop-Loss: {deterministic_rep['risk_officer']['stop_loss_level']} TL. Uyarı: {deterministic_rep['risk_officer']['warning']}\n\n"
            f"GÖREV:\n"
            f"Analistler arasındaki çelişkileri (Reconciliation) değerlendir ve tek bir net kurumsal karar bülteni yaz.\n"
            f"Format:\n"
            f"GÖRÜŞ: [GÜÇLÜ AL / KADEMELİ AL / TUT / İZLE / KISA VADELİ İZLE / RİSKLİ / UZAK DUR]\n"
            f"SKOR: [1-100 arası nihai konsensüs puanı]\n"
            f"ÖZET: [Yatırımcıya 2-3 cümlelik net profesyonel stratejik tavsiye ve nedenleri]"
        )
        
        messages = [
            {"role": "system", "content": "Sen kurumun baş portföy yöneticisisin. Ciddi, rasyonel, analitik ve net konuşursun."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            llm_res = self.llm.call_llm(messages)
            if llm_res and "Sistem Bildirimi" not in llm_res and ("GÖRÜŞ" in llm_res or "ÖZET" in llm_res):
                # LLM çıktısından görüş ve özeti parse et
                match_verdict = re.search(r"GÖRÜŞ:\s*([^\n]+)", llm_res)
                match_score = re.search(r"SKOR:\s*(\d+)", llm_res)
                match_summary = re.search(r"ÖZET:\s*([^\n]+(?:\n[^\n]+)?)", llm_res)
                
                if match_verdict:
                    deterministic_rep["final_decision"] = match_verdict.group(1).strip()
                if match_score:
                    deterministic_rep["consensus_score"] = int(match_score.group(1).strip())
                if match_summary:
                    deterministic_rep["executive_summary"] = match_summary.group(1).strip()
                    
                deterministic_rep["chief_portfolio_manager"] = {
                    "verdict": deterministic_rep["final_decision"],
                    "consensus_score": deterministic_rep["consensus_score"],
                    "summary": deterministic_rep["executive_summary"],
                    "full_statement": llm_res
                }
        except Exception as e:
            print(f"[InvestmentCommittee] LLM çağrı uyarısı: {e}")
            
        return deterministic_rep
