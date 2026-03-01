"""Settings service for managing application settings.

Implements the env-var-overrides-DB pattern: environment variable values
take precedence over database values and are marked as "locked".
"""

import os

import structlog

from zondarr.config import Settings
from zondarr.models.app_setting import AppSetting
from zondarr.repositories.app_setting import AppSettingRepository

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)  # pyright: ignore[reportAny]

# Database keys for settings
CSRF_ORIGIN_KEY = "csrf_origin"
SECURE_COOKIES_KEY = "secure_cookies"
SYNC_INTERVAL_KEY = "sync_interval_seconds"
EXPIRATION_INTERVAL_KEY = "expiration_check_interval_seconds"

# Defaults
DEFAULT_SYNC_INTERVAL = 900
DEFAULT_EXPIRATION_INTERVAL = 3600


class SettingsService:
    """Service for managing application-level settings.

    Follows the env-var-overrides-DB pattern: if a setting is defined
    via environment variable, it takes precedence and is marked as locked.

    Attributes:
        repository: The AppSettingRepository for data access.
        settings: Optional application Settings for env var checks.
    """

    repository: AppSettingRepository
    settings: Settings | None

    def __init__(
        self,
        repository: AppSettingRepository,
        /,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings

    async def get_secure_cookies(self) -> tuple[bool, bool]:
        """Get the secure cookies setting.

        Checks SECURE_COOKIES environment variable first (via presence check),
        then falls back to the database value.

        Returns:
            A tuple of (secure_cookies_enabled, is_locked).
            is_locked is True when the value comes from an environment variable.
        """
        env_val = os.environ.get("SECURE_COOKIES")
        if env_val is not None:
            return env_val.lower() in ("true", "1", "yes"), True

        # Fall back to DB
        setting = await self.repository.get_by_key(SECURE_COOKIES_KEY)
        if setting is not None and setting.value is not None:
            return setting.value.lower() in ("true", "1", "yes"), False

        return False, False

    async def set_secure_cookies(self, value: bool) -> AppSetting:
        """Set the secure cookies setting in the database.

        Args:
            value: Whether to enable secure cookies.

        Returns:
            The created or updated AppSetting.
        """
        return await self.repository.upsert(SECURE_COOKIES_KEY, str(value).lower())

    async def get_csrf_origin(self) -> tuple[str | None, bool]:
        """Get the CSRF origin setting.

        Checks environment variable first (via Settings), then falls back
        to the database value.

        Returns:
            A tuple of (origin_value, is_locked).
            is_locked is True when the value comes from an environment variable.
        """
        # Env var takes precedence
        if self.settings is not None and self.settings.csrf_origin:
            return self.settings.csrf_origin, True

        # Fall back to DB
        setting = await self.repository.get_by_key(CSRF_ORIGIN_KEY)
        if setting is not None and setting.value:
            return setting.value, False

        return None, False

    async def set_csrf_origin(self, origin: str | None) -> tuple[AppSetting, bool]:
        """Set the CSRF origin in the database.

        When the origin is HTTPS, automatically enables secure cookies
        in the database — unless the SECURE_COOKIES env var is set (locked)
        or secure cookies are already enabled.

        Args:
            origin: The origin URL to set, or None to clear.

        Returns:
            A tuple of (app_setting, secure_cookies_auto_enabled).
            secure_cookies_auto_enabled is True when secure cookies were
            automatically enabled as a result of this call.
        """
        setting = await self.repository.upsert(CSRF_ORIGIN_KEY, origin)
        auto_enabled = False

        if origin is not None and origin.startswith("https://"):
            env_val = os.environ.get("SECURE_COOKIES")
            if env_val is not None:
                logger.info(
                    "secure_cookies_auto_enable_skipped",
                    csrf_origin=origin,
                    reason="SECURE_COOKIES env var is set",
                )
            else:
                # Check if already enabled in DB to avoid redundant write
                current_val, _ = await self.get_secure_cookies()
                if not current_val:
                    _ = await self.set_secure_cookies(True)
                    auto_enabled = True
                    logger.info(
                        "secure_cookies_auto_enabled",
                        csrf_origin=origin,
                    )

        return setting, auto_enabled

    async def get_sync_interval(self) -> tuple[int, bool]:
        """Get the sync interval setting.

        Checks the SYNC_INTERVAL_SECONDS env var first, then falls back
        to the database value, then the default.

        Returns:
            A tuple of (interval_seconds, is_locked).
        """
        env_val = os.environ.get("SYNC_INTERVAL_SECONDS")
        if env_val is not None:
            return int(env_val), True

        setting = await self.repository.get_by_key(SYNC_INTERVAL_KEY)
        if setting is not None and setting.value:
            return int(setting.value), False

        return DEFAULT_SYNC_INTERVAL, False

    async def set_sync_interval(self, value: int) -> AppSetting:
        """Set the sync interval in the database.

        Args:
            value: Interval in seconds.

        Returns:
            The created or updated AppSetting.
        """
        return await self.repository.upsert(SYNC_INTERVAL_KEY, str(value))

    async def get_expiration_interval(self) -> tuple[int, bool]:
        """Get the expiration check interval setting.

        Checks the EXPIRATION_CHECK_INTERVAL_SECONDS env var first,
        then falls back to the database value, then the default.

        Returns:
            A tuple of (interval_seconds, is_locked).
        """
        env_val = os.environ.get("EXPIRATION_CHECK_INTERVAL_SECONDS")
        if env_val is not None:
            return int(env_val), True

        setting = await self.repository.get_by_key(EXPIRATION_INTERVAL_KEY)
        if setting is not None and setting.value:
            return int(setting.value), False

        return DEFAULT_EXPIRATION_INTERVAL, False

    async def set_expiration_interval(self, value: int) -> AppSetting:
        """Set the expiration check interval in the database.

        Args:
            value: Interval in seconds.

        Returns:
            The created or updated AppSetting.
        """
        return await self.repository.upsert(EXPIRATION_INTERVAL_KEY, str(value))
