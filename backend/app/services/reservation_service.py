import datetime
import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Seat, SeatStatus, Reservation, ReservationStatus, Ticket
from app.core.events import get_event_bus, DomainEvent, EventType
from app.core.redis import redis_service

class ReservationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_bus = get_event_bus()

    async def create_reservation(
        self,
        event_id: int,
        seat_ids: List[int],
        session_id: str,
        customer_name: str,
        customer_email: str = "",
        user_id: Optional[int] = None,
    ) -> Reservation:
        """
        Validates held seats for session and converts them into confirmed Reservation & Tickets.
        Publishes RESERVATION_CONFIRMED event to the event bus.
        """
        now = datetime.datetime.utcnow()

        if not await redis_service.verify_seat_locks_not_stolen(event_id, seat_ids, session_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="One or more selected seats are currently locked by another session.",
            )

        # Query seats locked by this session
        query = select(Seat).where(
            and_(
                Seat.event_id == event_id,
                Seat.id.in_(seat_ids),
            )
        )
        result = await self.db.execute(query)
        seats = result.scalars().all()

        if len(seats) != len(seat_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more selected seats were not found.",
            )

        # Ensure all seats are currently held by this session and not expired
        for seat in seats:
            if seat.status != SeatStatus.HELD or seat.held_by_session_id != session_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Seat {seat.row}-{seat.seat_number} is not locked by your session.",
                )
            if seat.held_until and seat.held_until < now:
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail=f"Hold for seat {seat.row}-{seat.seat_number} has expired. Please select again.",
                )

        total_amount = sum(s.price for s in seats)

        # Create Reservation
        reservation = Reservation(
            event_id=event_id,
            user_id=user_id,
            session_id=session_id,
            customer_name=customer_name,
            customer_email=customer_email,
            total_amount=total_amount,
            status=ReservationStatus.CONFIRMED,
        )
        self.db.add(reservation)
        await self.db.flush()  # populate reservation.id

        # Update seats and issue tickets
        tickets = []
        for seat in seats:
            seat.status = SeatStatus.RESERVED
            seat.held_by_session_id = None
            seat.held_until = None
            seat.version += 1

            ticket_code = f"TICK-{event_id}-{seat.row}{seat.seat_number}-{uuid.uuid4().hex[:6].upper()}"
            ticket = Ticket(
                reservation_id=reservation.id,
                seat_id=seat.id,
                ticket_code=ticket_code,
            )
            self.db.add(ticket)
            tickets.append(ticket)

        await self.db.commit()
        await redis_service.force_release_seat_locks(event_id, seat_ids)
        await redis_service.invalidate_seat_map(event_id)

        # Re-query with eagerly loaded tickets
        res_query = (
            select(Reservation)
            .options(selectinload(Reservation.tickets))
            .where(Reservation.id == reservation.id)
        )
        final_reservation = (await self.db.execute(res_query)).scalar_one()

        # Publish domain event
        await self.event_bus.publish(
            DomainEvent(
                event_type=EventType.RESERVATION_CONFIRMED,
                event_model_id=event_id,
                payload={
                    "reservation_id": reservation.id,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "total_amount": total_amount,
                    "seat_ids": seat_ids,
                    "ticket_codes": [t.ticket_code for t in tickets],
                },
            )
        )

        return final_reservation
