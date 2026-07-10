"""
Centralized backend configuration. Loads from environment / .env with safe
defaults so the app never crashes on a missing optional value (e.g. no
GROQ_API_KEY -> features that need it fall back, they don't blow up).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _list_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


# Optional — features that need it (Future Self LLM chat) fall back gracefully
# when this is unset; nothing in the app should raise ImportError/RuntimeError
# at import time because it's missing.
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY") or None

# Chat provider: groq | fireworks | ollama | vllm | mock. Default groq keeps
# existing behavior (raises without a key so extraction fails loudly / avatar
# falls back). "mock" is a deterministic offline provider.
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Fireworks (OpenAI-compatible) — optional.
FIREWORKS_API_KEY: str | None = os.getenv("FIREWORKS_API_KEY") or None
FIREWORKS_MODEL: str = os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/llama-v3p1-70b-instruct")

# Local OpenAI-compatible endpoints (Ollama / vLLM). vLLM is the AMD/ROCm path.
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
VLLM_BASE_URL: str = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_MODEL: str = os.getenv("VLLM_MODEL", "local-model")

# Embeddings: sentence_transformers | ollama | openai_like | mock.
EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Toggles the intended AMD/ROCm deployment mode (informational; surfaced in
# /llm/health). Does not itself select a provider — set LLM_PROVIDER=vllm.
AMD_MODE: bool = _bool_env("AMD_MODE", False)

# Agent council mode: deterministic | llm | hybrid.
#   deterministic — pure heuristic agents (default; reliable, used by tests).
#   llm           — LLM enriches each agent (falls back to deterministic on any failure).
#   hybrid        — deterministic baseline kept authoritative, LLM appends rationale.
AGENT_MODE: str = os.getenv("AGENT_MODE", "deterministic")

# demo | uploaded | web | hybrid  (web is a stub; falls back to demo when unavailable)
EVIDENCE_PROVIDER: str = os.getenv("EVIDENCE_PROVIDER", "demo")
# Optional live-web provider keys — absent by default; web provider stays a stub.
TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY") or None
SERPAPI_API_KEY: str | None = os.getenv("SERPAPI_API_KEY") or None

CHROMA_PATH: str = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "chroma_db"))
GRAPH_PATH: str = os.getenv("GRAPH_PATH", str(BASE_DIR / "graph.gpickle"))

# Local dev defaults (Vite on 5173, CRA-style on 3000). Override with a
# comma-separated CORS_ORIGINS env var in non-local deployments — avoid "*"
# once this is exposed beyond localhost.
CORS_ORIGINS: list[str] = _list_env(
    "CORS_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
)

DEMO_MODE: bool = _bool_env("DEMO_MODE", True)

# Safety / privacy.
# When false (default), ingested raw_text is PII/secret-redacted before storage.
STORE_RAW_UNREDACTED: bool = _bool_env("STORE_RAW_UNREDACTED", False)
# Informational retention window (0 = keep forever). Manual controls: POST /data/delete-all,
# POST /data/delete-source/{id}.
DATA_RETENTION_DAYS: int = int(os.getenv("DATA_RETENTION_DAYS", "0") or "0")
