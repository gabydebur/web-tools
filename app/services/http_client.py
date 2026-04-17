"""Shared async HTTP client and fetch helper."""
from __future__ import annotations

from typing import Optional

import httpx

from app.config import Settings, get_settings
from app.utils.errors import PayloadTooLargeError, UpstreamError
from app.utils.logging import get_logger

logger = get_logger(__name__)


_client: Optional[httpx.AsyncClient] = None


def _build_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.http_timeout_seconds),
        follow_redirects=True,
        max_redirects=settings.http_max_redirects,
        headers={
            "User-Agent": settings.http_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr,en;q=0.8",
        },
    )


async def startup_http_client() -> None:
    global _client
    if _client is None:
        _client = _build_client(get_settings())
        logger.info("http_client.started")


async def shutdown_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("http_client.stopped")


def get_http_client() -> httpx.AsyncClient:
    """Return the lazily-initialized shared client.

    Using a module-level singleton keeps things simple while still honoring
    FastAPI lifespan events for clean shutdown.
    """
    global _client
    if _client is None:
        _client = _build_client(get_settings())
    return _client


async def fetch(url: str, *, max_bytes: int) -> httpx.Response:
    """Perform a GET request with size guard.

    Raises:
        UpstreamError: on network / HTTP / timeout failure.
        PayloadTooLargeError: if the body exceeds `max_bytes`.
    """
    client = get_http_client()

    try:
        async with client.stream("GET", url) as response:
            # Pre-check Content-Length when available
            cl = response.headers.get("Content-Length")
            if cl is not None:
                try:
                    if int(cl) > max_bytes:
                        raise PayloadTooLargeError(
                            "Response exceeds maximum size",
                            detail=f"content-length={cl} max={max_bytes}",
                        )
                except ValueError:
                    pass  # malformed header, rely on streaming guard

            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise PayloadTooLargeError(
                        "Response exceeds maximum size",
                        detail=f"read={total} max={max_bytes}",
                    )
                chunks.append(chunk)

            # Attach the buffered content so callers can access `.content`/`.text`
            response._content = b"".join(chunks)  # type: ignore[attr-defined]
            return response

    except PayloadTooLargeError:
        raise
    except httpx.TimeoutException as exc:
        logger.warning("http_client.timeout", extra={"url": url})
        raise UpstreamError("Upstream request timed out", detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        logger.warning("http_client.http_error", extra={"url": url, "err": str(exc)})
        raise UpstreamError("Upstream request failed", detail=str(exc)) from exc
