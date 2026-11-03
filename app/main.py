
import time
import logging
import sys
import json

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.database import init_db, engine
from app.middleware import api_key_middleware
from app.routers import inventory


class JsonFormatter(logging.Formatter):
    """Format application logs as valid JSON."""

    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        return json.dumps(log_entry)


logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
)

for handler in logging.getLogger().handlers:
    handler.setFormatter(JsonFormatter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    logging.info(
        "Application started and database initialized."
    )

    yield

    await engine.dispose()

    logging.info("Database engine disposed.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_process_time_header(
    request: Request,
    call_next,
):
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time_ms = int(
        (time.perf_counter() - start_time) * 1000
    )

    response.headers["X-Response-Time-Ms"] = str(
        process_time_ms
    )

    return response


app.middleware("http")(api_key_middleware)


app.include_router(
    inventory.router,
    prefix="/api/v1",
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Api-Key",
        }
    }

    for path, methods in openapi_schema["paths"].items():
        if path != "/health":
            for method, operation in methods.items():
                operation["security"] = [
                    {"ApiKeyAuth": []}
                ]

    app.openapi_schema = openapi_schema

    return app.openapi_schema


app.openapi = custom_openapi
