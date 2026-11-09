"""
🧪 Test Suite for AI Agent Components
Ajan hafızasını, deterministik araçları, ReAct döngüsünü ve API rotalarını test eder.
"""

import unittest
import json
import database
import agent_tools
from agent_engine import StockAgent, LLMAdapter
from app import app

class TestAgentMemory(unittest.TestCase):
    def setUp(self):
        self.session_id = "test_session_123"
        database.clear_agent_history(self.session_id)

    def tearDown(self):
        database.clear_agent_history(self.session_id)

    def test_save_and_retrieve_messages(self):
        # 1. Mesaj kaydet
        database.save_agent_message(self.session_id, "user", "THYAO nasıl?")
        database.save_agent_message(
            self.session_id, 
            "assistant", 
            "THYAO güçlü trendde.", 
            tool_calls=[{"tool": "tool_analyze_stock", "arguments": {"symbol": "THYAO"}}]
        )

        # 2. Mesajları oku
        history = database.get_agent_chat_history(self.session_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "THYAO nasıl?")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["content"], "THYAO güçlü trendde.")
        self.assertIsInstance(history[1]["tool_calls"], list)

    def test_profile_management(self):
        database.set_agent_profile("risk_level", "Agresif")
        profile = database.get_agent_profile()
        self.assertEqual(profile["risk_level"], "Agresif")

        # Geri varsayılana al
        database.set_agent_profile("risk_level", "Dengeli")

class TestAgentTools(unittest.TestCase):
    def test_portfolio_summary_tool(self):
        res = agent_tools.execute_agent_tool("tool_get_portfolio_summary", {})
        self.assertIn("status", res)
        self.assertIn("total_portfolio_cost", res)
        self.assertIn("positions", res)

    def test_backtest_stats_tool(self):
        res = agent_tools.execute_agent_tool("tool_get_backtest_stats", {})
        self.assertIn("status", res)
        self.assertIn("total_signals", res)

    def test_active_signals_tool(self):
        res = agent_tools.execute_agent_tool("tool_get_active_signals", {})
        self.assertIn("status", res)

    def test_unknown_tool_handling(self):
        res = agent_tools.execute_agent_tool("non_existent_tool", {})
        self.assertEqual(res["status"], "error")

class TestReActParser(unittest.TestCase):
    def setUp(self):
        self.agent = StockAgent()

    def test_extract_tool_call(self):
        mock_output = (
            "Kullanıcının portföyünü incelemem gerekiyor.\n"
            "```tool_call\n"
            "{\n"
            '  "thought": "Portföy özetini çekmeliyim",\n'
            '  "tool": "tool_get_portfolio_summary",\n'
            '  "arguments": {}\n'
            "}\n"
            "```"
        )
        tool, args, thought = self.agent._extract_tool_call(mock_output)
        self.assertEqual(tool, "tool_get_portfolio_summary")
        self.assertEqual(args, {})
        self.assertEqual(thought, "Portföy özetini çekmeliyim")

    def test_extract_no_tool_call(self):
        mock_output = "THYAO için hedef fiyat 340 TL olarak izlenebilir."
        tool, args, thought = self.agent._extract_tool_call(mock_output)
        self.assertIsNone(tool)

class TestFlaskAgentAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_profile(self):
        res = self.client.get("/api/agent/profile")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("profile", data)

    def test_update_profile(self):
        res = self.client.post("/api/agent/profile", json={"risk_level": "Dengeli"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["profile"]["risk_level"], "Dengeli")

    def test_chat_empty_message_validation(self):
        res = self.client.post("/api/agent/chat", json={"message": ""})
        self.assertEqual(res.status_code, 400)

    def test_history_and_clear(self):
        res = self.client.get("/api/agent/history?session_id=api_test_session")
        self.assertEqual(res.status_code, 200)

        clear_res = self.client.post("/api/agent/clear", json={"session_id": "api_test_session"})
        self.assertEqual(clear_res.status_code, 200)

if __name__ == '__main__':
    unittest.main()

