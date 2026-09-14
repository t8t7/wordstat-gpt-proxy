from typing import cast

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.core.errors import AppError


RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


async def enforce_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    redis = cast(Redis, request.app.state.redis)
    try:
        result = await redis.eval(
            RATE_LIMIT_SCRIPT,
            1,
            "rate-limit:wordstat:top",
            settings.RATE_LIMIT_WINDOW_SECONDS,
        )
    except Exception as error:
        raise AppError(503, "rate_limiter_unavailable", "Service temporarily unavailable") from error

    current_count, ttl = int(result[0]), max(int(result[1]), 1)
    if current_count > settings.RATE_LIMIT_REQUESTS:
        raise AppError(429, "rate_limit_exceeded", f"Retry after {ttl} seconds")

