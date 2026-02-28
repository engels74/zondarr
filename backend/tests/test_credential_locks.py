"""Tests for credential lock status endpoint.

Tests for:
- GET /api/v1/servers/{server_id}/credential-locks endpoint
"""

from collections.abc import AsyncGenerator

import pytest
from litestar import Litestar
from litestar.datastructures import State
from litestar.di import Provide
from litestar.testing import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.conftest import create_test_engine
from zondarr.api.servers import ServerController
from zondarr.config import Settings
from zondarr.media.providers.jellyfin import JellyfinProvider
from zondarr.media.providers.plex import PlexProvider
from zondarr.media.registry import registry
from zondarr.models.media_server import MediaServer


def _make_test_settings(
    provider_credentials: dict[str, dict[str, str]] | None = None,
) -> Settings:
    """Create a Settings instance for testing."""
    return Settings(
        secret_key="a" * 32,
        provider_credentials=provider_credentials or {},
    )


def _ensure_registry() -> None:
    """Ensure the global registry has real providers registered."""
    registry.register(PlexProvider())
    registry.register(JellyfinProvider())


def _make_test_app(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> Litestar:
    """Create a Litestar test app with the ServerController."""
    _ensure_registry()

    async def provide_session() -> AsyncGenerator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def provide_settings_fn(state: State) -> Settings:
        return state.settings  # pyright: ignore[reportAny]

    return Litestar(
        route_handlers=[ServerController],
        state=State({"settings": settings}),
        dependencies={
            "session": Provide(provide_session),
            "settings": Provide(provide_settings_fn, sync_to_thread=False),
        },
    )


class TestCredentialLocks:
    """Integration tests for the credential-locks endpoint."""

    @pytest.mark.asyncio
    async def test_no_env_vars_returns_unlocked(self) -> None:
        """Both fields are unlocked when no env vars are set."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            settings = _make_test_settings()

            async with session_factory() as session:
                server = MediaServer(
                    name="Plex Main",
                    server_type="plex",
                    url="http://plex.local:32400",
                    api_key="token",
                    enabled=True,
                )
                session.add(server)
                await session.commit()
                server_id = server.id

            app = _make_test_app(session_factory, settings)

            with TestClient(app) as client:
                response = client.get(f"/api/v1/servers/{server_id}/credential-locks")
                assert response.status_code == 200
                data: dict[str, object] = response.json()  # pyright: ignore[reportAny]
                assert data["url_locked"] is False
                assert data["api_key_locked"] is False
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_both_env_vars_returns_locked(self) -> None:
        """Both fields are locked when both env vars are set."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            settings = _make_test_settings(
                provider_credentials={
                    "plex": {
                        "url": "http://plex.local:32400",
                        "api_key": "my-plex-token",
                    },
                }
            )

            async with session_factory() as session:
                server = MediaServer(
                    name="Plex Main",
                    server_type="plex",
                    url="http://plex.local:32400",
                    api_key="token",
                    enabled=True,
                )
                session.add(server)
                await session.commit()
                server_id = server.id

            app = _make_test_app(session_factory, settings)

            with TestClient(app) as client:
                response = client.get(f"/api/v1/servers/{server_id}/credential-locks")
                assert response.status_code == 200
                data: dict[str, object] = response.json()  # pyright: ignore[reportAny]
                assert data["url_locked"] is True
                assert data["api_key_locked"] is True
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_url_only_env_var(self) -> None:
        """Only url_locked is true when only URL env var is set."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            settings = _make_test_settings(
                provider_credentials={
                    "plex": {"url": "http://plex.local:32400"},
                }
            )

            async with session_factory() as session:
                server = MediaServer(
                    name="Plex Main",
                    server_type="plex",
                    url="http://plex.local:32400",
                    api_key="token",
                    enabled=True,
                )
                session.add(server)
                await session.commit()
                server_id = server.id

            app = _make_test_app(session_factory, settings)

            with TestClient(app) as client:
                response = client.get(f"/api/v1/servers/{server_id}/credential-locks")
                assert response.status_code == 200
                data: dict[str, object] = response.json()  # pyright: ignore[reportAny]
                assert data["url_locked"] is True
                assert data["api_key_locked"] is False
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_api_key_only_env_var(self) -> None:
        """Only api_key_locked is true when only API key env var is set."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            settings = _make_test_settings(
                provider_credentials={
                    "plex": {"api_key": "my-plex-token"},
                }
            )

            async with session_factory() as session:
                server = MediaServer(
                    name="Plex Main",
                    server_type="plex",
                    url="http://plex.local:32400",
                    api_key="token",
                    enabled=True,
                )
                session.add(server)
                await session.commit()
                server_id = server.id

            app = _make_test_app(session_factory, settings)

            with TestClient(app) as client:
                response = client.get(f"/api/v1/servers/{server_id}/credential-locks")
                assert response.status_code == 200
                data: dict[str, object] = response.json()  # pyright: ignore[reportAny]
                assert data["url_locked"] is False
                assert data["api_key_locked"] is True
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_jellyfin_provider_locks(self) -> None:
        """Lock status works for Jellyfin provider type."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            settings = _make_test_settings(
                provider_credentials={
                    "jellyfin": {
                        "url": "http://jellyfin.local:8096",
                        "api_key": "jf-api-key-12345",
                    },
                }
            )

            async with session_factory() as session:
                server = MediaServer(
                    name="Jellyfin Main",
                    server_type="jellyfin",
                    url="http://jellyfin.local:8096",
                    api_key="token",
                    enabled=True,
                )
                session.add(server)
                await session.commit()
                server_id = server.id

            app = _make_test_app(session_factory, settings)

            with TestClient(app) as client:
                response = client.get(f"/api/v1/servers/{server_id}/credential-locks")
                assert response.status_code == 200
                data: dict[str, object] = response.json()  # pyright: ignore[reportAny]
                assert data["url_locked"] is True
                assert data["api_key_locked"] is True
        finally:
            await engine.dispose()
