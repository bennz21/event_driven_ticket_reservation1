import asyncio
import datetime
import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, select, text

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
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

VERCEL_ORIGIN_RE = re.compile(r"^https://.*\.vercel\.app$")


def ensure_additive_schema(target_engine) -> None:
    """Safely create missing tables or columns (e.g. on Render/TiDB) without altering existing data."""
    Base.metadata.create_all(bind=target_engine)
    with target_engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        if "events" in tables:
            ev_cols = {c["name"] for c in inspector.get_columns("events")}
            if "seating_type" not in ev_cols:
                conn.execute(
                    text(
                        "ALTER TABLE events ADD COLUMN seating_type "
                        "VARCHAR(16) NOT NULL DEFAULT 'open'"
                    )
                    if target_engine.dialect.name == "sqlite"
                    else text(
                        "ALTER TABLE events ADD COLUMN seating_type "
                        "ENUM('seated','open') NOT NULL DEFAULT 'open'"
                    )
                )
            if "total_rows" not in ev_cols:
                conn.execute(text("ALTER TABLE events ADD COLUMN total_rows INT NULL"))
            if "seats_per_row" not in ev_cols:
                conn.execute(text("ALTER TABLE events ADD COLUMN seats_per_row INT NULL"))
            if "embedding_hash" not in ev_cols:
                conn.execute(text("ALTER TABLE events ADD COLUMN embedding_hash VARCHAR(64) NULL"))
        if "tickets" in tables:
            t_cols = {c["name"] for c in inspector.get_columns("tickets")}
            if "seat_id" not in t_cols:
                conn.execute(text("ALTER TABLE tickets ADD COLUMN seat_id INT NULL"))
            if "seat_label" not in t_cols:
                conn.execute(text("ALTER TABLE tickets ADD COLUMN seat_label VARCHAR(20) NULL"))


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
    ensure_additive_schema(engine)
    logger.info("MySQL PyMySQL database connection & schema verified.")

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

cors_origins = list(dict.fromkeys([*settings.CORS_ORIGINS, settings.FRONTEND_URL.rstrip("/")]))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def cors_aware_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    headers = {}
    origin = request.headers.get("origin")
    if origin and (origin in cors_origins or VERCEL_ORIGIN_RE.match(origin)):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
        headers=headers,
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
