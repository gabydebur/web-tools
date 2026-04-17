"""HTML -> text / title extraction."""
from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup

try:
    from readability import Document  # readability-lxml

    _HAS_READABILITY = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_READABILITY = False


@dataclass(slots=True)
class ExtractedContent:
    title: str
    text: str


def extract_title(html: str) -> str:
    """Extract a page title, robust to malformed HTML."""
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    return ""


def extract_readable(html: str) -> ExtractedContent:
    """Return a cleaned title + plain-text representation of the main content."""
    if not html:
        return ExtractedContent(title="", text="")

    title = ""
    content_html = html

    if _HAS_READABILITY:
        try:
            doc = Document(html)
            title = (doc.short_title() or "").strip()
            content_html = doc.summary(html_partial=True) or html
        except Exception:
            # Fallback to raw parsing below
            content_html = html

    try:
        soup = BeautifulSoup(content_html, "lxml")
    except Exception:
        soup = BeautifulSoup(content_html, "html.parser")

    # Remove noise
    for tag in soup(["script", "style", "noscript", "template", "iframe", "svg"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Collapse excessive blank lines
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)

    if not title:
        title = extract_title(html)

    return ExtractedContent(title=title, text=cleaned)


def truncate(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars]
