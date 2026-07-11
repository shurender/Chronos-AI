"""
Centralized backend configuration. Loads from environment / .env with safe
defaults so the app never crashes on a missing optional value (e.g. no
GROQ_API_KEY -> features that need it fall back, they don't blow up).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

# Load the repo-root .env explicitly so config is stable whether uvicorn is
# launched from the repo root, backend/, Docker, or a test runner.
load_dotenv(REPO_ROOT / ".env", override=False)
load_dotenv(BASE_DIR / ".env", override=False)


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


def _normalize_origin(origin: str) -> str:
    # Browsers send origins without a trailing slash, so normalize config
    # values like "http://localhost:5173/" to avoid silent CORS mismatches.
    return origin.rstrip("/")


# Optional — features that need it (Future Self LLM chat) fall back gracefully
# when this is unset; nothing in the app should raise ImportError/RuntimeError
# at import time because it's missing.
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY") or None

# Chat provider: groq | fireworks | ollama | vllm | mock. Default groq keeps
# existing behavior (raises without a key so extraction fails loudly / avatar
# falls back). "mock" is a deterministic offline provider.
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
REQUIRE_LIVE_LLM: bool = _bool_env("REQUIRE_LIVE_LLM", False)

# Fireworks (OpenAI-compatible) — optional.
FIREWORKS_API_KEY: str | None = os.getenv("FIREWORKS_API_KEY") or None
FIREWORKS_MODEL: str = os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/gpt-oss-120b")

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

# Authenticated data connectors. Secrets are read from env only and are never
# returned by diagnostics.
GITHUB_CLIENT_ID: str | None = os.getenv("GITHUB_CLIENT_ID") or None
GITHUB_CLIENT_SECRET: str | None = os.getenv("GITHUB_CLIENT_SECRET") or None
GITHUB_REDIRECT_URI: str = os.getenv(
    "GITHUB_REDIRECT_URI", "http://localhost:8000/connectors/github/callback"
)
GITHUB_TOKEN: str | None = os.getenv("GITHUB_TOKEN") or None

SLACK_CLIENT_ID: str | None = os.getenv("SLACK_CLIENT_ID") or None
SLACK_CLIENT_SECRET: str | None = os.getenv("SLACK_CLIENT_SECRET") or None
SLACK_SIGNING_SECRET: str | None = os.getenv("SLACK_SIGNING_SECRET") or None
SLACK_REDIRECT_URI: str = os.getenv(
    "SLACK_REDIRECT_URI", "http://localhost:8000/connectors/slack/callback"
)

NOTION_CLIENT_ID: str | None = os.getenv("NOTION_CLIENT_ID") or None
NOTION_CLIENT_SECRET: str | None = os.getenv("NOTION_CLIENT_SECRET") or None
NOTION_REDIRECT_URI: str = os.getenv(
    "NOTION_REDIRECT_URI", "http://localhost:8000/connectors/notion/callback"
)
NOTION_VERSION: str = os.getenv("NOTION_VERSION", "2026-03-11")
NOTION_TOKEN: str | None = os.getenv("NOTION_TOKEN") or None

CONNECTOR_TOKEN_STORE: str = os.getenv("CONNECTOR_TOKEN_STORE", "local")
CONNECTOR_ENCRYPTION_KEY: str = os.getenv("CONNECTOR_ENCRYPTION_KEY", "dev-only-local-key")
CONNECTOR_STORE_PATH: str = os.getenv(
    "CONNECTOR_STORE_PATH", str(BASE_DIR / "Connectors" / "tokens.json")
)

# Keep every storage consumer on the same paths. CHROMA_PATH remains supported
# for existing local .env files, while CHROMA_DB_PATH is the preferred name.
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR)))
CHROMA_DB_PATH: str = (
    os.getenv("CHROMA_DB_PATH")
    or os.getenv("CHROMA_PATH")
    or str(DATA_DIR / "chroma_db")
)
CHROMA_PATH: str = CHROMA_DB_PATH
GRAPH_PATH: str = os.getenv("GRAPH_PATH") or str(DATA_DIR / "graph.gpickle")

# Local dev defaults (Vite on 5173, CRA-style on 3000). Override with a
# comma-separated CORS_ORIGINS env var in non-local deployments — avoid "*"
# once this is exposed beyond localhost.
CORS_ORIGINS: list[str] = _list_env(
    "CORS_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
)
CORS_ORIGINS = [_normalize_origin(origin) for origin in CORS_ORIGINS]

DEMO_MODE: bool = _bool_env("DEMO_MODE", True)


def safe_debug_config() -> dict:
    return {
        "llmProvider": LLM_PROVIDER,
        "fireworksKeyPresent": bool(FIREWORKS_API_KEY),
        "groqKeyPresent": bool(GROQ_API_KEY),
        "evidenceProvider": EVIDENCE_PROVIDER,
        "tavilyKeyPresent": bool(TAVILY_API_KEY),
        "demoMode": DEMO_MODE,
        "corsOrigins": CORS_ORIGINS,
        "requireLiveLlm": REQUIRE_LIVE_LLM,
        "githubClientConfigured": bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET),
        "githubTokenPresent": bool(GITHUB_TOKEN),
        "slackClientConfigured": bool(SLACK_CLIENT_ID and SLACK_CLIENT_SECRET),
        "slackSigningSecretPresent": bool(SLACK_SIGNING_SECRET),
        "notionClientConfigured": bool(NOTION_CLIENT_ID and NOTION_CLIENT_SECRET),
        "notionTokenPresent": bool(NOTION_TOKEN),
        "connectorTokenStore": CONNECTOR_TOKEN_STORE,
    }

# Safety / privacy.
# When false (default), ingested raw_text is PII/secret-redacted before storage.
STORE_RAW_UNREDACTED: bool = _bool_env("STORE_RAW_UNREDACTED", False)
# Informational retention window (0 = keep forever). Manual controls: POST /data/delete-all,
# POST /data/delete-source/{id}.
DATA_RETENTION_DAYS: int = int(os.getenv("DATA_RETENTION_DAYS", "0") or "0")
