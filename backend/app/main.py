import asyncio
import datetime
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.api.v1.chatbot import router as chatbot_router
from app.models import ApprovalStatus, Event
from app.routers import admin, auth, organizer, public
from app.services.pinecone_service import (
    cleanup_past_events,
    close_pinecone_client,
    init_pinecone_client,
    sync_events_to_pinecone,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


async def _pinecone_maintenance_loop() -> None:
    """Periodically delete past events from Pinecone and backfill only unsynced upcoming rows."""
    interval = max(300, settings.PINECONE_PAST_CLEANUP_INTERVAL_SECONDS)
    while True:
        try:
            def _run_once() -> None:
                with SessionLocal() as db:
                    cleanup_past_events(db)
                    today = datetime.date.today()
                    unsynced = (
                        db.execute(
                            select(Event).where(
                                Event.approval_status == ApprovalStatus.APPROVED,
                                Event.event_date >= today,
                                Event.embedding_hash.is_(None),
                            )
                        )
                        .scalars()
                        .all()
                    )
                    if unsynced:
                        sync_events_to_pinecone(unsynced, db=db)

            await asyncio.to_thread(_run_once)
        except Exception as exc:
            logger.warning("Pinecone scheduled cleanup skipped: %s", exc)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("MySQL PyMySQL database connection verified.")

    init_pinecone_client()
    maintenance_task = asyncio.create_task(_pinecone_maintenance_loop())
    try:
        yield
    finally:
        maintenance_task.cancel()
        try:
            await maintenance_task
        except asyncio.CancelledError:
            pass
        close_pinecone_client()
        engine.dispose()
        logger.info("Database engine and Pinecone client disposed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="Role-Based Event & Ticket Booking Platform (Admin, Event Organizer, General Public)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Admin"])
app.include_router(organizer.router, prefix=f"{settings.API_V1_STR}/organizer", tags=["Event Organizer"])
app.include_router(public.router, prefix=f"{settings.API_V1_STR}/public", tags=["General Public"])
app.include_router(chatbot_router, prefix=f"{settings.API_V1_STR}/chatbot", tags=["AI Assistant"])


@app.get("/health", tags=["Health"])
def health_check():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "database": "mysql+pymysql",
    }
