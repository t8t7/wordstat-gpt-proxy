from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.core.rate_limit import enforce_rate_limit


class FakeRedis:
    def __init__(self, result: list[int] | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    async def eval(self, *_args: object) -> list[int]:
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def make_settings(limit: int = 2) -> Settings:
    return Settings(
        PROXY_API_KEY="p" * 32,
        RATE_LIMIT_REQUESTS=limit,
    )


@pytest.mark.asyncio
async def test_rate_limit_allows_request_within_limit() -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(redis=FakeRedis([2, 40]))))
    await enforce_rate_limit(request, make_settings())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_rate_limit_rejects_request_over_limit() -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(redis=FakeRedis([3, 40]))))

    with pytest.raises(AppError) as raised:
        await enforce_rate_limit(request, make_settings())  # type: ignore[arg-type]

    assert raised.value.status_code == 429
    assert raised.value.code == "rate_limit_exceeded"


@pytest.mark.asyncio
async def test_rate_limit_fails_closed_when_redis_is_unavailable() -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(redis=FakeRedis(error=ConnectionError())))
    )

    with pytest.raises(AppError) as raised:
        await enforce_rate_limit(request, make_settings())  # type: ignore[arg-type]

    assert raised.value.status_code == 503
    assert raised.value.code == "rate_limiter_unavailable"
