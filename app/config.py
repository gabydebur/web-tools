"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    All values are loadable from environment variables. A local `.env` file is
    also honored during development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    host: str = Field(default="0.0.0.0", description="Bind host.")
    port: int = Field(default=8000, ge=1, le=65535, description="Bind port.")
    log_level: str = Field(default="INFO", description="Logging level.")

    # Search backend
    searxng_base_url: HttpUrl = Field(
        default=HttpUrl("http://searxng:8080"),
        description="Base URL of the SearxNG instance.",
    )
    searxng_language: str = Field(default="fr", description="SearxNG language.")
    searxng_safesearch: int = Field(
        default=1, ge=0, le=2, description="0=off, 1=moderate, 2=strict."
    )

    # HTTP client
    http_timeout_seconds: float = Field(default=10.0, gt=0, le=60.0)
    http_user_agent: str = Field(
        default="web-tools/0.1 (+https://example.local)",
        description="User-Agent used for outgoing HTTP requests.",
    )
    http_max_redirects: int = Field(default=5, ge=0, le=20)

    # Size limits (characters or bytes, see usage)
    max_html_bytes: int = Field(
        default=2_000_000, gt=0, description="Max raw HTML bytes read."
    )
    max_html_chars: int = Field(
        default=500_000, gt=0, description="Max HTML chars returned by fetch_url."
    )
    max_text_chars: int = Field(
        default=50_000, gt=0, description="Max text chars returned by extract_text."
    )

    # Search limits
    search_default_limit: int = Field(default=5, ge=1, le=50)
    search_max_limit: int = Field(default=20, ge=1, le=100)

    # URL filtering (reserved for future SSRF hardening)
    allowed_schemes: tuple[str, ...] = Field(default=("http", "https"))

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        v_up = v.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v_up not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return v_up


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
