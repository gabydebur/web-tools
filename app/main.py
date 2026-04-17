"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import __version__
from app.config import get_settings
from app.routes import extract, fetch, health, search
from app.schemas import ErrorResponse
from app.services.http_client import shutdown_http_client, startup_http_client
from app.utils.errors import WebToolsError
from app.utils.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("app.lifespan")
    logger.info(
        "app.startup",
        extra={"version": __version__, "searxng": str(settings.searxng_base_url)},
    )
    await startup_http_client()
    try:
        yield
    finally:
        await shutdown_http_client()
        logger.info("app.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="web-tools",
        version=__version__,
        description="Minimal HTTP tooling service for local LLMs.",
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(search.router)
    app.include_router(fetch.router)
    app.include_router(extract.router)

    logger = get_logger("app.http")

    @app.exception_handler(WebToolsError)
    async def handle_domain_error(_: Request, exc: WebToolsError) -> JSONResponse:
        logger.warning(
            "request.domain_error",
            extra={"code": exc.code, "message": exc.message, "detail": exc.detail},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(error=exc.code, detail=exc.message).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Return the structured error list directly (not str()-stringified)
        # so clients can parse field-level issues.
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "detail": jsonable_encoder(exc.errors()),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("request.unhandled_exception")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="internal_error",
                detail="An unexpected error occurred.",
            ).model_dump(),
        )

    return app


app = create_app()
