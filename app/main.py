from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, request_logging_middleware
from app.modules.wordstat.application.use_cases import GetWordstatTop
from app.modules.wordstat.infrastructure.yandex_gateway import YandexWordstatGateway
from app.modules.wordstat.presentation.router import router as wordstat_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    http_client = httpx.AsyncClient(timeout=settings.YANDEX_TIMEOUT_SECONDS)
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.redis = redis
    app.state.get_wordstat_top = GetWordstatTop(
        YandexWordstatGateway(http_client, settings)
    )
    try:
        yield
    finally:
        await http_client.aclose()
        await redis.aclose()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Wordstat Proxy API",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.middleware("http")(request_logging_middleware)
    application.include_router(wordstat_router)

    @application.exception_handler(AppError)
    async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if error.status_code == 401 else None
        return JSONResponse(
            status_code=error.status_code,
            content={"success": False, "error": {"code": error.code, "message": error.message}},
            headers=headers,
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {"code": "validation_error", "message": "Invalid request parameters"},
            },
        )

    @application.get("/health", tags=["health"])
    async def health(request: Request) -> JSONResponse:
        try:
            await request.app.state.redis.ping()
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unhealthy"})
        return JSONResponse(content={"status": "ok"})

    return application


app = create_app()

