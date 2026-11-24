"""Cliente de LLM (API compatível com OpenAI: POST /chat/completions): DeepSeek na nuvem ou Ollama local."""
from __future__ import annotations

import re

import httpx

from .config import Settings


class LLMError(RuntimeError):
    pass


class DeepSeekClient:
    def __init__(self, s: Settings, transport: httpx.BaseTransport | None = None):
        self.s = s
        self.transport = transport  # injetável nos testes

    @property
    def enabled(self) -> bool:
        if self.s.llm_provider == "off":
            return False
        return True if self.s.llm_is_local else bool(self.s.deepseek_api_key)

    @property
    def label(self) -> str:
        return "Ollama" if self.s.llm_is_local else "DeepSeek"

    def local_status(self) -> dict:
        """O Ollama está no ar? Quais modelos já foram baixados? (GET /api/tags)"""
        root = self.s.ollama_base_url.removesuffix("/v1")
        try:
            with httpx.Client(timeout=2.5, transport=self.transport) as c:
                r = c.get(f"{root}/api/tags")
            r.raise_for_status()
            models = sorted(m.get("name", "") for m in r.json().get("models", []))
            return {"online": True, "models": models}
        except (httpx.HTTPError, ValueError):
            return {"online": False, "models": []}

    def chat(self, messages: list[dict], temperature: float = 0.2, max_tokens: int = 600) -> str:
        if not self.enabled:
            raise LLMError("modelo desligado ou DEEPSEEK_API_KEY não configurada")
        if self.s.llm_is_local:
            max_tokens = min(max_tokens, 320)  # modelo pequeno em CPU: respostas curtas respondem mais rápido
        try:
            with httpx.Client(timeout=self.s.llm_timeout_s, transport=self.transport) as c:
                r = c.post(
                    f"{self.s.llm_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.s.deepseek_api_key}"} if not self.s.llm_is_local else {},
                    json={"model": self.s.llm_model, "messages": messages,
                          "temperature": temperature, "max_tokens": max_tokens, "stream": False},
                )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
            return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()  # modelos "pensantes" (ex.: Qwen3)
        except httpx.HTTPStatusError as exc:
            try:
                msg = str(exc.response.json().get("error", {}).get("message", ""))
            except Exception:
                msg = exc.response.text[:120]
            msg = (msg.replace(self.s.deepseek_api_key, "***") if self.s.deepseek_api_key else msg)[:160]
            raise LLMError(f"{self.label} respondeu HTTP {exc.response.status_code}: {msg}") from None
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            # nunca inclui a chave nem o corpo da requisição na mensagem
            raise LLMError(f"falha ao chamar o {self.label}: {type(exc).__name__}") from exc
