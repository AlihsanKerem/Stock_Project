"""
🧪 Unit Tests for Universal LLM Adapter
Tests fallback mechanisms, provider detection, mock REST and OpenAI-compatible integration.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_engine import LLMAdapter

class TestLLMAdapter(unittest.TestCase):
    def test_provider_auto_detection_gemini(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyTestKey123", "LLM_PROVIDER": ""}, clear=True):
            adapter = LLMAdapter()
            self.assertEqual(adapter.provider, "gemini")
            self.assertEqual(adapter.model_name, "gemini-1.5-flash")

    def test_provider_auto_detection_ollama(self):
        with patch.dict(os.environ, {"OLLAMA_API_URL": "http://localhost:11434/api/generate", "LLM_PROVIDER": ""}, clear=True):
            adapter = LLMAdapter()
            self.assertEqual(adapter.provider, "ollama")
            self.assertEqual(adapter.model_name, "llama3")

    def test_provider_auto_detection_openai_compatible(self):
        with patch.dict(os.environ, {"LLM_BASE_URL": "https://api.groq.com/openai/v1", "LLM_API_KEY": "gsk_123", "LLM_PROVIDER": ""}, clear=True):
            adapter = LLMAdapter()
            self.assertIn(adapter.provider, ["openai_compatible", "openai"])

    def test_groq_or_deepseek_alias_sets_default_base_url(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "groq", "LLM_API_KEY": "gsk_test"}, clear=True):
            adapter = LLMAdapter()
            self.assertEqual(adapter.base_url, "https://api.groq.com/openai/v1")
            self.assertEqual(adapter.model_name, "llama-3.3-70b-versatile")

    @patch("requests.post")
    def test_openai_compatible_call_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Merhaba, BIST analizi hazır."}}]
        }
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {
            "LLM_PROVIDER": "openai_compatible",
            "LLM_BASE_URL": "http://localhost:1234/v1",
            "LLM_API_KEY": "lm-studio",
            "LLM_MODEL": "qwen2.5-7b"
        }, clear=True):
            adapter = LLMAdapter()
            res = adapter.call_llm([{"role": "user", "content": "test"}])
            self.assertEqual(res, "Merhaba, BIST analizi hazır.")

    @patch("requests.post")
    def test_ollama_call_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Ollama BIST yanıtı"}
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_API_URL": "http://localhost:11434/api/generate",
            "OLLAMA_MODEL": "llama3"
        }, clear=True):
            adapter = LLMAdapter()
            res = adapter.call_llm([{"role": "user", "content": "test"}])
            self.assertEqual(res, "Ollama BIST yanıtı")

    def test_fallback_message_when_no_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            adapter = LLMAdapter()
            # Force empty credentials
            adapter.gemini_model = None
            adapter.gemini_key = ""
            adapter.base_url = ""
            adapter.ollama_url = ""
            res = adapter.call_llm([{"role": "user", "content": "test"}])
            self.assertIn("Sistem Bildirimi", res)

if __name__ == "__main__":
    unittest.main()
