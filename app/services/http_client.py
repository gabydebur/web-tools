"""Shared async HTTP client and fetch helper."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import Settings, get_settings
from app.utils.errors import PayloadTooLargeError, UpstreamError
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True, frozen=True)
class FetchResult:
    """Lightweight, self-contained result of a GET request.

    Intentionally decoupled from httpx.Response so callers never depend on
    the client's private / lifecycle-bound internals.
    """

    final_url: str
    status_code: int
    content_type: str
    text: str
    content: bytes


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

    Prefer relying on the FastAPI lifespan to own the lifecycle. This fallback
    exists so out-of-app call sites (tests, scripts) still work.
    """
    global _client
    if _client is None:
        _client = _build_client(get_settings())
    return _client


def _decode(content: bytes, encoding: str | None) -> str:
    for enc in (encoding, "utf-8", "latin-1"):
        if not enc:
            continue
        try:
            return content.decode(enc, errors="replace")
        except LookupError:
            continue
    return content.decode("utf-8", errors="replace")


async def fetch(url: str, *, max_bytes: int) -> FetchResult:
    """Perform a GET request with a streaming size guard.

    Raises:
        UpstreamError: on network / HTTP / timeout failure.
        PayloadTooLargeError: if the body exceeds `max_bytes`.
    """
    client = get_http_client()

    try:
        async with client.stream("GET", url) as response:
            # Cheap pre-check when the server announces size
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

            content = b"".join(chunks)
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
            # `response.encoding` is derived from Content-Type charset when present.
            text = _decode(content, response.encoding)

            return FetchResult(
                final_url=str(response.url),
                status_code=response.status_code,
                content_type=content_type,
                text=text,
                content=content,
            )

    except PayloadTooLargeError:
        raise
    except httpx.TimeoutException as exc:
        logger.warning("http_client.timeout", extra={"url": url})
        raise UpstreamError("Upstream request timed out", detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        logger.warning("http_client.http_error", extra={"url": url, "err": str(exc)})
        raise UpstreamError("Upstream request failed", detail=str(exc)) from exc
