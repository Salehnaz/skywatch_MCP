import asyncio

import pytest

from skywatch.cache import TTLCache


@pytest.mark.asyncio
async def test_cache_returns_cached_value_within_ttl():
    cache = TTLCache(ttl=60)
    calls = 0

    async def producer():
        nonlocal calls
        calls += 1
        return "value"

    v1 = await cache.get_or_set("k", producer)
    v2 = await cache.get_or_set("k", producer)
    assert v1 == v2 == "value"
    assert calls == 1


@pytest.mark.asyncio
async def test_cache_refetches_after_ttl():
    cache = TTLCache(ttl=0.05)
    calls = 0

    async def producer():
        nonlocal calls
        calls += 1
        return calls

    await cache.get_or_set("k", producer)
    await asyncio.sleep(0.1)
    v2 = await cache.get_or_set("k", producer)
    assert v2 == 2


@pytest.mark.asyncio
async def test_concurrent_misses_coalesce():
    cache = TTLCache(ttl=60)
    calls = 0

    async def slow_producer():
        nonlocal calls
        await asyncio.sleep(0.05)
        calls += 1
        return calls

    results = await asyncio.gather(*[cache.get_or_set("k", slow_producer) for _ in range(10)])
    assert all(r == 1 for r in results)
    assert calls == 1
