import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.events import get_event_bus, DomainEvent
from app.core.websocket_manager import ws_manager
from app.services.background_worker import cleanup_worker
from app.db.init_db import init_database
from app.api.v1.router import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

async def forward_domain_events_to_websockets(event: DomainEvent):
    """EventBus subscriber that broadcasts all domain events to active WebSockets."""
    await ws_manager.broadcast(
        event_id=event.event_model_id,
        message={
            "type": event.event_type,
            "event_id": event.event_model_id,
            "payload": event.payload,
            "timestamp": event.timestamp,
        },
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info("Initializing database and seeding demo data...")
    await init_database()

    event_bus = get_event_bus()
    await event_bus.start()
    # Subscribe websocket broadcaster to all domain events
    event_bus.subscribe("*", forward_domain_events_to_websockets)

    # Start background cleanup worker for expired seat holds
    cleanup_worker.start()

    logger.info("Application startup complete.")
    yield

    # Shutdown sequence
    logger.info("Initiating graceful shutdown...")
    await cleanup_worker.stop()
    await event_bus.stop()
    logger.info("Shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Event-Driven Ticket & Real-Time Seat Reservation Backend with FastAPI and WebSockets",
    lifespan=lifespan,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "event_bus": "redis" if settings.USE_REDIS_EVENT_BUS else "in-memory",
    }
