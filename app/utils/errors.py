"""Domain exceptions used across services and mapped to HTTP errors."""
from __future__ import annotations


class WebToolsError(Exception):
    """Base class for all controlled errors in this service."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class InvalidURLError(WebToolsError):
    status_code = 400
    code = "invalid_url"


class UpstreamError(WebToolsError):
    """Raised when an upstream HTTP call fails (network, timeout, bad status)."""

    status_code = 502
    code = "upstream_error"


class PayloadTooLargeError(WebToolsError):
    status_code = 413
    code = "payload_too_large"


class SearchBackendError(WebToolsError):
    status_code = 502
    code = "search_backend_error"
