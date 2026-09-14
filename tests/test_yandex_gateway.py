import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.errors import UpstreamError
from app.modules.wordstat.infrastructure.yandex_gateway import YandexWordstatGateway


def make_settings() -> Settings:
    return Settings(
        YANDEX_API_KEY=SecretStr("yandex-secret"),
        YANDEX_FOLDER_ID="folder-id",
        PROXY_API_KEY=SecretStr("p" * 32),
    )


@pytest.mark.asyncio
async def test_gateway_uses_official_contract_and_normalizes_counts() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Api-Key yandex-secret"
        assert request.url.path == "/v2/wordstat/topRequests"
        assert request.content == (
            b'{"phrase":"test","numPhrases":50,"folderId":"folder-id"}'
        )
        return httpx.Response(
            200,
            json={
                "totalCount": "12",
                "results": [{"phrase": "test one", "count": "12"}],
                "associations": [],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await YandexWordstatGateway(client, make_settings()).get_top("test")

    assert result.total_count == 12
    assert result.results[0].count == 12


@pytest.mark.asyncio
async def test_gateway_does_not_expose_upstream_error_body() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="secret diagnostic")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(UpstreamError) as raised:
            await YandexWordstatGateway(client, make_settings()).get_top("test")

    assert raised.value.status_code == 502
    assert "secret diagnostic" not in raised.value.message

