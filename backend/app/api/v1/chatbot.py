"""
Chatbot API endpoints.

POST /api/v1/chatbot/message  — send a user message, get a bot reply
DELETE /api/v1/chatbot/session/{session_id}  — clear conversation history
"""

import uuid
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.chatbot_service import chat, clear_session

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str | None = Field(
        default=None,
        description="Existing session ID. Omit on first message — a new one will be created.",
    )
    message: str = Field(..., min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/message", response_model=ChatResponse)
async def send_message(req: ChatRequest):
    """
    Send a user message to the AI assistant and receive a reply.
    The session_id links messages in the same conversation.
    """
    session_id = req.session_id or str(uuid.uuid4())
    reply = await chat(session_id, req.message)
    return ChatResponse(session_id=session_id, reply=reply)


@router.delete("/session/{session_id}", status_code=204)
async def reset_session(session_id: str):
    """Clear the conversation history for a given session (e.g., on logout)."""
    clear_session(session_id)
