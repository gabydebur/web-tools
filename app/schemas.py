"""Pydantic request/response models."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


# ---------- Search ----------


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: Optional[int] = Field(default=None, ge=1, le=100)


class SearchResultItem(BaseModel):
    title: str
    url: HttpUrl
    snippet: str = ""
    source: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]


# ---------- Fetch ----------


class FetchRequest(BaseModel):
    url: HttpUrl


class FetchResponse(BaseModel):
    url: HttpUrl
    final_url: HttpUrl
    status_code: int
    content_type: str
    title: str = ""
    html: str


# ---------- Extract ----------


class ExtractRequest(BaseModel):
    url: HttpUrl


class ExtractResponse(BaseModel):
    url: HttpUrl
    final_url: HttpUrl
    title: str = ""
    content: str


# ---------- Misc ----------


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
