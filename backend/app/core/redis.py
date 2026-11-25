import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger("redis_service")

# Atomic Lua script: acquire lock if free (returns 1) or refresh if already owned by session (returns 2).
# Returns 0 if held by a different session.
_ACQUIRE_LOCK_LUA = """
local current = redis.call("GET", KEYS[1])
if not current then
    redis.call("SET", KEYS[1], ARGV[1], "EX", tonumber(ARGV[2]))
    return 1
elseif current == ARGV[1] then
    redis.call("SET", KEYS[1], ARGV[1], "EX", tonumber(ARGV[2]))
    return 2
end
return 0
"""

# Atomic Lua script: release lock only if owned by the requesting session.
_RELEASE_LOCK_LUA = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
end
return 0
"""


class RedisService:
    """
    Manages the shared async Redis connection pool, distributed seat hold locks,
    and JSON response caching with graceful fallback when Redis is unavailable.
    """

    def __init__(self) -> None:
        self._client: Optional[Any] = None
        self._available: bool = False

    @property
    def is_available(self) -> bool:
        return self._client is not None and self._available

    @property
    def locking_enabled(self) -> bool:
        return settings.USE_REDIS_SEAT_LOCKING and self.is_available

    @property
    def caching_enabled(self) -> bool:
        return settings.USE_REDIS_CACHE and self.is_available

    def set_client(self, client: Optional[Any]) -> None:
        """Inject a Redis-compatible async client (primarily for testing)."""
        self._client = client
        self._available = client is not None

    async def connect(self) -> bool:
        """Initialize Redis connection pool if locking or caching is enabled."""
        if not (settings.USE_REDIS_SEAT_LOCKING or settings.USE_REDIS_CACHE):
            logger.info("Redis locking and caching are disabled in configuration.")
            self._available = False
            return False

        client = None
        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
            )
            await client.ping()
            self._client = client
            self._available = True
            logger.info(f"RedisService connected to {settings.REDIS_URL}.")
            return True
        except (RedisError, OSError) as exc:
            logger.warning(
                f"Redis unavailable at {settings.REDIS_URL} ({exc}); "
                "falling back to MySQL-only locking and uncached reads."
            )
            if client is not None:
                await self._safe_close_client(client)
            self._client = None
            self._available = False
            return False

    async def disconnect(self) -> None:
        """Close the shared Redis client."""
        if self._client is not None:
            await self._safe_close_client(self._client)
            self._client = None
            self._available = False
            logger.info("RedisService disconnected.")

    @staticmethod
    async def _safe_close_client(client: Any) -> None:
        try:
            if hasattr(client, "aclose"):
                await client.aclose()
            else:
                await client.close()
        except Exception:
            pass

    # --- Key Builders ---

    @staticmethod
    def seat_lock_key(event_id: int, seat_id: int) -> str:
        return f"seat_lock:{event_id}:{seat_id}"

    @staticmethod
    def seat_map_key(event_id: int) -> str:
        return f"seat_map:{event_id}"

    @staticmethod
    def events_list_key() -> str:
        return "events:list"

    @staticmethod
    def event_key(event_id: int) -> str:
        return f"event:{event_id}"

    # --- Distributed Seat Locking ---

    async def acquire_seat_locks(
        self,
        event_id: int,
        seat_ids: List[int],
        session_id: str,
        ttl_seconds: int,
    ) -> Optional[Tuple[List[int], List[int], List[int]]]:
        """
        Atomically acquires or refreshes distributed locks for the given seats.
        Returns (newly_acquired_ids, refreshed_ids, blocked_ids), or None if Redis
        locking is disabled/unavailable.
        """
        if not self.locking_enabled or not seat_ids:
            return None

        newly_acquired: List[int] = []
        refreshed: List[int] = []
        blocked: List[int] = []

        try:
            for seat_id in seat_ids:
                key = self.seat_lock_key(event_id, seat_id)
                result = await self._client.eval(
                    _ACQUIRE_LOCK_LUA, 1, key, session_id, str(ttl_seconds)
                )
                if result == 1:
                    newly_acquired.append(seat_id)
                elif result == 2:
                    refreshed.append(seat_id)
                else:
                    blocked.append(seat_id)
            return newly_acquired, refreshed, blocked
        except (RedisError, OSError) as exc:
            logger.warning(f"Redis lock acquisition error; falling back to DB: {exc}")
            if newly_acquired:
                await self.release_seat_locks(event_id, newly_acquired, session_id)
            return None

    async def release_seat_locks(
        self,
        event_id: int,
        seat_ids: List[int],
        session_id: str,
    ) -> None:
        """Releases distributed seat locks only if owned by session_id."""
        if not self.locking_enabled or not seat_ids:
            return

        try:
            for seat_id in seat_ids:
                key = self.seat_lock_key(event_id, seat_id)
                await self._client.eval(_RELEASE_LOCK_LUA, 1, key, session_id)
        except (RedisError, OSError) as exc:
            logger.warning(f"Redis lock release error for event {event_id}: {exc}")

    async def force_release_seat_locks(self, event_id: int, seat_ids: List[int]) -> None:
        """Unconditionally deletes seat lock keys (e.g., on confirmation, expiry sweep, or reset)."""
        if not self.is_available or not seat_ids:
            return

        keys = [self.seat_lock_key(event_id, seat_id) for seat_id in seat_ids]
        await self.delete_keys(*keys)

    async def verify_seat_locks_not_stolen(
        self,
        event_id: int,
        seat_ids: List[int],
        session_id: str,
    ) -> bool:
        """
        Verifies no requested seat is currently locked in Redis by a different session.
        Returns True if safe to proceed (or Redis locking is disabled/unavailable).
        """
        if not self.locking_enabled or not seat_ids:
            return True

        try:
            keys = [self.seat_lock_key(event_id, seat_id) for seat_id in seat_ids]
            owners = await self._client.mget(*keys)
            return all(owner is None or owner == session_id for owner in owners)
        except (RedisError, OSError) as exc:
            logger.warning(f"Redis lock verification error; continuing with DB check: {exc}")
            return True

    # --- Generic JSON Caching ---

    async def get_json(self, key: str) -> Optional[Any]:
        if not self.caching_enabled:
            return None
        try:
            raw = await self._client.get(key)
            return json.loads(raw) if raw is not None else None
        except (RedisError, OSError, json.JSONDecodeError) as exc:
            logger.warning(f"Redis cache read error for '{key}': {exc}")
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        if not self.caching_enabled:
            return
        try:
            await self._client.set(key, json.dumps(value), ex=ttl_seconds)
        except (RedisError, OSError, TypeError) as exc:
            logger.warning(f"Redis cache write error for '{key}': {exc}")

    async def delete_keys(self, *keys: str) -> None:
        if not self.is_available or not keys:
            return
        try:
            await self._client.delete(*keys)
        except (RedisError, OSError) as exc:
            logger.warning(f"Redis delete error for keys {keys}: {exc}")

    # --- Domain Cache Helpers ---

    async def get_cached_seat_map(self, event_id: int) -> Optional[List[Dict[str, Any]]]:
        data = await self.get_json(self.seat_map_key(event_id))
        return data if isinstance(data, list) else None

    async def set_cached_seat_map(self, event_id: int, seats_data: List[Dict[str, Any]]) -> None:
        await self.set_json(
            self.seat_map_key(event_id),
            seats_data,
            settings.SEAT_CACHE_TTL_SECONDS,
        )

    async def invalidate_seat_map(self, event_id: int) -> None:
        await self.delete_keys(self.seat_map_key(event_id))

    async def get_cached_events(self) -> Optional[List[Dict[str, Any]]]:
        data = await self.get_json(self.events_list_key())
        return data if isinstance(data, list) else None

    async def set_cached_events(self, events_data: List[Dict[str, Any]]) -> None:
        await self.set_json(
            self.events_list_key(),
            events_data,
            settings.EVENT_CACHE_TTL_SECONDS,
        )

    async def get_cached_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        data = await self.get_json(self.event_key(event_id))
        return data if isinstance(data, dict) else None

    async def set_cached_event(self, event_id: int, event_data: Dict[str, Any]) -> None:
        await self.set_json(
            self.event_key(event_id),
            event_data,
            settings.EVENT_CACHE_TTL_SECONDS,
        )

    async def invalidate_events_cache(self, event_id: Optional[int] = None) -> None:
        keys = [self.events_list_key()]
        if event_id is not None:
            keys.append(self.event_key(event_id))
        await self.delete_keys(*keys)


redis_service = RedisService()
