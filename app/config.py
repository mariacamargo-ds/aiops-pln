from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)  # o .env do projeto vale mais que variáveis de ambiente antigas


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v not in (None, "") else default


@dataclass
class Settings:
    """Todas as opções vêm de variáveis de ambiente (ou do arquivo .env)."""

    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'aiops.db'}"
    chroma_dir: str = str(BASE_DIR / "data" / "chroma")
    dataset_csv: str = str(BASE_DIR / "data" / "aiops_logs_sinteticos.csv")
    incidents_json: str = str(BASE_DIR / "data" / "incidents.json")

    web_dir: str = str(BASE_DIR / "web")

    embedder: str = "hash"  # "hash" (offline, sem download) ou "st" (sentence-transformers)
    st_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    llm_provider: str = "deepseek"  # "deepseek" (nuvem, paga por token), "ollama" (modelo local, gratuito) ou "off" (sem IA: resposta extrativa)
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5:3b"  # cabe em notebooks de 8 GB de RAM; com 16 GB considere gemma3:4b
    llm_timeout_s: float = 40.0

    top_k: int = 24
    context_passages: int = 10
    min_similarity: float = 0.12
    sensitivity_default: float = 0.5

    @property
    def llm_is_local(self) -> bool:
        return self.llm_provider == "ollama"

    def apply_provider(self, provider: str) -> None:
        """Troca o provedor em execução e ajusta o que depende dele (modelo pequeno = menos contexto, mais tempo)."""
        self.llm_provider = provider
        local = provider == "ollama"
        self.llm_timeout_s = float(_env("LLM_TIMEOUT_S", "120" if local else "40"))
        self.context_passages = int(_env("CONTEXT_PASSAGES", "6" if local else "10"))

    @property
    def llm_model(self) -> str:
        return self.ollama_model if self.llm_is_local else self.deepseek_model

    @property
    def llm_base_url(self) -> str:
        return self.ollama_base_url if self.llm_is_local else self.deepseek_base_url

    @classmethod
    def from_env(cls) -> "Settings":
        d = cls()
        prov = _env("LLM_PROVIDER", d.llm_provider).lower()
        prov = prov if prov in ("ollama", "deepseek", "off") else "deepseek"
        local = prov == "ollama"
        return cls(
            llm_provider=prov,
            ollama_base_url=_env("OLLAMA_BASE_URL", d.ollama_base_url).rstrip("/"),
            ollama_model=_env("OLLAMA_MODEL", d.ollama_model),
            database_url=_env("DATABASE_URL", d.database_url),
            chroma_dir=_env("CHROMA_DIR", d.chroma_dir),
            dataset_csv=_env("DATASET_CSV", d.dataset_csv),
            incidents_json=_env("INCIDENTS_JSON", d.incidents_json),
            web_dir=_env("WEB_DIR", d.web_dir),
            embedder=_env("EMBEDDER", d.embedder).lower(),
            st_model=_env("ST_MODEL", d.st_model),
            deepseek_api_key=_env("DEEPSEEK_API_KEY", ""),
            deepseek_base_url=_env("DEEPSEEK_BASE_URL", d.deepseek_base_url).rstrip("/"),
            deepseek_model=_env("DEEPSEEK_MODEL", d.deepseek_model),
            llm_timeout_s=float(_env("LLM_TIMEOUT_S", "120" if local else str(d.llm_timeout_s))),
            top_k=int(_env("TOP_K", str(d.top_k))),
            context_passages=int(_env("CONTEXT_PASSAGES", "6" if local else str(d.context_passages))),
            min_similarity=float(_env("MIN_SIMILARITY", str(d.min_similarity))),
            sensitivity_default=float(_env("SENSITIVITY_DEFAULT", str(d.sensitivity_default))),
        )
