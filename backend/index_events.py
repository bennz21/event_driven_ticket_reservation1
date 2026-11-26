"""
index_events.py — One-shot script to index all events from the DB into Pinecone.

Run from the backend/ directory:
    python index_events.py

Re-run any time you add new events.
Requires GEMINI_API_KEY and PINECONE_API_KEY in backend/.env
"""

import asyncio
import logging
import sys
import os

# Make sure the backend package is on the path
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("indexer")


async def main():
    from app.core.database import AsyncSessionLocal
    from app.core.config import settings
    from app.models import Event
    from app.services.pinecone_service import index_events, _get_index
    from sqlalchemy import select

    # Quick pre-flight checks
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your_"):
        logger.error(
            "GEMINI_API_KEY is not set in backend/.env — embeddings require a valid key.\n"
            "Get one free at https://ai.google.dev"
        )
        return

    if not settings.PINECONE_API_KEY or settings.PINECONE_API_KEY.startswith("your_"):
        logger.error(
            "PINECONE_API_KEY is not set in backend/.env.\n"
            "Get it from: https://app.pinecone.io → API Keys"
        )
        return

    index = _get_index()
    if index is None:
        logger.error("Could not connect to Pinecone index '%s'. Check your API key and index name.", settings.PINECONE_INDEX_NAME)
        return

    logger.info("Connected to Pinecone index: '%s'", settings.PINECONE_INDEX_NAME)
    logger.info("Fetching events from database...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Event).order_by(Event.id))
        events = result.scalars().all()

    if not events:
        logger.warning("No events found in the database. Run the backend first to seed demo data.")
        return

    logger.info("Found %d event(s). Generating embeddings and uploading to Pinecone...", len(events))
    index_events(events)
    logger.info("✅ Done! Pinecone index '%s' now has %d event(s) indexed.", settings.PINECONE_INDEX_NAME, len(events))
    logger.info("Restart your backend server to activate RAG for the chatbot.")


if __name__ == "__main__":
    asyncio.run(main())
