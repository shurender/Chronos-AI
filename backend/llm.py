"""
LLM + embedding compatibility shim.

Chat and embeddings now go through backend.LLM.llm_service (provider
abstraction: groq | fireworks | ollama | vllm | mock for chat;
sentence_transformers | ollama | openai_like | mock for embeddings). This
module keeps the historical import surface (embed_text, embed_texts,
get_chat_model) so existing callers keep working unchanged.
"""

from __future__ import annotations

# Re-export embeddings from the service so every existing `from backend.llm
# import embed_text` caller automatically uses the embedding provider.
from backend.LLM.llm_service import embed_text, embed_texts  # noqa: F401


def get_chat_model(temperature: float = 0.0):
    """Legacy Groq chat accessor, preserved for backward compatibility.
    Prefer backend.LLM.llm_service.chat(). Requires GROQ_API_KEY."""
    from langchain_groq import ChatGroq

    from backend import config

    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set. Copy .env.example to .env and add your key.")
    return ChatGroq(model=config.GROQ_MODEL, temperature=temperature, api_key=config.GROQ_API_KEY)
