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

    PROXY_API_KEY: SecretStr
    REDIS_URL: str = "redis://redis:6379/0"
    RATE_LIMIT_REQUESTS: int = Field(default=60, ge=1, le=10_000)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, ge=1, le=86_400)
    WORDSTAT_TIMEOUT_SECONDS: float = Field(default=30, gt=0, le=120)
    WORDSTAT_NUM_PHRASES: int = Field(default=50, ge=1, le=2_000)
    LOG_LEVEL: str = "INFO"
    PUBLIC_BASE_URL: HttpUrl | None = None
    WORDSTAT_SITE_URL: HttpUrl = HttpUrl("https://wordstat.yandex.ru/")

    def validate_secrets(self) -> None:
        if len(self.PROXY_API_KEY.get_secret_value()) < 32:
            raise ValueError("PROXY_API_KEY must contain at least 32 characters")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_secrets()
    return settings
