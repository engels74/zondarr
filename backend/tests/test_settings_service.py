"""Tests for SettingsService business logic.

Tests the env-var-overrides-DB pattern for CSRF origin settings.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from zondarr.config import Settings
from zondarr.repositories.app_setting import AppSettingRepository
from zondarr.services.settings import SECURE_COOKIES_KEY, SettingsService


def _make_settings(csrf_origin: str | None = None) -> Settings:
    """Create a Settings instance for testing."""
    return Settings(secret_key="a" * 32, csrf_origin=csrf_origin)


class TestGetCsrfOrigin:
    """Tests for SettingsService.get_csrf_origin."""

    @pytest.mark.asyncio
    async def test_returns_env_var_when_set(self, session: AsyncSession) -> None:
        repo = AppSettingRepository(session)
        service = SettingsService(
            repo, settings=_make_settings(csrf_origin="https://x.com")
        )

        origin, is_locked = await service.get_csrf_origin()
        assert origin == "https://x.com"
        assert is_locked is True

    @pytest.mark.asyncio
    async def test_returns_db_value_when_no_env(self, session: AsyncSession) -> None:
        repo = AppSettingRepository(session)
        _ = await repo.upsert("csrf_origin", "https://db.com")

        service = SettingsService(repo, settings=_make_settings())
        origin, is_locked = await service.get_csrf_origin()
        assert origin == "https://db.com"
        assert is_locked is False

    @pytest.mark.asyncio
    async def test_returns_none_when_nothing_configured(
        self, session: AsyncSession
    ) -> None:
        repo = AppSettingRepository(session)
        service = SettingsService(repo, settings=_make_settings())

        origin, is_locked = await service.get_csrf_origin()
        assert origin is None
        assert is_locked is False

    @pytest.mark.asyncio
    async def test_env_takes_precedence_over_db(self, session: AsyncSession) -> None:
        repo = AppSettingRepository(session)
        _ = await repo.upsert("csrf_origin", "https://db.com")

        service = SettingsService(
            repo, settings=_make_settings(csrf_origin="https://env.com")
        )
        origin, is_locked = await service.get_csrf_origin()
        assert origin == "https://env.com"
        assert is_locked is True

    @pytest.mark.asyncio
    async def test_none_settings_falls_to_db(self, session: AsyncSession) -> None:
        repo = AppSettingRepository(session)
        _ = await repo.upsert("csrf_origin", "https://db.com")

        service = SettingsService(repo, settings=None)
        origin, is_locked = await service.get_csrf_origin()
        assert origin == "https://db.com"
        assert is_locked is False


class TestSetCsrfOrigin:
    """Tests for SettingsService.set_csrf_origin."""

    @pytest.mark.asyncio
    async def test_set_creates_new_setting(self, session: AsyncSession) -> None:
        repo = AppSettingRepository(session)
        service = SettingsService(repo, settings=_make_settings())

        result, _ = await service.set_csrf_origin("https://new.com")
        assert result.key == "csrf_origin"
        assert result.value == "https://new.com"

    @pytest.mark.asyncio
    async def test_set_updates_existing_setting(self, session: AsyncSession) -> None:
        repo = AppSettingRepository(session)
        service = SettingsService(repo, settings=_make_settings())

        _, _ = await service.set_csrf_origin("https://first.com")
        result, _ = await service.set_csrf_origin("https://second.com")
        assert result.value == "https://second.com"

    @pytest.mark.asyncio
    async def test_set_none_clears_value(self, session: AsyncSession) -> None:
        repo = AppSettingRepository(session)
        service = SettingsService(repo, settings=_make_settings())

        _, _ = await service.set_csrf_origin("https://set.com")
        result, _ = await service.set_csrf_origin(None)
        assert result.value is None

    @pytest.mark.asyncio
    async def test_set_then_get_round_trip(self, session: AsyncSession) -> None:
        repo = AppSettingRepository(session)
        service = SettingsService(repo, settings=_make_settings())

        _, _ = await service.set_csrf_origin("https://round.trip")
        origin, is_locked = await service.get_csrf_origin()
        assert origin == "https://round.trip"
        assert is_locked is False


class TestSetCsrfOriginAutoEnableSecureCookies:
    """Tests for automatic secure_cookies enablement when setting HTTPS CSRF origin."""

    @pytest.mark.asyncio
    async def test_https_origin_auto_enables_secure_cookies(
        self, session: AsyncSession
    ) -> None:
        """Setting an HTTPS origin should auto-enable secure_cookies in the DB."""
        repo = AppSettingRepository(session)
        service = SettingsService(repo, settings=_make_settings())

        _, auto_enabled = await service.set_csrf_origin("https://example.com")

        assert auto_enabled is True
        secure_setting = await repo.get_by_key(SECURE_COOKIES_KEY)
        assert secure_setting is not None
        assert secure_setting.value == "true"

    @pytest.mark.asyncio
    async def test_http_origin_does_not_auto_enable(
        self, session: AsyncSession
    ) -> None:
        """Setting an HTTP origin should NOT auto-enable secure_cookies."""
        repo = AppSettingRepository(session)
        service = SettingsService(repo, settings=_make_settings())

        _, auto_enabled = await service.set_csrf_origin("http://example.com")

        assert auto_enabled is False
        secure_setting = await repo.get_by_key(SECURE_COOKIES_KEY)
        assert secure_setting is None

    @pytest.mark.asyncio
    async def test_none_origin_does_not_auto_enable(
        self, session: AsyncSession
    ) -> None:
        """Setting origin to None should NOT auto-enable secure_cookies."""
        repo = AppSettingRepository(session)
        service = SettingsService(repo, settings=_make_settings())

        _, auto_enabled = await service.set_csrf_origin(None)

        assert auto_enabled is False
        secure_setting = await repo.get_by_key(SECURE_COOKIES_KEY)
        assert secure_setting is None

    @pytest.mark.asyncio
    async def test_https_skips_when_env_locked(
        self, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When SECURE_COOKIES env var is set, auto-enable should be skipped."""
        monkeypatch.setenv("SECURE_COOKIES", "false")
        repo = AppSettingRepository(session)
        service = SettingsService(repo, settings=_make_settings())

        _, auto_enabled = await service.set_csrf_origin("https://example.com")

        assert auto_enabled is False
        # No DB write for secure_cookies should have happened
        secure_setting = await repo.get_by_key(SECURE_COOKIES_KEY)
        assert secure_setting is None

    @pytest.mark.asyncio
    async def test_https_already_enabled_no_redundant_write(
        self, session: AsyncSession
    ) -> None:
        """When secure_cookies is already enabled, auto_enabled should be False."""
        repo = AppSettingRepository(session)
        service = SettingsService(repo, settings=_make_settings())

        # Pre-enable secure cookies
        _ = await service.set_secure_cookies(True)

        _, auto_enabled = await service.set_csrf_origin("https://example.com")

        assert auto_enabled is False
        # Still enabled
        value, _ = await service.get_secure_cookies()
        assert value is True

    @pytest.mark.asyncio
    async def test_returns_setting_and_auto_enabled_flag(
        self, session: AsyncSession
    ) -> None:
        """Return value should be a tuple of (AppSetting, auto_enabled)."""
        repo = AppSettingRepository(session)
        service = SettingsService(repo, settings=_make_settings())

        setting, auto_enabled = await service.set_csrf_origin("https://example.com")

        assert setting.key == "csrf_origin"
        assert setting.value == "https://example.com"
        assert auto_enabled is True
