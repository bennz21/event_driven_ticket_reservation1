import datetime
from typing import List, Tuple
from sqlalchemy import select, and_, not_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Seat, SeatStatus, Ticket
from app.schemas import SeatResponse
from app.core.config import settings
from app.core.events import get_event_bus, DomainEvent, EventType
from app.core.redis import redis_service


class SeatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_bus = get_event_bus()

    @staticmethod
    def _has_expired_cached_hold(cached_seats: List[dict], now: datetime.datetime) -> bool:
        for seat in cached_seats:
            if seat.get("status") == SeatStatus.HELD.value and seat.get("held_until"):
                try:
                    if datetime.datetime.fromisoformat(seat["held_until"]) < now:
                        return True
                except ValueError:
                    return True
        return False

    async def get_seats_for_event(self, event_id: int) -> List[SeatResponse]:
        """Fetch all seats for an event, using Redis cache when fresh and reconciling expired holds."""
        now = datetime.datetime.utcnow()

        cached = await redis_service.get_cached_seat_map(event_id)
        if cached is not None and not self._has_expired_cached_hold(cached, now):
            return [SeatResponse.model_validate(item) for item in cached]

        if cached is not None:
            await redis_service.invalidate_seat_map(event_id)

        query = select(Seat).where(Seat.event_id == event_id).order_by(Seat.row, Seat.seat_number)
        result = await self.db.execute(query)
        seats = result.scalars().all()

        # Reconcile any in-flight expired holds or orphaned reservations on read
        reconciled_seat_ids: List[int] = []
        for seat in seats:
            if seat.status == SeatStatus.HELD and seat.held_until and seat.held_until < now:
                seat.status = SeatStatus.AVAILABLE
                seat.held_by_session_id = None
                seat.held_until = None
                seat.version += 1
                reconciled_seat_ids.append(seat.id)

        # Check for orphaned reserved seats (seats marked reserved with no active ticket)
        orphaned_query = select(Seat).where(
            and_(
                Seat.event_id == event_id,
                Seat.status == SeatStatus.RESERVED,
                not_(Seat.id.in_(select(Ticket.seat_id))),
            )
        )
        orphaned_res = await self.db.execute(orphaned_query)
        orphaned_seats = orphaned_res.scalars().all()
        for seat in orphaned_seats:
            seat.status = SeatStatus.AVAILABLE
            seat.held_by_session_id = None
            seat.held_until = None
            seat.version += 1
            if seat.id not in reconciled_seat_ids:
                reconciled_seat_ids.append(seat.id)

        if reconciled_seat_ids:
            await self.db.commit()
            await redis_service.force_release_seat_locks(event_id, reconciled_seat_ids)
            await redis_service.invalidate_seat_map(event_id)
            await self.event_bus.publish(
                DomainEvent(
                    event_type=EventType.SEAT_RELEASED,
                    event_model_id=event_id,
                    payload={"seat_ids": reconciled_seat_ids, "reason": "reconciled_on_read"},
                )
            )

        serialized = [SeatResponse.model_validate(s) for s in seats]
        await redis_service.set_cached_seat_map(
            event_id,
            [item.model_dump(mode="json") for item in serialized],
        )
        return serialized

    async def hold_seats(
        self, event_id: int, seat_ids: List[int], session_id: str
    ) -> Tuple[List[int], List[int], datetime.datetime]:
        """
        Attempts to hold requested seats for a user session using Redis distributed locks
        (when enabled/available) backed by database persistence.
        Returns: (held_seat_ids, failed_seat_ids, hold_expiration_time)
        """
        now = datetime.datetime.utcnow()
        hold_until = now + datetime.timedelta(seconds=settings.SEAT_HOLD_DURATION_SECONDS)
        unique_seat_ids = list(dict.fromkeys(seat_ids))

        lock_result = await redis_service.acquire_seat_locks(
            event_id=event_id,
            seat_ids=unique_seat_ids,
            session_id=session_id,
            ttl_seconds=settings.SEAT_HOLD_DURATION_SECONDS,
        )

        if lock_result is not None:
            newly_acquired, refreshed, blocked_in_redis = lock_result
            candidate_ids = newly_acquired + refreshed
        else:
            newly_acquired, blocked_in_redis = [], []
            candidate_ids = unique_seat_ids

        held_seat_ids: List[int] = []
        failed_seat_ids: List[int] = list(blocked_in_redis)

        if candidate_ids:
            try:
                query = select(Seat).where(
                    and_(
                        Seat.event_id == event_id,
                        Seat.id.in_(candidate_ids),
                    )
                )
                result = await self.db.execute(query)
                seats = result.scalars().all()
            except Exception:
                await redis_service.release_seat_locks(event_id, newly_acquired, session_id)
                raise

            for seat in seats:
                is_available = seat.status == SeatStatus.AVAILABLE
                is_expired = (
                    seat.status == SeatStatus.HELD
                    and seat.held_until is not None
                    and seat.held_until < now
                )
                is_own_hold = (
                    seat.status == SeatStatus.HELD
                    and seat.held_by_session_id == session_id
                )

                if is_available or is_expired or is_own_hold:
                    seat.status = SeatStatus.HELD
                    seat.held_by_session_id = session_id
                    seat.held_until = hold_until
                    seat.version += 1
                    held_seat_ids.append(seat.id)
                else:
                    failed_seat_ids.append(seat.id)

            found_ids = {s.id for s in seats}
            for sid in candidate_ids:
                if sid not in found_ids and sid not in failed_seat_ids:
                    failed_seat_ids.append(sid)

        # Roll back newly acquired Redis locks for any seat that could not be held in DB
        if newly_acquired:
            held_set = set(held_seat_ids)
            to_unlock = [sid for sid in newly_acquired if sid not in held_set]
            if to_unlock:
                await redis_service.release_seat_locks(event_id, to_unlock, session_id)

        if held_seat_ids:
            try:
                await self.db.commit()
            except Exception:
                await redis_service.release_seat_locks(event_id, newly_acquired, session_id)
                raise

            await redis_service.invalidate_seat_map(event_id)
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
            await redis_service.release_seat_locks(event_id, released_ids, session_id)
            await redis_service.invalidate_seat_map(event_id)
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
