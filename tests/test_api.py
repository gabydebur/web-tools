"""End-to-end API tests using FastAPI TestClient."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas import SearchResultItem
from app.services.http_client import FetchResult


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
    body = r.json()
    assert body["error"] == "validation_error"
    # detail must be a JSON-parseable structure, not a str(list) blob
    assert isinstance(body["detail"], list)


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


def _make_fetch_result(html: str, content_type: str = "text/html; charset=utf-8",
                       final_url: str = "https://example.com/") -> FetchResult:
    return FetchResult(
        final_url=final_url,
        status_code=200,
        content_type=content_type.split(";")[0].strip(),
        text=html,
        content=html.encode(),
    )


def test_fetch_url_happy_path(client: TestClient) -> None:
    result = _make_fetch_result(
        "<html><head><title>Ex</title></head><body>Hi</body></html>",
    )

    async def fake_fetch(url: str, *, max_bytes: int) -> FetchResult:
        return result

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
    result = _make_fetch_result(html, final_url="https://example.com/article")

    async def fake_fetch(url: str, *, max_bytes: int) -> FetchResult:
        return result

    with patch("app.routes.extract.fetch", new=fake_fetch):
        r = client.post("/extract_text", json={"url": "https://example.com/article"})

    assert r.status_code == 200
    data = r.json()
    assert "Paragraph content" in data["content"]
    assert data["title"]


def test_extract_text_non_html_is_skipped(client: TestClient) -> None:
    # A binary/PDF-like response should not be fed to BS4.
    result = FetchResult(
        final_url="https://example.com/file.pdf",
        status_code=200,
        content_type="application/pdf",
        text="%PDF-1.4 garbage",
        content=b"%PDF-1.4 garbage",
    )

    async def fake_fetch(url: str, *, max_bytes: int) -> FetchResult:
        return result

    with patch("app.routes.extract.fetch", new=fake_fetch):
        r = client.post("/extract_text", json={"url": "https://example.com/file.pdf"})

    assert r.status_code == 200
    data = r.json()
    assert data["content"] == ""
    assert data["title"] == ""


def test_extract_text_plain_text(client: TestClient) -> None:
    result = FetchResult(
        final_url="https://example.com/robots.txt",
        status_code=200,
        content_type="text/plain",
        text="User-agent: *\nDisallow:",
        content=b"User-agent: *\nDisallow:",
    )

    async def fake_fetch(url: str, *, max_bytes: int) -> FetchResult:
        return result

    with patch("app.routes.extract.fetch", new=fake_fetch):
        r = client.post("/extract_text", json={"url": "https://example.com/robots.txt"})

    assert r.status_code == 200
    data = r.json()
    assert "User-agent" in data["content"]
