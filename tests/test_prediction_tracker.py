"""
🧪 Unit Tests for Prediction Tracker, BIST Market Hours Guard & Smart Funnel Digest
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
from prediction_tracker import (
    is_bist_market_open,
    is_weekday,
    select_top_candidates,
    run_funnel_committee_digest,
    evaluate_open_predictions
)

class TestMarketHours(unittest.TestCase):
    def test_weekday_session_open(self):
        # Monday 10:30
        self.assertTrue(is_bist_market_open(datetime(2026, 11, 9, 10, 30)))
        # Friday 18:15
        self.assertTrue(is_bist_market_open(datetime(2026, 11, 13, 18, 15)))

    def test_weekday_outside_session(self):
        # Monday 09:00 (before open)
        self.assertFalse(is_bist_market_open(datetime(2026, 11, 9, 9, 0)))
        # Wednesday 21:00 (night)
        self.assertFalse(is_bist_market_open(datetime(2026, 11, 11, 21, 0)))

    def test_weekend_closed(self):
        # Saturday 14:00
        self.assertFalse(is_bist_market_open(datetime(2026, 11, 14, 14, 0)))
        self.assertFalse(is_weekday(datetime(2026, 11, 14, 14, 0)))
        # Sunday 11:00
        self.assertFalse(is_bist_market_open(datetime(2026, 11, 15, 11, 0)))
        self.assertFalse(is_weekday(datetime(2026, 11, 15, 11, 0)))

class TestFunnelAndPredictions(unittest.TestCase):
    def setUp(self):
        # Clear any test predictions
        conn = database.get_connection()
        conn.execute("DELETE FROM ai_predictions WHERE symbol IN ('TESTA', 'TESTB', 'TESTC')")
        conn.commit()
        conn.close()

    def tearDown(self):
        conn = database.get_connection()
        conn.execute("DELETE FROM ai_predictions WHERE symbol IN ('TESTA', 'TESTB', 'TESTC')")
        conn.commit()
        conn.close()

    def test_select_top_candidates(self):
        signals = [
            {"symbol": "TESTA.IS", "action": "BUY", "is_conflict": 0, "is_validated": 1, "win_rate": 68.0, "avg_return": 4.2},
            {"symbol": "TESTA.IS", "action": "BUY", "is_conflict": 0, "is_validated": 1, "win_rate": 62.0, "avg_return": 3.1},
            {"symbol": "TESTB.IS", "action": "SELL", "is_conflict": 0, "is_validated": 1, "win_rate": 75.0, "avg_return": 5.0},
            {"symbol": "TESTC.IS", "action": "BUY", "is_conflict": 1, "is_validated": 1, "win_rate": 80.0, "avg_return": 6.0},
            {"symbol": "THYAO.IS", "action": "BUY", "is_conflict": 0, "is_validated": 1, "win_rate": 72.0, "avg_return": 5.5},
        ]
        top = select_top_candidates(signals, max_candidates=2)
        # Should pick THYAO and TESTA (no SELL, no conflict, deduplicated)
        self.assertEqual(top, ["THYAO", "TESTA"])

    @patch("prediction_tracker.run_time_machine_simulation")
    @patch("prediction_tracker.BistInvestmentCommittee")
    def test_run_funnel_committee_digest(self, mock_comm_cls, mock_tm):
        mock_comm = MagicMock()
        mock_comm.evaluate_stock.return_value = {
            "symbol": "TESTA",
            "current_price": 100.0,
            "consensus_score": 82,
            "final_decision": "GÜÇLÜ AL",
            "executive_summary": "Güçlü temel ve teknik uyum."
        }
        mock_comm_cls.return_value = mock_comm

        mock_tm.return_value = {
            "status": "success",
            "brackets": {"entry_price": 100.0, "stop_loss": 94.0, "target_1": 106.0, "target_2": 112.0},
            "simulation": {"win_rate_percent": 65.0, "profit_factor": 1.8}
        }

        signals = [{"symbol": "TESTA.IS", "action": "BUY", "is_conflict": 0, "is_validated": 1, "win_rate": 65.0, "avg_return": 4.0}]
        res = run_funnel_committee_digest(signals, max_candidates=3)

        self.assertEqual(len(res["evaluated"]), 1)
        self.assertIn("TESTA", res["digest_message"])
        self.assertIn("GÜÇLÜ AL", res["digest_message"])

        # Verify saved to ai_predictions
        open_preds = database.get_open_ai_predictions()
        symbols = [p["symbol"] for p in open_preds]
        self.assertIn("TESTA", symbols)

    def test_evaluate_open_predictions(self):
        database.save_ai_prediction("TESTA", "GÜÇLÜ AL", 85, 100.0, 106.0, 95.0)
        database.save_ai_prediction("TESTB", "KADEMELİ AL", 72, 50.0, 55.0, 47.0)

        def mock_fetcher(sym):
            return {"TESTA": 107.0, "TESTB": 46.5}.get(sym)

        res = evaluate_open_predictions(price_fetcher=mock_fetcher)
        self.assertGreaterEqual(res["checked_count"], 2)
        self.assertIn("TESTA", res["report_message"])
        self.assertIn("Hedefe", res["report_message"])
        self.assertIn("TESTB", res["report_message"])
        self.assertIn("Stop", res["report_message"])

    def test_save_ai_prediction_preserves_original_entry(self):
        database.save_ai_prediction("TESTA", "KADEMELİ AL", 70, 100.0, 106.0, 95.0)
        # Attempt to save again while OPEN with a different price
        database.save_ai_prediction("TESTA", "GÜÇLÜ AL", 80, 92.0, 98.0, 88.0)

        open_preds = [p for p in database.get_open_ai_predictions() if p["symbol"] == "TESTA"]
        self.assertEqual(len(open_preds), 1)
        self.assertEqual(open_preds[0]["entry_price"], 100.0)

    def test_evaluate_open_predictions_flat_zero_pct(self):
        database.save_ai_prediction("TESTC", "KADEMELİ AL", 70, 50.0, 55.0, 47.0)
        res = evaluate_open_predictions(price_fetcher=lambda s: 50.0 if s == "TESTC" else None)
        self.assertIn("Yatay", res["report_message"])

    @patch("prediction_tracker.run_time_machine_simulation")
    @patch("prediction_tracker.BistInvestmentCommittee")
    def test_funnel_penalizes_low_time_machine(self, mock_comm_cls, mock_tm):
        mock_comm = MagicMock()
        mock_comm.evaluate_stock.return_value = {
            "symbol": "TESTC",
            "current_price": 100.0,
            "consensus_score": 70,
            "final_decision": "GÜÇLÜ AL",
            "executive_summary": "Özet."
        }
        mock_comm_cls.return_value = mock_comm

        mock_tm.return_value = {
            "status": "success",
            "brackets": {"entry_price": 100.0, "stop_loss": 94.0, "target_1": 106.0},
            "simulation": {"win_rate_percent": 32.0, "profit_factor": 0.9}
        }

        signals = [{"symbol": "TESTC.IS", "action": "BUY", "is_conflict": 0, "is_validated": 1, "win_rate": 60.0, "avg_return": 3.0}]
        res = run_funnel_committee_digest(signals, max_candidates=3)
        item = res["evaluated"][0]
        self.assertEqual(item["score"], 55)
        self.assertNotEqual(item["decision"], "GÜÇLÜ AL")
        # Low time machine (<45%) should NOT be saved as an active AL prediction
        open_syms = [p["symbol"] for p in database.get_open_ai_predictions()]
        self.assertNotIn("TESTC", open_syms)

if __name__ == "__main__":
    unittest.main()
