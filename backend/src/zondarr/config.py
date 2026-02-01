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

    # Security
    secret_key: Annotated[str, msgspec.Meta(min_length=32)]


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
        "secret_key": secret_key,
    }

    # msgspec.convert validates constraints
    return msgspec.convert(settings_dict, Settings)
