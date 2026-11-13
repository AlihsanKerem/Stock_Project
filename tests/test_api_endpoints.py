"""
🧪 Unit Tests for New Flask API Endpoints
Tests /api/agent/committee/<symbol> and /api/agent/timemachine/<symbol>
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app

class TestNewAgentEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch("committee_engine.BistInvestmentCommittee.evaluate_stock")
    def test_committee_endpoint(self, mock_eval):
        mock_eval.return_value = {
            "symbol": "THYAO",
            "consensus_score": 82,
            "final_decision": "GÜÇLÜ AL",
            "executive_summary": "Test komite kararı."
        }
        res = self.client.get("/api/agent/committee/THYAO")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["final_decision"], "GÜÇLÜ AL")

    @patch("day_trader_engine.run_time_machine_simulation")
    def test_timemachine_endpoint(self, mock_sim):
        mock_sim.return_value = {
            "symbol": "EREGL",
            "status": "success",
            "simulation": {
                "sample_size": 25,
                "win_rate_percent": 68.0,
                "profit_factor": 1.95,
                "verdict": "🟢 YÜKSEK BAŞARI OLASILIĞI"
            }
        }
        res = self.client.get("/api/agent/timemachine/EREGL?target=3.5&stop=2.0")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["simulation"]["win_rate_percent"], 68.0)

if __name__ == "__main__":
    unittest.main()
