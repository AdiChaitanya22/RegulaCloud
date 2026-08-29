import os
import requests
import json
from typing import Dict, Any, List, Optional
from backend.app.engines.rag_engine import RAGContext
from backend.app.engines.guardrails import GuardrailEngine, SYSTEM_PROMPT

class LLMClient:
    """
    Unified LLM Client supporting Google Gemini API, OpenAI API, local Ollama,
    and Deterministic Grounded Fallback synthesis.
    """

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")

    def generate_response(
        self,
        user_message: str,
        context: RAGContext,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        prompt_context = context.to_prompt_text()
        system_instruction = f"{SYSTEM_PROMPT}\n\n[RETRIEVED STATUTORY & EMPIRICAL EVIDENCE CONTEXT]:\n{prompt_context}"

        # 1. Try Google Gemini API if API key configured
        if self.gemini_api_key:
            try:
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_api_key}"
                contents = []
                
                # Add conversation history
                if history:
                    for h in history[-4:]:
                        role = "user" if h.get("role") == "user" else "model"
                        contents.append({
                            "role": role,
                            "parts": [{"text": h.get("content", "")}]
                        })

                # Add current message with context
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"Context:\n{prompt_context}\n\nQuestion: {user_message}"}]
                })

                payload = {
                    "system_instruction": {
                        "parts": [{"text": SYSTEM_PROMPT}]
                    },
                    "contents": contents,
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 1000
                    }
                }

                res = requests.post(gemini_url, json=payload, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        reply_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if reply_text:
                            return {
                                "reply": reply_text.strip(),
                                "provider": "REAL_GOOGLE_GEMINI_API (gemini-2.5-flash)"
                            }
            except Exception as e:
                print(f"[WARN] Gemini API call failed: {e}. Falling back to deterministic grounded engine.")

        # 2. Try Local Ollama if configured
        if self.provider == "ollama":
            try:
                messages = [{"role": "system", "content": system_instruction}]
                if history:
                    for h in history[-4:]:
                        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
                messages.append({"role": "user", "content": user_message})

                payload = {
                    "model": self.ollama_model,
                    "messages": messages,
                    "stream": False
                }
                res = requests.post(self.ollama_url, json=payload, timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    reply = data.get("message", {}).get("content", "")
                    if reply:
                        return {
                            "reply": reply.strip(),
                            "provider": f"REAL_LOCAL_OLLAMA ({self.ollama_model})"
                        }
            except Exception as e:
                print(f"[WARN] Local Ollama call failed: {e}. Falling back to deterministic grounded engine.")

        # 3. Deterministic Grounded Evidence Engine (Zero-Downtime Authoritative Fallback)
        deterministic_reply = GuardrailEngine.generate_deterministic_grounded_response(user_message, context)
        return {
            "reply": deterministic_reply,
            "provider": "DETERMINISTIC_GROUNDED_ENGINE (Knowledge Base & Evidence Vault)"
        }
