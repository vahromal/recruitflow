"""FastAPI application entry point."""
import logging
import logging.handlers
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers

__all__ = ["app"]


def configure_logging() -> None:
    """Structured single-line JSON-ish logs to stdout, rotation handled by Docker log driver."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
        )
    )
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    root.handlers = [handler]


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logging.getLogger(__name__).info("Starting %s (env=%s)", settings.app_name, settings.environment)
    yield
    logging.getLogger(__name__).info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.environment != "prod" else None,
    openapi_url="/api/openapi.json" if settings.environment != "prod" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix="/api")


@app.get("/health", tags=["system"])
def health() -> dict:
    """Health-check endpoint used by Docker and reverse proxy."""
    return {"status": "ok", "service": settings.app_name, "env": settings.environment}
