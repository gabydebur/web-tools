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


def _is_html(content_type: str) -> bool:
    ct = (content_type or "").lower()
    return "html" in ct or "xml" in ct


def _is_plain_text(content_type: str) -> bool:
    ct = (content_type or "").lower()
    return ct.startswith("text/") and not _is_html(ct)


@router.post("/extract_text", response_model=ExtractResponse)
async def extract_text(
    payload: ExtractRequest,
    settings: Settings = Depends(get_settings),
) -> ExtractResponse:
    url = validate_url(str(payload.url), allowed_schemes=settings.allowed_schemes)

    logger.info("extract_text.request", extra={"url": url})

    result = await fetch(url, max_bytes=settings.max_html_bytes)

    title = ""
    content = ""

    if _is_html(result.content_type):
        extracted = extract_readable(result.text)
        title = extracted.title
        content = extracted.text
        # Fallback: readability sometimes returns empty text on poorly structured pages.
        if not content:
            content = result.text
    elif _is_plain_text(result.content_type):
        content = result.text
    else:
        # Non-text content (PDF, image, binary): no extraction.
        logger.info(
            "extract_text.skipped_non_text",
            extra={"url": url, "content_type": result.content_type},
        )

    content = truncate(content, settings.max_text_chars)

    return ExtractResponse(
        url=payload.url,
        final_url=result.final_url,
        title=title,
        content=content,
    )
