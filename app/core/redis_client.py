import json
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

_redis_pool: aioredis.Redis | None = None


async def get_redis_pool() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def close_redis_pool() -> None:
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    pool = await get_redis_pool()
    yield pool


# --- Token blacklist ---

async def blacklist_token(redis: aioredis.Redis, jti: str, ttl_seconds: int) -> None:
    await redis.setex(f"blacklist:{jti}", ttl_seconds, "1")


async def is_token_blacklisted(redis: aioredis.Redis, jti: str) -> bool:
    return await redis.exists(f"blacklist:{jti}") == 1


# --- Generic cache helpers ---

async def cache_set(redis: aioredis.Redis, key: str, value: Any, ttl: int = 60) -> None:
    await redis.setex(key, ttl, json.dumps(value, default=str))


async def cache_get(redis: aioredis.Redis, key: str) -> Any | None:
    raw = await redis.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def cache_delete(redis: aioredis.Redis, key: str) -> None:
    await redis.delete(key)


async def cache_invalidate_pattern(redis: aioredis.Redis, pattern: str) -> None:
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)
