"""vLLM chat provider — OpenAI-compatible local endpoint. This is the clean
AMD/ROCm deployment path: run vLLM locally, point VLLM_BASE_URL at it, set
LLM_PROVIDER=vllm. No API key required by default."""

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


class VllmProvider(LLMProvider):
    provider_name = "vllm"
    supports_structured_output = True
    supports_embeddings = False

    def __init__(self) -> None:
        self.model_name = config.VLLM_MODEL
        self.base_url = config.VLLM_BASE_URL

    def chat(self, messages: Messages, temperature: float = 0.0, response_schema: Optional[type[BaseModel]] = None):
        # vLLM typically needs no auth; some deployments accept a bearer token.
        return openai_chat(self.base_url, None, self.model_name, messages, temperature, response_schema)

    def health(self) -> ProviderHealth:
        reachable = probe_openai_endpoint(self.base_url, None)
        return ProviderHealth(
            provider=self.provider_name,
            model=self.model_name,
            available=reachable,
            supports_structured_output=True,
            supports_embeddings=False,
            detail=(
                f"Reachable at {self.base_url}" if reachable else f"No OpenAI-compatible endpoint at {self.base_url}"
            ),
        )
