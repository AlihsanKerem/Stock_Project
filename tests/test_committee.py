"""
🧪 Unit Tests for BIST Investment Committee (ai-hedge-fund adaptations)
Tests the 4-role multi-agent committee, signal reconciliation, and deterministic fallback.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from committee_engine import (
    BistInvestmentCommittee,
    reconcile_committee_views,
    build_deterministic_committee_report
)

class TestInvestmentCommittee(unittest.TestCase):
    def setUp(self):
        self.sample_metrics = {
            "symbol": "THYAO",
            "current_price": 310.50,
            "pe_ratio": 4.8,
            "pb_ratio": 0.85,
            "dividend_yield": 3.2,
            "rsi": 42.0,
            "trend": "YUKARI",
            "volume_confirmation": True,
            "atr_14": 8.4,
            "risk_level": "Orta",
            "stop_loss": 293.70,
            "setups": [{"setup_type": "BOĞA_FLAMASI_KIRILIMI", "confidence": 80}]
        }

    def test_reconcile_conflicting_views(self):
        # Value is very bullish, Momentum is bearish
        value_report = {"stance": "BULLISH", "score": 85, "thesis": "Hisse F/K 4.8 ile çok ucuz."}
        momentum_report = {"stance": "BEARISH", "score": 35, "thesis": "Kısa vadeli satış baskısı var."}
        risk_report = {"risk_score": 60, "max_allocation_pct": 10.0, "warning": "ATR oynaklığı normal."}

        final = reconcile_committee_views("THYAO", value_report, momentum_report, risk_report)
        self.assertIn("final_decision", final)
        self.assertIn("consensus_score", final)
        self.assertIn("executive_summary", final)
        # Check that it recommends scaling or balanced approach
        self.assertIn(final["final_decision"], ["KADEMELİ AL", "TUT / İZLE", "DENGELİ"])

    def test_deterministic_committee_report(self):
        rep = build_deterministic_committee_report(self.sample_metrics)
        self.assertEqual(rep["symbol"], "THYAO")
        self.assertIn("final_decision", rep)
        self.assertIn("value_analyst", rep)
        self.assertIn("momentum_analyst", rep)
        self.assertIn("risk_officer", rep)
        self.assertIn("chief_portfolio_manager", rep)
        self.assertGreaterEqual(rep["consensus_score"], 0)
        self.assertLessEqual(rep["consensus_score"], 100)

    @patch("committee_engine.LLMAdapter.call_llm")
    def test_committee_llm_execution(self, mock_call):
        mock_call.return_value = (
            "GÖRÜŞ: KADEMELİ AL\n"
            "SKOR: 78\n"
            "ÖZET: Temel rasyolar oldukça cazip, kısa vade volatiliteye karşı kademeli alım önerilir."
        )
        committee = BistInvestmentCommittee()
        rep = committee.evaluate_stock("THYAO", sample_metrics=self.sample_metrics)
        self.assertEqual(rep["symbol"], "THYAO")
        self.assertIn("chief_portfolio_manager", rep)

if __name__ == "__main__":
    unittest.main()
