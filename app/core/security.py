import secrets

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.errors import AppError


bearer_scheme = HTTPBearer(auto_error=False)


async def require_proxy_authorization(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    expected_key = settings.PROXY_API_KEY.get_secret_value()
    supplied_key = credentials.credentials if credentials else ""
    is_bearer = credentials is not None and credentials.scheme.lower() == "bearer"
    if not is_bearer or not secrets.compare_digest(supplied_key, expected_key):
        raise AppError(401, "unauthorized", "Valid Bearer token required")

