"""
🧪 Unit Tests for Strategy Laboratory (9 Virtual Portfolios + Self-Audit + Bounded Tuning)
"""

import unittest
from unittest.mock import patch
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
from strategy_lab import (
    DEFAULT_PORTFOLIO_BLUEPRINTS,
    initialize_lab_portfolios,
    select_stocks_for_portfolio,
    open_positions_for_portfolio,
    evaluate_portfolio_positions,
    run_portfolio_self_audit,
    clamp_param
)

class TestStrategyLab(unittest.TestCase):
    def setUp(self):
        # Clean lab tables before each test
        conn = database.get_connection()
        conn.execute("DELETE FROM lab_audit_logs")
        conn.execute("DELETE FROM lab_positions")
        conn.execute("DELETE FROM lab_portfolios")
        conn.commit()
        conn.close()

    def tearDown(self):
        conn = database.get_connection()
        conn.execute("DELETE FROM lab_audit_logs")
        conn.execute("DELETE FROM lab_positions")
        conn.execute("DELETE FROM lab_portfolios")
        conn.commit()
        conn.close()

    def test_initialize_9_portfolios_with_2000_tl(self):
        initialize_lab_portfolios()
        portfolios = database.get_all_lab_portfolios()
        self.assertEqual(len(portfolios), 9)

        horizons = [p["horizon_days"] for p in portfolios]
        self.assertEqual(horizons.count(3), 3)
        self.assertEqual(horizons.count(7), 3)
        self.assertEqual(horizons.count(21), 3)

        for p in portfolios:
            self.assertEqual(p["initial_capital"], 2000.0)
            self.assertEqual(p["cash_balance"], 2000.0)
            self.assertEqual(p["version"], 1)

    def test_select_stocks_respects_2000_tl_budget(self):
        initialize_lab_portfolios()
        p = database.get_lab_portfolio_by_code("O1")

        # Stock A is 1200 TL (too expensive for 1/3 of 2000 TL = 666 TL), Stock B is 100 TL, Stock C is 50 TL
        candidates = [
            {"symbol": "EXPENSIVE", "price": 1200.0, "rsi": 52.0, "pe_ratio": 6.0, "pb_ratio": 1.0, "div_yield": 2.0, "atr": 30.0, "committee_score": 80, "tm_wr": 60.0, "trend": "YUKARI"},
            {"symbol": "CHEAPB", "price": 100.0, "rsi": 55.0, "pe_ratio": 7.0, "pb_ratio": 1.2, "div_yield": 3.0, "atr": 3.0, "committee_score": 75, "tm_wr": 55.0, "trend": "YUKARI"},
            {"symbol": "CHEAPC", "price": 50.0, "rsi": 48.0, "pe_ratio": 8.0, "pb_ratio": 1.1, "div_yield": 2.5, "atr": 1.5, "committee_score": 70, "tm_wr": 50.0, "trend": "YUKARI"},
        ]
        picks = select_stocks_for_portfolio(p, candidates)
        syms = [x["symbol"] for x in picks]
        self.assertNotIn("EXPENSIVE", syms)
        self.assertIn("CHEAPB", syms)
        self.assertIn("CHEAPC", syms)

        opened = open_positions_for_portfolio(p, picks)
        self.assertEqual(len(opened), 2)
        updated_p = database.get_lab_portfolio_by_code("O1")
        self.assertGreaterEqual(updated_p["cash_balance"], 0.0)
        self.assertLess(updated_p["cash_balance"], 2000.0)

    def test_position_lifecycle_target_and_stop(self):
        initialize_lab_portfolios()
        p = database.get_lab_portfolio_by_code("K1")
        # Open 2 positions spending ~1300 TL
        database.add_lab_position(p["id"], "WINSTOCK", 10, 50.0, 55.0, 47.0)
        database.add_lab_position(p["id"], "LOSSSTOCK", 10, 80.0, 88.0, 75.0)
        database.update_lab_portfolio_state(p["id"], 2000.0 - 1300.0, p["version"], p["params"])

        res = evaluate_portfolio_positions(
            database.get_lab_portfolio_by_code("K1"),
            price_fetcher=lambda s: {"WINSTOCK": 56.0, "LOSSSTOCK": 74.0}.get(s)
        )
        self.assertEqual(res["closed_count"], 2)
        open_pos = database.get_lab_positions(p["id"], status="OPEN")
        self.assertEqual(len(open_pos), 0)

        # Cash should be 700 + (10*56) + (10*74) = 2000.0
        updated_p = database.get_lab_portfolio_by_code("K1")
        self.assertAlmostEqual(updated_p["cash_balance"], 2000.0, delta=0.01)

    @patch("strategy_lab.LLMAdapter.call_llm")
    def test_self_audit_and_bounded_parameter_evolution(self, mock_llm):
        initialize_lab_portfolios()
        p = database.get_lab_portfolio_by_code("K1")

        # Add a closed losing trade
        pos_id = database.add_lab_position(p["id"], "BADSTOCK", 10, 100.0, 106.0, 95.0)
        database.update_lab_position(pos_id, 94.0, -60.0, -6.0, "HIT_STOP")

        # LLM suggests out-of-bounds value (max_rsi: 999) + valid stop_atr_mult: 1.8
        mock_llm.return_value = '''
        {
          "diagnosis": "RSI tavanı çok yüksek olduğu için aşırı alınmış hisselerde stop olduk.",
          "changes": {
            "max_rsi": 999,
            "stop_atr_mult": 1.8
          }
        }
        '''
        audit_res = run_portfolio_self_audit(p)
        self.assertIsNotNone(audit_res)

        updated_p = database.get_lab_portfolio_by_code("K1")
        self.assertEqual(updated_p["version"], 2)
        # Verify clamping respected bounds
        max_rsi_bound = updated_p["bounds"]["max_rsi"][1]
        self.assertLessEqual(updated_p["params"]["max_rsi"], max_rsi_bound)
        self.assertEqual(updated_p["params"]["stop_atr_mult"], 1.8)

        logs = database.get_lab_audit_logs(p["id"])
        self.assertEqual(len(logs), 1)
        self.assertIn("RSI tavanı", logs[0]["diagnosis"])

if __name__ == "__main__":
    unittest.main()
