"""SearxNG search backend client."""
from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.schemas import SearchResultItem
from app.utils.errors import SearchBackendError
from app.utils.logging import get_logger
from app.services.http_client import get_http_client

logger = get_logger(__name__)


async def search(query: str, limit: int, settings: Settings) -> list[SearchResultItem]:
    """Run a query against SearxNG and return normalized results.

    SearxNG must expose the JSON format (enabled in settings.yml).
    """
    base_url = str(settings.searxng_base_url).rstrip("/")
    endpoint = f"{base_url}/search"

    params = {
        "q": query,
        "format": "json",
        "language": settings.searxng_language,
        "safesearch": settings.searxng_safesearch,
    }

    client = get_http_client()

    try:
        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    except httpx.TimeoutException as exc:
        logger.warning("searxng.timeout", extra={"query": query})
        raise SearchBackendError("SearxNG timed out", detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "searxng.bad_status",
            extra={"query": query, "status": exc.response.status_code},
        )
        raise SearchBackendError(
            "SearxNG returned a bad status",
            detail=f"status={exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("searxng.http_error", extra={"query": query, "err": str(exc)})
        raise SearchBackendError("SearxNG request failed", detail=str(exc)) from exc
    except ValueError as exc:
        raise SearchBackendError("SearxNG returned invalid JSON", detail=str(exc)) from exc

    raw_results = payload.get("results", [])
    if not isinstance(raw_results, list):
        raise SearchBackendError("SearxNG payload missing 'results' array")

    items: list[SearchResultItem] = []
    for entry in raw_results:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        title = entry.get("title")
        if not url or not title:
            continue
        try:
            items.append(
                SearchResultItem(
                    title=str(title),
                    url=url,
                    snippet=str(entry.get("content") or ""),
                    source=entry.get("engine") or None,
                )
            )
        except Exception:
            # Ignore individual entries that fail URL validation
            continue
        if len(items) >= limit:
            break

    logger.info(
        "searxng.search.ok",
        extra={"query": query, "count": len(items), "limit": limit},
    )
    return items
