"""
LLM service — selects a chat provider (LLM_PROVIDER) and an embedding backend
(EMBEDDING_PROVIDER), and exposes stable helpers the rest of the app calls:
chat(), embed_text(), embed_texts(), health().

Defaults preserve existing behavior: LLM_PROVIDER=groq (raises without a key so
the extraction pipeline still fails loudly, and avatar_engine still falls back),
EMBEDDING_PROVIDER=sentence_transformers (local, no key). LLM_PROVIDER=mock gives
a deterministic offline chat provider.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional

from pydantic import BaseModel

from backend import config
from backend.logging_config import get_logger

from .providers.base import LLMProvider, LLMProviderError, Messages, ProviderHealth

logger = get_logger(__name__)


# --- Mock chat provider (deterministic, offline) ---------------------------
def _empty_schema_instance(schema: type[BaseModel]) -> BaseModel:
    kwargs = {}
    for name, field in schema.model_fields.items():
        ann = str(field.annotation).lower()
        kwargs[name] = [] if "list" in ann else ("" if "str" in ann else None)
    try:
        return schema(**kwargs)
    except Exception:
        return schema.model_construct(**kwargs)


def _last_user_text(messages: Messages) -> str:
    if isinstance(messages, str):
        return messages
    for role, content in reversed(messages):
        if role == "human":
            return content
    return messages[-1][1] if messages else ""


def _extract_chunk_text(text: str) -> str:
    marker = "Chunk text:"
    if marker in text:
        text = text.split(marker, 1)[1]
    marker = "Entities:"
    if marker in text:
        text = text.split(marker, 1)[0]
    return text.strip()


def _mock_structured_output(messages: Messages, schema: type[BaseModel]) -> BaseModel:
    from backend.schema import CandidateEdge, CandidateEdges, CandidateNode, CandidateNodes, Tag, Tags

    text = _extract_chunk_text(_last_user_text(messages))
    first_sentence = re.split(r"(?<=[.!?])\s+", text.replace("\n", " ").strip())[0][:240]

    if schema is CandidateNodes:
        nodes: list[CandidateNode] = []
        if "Chronos" in text:
            nodes.append(CandidateNode(node_type="project", label="Chronos-AI", description=first_sentence or "Chronos-AI project activity."))
        if re.search(r"\b(Alice|Bob|Charlie|Jane Doe)\b", text):
            person = re.search(r"\b(Alice|Bob|Charlie|Jane Doe)\b", text).group(1)
            nodes.append(CandidateNode(node_type="person", label=person, description=f"{person} is mentioned in this source chunk."))
        if re.search(r"\b(implement|verified|need|switch|pivot|decision|should)\b", text, re.I):
            nodes.append(CandidateNode(node_type="decision", label=first_sentence[:80] or "Recorded decision", description=first_sentence or text[:240]))
        if re.search(r"\b(failure|error|cleanly|renewed|caused|result|outcome)\b", text, re.I):
            nodes.append(CandidateNode(node_type="outcome", label=first_sentence[:80] or "Recorded outcome", description=first_sentence or text[:240]))
        if not nodes and text:
            nodes.append(CandidateNode(node_type="project", label="Imported evidence", description=text[:240]))
        return CandidateNodes(nodes=nodes[:4])

    if schema is CandidateEdges:
        labels = re.findall(r"- \([^)]+\) ([^:]+):", _last_user_text(messages))
        edges: list[CandidateEdge] = []
        if len(labels) >= 2:
            edges.append(
                CandidateEdge(
                    source_label=labels[0],
                    target_label=labels[1],
                    edge_type="contributory",
                    description=f"{labels[0]} is related to {labels[1]} in the same source chunk.",
                )
            )
        return CandidateEdges(edges=edges)

    if schema is Tags:
        labels = re.findall(r"- (?:NODE|EDGE): ([^:\n]+)", _last_user_text(messages))
        return Tags(tags=[Tag(label_or_description=label.strip(), evidence_type="fact", confidence=0.72) for label in labels[:8]])

    return _empty_schema_instance(schema)


class MockChatProvider(LLMProvider):
    provider_name = "mock"
    model_name = "mock-deterministic"
    supports_structured_output = True
    supports_embeddings = False

    def chat(self, messages: Messages, temperature: float = 0.0, response_schema: Optional[type[BaseModel]] = None):
        if response_schema is not None:
            return _mock_structured_output(messages, response_schema)
        return (
            "[mock LLM] No live model is configured (LLM_PROVIDER=mock). This is a "
            "deterministic offline response; configure a real provider for grounded generation."
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_name,
            model=self.model_name,
            available=True,
            supports_structured_output=True,
            supports_embeddings=False,
            detail="Deterministic offline mock provider.",
        )


# --- Provider selection (cached) -------------------------------------------
_chat_providers: dict[str, LLMProvider] = {}


def _make_chat_provider(name: str) -> LLMProvider:
    if name == "groq":
        from .providers.groq_provider import GroqProvider

        return GroqProvider()
    if name == "fireworks":
        from .providers.fireworks_provider import FireworksProvider

        return FireworksProvider()
    if name == "ollama":
        from .providers.ollama_provider import OllamaProvider

        return OllamaProvider()
    if name == "vllm":
        from .providers.vllm_provider import VllmProvider

        return VllmProvider()
    if name == "mock":
        return MockChatProvider()
    logger.warning("Unknown LLM_PROVIDER=%r; using groq.", name)
    from .providers.groq_provider import GroqProvider

    return GroqProvider()


def get_chat_provider() -> LLMProvider:
    name = (config.LLM_PROVIDER or "groq").strip().lower()
    if name not in _chat_providers:
        _chat_providers[name] = _make_chat_provider(name)
    return _chat_providers[name]


def chat(messages: Messages, temperature: float = 0.0, response_schema: Optional[type[BaseModel]] = None):
    """Delegate to the active chat provider. Raises LLMProviderError if the
    provider is unavailable — callers that want a fallback should catch it."""
    provider_name = (config.LLM_PROVIDER or "groq").strip().lower()
    try:
        return get_chat_provider().chat(messages, temperature=temperature, response_schema=response_schema)
    except LLMProviderError as exc:
        if provider_name == "fireworks":
            if config.REQUIRE_LIVE_LLM:
                logger.error("Fireworks provider failed and REQUIRE_LIVE_LLM=true: %s", exc)
                raise
            if config.GROQ_API_KEY:
                logger.warning("Fireworks provider failed; falling back to Groq: %s", exc)
                return _make_chat_provider("groq").chat(
                    messages, temperature=temperature, response_schema=response_schema
                )
            if response_schema is None:
                logger.warning("Fireworks provider failed; deterministic caller fallback required: %s", exc)
                raise
            logger.warning("Fireworks provider failed; falling back to deterministic mock.")
            return _make_chat_provider("mock").chat(
                messages, temperature=temperature, response_schema=response_schema
            )
        raise


# --- Embeddings ------------------------------------------------------------
_st_model = None


def _st_embed(texts: list[str]) -> list[list[float]]:
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer

        trust_remote = "nomic" in config.EMBEDDING_MODEL.lower()
        _st_model = SentenceTransformer(config.EMBEDDING_MODEL, trust_remote_code=trust_remote)
    return _st_model.encode(texts, normalize_embeddings=True).tolist()


def _mock_embed(texts: list[str]) -> list[list[float]]:
    # Deterministic 8-dim vectors — offline, no model download.
    out = []
    for t in texts:
        digest = hashlib.sha256((t or "").encode("utf-8")).digest()
        out.append([b / 255.0 for b in digest[:8]])
    return out


def _openai_like_embed(texts: list[str]) -> list[list[float]]:
    import httpx

    base = config.VLLM_BASE_URL  # OpenAI-compatible embeddings endpoint
    try:
        resp = httpx.post(
            f"{base}/embeddings", json={"model": config.EMBEDDING_MODEL, "input": texts}, timeout=30.0
        )
        resp.raise_for_status()
        return [d["embedding"] for d in resp.json()["data"]]
    except Exception as exc:  # noqa: BLE001
        raise LLMProviderError(f"openai_like embeddings failed at {base}: {exc}") from exc


def _ollama_embed(texts: list[str]) -> list[list[float]]:
    import httpx

    base = config.OLLAMA_BASE_URL.rstrip("/")
    try:
        out = []
        for t in texts:
            resp = httpx.post(
                f"{base}/api/embeddings", json={"model": config.OLLAMA_MODEL, "prompt": t}, timeout=30.0
            )
            resp.raise_for_status()
            out.append(resp.json()["embedding"])
        return out
    except Exception as exc:  # noqa: BLE001
        raise LLMProviderError(f"ollama embeddings failed at {base}: {exc}") from exc


def embed_texts(texts: list[str]) -> list[list[float]]:
    provider = (config.EMBEDDING_PROVIDER or "sentence_transformers").strip().lower()
    if provider == "mock":
        return _mock_embed(texts)
    if provider == "ollama":
        return _ollama_embed(texts)
    if provider == "openai_like":
        return _openai_like_embed(texts)
    if provider != "sentence_transformers":
        logger.warning("Unknown EMBEDDING_PROVIDER=%r; using sentence_transformers.", provider)
    return _st_embed(texts)


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


# --- Health ----------------------------------------------------------------
def _embedding_health() -> dict:
    provider = (config.EMBEDDING_PROVIDER or "sentence_transformers").strip().lower()
    # sentence_transformers/mock are always available locally; remote ones are
    # assumed reachable when configured (not probed here to keep health cheap).
    available = provider in ("sentence_transformers", "mock", "ollama", "openai_like")
    return {"provider": provider, "model": config.EMBEDDING_MODEL, "available": available}


def health() -> dict:
    chat_health = get_chat_provider().health()
    provider = (config.LLM_PROVIDER or "groq").strip().lower()
    key_configured = {
        "groq": bool(config.GROQ_API_KEY),
        "fireworks": bool(config.FIREWORKS_API_KEY),
        "ollama": True,
        "vllm": True,
        "mock": True,
    }.get(provider, False)
    return {
        "llm_provider": config.LLM_PROVIDER,
        "configured_provider": provider,
        "provider_key_configured": key_configured,
        "fallback_provider": "deterministic",
        "fallback_available": True,
        "embedding_provider": config.EMBEDDING_PROVIDER,
        "amd_mode": config.AMD_MODE,
        "chat": chat_health.model_dump(),
        "embedding": _embedding_health(),
    }
