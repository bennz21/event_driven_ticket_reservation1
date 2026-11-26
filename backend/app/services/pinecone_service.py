"""
Pinecone service — uses Gemini v1 REST API directly via httpx.
No google-generativeai or google-genai package required.
httpx is already in requirements.txt.
"""

import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("pinecone not installed — RAG disabled. Run: pip install pinecone")

from app.core.config import settings

_pinecone_index = None

GEMINI_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-embedding-001:embedContent"
)


def _get_index():
    global _pinecone_index
    if _pinecone_index is not None:
        return _pinecone_index
    if not PINECONE_AVAILABLE:
        return None

    api_key    = getattr(settings, "PINECONE_API_KEY", "")
    index_name = getattr(settings, "PINECONE_INDEX_NAME", "ticket-chatbot")

    if not api_key or api_key.startswith("your_"):
        logger.warning("PINECONE_API_KEY not set — RAG disabled.")
        return None

    try:
        pc = Pinecone(api_key=api_key)
        _pinecone_index = pc.Index(index_name)
        logger.info("Pinecone index '%s' connected.", index_name)
    except Exception as exc:
        logger.error("Pinecone connection failed: %s", exc)
    return _pinecone_index


def _get_embedding(text: str) -> Optional[list]:
    """
    Calls Gemini gemini-embedding-001 via REST v1beta API using httpx (sync).
    Returns 1024-dim float list matching Pinecone index, or None on failure.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key or api_key.startswith("your_"):
        logger.warning("GEMINI_API_KEY not set — embeddings disabled.")
        return None
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                GEMINI_EMBED_URL,
                params={"key": api_key},
                json={
                    "model": "models/gemini-embedding-001",
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": 1024,
                },
            )
            resp.raise_for_status()
            return resp.json()["embedding"]["values"]
    except Exception as exc:
        logger.error("Embedding failed: %s", exc)
        return None


def index_events(events: list) -> None:
    """Upsert event documents into Pinecone (supports both Document schema and Vector index)."""
    index = _get_index()
    if index is None:
        return

    documents = []
    vectors = []

    for event in events:
        if hasattr(event, "__dict__"):
            title = getattr(event, "title", "")
            venue = getattr(event, "venue_name", "")
            date  = str(getattr(event, "event_date", ""))
            price = getattr(event, "base_price", 0)
            desc  = getattr(event, "description", "")
            eid   = getattr(event, "id", 0)
        else:
            title = event.get("title", "")
            venue = event.get("venue_name", "")
            date  = str(event.get("event_date", ""))
            price = event.get("base_price", 0)
            desc  = event.get("description", "")
            eid   = event.get("id", 0)

        text = (
            f"Event: {title}. Venue: {venue}. Date: {date}. "
            f"Base price: ${price}. Description: {desc}"
        )

        documents.append({
            "_id": f"event-{eid}",
            "title": title,
            "chunk_text": text,
        })

        embedding = _get_embedding(text)
        if embedding:
            vectors.append({
                "id": f"event-{eid}",
                "values": embedding,
                "metadata": {"text": text, "event_id": eid, "title": title},
            })

    # Try Documents API first (matches managed schema indexes)
    if hasattr(index, "documents") and documents:
        try:
            index.documents.upsert(namespace="events", documents=documents)
            logger.info("Indexed %d event document(s) into Pinecone.", len(documents))
            return
        except Exception as doc_exc:
            logger.debug("Pinecone documents.upsert fallback: %s", doc_exc)

    # Fallback to classic vector upsert
    if vectors:
        try:
            index.upsert(vectors=vectors, namespace="events")
            logger.info("Indexed %d event vector(s) into Pinecone.", len(vectors))
        except Exception as exc:
            logger.error("Pinecone vector upsert failed: %s", exc)


def search_relevant_context(query: str, top_k: int = 3) -> str:
    """Search Pinecone for relevant event context (supports Document and Vector indexes)."""
    index = _get_index()
    if index is None:
        return ""

    # 1. Try Document search (for indexes configured with schema & embedded field)
    if hasattr(index, "documents"):
        try:
            res = index.documents.search(
                namespace="events",
                score_by=[{"type": "embed", "field": "chunk_text", "query": query}],
                include_fields=["title", "chunk_text"],
                top_k=top_k,
            )
            chunks = []
            for m in getattr(res, "matches", []):
                chunk = getattr(m, "chunk_text", None) or m.to_dict().get("chunk_text", "")
                if chunk:
                    chunks.append(chunk)
            if chunks:
                return "\n".join(chunks)
        except Exception as doc_exc:
            logger.debug("Pinecone document search exception: %s", doc_exc)

    # 2. Try classic vector query
    embedding = _get_embedding(query)
    if embedding is not None:
        try:
            results = index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True,
                namespace="events",
            )
            chunks = [
                m["metadata"]["text"]
                for m in results.get("matches", [])
                if m.get("score", 0) > 0.5 and "text" in m.get("metadata", {})
            ]
            return "\n".join(chunks)
        except Exception as exc:
            logger.debug("Pinecone vector query exception: %s", exc)

    return ""
