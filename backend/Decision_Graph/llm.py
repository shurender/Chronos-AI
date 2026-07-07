"""
LLM + embedding setup.

- Chat model: Groq via langchain-groq, used with .with_structured_output()
  so extraction is forced into our Pydantic schema instead of free text.
- Embeddings: local sentence-transformers model (no API key needed).
  Swap EMBEDDING_MODEL in .env to "nomic-ai/nomic-embed-text-v1.5" if you
  want to match the original spec exactly (needs trust_remote_code=True and
  a bigger download). Keeping the swap isolated to this one function is what
  lets you move to a different embedding backend (e.g. Person E's ROCm-hosted
  model) later with a one-line change.
"""

import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

_embedding_model = None


def get_chat_model(temperature: float = 0.0) -> ChatGroq:
    """Return a Groq chat model. Requires GROQ_API_KEY in the environment."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return ChatGroq(model=GROQ_MODEL, temperature=temperature, api_key=api_key)


def get_embedding_model() -> SentenceTransformer:
    """Lazily load and cache the local embedding model."""
    global _embedding_model
    if _embedding_model is None:
        trust_remote = "nomic" in EMBEDDING_MODEL_NAME.lower()
        _embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_NAME, trust_remote_code=trust_remote
        )
    return _embedding_model


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    return model.encode(texts, normalize_embeddings=True).tolist()