"""
🧪 Unit Tests for Day-Trader Engine (day-trader-skill adaptations)
Tests Setup Scanning, Time-Machine Replay Simulation, and Bracket Order Calculations.
"""

import unittest
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from day_trader_engine import (
    calculate_trade_brackets,
    detect_chart_setups,
    simulate_time_machine_from_df
)

class TestDayTraderEngine(unittest.TestCase):
    def setUp(self):
        # Create a synthetic 100-day OHLCV dataframe
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=100)
        close_prices = 100 + np.cumsum(np.random.normal(0.2, 1.5, 100))
        high_prices = close_prices + np.random.uniform(0.5, 2.0, 100)
        low_prices = close_prices - np.random.uniform(0.5, 2.0, 100)
        open_prices = low_prices + np.random.uniform(0.1, 1.0, 100)
        volume = np.random.randint(100000, 5000000, 100)

        self.df = pd.DataFrame({
            "Open": open_prices,
            "High": high_prices,
            "Low": low_prices,
            "Close": close_prices,
            "Volume": volume
        }, index=dates)

    def test_calculate_trade_brackets(self):
        entry_price = 100.0
        atr = 2.5
        brackets = calculate_trade_brackets(entry_price=entry_price, atr=atr, risk_reward_ratio=2.0)
        
        self.assertEqual(brackets["entry_price"], 100.0)
        self.assertLess(brackets["stop_loss"], 100.0)
        self.assertGreater(brackets["target_1"], 100.0)
        self.assertGreater(brackets["target_2"], brackets["target_1"])
        self.assertAlmostEqual(brackets["risk_reward_ratio"], 2.0, delta=0.1)

    def test_detect_chart_setups(self):
        # Run detection on synthetic data
        setups = detect_chart_setups(self.df)
        self.assertIsInstance(setups, list)
        for s in setups:
            self.assertIn("setup_type", s)
            self.assertIn("direction", s)
            self.assertIn("confidence", s)

    def test_simulate_time_machine_from_df(self):
        # Run Time-Machine replay
        res = simulate_time_machine_from_df(
            self.df,
            target_pct=3.0,
            stop_pct=2.0,
            max_holding_bars=5
        )
        self.assertIn("sample_size", res)
        self.assertIn("win_rate_percent", res)
        self.assertIn("expectancy_percent", res)
        self.assertIn("profit_factor", res)
        self.assertGreaterEqual(res["sample_size"], 0)

if __name__ == "__main__":
    unittest.main()
