"""
🧠 AI Agent Engine (Çıkarım ve ReAct Orkestrasyon Motoru)
Dokümandaki 5 mimari prensibe (Persona, Tools, Memory, State, Guardrails) uygun,
Pluggable (Gemini, Ollama, OpenAI-compatible, DeepSeek vb.) çalışan otonom finansal ajan.
"""

import os
import json
import re
import requests
from dotenv import load_dotenv

from agent_tools import AVAILABLE_TOOLS_SCHEMA, execute_agent_tool, TOOLS_MAP
from database import (
    save_agent_message, get_agent_chat_history, 
    get_agent_profile, set_agent_profile
)

load_dotenv()

# ==========================================
# 🔌 Pluggable LLM Adapter (Evrensel Adaptör)
# ==========================================

class LLMAdapter:
    """
    Gemini, Ollama, OpenAI-compatible (DeepSeek, Groq, OpenRouter, LM Studio, FreeLLM vb.)
    sağlayıcılarını tek tip arayüzle çalıştırır.
    """
    KNOWN_PROVIDERS = {
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "default_model": "llama-3.3-70b-versatile"
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-chat"
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "default_model": "google/gemini-2.0-flash-exp:free"
        },
        "lmstudio": {
            "base_url": "http://localhost:1234/v1",
            "default_model": "local-model"
        }
    }

    def __init__(self):
        # Sağlayıcı Seçimi (.env veya otomatik algılama)
        self.provider = os.getenv("LLM_PROVIDER", "").strip().lower()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.ollama_url = os.getenv("OLLAMA_API_URL", "").strip()
        self.base_url = os.getenv("LLM_BASE_URL", "").strip()
        self.api_key = os.getenv("LLM_API_KEY", self.gemini_key or "").strip()
        self.model_name = os.getenv("LLM_MODEL", "").strip()

        # Bilinen provider takma adlarını yapılandır
        if self.provider in self.KNOWN_PROVIDERS:
            meta = self.KNOWN_PROVIDERS[self.provider]
            if not self.base_url:
                self.base_url = meta["base_url"]
            if not self.model_name:
                self.model_name = meta["default_model"]

        # Otomatik varsayılan belirleme
        is_gemini_valid = (
            bool(self.gemini_key)
            and self.gemini_key not in ["your_gemini_api_key_here", "your_google_gemini_api_key_here"]
        )

        if not self.provider:
            if is_gemini_valid:
                self.provider = "gemini"
            elif self.ollama_url:
                self.provider = "ollama"
            elif self.base_url:
                self.provider = "openai_compatible"
            else:
                self.provider = "gemini"

        if not self.model_name:
            if self.provider == "gemini":
                self.model_name = "gemini-1.5-flash"
            elif self.provider == "ollama":
                self.model_name = os.getenv("OLLAMA_MODEL", "llama3")
            elif self.provider in ["openai", "openai_compatible"]:
                self.model_name = "gpt-4o-mini"
            else:
                self.model_name = "gemini-1.5-flash"

        self._init_client()

    def _init_client(self):
        self.gemini_model = None
        is_gemini_valid = (
            bool(self.gemini_key)
            and self.gemini_key not in ["your_gemini_api_key_here", "your_google_gemini_api_key_here"]
        )
        if self.provider == "gemini" and is_gemini_valid:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                self.gemini_model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                print(f"[LLMAdapter] Gemini SDK başlatma uyarısı: {e}")

    def call_llm(self, messages: list, tools_schema: list = None) -> str:
        """
        Modelden metin yanıtı alır.
        """
        # 1. Gemini Sağlayıcısı (SDK veya REST API)
        if self.provider == "gemini":
            if self.gemini_model:
                try:
                    prompt_text = ""
                    for msg in messages:
                        role_prefix = "User" if msg["role"] == "user" else "System" if msg["role"] == "system" else "Model"
                        prompt_text += f"{role_prefix}: {msg['content']}\n\n"
                    
                    response = self.gemini_model.generate_content(prompt_text)
                    if response and response.text:
                        return response.text
                except Exception as ge:
                    print(f"[LLMAdapter] Gemini SDK çağrı hatası: {ge}")

            # REST Fallback for Gemini
            if self.gemini_key and self.gemini_key not in ["your_gemini_api_key_here", "your_google_gemini_api_key_here"]:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.gemini_key}"
                    contents = []
                    for msg in messages:
                        contents.append({
                            "role": "user" if msg["role"] in ["user", "system"] else "model",
                            "parts": [{"text": msg["content"]}]
                        })
                    res = requests.post(url, json={"contents": contents}, timeout=30)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "")
                except Exception as rest_e:
                    print(f"[LLMAdapter] Gemini REST API hatası: {rest_e}")

        # 2. Ollama Sağlayıcısı (Native REST)
        if self.provider == "ollama" and self.ollama_url:
            try:
                prompt_text = ""
                for msg in messages:
                    prompt_text += f"[{msg['role'].upper()}]: {msg['content']}\n\n"
                
                payload = {
                    "model": self.model_name,
                    "prompt": prompt_text,
                    "stream": False
                }
                res = requests.post(self.ollama_url, json=payload, timeout=60)
                if res.status_code == 200:
                    return res.json().get("response", "")
            except Exception as oe:
                print(f"[LLMAdapter] Ollama çağrı hatası: {oe}")

        # 3. OpenAI-Compatible REST Sağlayıcısı (Groq, DeepSeek, OpenRouter, LM Studio, vLLM vb.)
        target_base_url = self.base_url
        if not target_base_url and self.provider in self.KNOWN_PROVIDERS:
            target_base_url = self.KNOWN_PROVIDERS[self.provider]["base_url"]

        if target_base_url:
            try:
                endpoint = target_base_url.rstrip("/") + "/chat/completions"
                headers = {
                    "Content-Type": "application/json"
                }
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                # OpenRouter header ekleri
                if "openrouter" in target_base_url:
                    headers["HTTP-Referer"] = "https://github.com/virattt/ai-hedge-fund"
                    headers["X-Title"] = "BIST Algo-Trade System"

                payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": 0.2
                }
                res = requests.post(endpoint, headers=headers, json=payload, timeout=60)
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
            except Exception as ope:
                print(f"[LLMAdapter] OpenAI-Compatible çağrı hatası: {ope}")

        # Fallback: API anahtarı ayarlanmamışsa bilgilendirici deterministik mesaj
        return (
            "⚠️ [Sistem Bildirimi]: LLM sağlayıcısı API anahtarı (.env içerisindeki GEMINI_API_KEY, "
            "OLLAMA_API_URL veya LLM_BASE_URL) henüz yapılandırılmamış veya servis yanıt vermiyor. "
            "Lütfen .env dosyanızı kontrol ediniz."
        )

