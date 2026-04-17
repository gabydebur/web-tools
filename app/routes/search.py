"""/web_search endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas import SearchRequest, SearchResponse
from app.services import searxng
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["tools"])


@router.post("/web_search", response_model=SearchResponse)
async def web_search(
    payload: SearchRequest,
    settings: Settings = Depends(get_settings),
) -> SearchResponse:
    limit = payload.limit or settings.search_default_limit
    limit = min(limit, settings.search_max_limit)

    logger.info("web_search.request", extra={"query": payload.query, "limit": limit})

    results = await searxng.search(payload.query, limit=limit, settings=settings)
    return SearchResponse(query=payload.query, results=results)
