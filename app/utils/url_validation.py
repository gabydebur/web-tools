"""URL validation utilities.

This module is deliberately conservative and structured so SSRF hardening
(IP whitelist/blacklist, DNS resolution checks) can be plugged in later
without touching callers.
"""
from __future__ import annotations

from urllib.parse import urlparse

from app.utils.errors import InvalidURLError


def validate_url(raw_url: str, *, allowed_schemes: tuple[str, ...] = ("http", "https")) -> str:
    """Validate and normalize a URL.

    Raises:
        InvalidURLError: if the URL is malformed or uses a forbidden scheme.
    """
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise InvalidURLError("URL is empty")

    url = raw_url.strip()

    try:
        parsed = urlparse(url)
    except (ValueError, AttributeError) as exc:
        raise InvalidURLError("URL could not be parsed", detail=str(exc)) from exc

    if not parsed.scheme:
        raise InvalidURLError("URL must include a scheme (http/https)")

    if parsed.scheme.lower() not in allowed_schemes:
        raise InvalidURLError(
            f"URL scheme '{parsed.scheme}' is not allowed",
            detail=f"allowed: {','.join(allowed_schemes)}",
        )

    if not parsed.netloc:
        raise InvalidURLError("URL must include a host")

    # Reserved hook for future SSRF guards: disallow IP literals, private CIDRs,
    # localhost unless explicitly whitelisted, etc.
    # _reject_private_hosts(parsed.hostname)

    return url
