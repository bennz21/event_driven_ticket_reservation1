import asyncio
import json
import logging
import time
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("event_bus")

# Domain Event Types
class EventType:
    SEAT_HOLD_REQUESTED = "seat.hold.requested"
    SEAT_HELD = "seat.held"
    SEAT_RELEASED = "seat.released"
    RESERVATION_INITIATED = "reservation.initiated"
    RESERVATION_CONFIRMED = "reservation.confirmed"
    RESERVATION_EXPIRED = "reservation.expired"
    SEAT_MAP_SYNC = "seat_map.sync"

class DomainEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    event_model_id: int  # The concert/event ID this domain event pertains to
    payload: Dict[str, Any]
    timestamp: float = Field(default_factory=time.time)

EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]

class BaseEventBus:
    async def publish(self, event: DomainEvent) -> None:
        raise NotImplementedError

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        raise NotImplementedError

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

class InMemoryEventBus(BaseEventBus):
    """
    In-memory async event bus using asyncio queues.
    Zero external dependencies needed, suitable for development and single-instance deployments.
    """
    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._queue: asyncio.Queue[DomainEvent] = asyncio.Queue()
        self._running: bool = False
        self._worker_task: Optional[asyncio.Task] = None

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"Subscribed handler {handler.__name__} to event: {event_type}")

    async def publish(self, event: DomainEvent) -> None:
        await self._queue.put(event)

    async def _worker(self) -> None:
        while self._running:
            try:
                event = await self._queue.get()
                handlers = self._handlers.get(event.event_type, [])
                # Also support wildcard '*' subscribers
                handlers = handlers + self._handlers.get("*", [])
                
                if handlers:
                    await asyncio.gather(
                        *(handler(event) for handler in handlers),
                        return_exceptions=True
                    )
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error dispatching event: {e}", exc_info=True)

    async def start(self) -> None:
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("InMemoryEventBus started.")

    async def stop(self) -> None:
        if self._running:
            self._running = False
            if self._worker_task:
                self._worker_task.cancel()
                try:
                    await self._worker_task
                except asyncio.CancelledError:
                    pass
            logger.info("InMemoryEventBus stopped.")

class RedisEventBus(BaseEventBus):
    """
    Distributed Redis Pub/Sub Event Bus for multi-instance scaling.
    """
    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._running: bool = False
        self._client: Optional[Any] = None
        self._pubsub: Optional[Any] = None
        self._listener_task: Optional[asyncio.Task] = None

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        if self._client:
            channel = f"events:{event.event_type}"
            await self._client.publish(channel, event.model_dump_json())

    async def _listener(self) -> None:
        try:
            while self._running and self._pubsub:
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("data"):
                    data = json.loads(message["data"])
                    event = DomainEvent(**data)
                    handlers = self._handlers.get(event.event_type, []) + self._handlers.get("*", [])
                    if handlers:
                        await asyncio.gather(*(h(event) for h in handlers), return_exceptions=True)
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error: {e}", exc_info=True)

    async def start(self) -> None:
        import redis.asyncio as aioredis
        self._client = aioredis.from_url(self.redis_url, decode_responses=True)
        self._pubsub = self._client.pubsub()
        await self._pubsub.psubscribe("events:*")
        self._running = True
        self._listener_task = asyncio.create_task(self._listener())
        logger.info(f"RedisEventBus connected to {self.redis_url} and started.")

    async def stop(self) -> None:
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.punsubscribe("events:*")
            if hasattr(self._pubsub, "aclose"):
                await self._pubsub.aclose()
            else:
                await self._pubsub.close()
        if self._client:
            if hasattr(self._client, "aclose"):
                await self._client.aclose()
            else:
                await self._client.close()
        logger.info("RedisEventBus stopped.")

# Factory function to get the configured event bus
_event_bus_instance: Optional[BaseEventBus] = None

def get_event_bus() -> BaseEventBus:
    global _event_bus_instance
    if _event_bus_instance is None:
        from app.core.config import settings
        if settings.USE_REDIS_EVENT_BUS:
            _event_bus_instance = RedisEventBus(settings.REDIS_URL)
        else:
            _event_bus_instance = InMemoryEventBus()
    return _event_bus_instance
