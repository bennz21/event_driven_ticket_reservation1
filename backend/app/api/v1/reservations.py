from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_optional_current_user, get_reservation_service
from app.core.database import get_db
from app.models import Reservation, User
from app.services.reservation_service import ReservationService
from app.schemas import ReservationCreate, ReservationResponse

router = APIRouter()

@router.post("/{event_id}/reservations/confirm", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def confirm_reservation(
    event_id: int,
    req: ReservationCreate,
    reservation_service: ReservationService = Depends(get_reservation_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Confirms held seats, books reservation, and generates digital tickets.
    Emits RESERVATION_CONFIRMED event across the event bus and notifies WebSocket listeners.
    """
    email = req.customer_email or (current_user.email if current_user and current_user.email else "")
    return await reservation_service.create_reservation(
        event_id=event_id,
        seat_ids=req.seat_ids,
        session_id=req.session_id,
        customer_name=req.customer_name,
        customer_email=email,
        user_id=current_user.id if current_user else None,
    )

@router.get("/reservations/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve reservation and ticket details."""
    query = (
        select(Reservation)
        .options(selectinload(Reservation.tickets))
        .where(Reservation.id == reservation_id)
    )
    result = await db.execute(query)
    reservation = result.scalars().first()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    return reservation
