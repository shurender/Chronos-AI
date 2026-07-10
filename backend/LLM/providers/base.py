"""
LLM provider abstraction.

A provider implements chat() (optionally structured), embed(), and health().
Shared helpers for OpenAI-compatible HTTP endpoints (Fireworks / vLLM / Ollama)
live here so those providers stay tiny. No network calls at import time.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel


class LLMProviderError(RuntimeError):
    """Raised when a provider cannot serve a request (missing key, unreachable, etc.)."""


class ProviderHealth(BaseModel):
    provider: str
    model: str = ""
    available: bool
    supports_structured_output: bool = False
    supports_embeddings: bool = False
    detail: str = ""


# Messages accepted by chat(): a plain string, or a list of (role, content)
# tuples / {"role","content"} dicts.
Messages = Any


def to_openai_messages(messages: Messages) -> list[dict]:
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    role_map = {"human": "user", "ai": "assistant", "system": "system"}
    out: list[dict] = []
    for m in messages:
        if isinstance(m, dict):
            out.append(m)
        else:
            role, content = m
            out.append({"role": role_map.get(role, role), "content": content})
    return out


def openai_chat(
    base_url: str,
    api_key: Optional[str],
    model: str,
    messages: Messages,
    temperature: float,
    response_schema: Optional[type[BaseModel]],
    timeout: float = 30.0,
):
    """Call an OpenAI-compatible /chat/completions endpoint. Returns parsed
    `response_schema` instance when given, else the text content."""
    import httpx

    payload_messages = to_openai_messages(messages)
    body: dict = {"model": model, "messages": payload_messages, "temperature": temperature}
    if response_schema is not None:
        schema_json = json.dumps(response_schema.model_json_schema())
        payload_messages.append(
            {"role": "system", "content": f"Respond ONLY with JSON matching this schema: {schema_json}"}
        )
        body["response_format"] = {"type": "json_object"}

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = httpx.post(f"{base_url}/chat/completions", json=body, headers=headers, timeout=timeout)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001 — normalized into a provider error
        raise LLMProviderError(f"OpenAI-compatible chat failed at {base_url}: {exc}") from exc

    if response_schema is not None:
        return response_schema.model_validate_json(content)
    return content


def probe_openai_endpoint(base_url: str, api_key: Optional[str], timeout: float = 1.5) -> bool:
    """Cheap best-effort reachability check for /models. Never raises."""
    import httpx

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        resp = httpx.get(f"{base_url}/models", headers=headers, timeout=timeout)
        return resp.status_code < 500
    except Exception:
        return False


class LLMProvider(ABC):
    provider_name: str = "base"
    model_name: str = ""
    supports_structured_output: bool = False
    supports_embeddings: bool = False

    @abstractmethod
    def chat(self, messages: Messages, temperature: float = 0.0, response_schema: Optional[type[BaseModel]] = None):
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise LLMProviderError(f"{self.provider_name} provider does not support embeddings.")

    @abstractmethod
    def health(self) -> ProviderHealth:
        ...
