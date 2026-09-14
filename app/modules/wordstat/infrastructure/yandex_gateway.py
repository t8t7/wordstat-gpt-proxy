import logging

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.core.errors import UpstreamError
from app.modules.wordstat.domain.entities import PhraseStat, WordstatTop


class YandexPhraseInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    phrase: str
    count: int = Field(ge=0)


class YandexTopResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    totalCount: int = Field(ge=0)
    results: list[YandexPhraseInfo] = Field(default_factory=list)
    associations: list[YandexPhraseInfo] = Field(default_factory=list)


class YandexWordstatGateway:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http_client = http_client
        self._settings = settings
        self._logger = logging.getLogger("wordstat.yandex")

    async def get_top(self, phrase: str) -> WordstatTop:
        try:
            response = await self._http_client.post(
                str(self._settings.YANDEX_WORDSTAT_URL),
                headers={
                    "Authorization": (
                        f"Api-Key {self._settings.YANDEX_API_KEY.get_secret_value()}"
                    ),
                    "Content-Type": "application/json",
                },
                json={
                    "phrase": phrase,
                    "numPhrases": self._settings.WORDSTAT_NUM_PHRASES,
                    "folderId": self._settings.YANDEX_FOLDER_ID,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            status_code = self._map_upstream_status(error.response.status_code)
            self._logger.warning(
                "Yandex Wordstat returned status=%s", error.response.status_code
            )
            raise UpstreamError(status_code, "yandex_api_error", "Yandex API request failed") from error
        except httpx.RequestError as error:
            self._logger.warning("Yandex Wordstat connection failed: %s", type(error).__name__)
            raise UpstreamError(502, "yandex_unavailable", "Yandex API is unavailable") from error

        try:
            payload = YandexTopResponse.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            self._logger.error("Yandex Wordstat returned an invalid response")
            raise UpstreamError(502, "invalid_yandex_response", "Invalid response from Yandex API") from error

        return WordstatTop(
            query=phrase,
            total_count=payload.totalCount,
            results=tuple(PhraseStat(item.phrase, item.count) for item in payload.results),
            associations=tuple(
                PhraseStat(item.phrase, item.count) for item in payload.associations
            ),
        )

    @staticmethod
    def _map_upstream_status(status_code: int) -> int:
        if status_code == 429:
            return 429
        if status_code == 503:
            return 503
        return 502

