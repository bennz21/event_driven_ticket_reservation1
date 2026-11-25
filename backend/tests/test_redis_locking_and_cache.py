import datetime
import time
import unittest
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.events import create_event, get_event, list_events
from app.core.database import Base
from app.core.redis import _ACQUIRE_LOCK_LUA, _RELEASE_LOCK_LUA, redis_service
from app.models import Event, Seat, SeatStatus
from app.schemas import EventCreate
from app.services.reservation_service import ReservationService
from app.services.seat_service import SeatService


class FakeAsyncRedis:
    """Minimal in-memory async Redis test double supporting Lua lock scripts, TTL, and basic KV ops."""

    def __init__(self) -> None:
        self._store: Dict[str, Tuple[str, Optional[float]]] = {}
        self.get_calls: int = 0
        self.set_calls: int = 0

    def _purge_if_expired(self, key: str) -> None:
        entry = self._store.get(key)
        if entry is not None and entry[1] is not None and time.monotonic() >= entry[1]:
            del self._store[key]

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None

    async def get(self, key: str) -> Optional[str]:
        self.get_calls += 1
        self._purge_if_expired(key)
        entry = self._store.get(key)
        return entry[0] if entry is not None else None

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self.set_calls += 1
        expires_at = (time.monotonic() + ex) if ex is not None else None
        self._store[key] = (value, expires_at)
        return True

    async def mget(self, *keys: str) -> List[Optional[str]]:
        results = []
        for k in keys:
            self._purge_if_expired(k)
            entry = self._store.get(k)
            results.append(entry[0] if entry is not None else None)
        return results

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                deleted += 1
        return deleted

    async def eval(self, script: str, numkeys: int, *keys_and_args: Any) -> int:
        keys = keys_and_args[:numkeys]
        args = keys_and_args[numkeys:]
        key = keys[0]
        self._purge_if_expired(key)

        if script == _ACQUIRE_LOCK_LUA:
            session_id = str(args[0])
            ttl = int(args[1])
            current = self._store.get(key)
            if current is None:
                await self.set(key, session_id, ex=ttl)
                return 1
            if current[0] == session_id:
                await self.set(key, session_id, ex=ttl)
                return 2
            return 0

        if script == _RELEASE_LOCK_LUA:
            session_id = str(args[0])
            current = self._store.get(key)
            if current is not None and current[0] == session_id:
                del self._store[key]
                return 1
            return 0

        raise NotImplementedError("Unsupported Lua script in FakeAsyncRedis")

    def expire_now(self, key: str) -> None:
        if key in self._store:
            val, _ = self._store[key]
            self._store[key] = (val, time.monotonic() - 1)


class RedisLockingAndCachingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self.fake_redis = FakeAsyncRedis()
        redis_service.set_client(self.fake_redis)

        async with self.session_factory() as db:
            event = Event(
                id=1,
                title="Test Concert",
                description="Live test",
                venue_name="Test Arena",
                event_date=datetime.datetime.utcnow() + datetime.timedelta(days=7),
                total_rows=1,
                seats_per_row=3,
                base_price=50.0,
            )
            db.add(event)
            await db.flush()
            db.add_all(
                [
                    Seat(id=1, event_id=1, row="A", seat_number=1, tier="VIP", price=90.0),
                    Seat(id=2, event_id=1, row="A", seat_number=2, tier="VIP", price=90.0),
                    Seat(
                        id=3,
                        event_id=1,
                        row="A",
                        seat_number=3,
                        tier="VIP",
                        price=90.0,
                        status=SeatStatus.RESERVED,
                    ),
                ]
            )
            await db.commit()

    async def asyncTearDown(self) -> None:
        redis_service.set_client(None)
        await self.engine.dispose()

    async def test_distributed_lock_ownership_refresh_and_expiry(self) -> None:
        acq = await redis_service.acquire_seat_locks(1, [1], "sess_a", 60)
        self.assertEqual(acq, ([1], [], []))

        blocked = await redis_service.acquire_seat_locks(1, [1], "sess_b", 60)
        self.assertEqual(blocked, ([], [], [1]))

        # Refreshing existing lock + acquiring new seat
        refreshed = await redis_service.acquire_seat_locks(1, [1, 2], "sess_a", 60)
        self.assertEqual(refreshed, ([2], [1], []))

        # Session B cannot release Session A's lock
        await redis_service.release_seat_locks(1, [1], "sess_b")
        still_blocked = await redis_service.acquire_seat_locks(1, [1], "sess_b", 60)
        self.assertEqual(still_blocked, ([], [], [1]))

        # Expiry allows Session B to acquire
        self.fake_redis.expire_now(redis_service.seat_lock_key(1, 1))
        now_acquired = await redis_service.acquire_seat_locks(1, [1], "sess_b", 60)
        self.assertEqual(now_acquired, ([1], [], []))

    async def test_seat_hold_blocks_other_session_and_rolls_back_reserved_locks(self) -> None:
        async with self.session_factory() as db:
            svc = SeatService(db)
            held, failed, _ = await svc.hold_seats(1, [1], "sess_a")
            self.assertEqual(held, [1])
            self.assertEqual(failed, [])

            # Session B is blocked by Redis lock on seat 1, and seat 3 is RESERVED in DB
            held_b, failed_b, _ = await svc.hold_seats(1, [1, 3], "sess_b")
            self.assertEqual(held_b, [])
            self.assertEqual(sorted(failed_b), [1, 3])
            # Failed seat 3 must not remain locked in Redis
            self.assertIsNone(await self.fake_redis.get(redis_service.seat_lock_key(1, 3)))

            # Session A refreshes seat 1 while attempting reserved seat 3:
            # seat 1 lock must stay owned by sess_a
            held_a2, failed_a2, _ = await svc.hold_seats(1, [1, 3], "sess_a")
            self.assertEqual(held_a2, [1])
            self.assertEqual(failed_a2, [3])
            self.assertEqual(await self.fake_redis.get(redis_service.seat_lock_key(1, 1)), "sess_a")

    async def test_seat_map_caching_invalidation_and_expired_hold_reconciliation(self) -> None:
        async with self.session_factory() as db:
            svc = SeatService(db)

            # First read populates cache
            seats_first = await svc.get_seats_for_event(1)
            self.assertEqual(len(seats_first), 3)
            self.assertIsNotNone(await self.fake_redis.get(redis_service.seat_map_key(1)))

            # Second read hits cache
            prev_sets = self.fake_redis.set_calls
            seats_second = await svc.get_seats_for_event(1)
            self.assertEqual(len(seats_second), 3)
            self.assertEqual(self.fake_redis.set_calls, prev_sets)

            # Holding invalidates seat map cache
            await svc.hold_seats(1, [1], "sess_a")
            self.assertIsNone(await self.fake_redis.get(redis_service.seat_map_key(1)))

            # Populate cache with a held seat, then backdate held_until in DB & cache to simulate expiry
            seats_held = await svc.get_seats_for_event(1)
            self.assertEqual(seats_held[0].status, SeatStatus.HELD)

            past = datetime.datetime.utcnow() - datetime.timedelta(seconds=10)
            seat1 = await db.get(Seat, 1)
            seat1.held_until = past
            await db.commit()

            cached_raw = await redis_service.get_cached_seat_map(1)
            cached_raw[0]["held_until"] = past.isoformat()
            await redis_service.set_cached_seat_map(1, cached_raw)

            # Reading now must detect the expired cached hold, reconcile DB, and clear Redis lock
            reconciled = await svc.get_seats_for_event(1)
            self.assertEqual(reconciled[0].status, SeatStatus.AVAILABLE)
            self.assertIsNone(await self.fake_redis.get(redis_service.seat_lock_key(1, 1)))

    async def test_reservation_confirmation_releases_hold_lock_and_invalidates_cache(self) -> None:
        async with self.session_factory() as db:
            seat_svc = SeatService(db)
            res_svc = ReservationService(db)

            await seat_svc.hold_seats(1, [1, 2], "sess_a")
            await seat_svc.get_seats_for_event(1)
            self.assertIsNotNone(await self.fake_redis.get(redis_service.seat_map_key(1)))

            reservation = await res_svc.create_reservation(
                event_id=1,
                seat_ids=[1, 2],
                session_id="sess_a",
                customer_name="Alice",
                customer_email="alice@example.com",
            )
            self.assertEqual(len(reservation.tickets), 2)
            self.assertIsNone(await self.fake_redis.get(redis_service.seat_lock_key(1, 1)))
            self.assertIsNone(await self.fake_redis.get(redis_service.seat_lock_key(1, 2)))
            self.assertIsNone(await self.fake_redis.get(redis_service.seat_map_key(1)))

    async def test_events_cache_and_invalidation(self) -> None:
        async with self.session_factory() as db:
            events_1 = await list_events(db)
            self.assertEqual(len(events_1), 1)
            self.assertIsNotNone(await redis_service.get_cached_events())

            ev_1 = await get_event(1, db)
            self.assertEqual(ev_1.title, "Test Concert")
            self.assertIsNotNone(await redis_service.get_cached_event(1))

            await create_event(
                EventCreate(
                    title="Second Show",
                    description="Encore",
                    venue_name="Arena 2",
                    event_date=datetime.datetime.utcnow() + datetime.timedelta(days=10),
                ),
                db,
            )
            self.assertIsNone(await redis_service.get_cached_events())

    async def test_graceful_fallback_when_redis_unavailable(self) -> None:
        redis_service.set_client(None)
        async with self.session_factory() as db:
            seat_svc = SeatService(db)
            held, failed, _ = await seat_svc.hold_seats(1, [1], "sess_a")
            self.assertEqual(held, [1])
            self.assertEqual(failed, [])

            released = await seat_svc.release_seats(1, [1], "sess_a")
            self.assertEqual(released, [1])


if __name__ == "__main__":
    unittest.main()
