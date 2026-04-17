"""Unit tests for HTML extraction helpers."""
from __future__ import annotations

from app.services.extractor import extract_readable, extract_title, truncate


HTML_SAMPLE = """
<html>
  <head><title>My Page</title></head>
  <body>
    <script>alert('x')</script>
    <style>.a{}</style>
    <h1>Hello</h1>
    <p>Some <b>useful</b> content here.</p>
    <p>Second paragraph.</p>
  </body>
</html>
"""


def test_extract_title() -> None:
    assert extract_title(HTML_SAMPLE) == "My Page"


def test_extract_title_empty() -> None:
    assert extract_title("") == ""


def test_extract_readable_strips_scripts() -> None:
    result = extract_readable(HTML_SAMPLE)
    assert "alert" not in result.text
    assert "Hello" in result.text
    assert "useful" in result.text
    assert result.title != ""


def test_truncate() -> None:
    assert truncate("abcdef", 3) == "abc"
    assert truncate("abc", 10) == "abc"
    assert truncate("abc", 0) == "abc"
