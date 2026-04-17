"""/extract_text endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas import ExtractRequest, ExtractResponse
from app.services.extractor import extract_readable, truncate
from app.services.http_client import fetch
from app.utils.logging import get_logger
from app.utils.url_validation import validate_url

logger = get_logger(__name__)
router = APIRouter(tags=["tools"])


@router.post("/extract_text", response_model=ExtractResponse)
async def extract_text(
    payload: ExtractRequest,
    settings: Settings = Depends(get_settings),
) -> ExtractResponse:
    url = validate_url(str(payload.url), allowed_schemes=settings.allowed_schemes)

    logger.info("extract_text.request", extra={"url": url})

    response = await fetch(url, max_bytes=settings.max_html_bytes)

    try:
        html = response.text
    except Exception:
        html = response.content.decode("utf-8", errors="replace")

    extracted = extract_readable(html)
    content = truncate(extracted.text, settings.max_text_chars)

    return ExtractResponse(
        url=payload.url,
        final_url=str(response.url),
        title=extracted.title,
        content=content,
    )
