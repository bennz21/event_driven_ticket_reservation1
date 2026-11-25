import asyncio
import datetime
import logging
from sqlalchemy import select, and_, not_
from app.core.database import AsyncSessionLocal
from app.models import Seat, SeatStatus, Ticket
from app.core.events import get_event_bus, DomainEvent, EventType
from app.core.redis import redis_service

logger = logging.getLogger("background_worker")

class ExpiredHoldCleanupWorker:
    """
    Background worker that runs periodically to release seats whose hold TTL has expired
    or whose reservation was deleted from the database.
    Emits SEAT_RELEASED domain events so WebSockets instantly reflect available seats.
    """
    def __init__(self, interval_seconds: int = 3):
        self.interval = interval_seconds
        self.is_running = False
        self._task = None

    async def _sweep(self):
        while self.is_running:
            try:
                now = datetime.datetime.utcnow()
                async with AsyncSessionLocal() as session:
                    events_map = {}

                    # 1. Find held seats that have expired
                    query = select(Seat).where(
                        and_(
                            Seat.status == SeatStatus.HELD,
                            Seat.held_until.isnot(None),
                            Seat.held_until < now,
                        )
                    )
                    result = await session.execute(query)
                    expired_seats = result.scalars().all()

                    for seat in expired_seats:
                        seat.status = SeatStatus.AVAILABLE
                        seat.held_by_session_id = None
                        seat.held_until = None
                        seat.version += 1
                        events_map.setdefault(seat.event_id, []).append(seat.id)

                    # 2. Find reserved seats whose reservation was deleted (orphaned reservations)
                    orphaned_query = select(Seat).where(
                        and_(
                            Seat.status == SeatStatus.RESERVED,
                            not_(Seat.id.in_(select(Ticket.seat_id))),
                        )
                    )
                    orphaned_result = await session.execute(orphaned_query)
                    orphaned_seats = orphaned_result.scalars().all()

                    for seat in orphaned_seats:
                        seat.status = SeatStatus.AVAILABLE
                        seat.held_by_session_id = None
                        seat.held_until = None
                        seat.version += 1
                        events_map.setdefault(seat.event_id, []).append(seat.id)

                    total_cleaned = len(expired_seats) + len(orphaned_seats)
                    if total_cleaned > 0:
                        await session.commit()
                        logger.info(
                            f"Sweep reconciled: {len(expired_seats)} expired holds, "
                            f"{len(orphaned_seats)} orphaned reserved seats."
                        )

                        event_bus = get_event_bus()
                        for event_id, seat_ids in events_map.items():
                            await redis_service.force_release_seat_locks(event_id, seat_ids)
                            await redis_service.invalidate_seat_map(event_id)
                            await event_bus.publish(
                                DomainEvent(
                                    event_type=EventType.SEAT_RELEASED,
                                    event_model_id=event_id,
                                    payload={
                                        "seat_ids": seat_ids,
                                        "reason": "hold_expired_or_reservation_removed",
                                    },
                                )
                            )
            except Exception as e:
                logger.error(f"Error in ExpiredHoldCleanupWorker sweep: {e}", exc_info=True)

            await asyncio.sleep(self.interval)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._sweep())
            logger.info("ExpiredHoldCleanupWorker started.")

    async def stop(self):
        if self.is_running:
            self.is_running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            logger.info("ExpiredHoldCleanupWorker stopped.")

cleanup_worker = ExpiredHoldCleanupWorker()
