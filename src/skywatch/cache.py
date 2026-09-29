"""In-memory TTL cache used to avoid re-hitting OpenSky for repeated queries."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

DEFAULT_TTL = 60.0  # seconds


class TTLCache:
    """Async TTL cache with per-key locking to coalesce concurrent misses."""

    def __init__(self, ttl: float = DEFAULT_TTL) -> None:
        self.ttl = ttl
        self._store: dict[Any, tuple[float, Any]] = {}
        self._locks: dict[Any, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def _get_lock(self, key: Any) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    async def get_or_set(
        self, key: Any, producer: Callable[[], Awaitable[Any]]
    ) -> Any:
        now = time.time()
        entry = self._store.get(key)
        if entry and now - entry[0] < self.ttl:
            return entry[1]

        async with self._global_lock:
            lock = self._get_lock(key)

        async with lock:
            entry = self._store.get(key)
            now = time.time()
            if entry and now - entry[0] < self.ttl:
                return entry[1]
            value = await producer()
            self._store[key] = (time.time(), value)
            return value

    def clear(self) -> None:
        self._store.clear()
