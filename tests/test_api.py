"""End-to-end API tests using FastAPI TestClient."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas import SearchResultItem


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready(client: TestClient) -> None:
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_web_search_validation_error_empty_query(client: TestClient) -> None:
    r = client.post("/web_search", json={"query": "", "limit": 3})
    assert r.status_code == 422


def test_web_search_happy_path(client: TestClient) -> None:
    fake_results = [
        SearchResultItem(
            title="Example",
            url="https://example.com",
            snippet="An example",
            source="duckduckgo",
        ),
    ]

    with patch(
        "app.routes.search.searxng.search",
        new=AsyncMock(return_value=fake_results),
    ):
        r = client.post("/web_search", json={"query": "hello", "limit": 1})

    assert r.status_code == 200
    data = r.json()
    assert data["query"] == "hello"
    assert len(data["results"]) == 1
    assert data["results"][0]["url"].startswith("https://example.com")


def test_fetch_url_invalid_scheme(client: TestClient) -> None:
    r = client.post("/fetch_url", json={"url": "ftp://example.com"})
    # Pydantic HttpUrl rejects non-http(s) at the schema layer -> 422
    assert r.status_code == 422


def test_fetch_url_happy_path(client: TestClient) -> None:
    class FakeResponse:
        status_code = 200
        url = "https://example.com/"
        headers = {"Content-Type": "text/html; charset=utf-8"}
        text = "<html><head><title>Ex</title></head><body>Hi</body></html>"
        content = text.encode()

    async def fake_fetch(url: str, *, max_bytes: int) -> Any:
        return FakeResponse()

    with patch("app.routes.fetch.fetch", new=fake_fetch):
        r = client.post("/fetch_url", json={"url": "https://example.com"})

    assert r.status_code == 200
    data = r.json()
    assert data["status_code"] == 200
    assert data["content_type"] == "text/html"
    assert data["title"] == "Ex"
    assert "Hi" in data["html"]


def test_extract_text_happy_path(client: TestClient) -> None:
    html = (
        "<html><head><title>T</title></head>"
        "<body><article><h1>Head</h1>"
        "<p>Paragraph content here.</p></article></body></html>"
    )

    class FakeResponse:
        status_code = 200
        url = "https://example.com/article"
        headers = {"Content-Type": "text/html"}
        text = html
        content = html.encode()

    async def fake_fetch(url: str, *, max_bytes: int) -> Any:
        return FakeResponse()

    with patch("app.routes.extract.fetch", new=fake_fetch):
        r = client.post("/extract_text", json={"url": "https://example.com/article"})

    assert r.status_code == 200
    data = r.json()
    assert "Paragraph content" in data["content"]
    assert data["title"]
