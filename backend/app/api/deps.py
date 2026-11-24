from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.seat_service import SeatService
from app.services.reservation_service import ReservationService

async def get_seat_service(db: AsyncSession = Depends(get_db)) -> SeatService:
    return SeatService(db)

async def get_reservation_service(db: AsyncSession = Depends(get_db)) -> ReservationService:
    return ReservationService(db)
