"""Ollama chat provider — uses Ollama's OpenAI-compatible endpoint
(OLLAMA_BASE_URL + /v1). Optional local provider; no key required."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from backend import config

from .base import (
    LLMProvider,
    Messages,
    ProviderHealth,
    openai_chat,
    probe_openai_endpoint,
)


class OllamaProvider(LLMProvider):
    provider_name = "ollama"
    supports_structured_output = True
    supports_embeddings = False

    def __init__(self) -> None:
        self.model_name = config.OLLAMA_MODEL
        self.base_url = config.OLLAMA_BASE_URL.rstrip("/") + "/v1"

    def chat(self, messages: Messages, temperature: float = 0.0, response_schema: Optional[type[BaseModel]] = None):
        return openai_chat(self.base_url, None, self.model_name, messages, temperature, response_schema)

    def health(self) -> ProviderHealth:
        reachable = probe_openai_endpoint(self.base_url, None)
        return ProviderHealth(
            provider=self.provider_name,
            model=self.model_name,
            available=reachable,
            supports_structured_output=True,
            supports_embeddings=False,
            detail=(f"Reachable at {self.base_url}" if reachable else f"Ollama not reachable at {self.base_url}"),
        )
