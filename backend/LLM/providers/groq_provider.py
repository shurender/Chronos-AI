"""Groq chat provider (via langchain-groq). Preserves the existing Groq path,
including structured output used by the extraction pipeline."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from backend import config

from .base import LLMProvider, LLMProviderError, Messages, ProviderHealth


class GroqProvider(LLMProvider):
    provider_name = "groq"
    supports_structured_output = True
    supports_embeddings = False

    def __init__(self) -> None:
        self.model_name = config.GROQ_MODEL

    def _model(self, temperature: float):
        if not config.GROQ_API_KEY:
            raise LLMProviderError("GROQ_API_KEY is not set.")
        from langchain_groq import ChatGroq

        return ChatGroq(model=self.model_name, temperature=temperature, api_key=config.GROQ_API_KEY)

    def chat(self, messages: Messages, temperature: float = 0.0, response_schema: Optional[type[BaseModel]] = None):
        model = self._model(temperature)
        if response_schema is not None:
            return model.with_structured_output(response_schema).invoke(messages)
        resp = model.invoke(messages)
        return getattr(resp, "content", str(resp))

    def health(self) -> ProviderHealth:
        ok = bool(config.GROQ_API_KEY)
        return ProviderHealth(
            provider=self.provider_name,
            model=self.model_name,
            available=ok,
            supports_structured_output=True,
            supports_embeddings=False,
            detail="GROQ_API_KEY present" if ok else "GROQ_API_KEY missing — chat unavailable",
        )
