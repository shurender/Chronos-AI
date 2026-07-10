"""
FastAPI route for the Future Self avatar chat.

POST /avatar/chat — grounded, timeline-aware replies. Uses the Groq LLM when
GROQ_API_KEY is set, otherwise a deterministic labelled fallback (never crashes).
"""

from fastapi import APIRouter

from .avatar_engine import generate_avatar_reply
from .avatar_schema import AvatarChatRequest, AvatarChatResponse

router = APIRouter(prefix="/avatar", tags=["future-self"])


@router.post("/chat", response_model=AvatarChatResponse)
def avatar_chat(request: AvatarChatRequest):
    return generate_avatar_reply(request)
