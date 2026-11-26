"""
Chatbot service — uses Gemini v1 REST API directly via httpx.
No google-generativeai or google-genai package required.
httpx is already in requirements.txt.
"""

import asyncio
import datetime
import logging
import uuid
import httpx

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.services.pinecone_service import format_events_for_context, search_relevant_context

# ---------------------------------------------------------------------------
# In-memory session store: { session_id: [ {role, parts:[{text}]}, ... ] }
# REST API content format — same for both user and model turns.
# ---------------------------------------------------------------------------
_sessions: dict[str, list] = {}

CANDIDATE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3.8-flash",
]

SYSTEM_PROMPT = """\
You are a friendly and knowledgeable ticket reservation assistant for SeatStream.

Your capabilities:
- Help users discover approved events, check ticket/seat availability, and understand pricing
- Guide users through creating a Public or Event Organizer account, selecting seats (for seated events) or ticket quantity (for open events, max 5 per booking), and completing payment
- Explain cancellation policies (bookings can be cancelled before the event starts to restore tickets and refund payment)

Rules:
- Be concise and helpful; answer in 2-4 sentences unless more detail is needed
- When context about specific events is provided, use it; otherwise say you don't have live event details
- Never invent event names, seat numbers, or prices — only state facts present in the context
"""


async def _augment(user_message: str) -> str:
    # 1. Try vector retrieval (Pinecone) in worker thread so event loop isn't blocked
    context = ""
    try:
        context = await asyncio.to_thread(search_relevant_context, user_message, 3)
    except Exception as exc:
        logger.debug("Pinecone search skipped/failed: %s", exc)

    # 2. Fall back to upcoming approved event records in MySQL
    if not context:
        try:
            from sqlalchemy import select
            from app.core.database import SessionLocal
            from app.models import ApprovalStatus, Event

            today = datetime.date.today()
            with SessionLocal() as session:
                events = (
                    session.execute(
                        select(Event)
                        .where(
                            Event.approval_status == ApprovalStatus.APPROVED,
                            Event.event_date >= today,
                        )
                        .order_by(Event.event_date.asc(), Event.event_time.asc())
                        .limit(5)
                    )
                    .scalars()
                    .all()
                )
                if events:
                    context = format_events_for_context(events)
        except Exception as exc:
            logger.debug("Fallback event query skipped: %s", exc)

    if context:
        return (
            f"[Relevant event information from our platform]\n{context}\n\n"
            f"[User question]\n{user_message}"
        )
    return user_message


async def chat(session_id: str, user_message: str) -> str:
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key or api_key.startswith("your_"):
        return (
            "⚠️ Add your GEMINI_API_KEY to backend/.env and restart the server. "
            "Get a free key at https://ai.google.dev"
        )

    augmented = await _augment(user_message)
    history   = _sessions.get(session_id, [])

    # Build contents list: existing history + new user turn
    contents = history + [
        {"role": "user", "parts": [{"text": augmented}]}
    ]

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": 512,
            "temperature": 0.7,
        },
    }

    last_error = None
    for model_name in CANDIDATE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    params={"key": api_key},
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    bot_reply = data["candidates"][0]["content"]["parts"][0]["text"]

                    # Persist conversation history (keep last 20 turns)
                    updated = contents + [
                        {"role": "model", "parts": [{"text": bot_reply}]}
                    ]
                    _sessions[session_id] = updated[-20:]
                    return bot_reply
                else:
                    logger.warning(
                        "Model %s returned status %d: %s",
                        model_name,
                        resp.status_code,
                        resp.text[:200],
                    )
                    last_error = f"HTTP {resp.status_code}"
        except httpx.TimeoutException:
            logger.warning("Model %s timed out after 30s.", model_name)
            last_error = "timeout"
        except Exception as exc:
            logger.warning("Error with model %s: %s", model_name, exc)
            last_error = str(exc)

    logger.error("All Gemini candidate models failed for session %s: %s", session_id, last_error)
    return "Sorry, I ran into an issue connecting to the AI assistant. Please try again in a moment."


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


def new_session_id() -> str:
    return str(uuid.uuid4())
