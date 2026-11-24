import datetime
from typing import List, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Seat, SeatStatus
from app.core.config import settings
from app.core.events import get_event_bus, DomainEvent, EventType

class SeatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_bus = get_event_bus()

    async def get_seats_for_event(self, event_id: int) -> List[Seat]:
        """Fetch all seats for an event, automatically reconciling expired holds."""
        now = datetime.datetime.utcnow()
        query = select(Seat).where(Seat.event_id == event_id).order_by(Seat.row, Seat.seat_number)
        result = await self.db.execute(query)
        seats = result.scalars().all()

        # Reconcile any in-flight expired holds on read
        expired_seat_ids = []
        for seat in seats:
            if seat.status == SeatStatus.HELD and seat.held_until and seat.held_until < now:
                seat.status = SeatStatus.AVAILABLE
                seat.held_by_session_id = None
                seat.held_until = None
                seat.version += 1
                expired_seat_ids.append(seat.id)

        if expired_seat_ids:
            await self.db.commit()
            # Publish event for released expired seats
            await self.event_bus.publish(
                DomainEvent(
                    event_type=EventType.SEAT_RELEASED,
                    event_model_id=event_id,
                    payload={"seat_ids": expired_seat_ids, "reason": "expired_hold_on_read"},
                )
            )

        return list(seats)

    async def hold_seats(
        self, event_id: int, seat_ids: List[int], session_id: str
    ) -> Tuple[List[int], List[int], datetime.datetime]:
        """
        Attempts to hold requested seats for a user session with optimistic locking.
        Returns: (held_seat_ids, failed_seat_ids, hold_expiration_time)
        """
        now = datetime.datetime.utcnow()
        hold_until = now + datetime.timedelta(seconds=settings.SEAT_HOLD_DURATION_SECONDS)

        query = select(Seat).where(
            and_(
                Seat.event_id == event_id,
                Seat.id.in_(seat_ids)
            )
        )
        result = await self.db.execute(query)
        seats = result.scalars().all()

        held_seat_ids: List[int] = []
        failed_seat_ids: List[int] = []

        for seat in seats:
            # A seat is eligible for hold if:
            # 1. It is AVAILABLE, OR
            # 2. It was HELD but the hold expired, OR
            # 3. It is already HELD by the current session (refreshing the hold)
            is_available = seat.status == SeatStatus.AVAILABLE
            is_expired = seat.status == SeatStatus.HELD and seat.held_until and seat.held_until < now
            is_own_hold = seat.status == SeatStatus.HELD and seat.held_by_session_id == session_id

            if is_available or is_expired or is_own_hold:
                seat.status = SeatStatus.HELD
                seat.held_by_session_id = session_id
                seat.held_until = hold_until
                seat.version += 1
                held_seat_ids.append(seat.id)
            else:
                failed_seat_ids.append(seat.id)

        # Also account for any seat IDs that weren't even found
        found_ids = {s.id for s in seats}
        for sid in seat_ids:
            if sid not in found_ids and sid not in failed_seat_ids:
                failed_seat_ids.append(sid)

        if held_seat_ids:
            await self.db.commit()

            # Publish event to event bus
            await self.event_bus.publish(
                DomainEvent(
                    event_type=EventType.SEAT_HELD,
                    event_model_id=event_id,
                    payload={
                        "seat_ids": held_seat_ids,
                        "session_id": session_id,
                        "held_until": hold_until.isoformat(),
                    },
                )
            )

        return held_seat_ids, failed_seat_ids, hold_until

    async def release_seats(self, event_id: int, seat_ids: List[int], session_id: str) -> List[int]:
        """Release held seats belonging to this session."""
        query = select(Seat).where(
            and_(
                Seat.event_id == event_id,
                Seat.id.in_(seat_ids),
                Seat.status == SeatStatus.HELD,
                Seat.held_by_session_id == session_id,
            )
        )
        result = await self.db.execute(query)
        seats = result.scalars().all()

        released_ids = []
        for seat in seats:
            seat.status = SeatStatus.AVAILABLE
            seat.held_by_session_id = None
            seat.held_until = None
            seat.version += 1
            released_ids.append(seat.id)

        if released_ids:
            await self.db.commit()
            await self.event_bus.publish(
                DomainEvent(
                    event_type=EventType.SEAT_RELEASED,
                    event_model_id=event_id,
                    payload={
                        "seat_ids": released_ids,
                        "session_id": session_id,
                        "reason": "user_cancelled",
                    },
                )
            )

        return released_ids
