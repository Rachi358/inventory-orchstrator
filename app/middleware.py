
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import settings


PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


async def api_key_middleware(request: Request, call_next):
    """Validate API keys for private application endpoints."""

    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    configured_key = settings.API_KEY_SECRET
    provided_key = request.headers.get("X-Api-Key")

    if not configured_key or not provided_key:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"},
        )

    if not secrets.compare_digest(provided_key, configured_key):
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"},
        )

    return await call_next(request)
