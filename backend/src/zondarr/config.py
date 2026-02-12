"""Application configuration with environment variable loading.

Uses msgspec.Struct for high-performance serialization and validation.
"""

import os
from typing import Annotated

import msgspec


class Settings(msgspec.Struct, kw_only=True, forbid_unknown_fields=True):
    """Application settings loaded from environment variables.

    Uses Python 3.14 deferred annotations - no forward reference quotes needed.
    """

    # Database
    database_url: Annotated[
        str,
        msgspec.Meta(
            description="Database connection URL (sqlite+aiosqlite:// or postgresql+asyncpg://)"
        ),
    ] = "sqlite+aiosqlite:///./zondarr.db"

    # Server
    host: str = "0.0.0.0"  # noqa: S104
    port: Annotated[int, msgspec.Meta(ge=1, le=65535)] = 8000
    debug: bool = False

    # CORS
    cors_origins: Annotated[
        list[str],
        msgspec.Meta(
            description=(
                "Allowed CORS origins (empty = CORS disabled)."
                " From comma-separated CORS_ORIGINS env var."
            )
        ),
    ] = []

    # Security
    secret_key: Annotated[str, msgspec.Meta(min_length=32)]
    secure_cookies: Annotated[
        bool,
        msgspec.Meta(
            description="Set True when serving over HTTPS to enforce Secure flag on cookies"
        ),
    ] = False

    # Legacy media server credentials (kept for backwards compatibility)
    plex_url: str | None = None
    plex_token: str | None = None
    jellyfin_url: str | None = None
    jellyfin_api_key: str | None = None

    # Dynamic provider credentials populated from env vars
    # Keyed by server_type (e.g., "plex", "jellyfin")
    # Each value is a dict with "url" and "api_key" keys
    provider_credentials: dict[str, dict[str, str]] = {}

    # Background task intervals (in seconds)
    expiration_check_interval_seconds: Annotated[
        int,
        msgspec.Meta(
            ge=60,
            description="Interval in seconds for checking expired invitations (default: 1 hour)",
        ),
    ] = 3600
    sync_interval_seconds: Annotated[
        int,
        msgspec.Meta(
            ge=60,
            description="Interval in seconds for syncing media servers (default: 15 minutes)",
        ),
    ] = 900


def load_settings() -> Settings:
    """Load and validate settings from environment variables.

    Uses walrus operator for cleaner required value handling.
    Raises ConfigurationError if required values are missing.
    """
    from .core.exceptions import ConfigurationError

    # Check required values first (fail fast)
    if (secret_key := os.environ.get("SECRET_KEY")) is None:
        raise ConfigurationError(
            "SECRET_KEY environment variable is required",
            "MISSING_CONFIG",
            field="SECRET_KEY",
        )

    # Build settings dict for validation via msgspec.convert
    settings_dict = {
        "database_url": os.environ.get(
            "DATABASE_URL", "sqlite+aiosqlite:///./zondarr.db"
        ),
        "host": os.environ.get("HOST", "0.0.0.0"),  # noqa: S104
        "port": int(os.environ.get("PORT", "8000")),
        "debug": os.environ.get("DEBUG", "").lower() in ("true", "1", "yes"),
        "cors_origins": [
            origin.strip()
            for origin in os.environ.get("CORS_ORIGINS", "").split(",")
            if origin.strip()
        ],
        "secret_key": secret_key,
        "secure_cookies": os.environ.get("SECURE_COOKIES", "").lower()
        in ("true", "1", "yes"),
        "expiration_check_interval_seconds": int(
            os.environ.get("EXPIRATION_CHECK_INTERVAL_SECONDS", "3600")
        ),
        "sync_interval_seconds": int(os.environ.get("SYNC_INTERVAL_SECONDS", "900")),
        "plex_url": os.environ.get("PLEX_URL") or None,
        "plex_token": os.environ.get("PLEX_TOKEN") or None,
        "jellyfin_url": os.environ.get("JELLYFIN_URL") or None,
        "jellyfin_api_key": os.environ.get("JELLYFIN_API_KEY") or None,
    }

    # msgspec.convert validates constraints
    settings = msgspec.convert(settings_dict, Settings)

    # Populate provider_credentials dynamically from registry metadata
    _populate_provider_credentials(settings)

    return settings


def _populate_provider_credentials(settings: Settings) -> None:
    """Populate provider_credentials from env vars using registry metadata.

    Reads each registered provider's declared env var names and populates
    the provider_credentials dict. Falls back to legacy fields for
    backwards compatibility.
    """
    from .media.registry import registry

    provider_creds: dict[str, dict[str, str]] = {}

    for meta in registry.get_all_metadata():
        creds: dict[str, str] = {}

        # Read URL from provider's declared env var
        url_val = os.environ.get(meta.env_url_var) or None
        if url_val:
            creds["url"] = url_val

        # Read API key from provider's declared env var
        api_key_val = os.environ.get(meta.env_api_key_var) or None
        if api_key_val:
            creds["api_key"] = api_key_val

        if creds:
            provider_creds[meta.server_type] = creds

    # Backwards compatibility: also check legacy fields
    # Only use legacy values when the provider doesn't already have that specific key
    if settings.plex_url:
        provider_creds.setdefault("plex", {}).setdefault("url", settings.plex_url)
    if settings.plex_token:
        provider_creds.setdefault("plex", {}).setdefault("api_key", settings.plex_token)
    if settings.jellyfin_url:
        provider_creds.setdefault("jellyfin", {}).setdefault(
            "url", settings.jellyfin_url
        )
    if settings.jellyfin_api_key:
        provider_creds.setdefault("jellyfin", {}).setdefault(
            "api_key", settings.jellyfin_api_key
        )

    settings.provider_credentials = provider_creds
