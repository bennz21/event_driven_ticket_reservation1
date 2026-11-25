from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.events import router as events_router
from app.api.v1.seats import router as seats_router
from app.api.v1.reservations import router as reservations_router
from app.api.v1.ws import router as ws_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(events_router, prefix="/events", tags=["Events"])
api_router.include_router(seats_router, prefix="/events", tags=["Seats"])
api_router.include_router(reservations_router, prefix="/events", tags=["Reservations"])
api_router.include_router(ws_router, tags=["WebSockets"])
