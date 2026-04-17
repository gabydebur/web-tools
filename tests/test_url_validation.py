"""Unit tests for URL validation."""
from __future__ import annotations

import pytest

from app.utils.errors import InvalidURLError
from app.utils.url_validation import validate_url


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://example.com/path?q=1",
        "HTTPS://EXAMPLE.COM",
    ],
)
def test_validate_url_accepts_http_https(url: str) -> None:
    assert validate_url(url) == url.strip()


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "ftp://example.com",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "not a url",
        "://missing-scheme",
    ],
)
def test_validate_url_rejects_invalid(url: str) -> None:
    with pytest.raises(InvalidURLError):
        validate_url(url)


def test_validate_url_rejects_missing_host() -> None:
    with pytest.raises(InvalidURLError):
        validate_url("http://")
