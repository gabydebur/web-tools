"""/fetch_url endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas import FetchRequest, FetchResponse
from app.services.extractor import extract_title
from app.services.http_client import fetch
from app.utils.logging import get_logger
from app.utils.url_validation import validate_url

logger = get_logger(__name__)
router = APIRouter(tags=["tools"])


@router.post("/fetch_url", response_model=FetchResponse)
async def fetch_url(
    payload: FetchRequest,
    settings: Settings = Depends(get_settings),
) -> FetchResponse:
    url = validate_url(str(payload.url), allowed_schemes=settings.allowed_schemes)

    logger.info("fetch_url.request", extra={"url": url})

    response = await fetch(url, max_bytes=settings.max_html_bytes)

    try:
        html = response.text
    except Exception:
        html = response.content.decode("utf-8", errors="replace")

    if len(html) > settings.max_html_chars:
        html = html[: settings.max_html_chars]

    content_type = response.headers.get("Content-Type", "").split(";")[0].strip()

    title = ""
    if "html" in (content_type or "").lower():
        title = extract_title(html)

    return FetchResponse(
        url=payload.url,
        final_url=str(response.url),
        status_code=response.status_code,
        content_type=content_type,
        title=title,
        html=html,
    )