# ==========================================
# 🎯 BIST AI Agent Motoru (ReAct & Persona)
# ==========================================

class StockAgent:
    """
    BIST Portföy & Piyasa Karar Destek Ajanı.
    ReAct döngüsü, araç çağırma (Tool-Calling) ve hafıza yönetimi içerir.
    """
    def __init__(self):
        self.llm = LLMAdapter()
        self.max_iterations = 6  # Sonsuz döngü engeli (Guardrail)

    def _build_system_prompt(self, user_profile: dict) -> str:
        tools_description = "\n".join([
            f"- `{t['function']['name']}`: {t['function']['description']}"
            for t in AVAILABLE_TOOLS_SCHEMA
        ])

        return f"""
Sen Borsa İstanbul (BIST) piyasasında uzmanlaşmış, risk yönetimi prensiplerine sıkı sıkıya bağlı **Kıdemli Portföy ve Strateji Analisti Ajanısın**.

### KULLANICI PROFİLİ VE TERCİHLERİ:
- Risk Toleransı: {user_profile.get('risk_level', 'Dengeli')}
- Yatırım Vadesi: {user_profile.get('horizon', 'Orta Vade')}
- Stop-Loss Disiplini: {user_profile.get('stop_loss_discipline', 'Katı')}
- Odak Sektörler: {user_profile.get('favorite_sectors', 'BIST30 / Sanayi / Bankacılık')}

### ÇALIŞMA KURALLARIN VE GÜVENLİK BARİYERLERİ (GUARDRAILS):
1. **İddialarını Doğrula:** Asla hisse fiyatı, rasyo veya kâr/zarar tahmini uydurma. Veriye ihtiyacın olduğunda MUTLAKA elindeki araçları (Tools) çağır.
2. **Çelişkileri Yakala:** Bir hissede AL sinyali varken haber akışı olumsuzsa veya 5 yıllık backtest başarı oranı düşükse bunu dürüstçe vurgula.
3. **Risk Odaklı Ol:** Her hisse önerisinde ATR bazlı Stop-Loss seviyesini ve volatilite riskini hatırlat.
4. **İşlem Sınırı:** Sen otomatik hisse ALIP SATAMAZSIN. Kullanıcıya net, gerekçeli stratejik karar desteği sunarsın.

### KULLANABİLECEĞİN ARAÇLAR (TOOLS):
{tools_description}

### BİLİŞSEL DÖNGÜ PROTOKOLÜ (ReAct):
Bir adımda araç çağırmak istediğinde TAM OLARAK şu JSON formatını kullan:
```tool_call
{{
  "thought": "Kullanıcının portföy durumunu görmek için portföy aracını çağırmalıyım.",
  "tool": "tool_get_portfolio_summary",
  "arguments": {{}}
}}
```
Aracın sonucu sana `[Observation]` olarak geri beslenecektir.
Nihai hedefe ulaştığında veya kullanıcıya doğrudan yanıt vereceğinde ise `tool_call` bloğu açmadan, profesyonel, maddeli ve Markdown formatında Türkçe nihai yanıtını yaz.
"""

    def _extract_tool_call(self, text: str):
        """Metin içerisindeki ```tool_call {...} ``` bloğunu ayıklar."""
        pattern = r"```tool_call\s*(\{.*?\})\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                return data.get("tool"), data.get("arguments", {}), data.get("thought", "")
            except Exception:
                pass
        
        # Alternatif JSON bloğu
        alt_pattern = r"\{\s*\"tool\"\s*:\s*\"([a-zA-Z0-9_]+)\"\s*,\s*\"arguments\"\s*:\s*(\{.*?\})\s*\}"
        alt_match = re.search(alt_pattern, text, re.DOTALL)
        if alt_match:
            try:
                tool_name = alt_match.group(1)
                args = json.loads(alt_match.group(2))
                return tool_name, args, "Araç çalıştırılıyor."
            except Exception:
                pass
                
        return None, None, None

    def ask(self, user_message: str, session_id: str = "default") -> dict:
        """
        Kullanıcı mesajını ReAct döngüsünden geçirerek yanıtlar.
        Hafızayı yükler, kaydeder ve düşünce adımlarını raporlar.
        """
        profile = get_agent_profile()
        system_prompt = self._build_system_prompt(profile)
        history = get_agent_chat_history(session_id, limit=6)

        # Mesaj listesi hazırla
        messages = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        
        messages.append({"role": "user", "content": user_message})

        thought_steps = []
        tools_executed = []
        iteration = 0
        final_answer = ""

        # ReAct Bilişsel Döngüsü
        while iteration < self.max_iterations:
            iteration += 1
            response_text = self.llm.call_llm(messages, AVAILABLE_TOOLS_SCHEMA)

            tool_name, tool_args, thought = self._extract_tool_call(response_text)

            if tool_name and tool_name in TOOLS_MAP:
                thought_steps.append({
                    "step": iteration,
                    "thought": thought or f"'{tool_name}' aracı çağrılıyor...",
                    "tool": tool_name,
                    "arguments": tool_args
                })
                tools_executed.append(tool_name)

                # Aracı çalıştır (Observation)
                tool_result = execute_agent_tool(tool_name, tool_args)
                
                # Modeli bilgilendir ve döngüye devam et
                messages.append({"role": "assistant", "content": f"```tool_call\n{json.dumps({'thought': thought, 'tool': tool_name, 'arguments': tool_args}, ensure_ascii=False)}\n```"})
                messages.append({"role": "user", "content": f"[Observation for {tool_name}]:\n{json.dumps(tool_result, ensure_ascii=False)}"})
            else:
                # Araç çağrısı yok, nihai yanıta ulaşıldı
                final_answer = response_text
                # Varsa kalan tool_call bloklarını temizle
                final_answer = re.sub(r"```tool_call\s*\{.*?\}\s*```", "", final_answer, flags=re.DOTALL).strip()
                break

        if not final_answer:
            final_answer = "İşlemler tamamlandı ancak nihai bir özet üretilemedi. Lütfen sorunuzu tekrarlayınız."

        # Hafızaya kaydet
        save_agent_message(session_id, "user", user_message)
        save_agent_message(session_id, "assistant", final_answer, tool_calls=thought_steps)

        return {
            "status": "success",
            "session_id": session_id,
            "response": final_answer,
            "thought_steps": thought_steps,
            "tools_used": tools_executed,
            "iterations": iteration
        }

    def generate_executive_briefing(self) -> dict:
        """
        Dashboard ve Telegram için anlık tek tıkla Yönetici Strateji Raporu üretir.
        Portföyü, aktif sinyalleri ve backtestleri sentezler.
        """
        prompt = (
            "Bana bugün için kapsamlı bir 'BIST Yönetici Özeti ve Portföy Strateji Bülteni' hazırla. "
            "Önce portföyümün güncel kâr/zararını ve riskli pozisyonlarını incele, ardından bugünün sinyallerini "
            "ve bu sinyallerin geçmiş backtest başarı oranlarını değerlendirerek bana uygulanabilir 3 temel tavsiye sun."
        )
        return self.ask(prompt, session_id="executive_briefing")

# Global Ajan Örneği
stock_agent = StockAgent()
