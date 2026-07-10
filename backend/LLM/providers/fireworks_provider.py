"""Fireworks chat provider using the OpenAI-compatible API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from backend import config

from .base import (
    LLMProvider,
    LLMProviderError,
    Messages,
    ProviderHealth,
    openai_chat,
    probe_openai_endpoint,
)

FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"


class FireworksProvider(LLMProvider):
    provider_name = "fireworks"
    supports_structured_output = True
    supports_embeddings = False

    def __init__(self) -> None:
        self.model_name = config.FIREWORKS_MODEL

    def chat(
        self,
        messages: Messages,
        temperature: float = 0.0,
        response_schema: Optional[type[BaseModel]] = None,
    ):
        if not config.FIREWORKS_API_KEY:
            raise LLMProviderError("FIREWORKS_API_KEY is not set.")
        return openai_chat(
            FIREWORKS_BASE_URL,
            config.FIREWORKS_API_KEY,
            self.model_name,
            messages,
            temperature,
            response_schema,
        )

    def health(self) -> ProviderHealth:
        key_present = bool(config.FIREWORKS_API_KEY)
        reachable = probe_openai_endpoint(FIREWORKS_BASE_URL, config.FIREWORKS_API_KEY) if key_present else False
        return ProviderHealth(
            provider=self.provider_name,
            model=self.model_name,
            available=key_present,
            supports_structured_output=True,
            supports_embeddings=False,
            detail=(
                f"FIREWORKS_API_KEY present; models endpoint reachable={reachable}"
                if key_present
                else "FIREWORKS_API_KEY missing; chat will fall back."
            ),
        )
