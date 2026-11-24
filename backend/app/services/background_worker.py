import asyncio
import datetime
import logging
from sqlalchemy import select, and_
from app.core.database import AsyncSessionLocal
from app.models import Seat, SeatStatus
from app.core.events import get_event_bus, DomainEvent, EventType

logger = logging.getLogger("background_worker")

class ExpiredHoldCleanupWorker:
    """
    Background worker that runs periodically to release seats whose hold TTL has expired.
    Emits SEAT_RELEASED domain events so WebSockets instantly reflect available seats.
    """
    def __init__(self, interval_seconds: int = 5):
        self.interval = interval_seconds
        self.is_running = False
        self._task = None

    async def _sweep(self):
        while self.is_running:
            try:
                now = datetime.datetime.utcnow()
                async with AsyncSessionLocal() as session:
                    # Find held seats that have expired
                    query = select(Seat).where(
                        and_(
                            Seat.status == SeatStatus.HELD,
                            Seat.held_until.isnot(None),
                            Seat.held_until < now,
                        )
                    )
                    result = await session.execute(query)
                    expired_seats = result.scalars().all()

                    if expired_seats:
                        # Group by event_id to publish domain events per event
                        events_map = {}
                        for seat in expired_seats:
                            seat.status = SeatStatus.AVAILABLE
                            seat.held_by_session_id = None
                            seat.held_until = None
                            seat.version += 1
                            events_map.setdefault(seat.event_id, []).append(seat.id)

                        await session.commit()
                        logger.info(f"Cleaned up {len(expired_seats)} expired seat holds.")

                        event_bus = get_event_bus()
                        for event_id, seat_ids in events_map.items():
                            await event_bus.publish(
                                DomainEvent(
                                    event_type=EventType.SEAT_RELEASED,
                                    event_model_id=event_id,
                                    payload={
                                        "seat_ids": seat_ids,
                                        "reason": "hold_timeout_expired",
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
