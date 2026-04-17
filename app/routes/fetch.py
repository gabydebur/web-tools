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


def _is_html(content_type: str) -> bool:
    ct = (content_type or "").lower()
    return "html" in ct or "xml" in ct


@router.post("/fetch_url", response_model=FetchResponse)
async def fetch_url(
    payload: FetchRequest,
    settings: Settings = Depends(get_settings),
) -> FetchResponse:
    url = validate_url(str(payload.url), allowed_schemes=settings.allowed_schemes)

    logger.info("fetch_url.request", extra={"url": url})

    result = await fetch(url, max_bytes=settings.max_html_bytes)

    # Extract the title BEFORE truncation so cut HTML can't hide <title>.
    title = extract_title(result.text) if _is_html(result.content_type) else ""

    html = result.text
    if len(html) > settings.max_html_chars:
        html = html[: settings.max_html_chars]

    return FetchResponse(
        url=payload.url,
        final_url=result.final_url,
        status_code=result.status_code,
        content_type=result.content_type,
        title=title,
        html=html,
    )
