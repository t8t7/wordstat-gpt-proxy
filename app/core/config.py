from functools import lru_cache

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    YANDEX_API_KEY: SecretStr
    YANDEX_FOLDER_ID: str = Field(min_length=1, max_length=50)
    PROXY_API_KEY: SecretStr
    REDIS_URL: str = "redis://redis:6379/0"
    RATE_LIMIT_REQUESTS: int = Field(default=60, ge=1, le=10_000)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, ge=1, le=86_400)
    YANDEX_TIMEOUT_SECONDS: float = Field(default=15, gt=0, le=60)
    WORDSTAT_NUM_PHRASES: int = Field(default=50, ge=1, le=2_000)
    LOG_LEVEL: str = "INFO"
    PUBLIC_BASE_URL: HttpUrl | None = None
    YANDEX_WORDSTAT_URL: HttpUrl = HttpUrl(
        "https://searchapi.api.cloud.yandex.net/v2/wordstat/topRequests"
    )

    def validate_secrets(self) -> None:
        if len(self.PROXY_API_KEY.get_secret_value()) < 32:
            raise ValueError("PROXY_API_KEY must contain at least 32 characters")
        if not self.YANDEX_API_KEY.get_secret_value().strip():
            raise ValueError("YANDEX_API_KEY must not be empty")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_secrets()
    return settings
