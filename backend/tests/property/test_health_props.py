"""Property-based tests for health endpoints.

Feature: zondarr-foundation
Property: 12
Validates: Requirements 8.4, 8.5, 8.6, 8.7
"""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from litestar import Litestar
from litestar.di import Provide
from litestar.testing import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from zondarr.api.health import HealthController
from zondarr.models.base import Base


async def create_test_engine() -> AsyncEngine:
    """Create an async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(  # pyright: ignore[reportUnusedFunction]
        dbapi_connection: Any,  # pyright: ignore[reportExplicitAny,reportAny]
        connection_record: Any,  # pyright: ignore[reportExplicitAny,reportUnusedParameter,reportAny]
    ) -> None:
        cursor = dbapi_connection.cursor()  # pyright: ignore[reportAny]
        cursor.execute("PRAGMA foreign_keys=ON")  # pyright: ignore[reportAny]
        cursor.close()  # pyright: ignore[reportAny]

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


def create_test_app(session_factory: async_sessionmaker[AsyncSession]) -> Litestar:
    """Create a test Litestar app with the health controller."""

    async def provide_session() -> AsyncGenerator[AsyncSession]:
        async with session_factory() as session:
            yield session

    return Litestar(
        route_handlers=[HealthController],
        dependencies={"session": Provide(provide_session)},
    )


class TestHealthEndpointsReturnCorrectStatus:
    """
    Feature: zondarr-foundation
    Property 12: Health Endpoints Return Correct Status

    *For any* application state:
    - If all dependencies are healthy, `/health` SHALL return HTTP 200 with status "healthy"
    - If any dependency is unhealthy, `/health` SHALL return HTTP 503 with status "degraded"
    - `/health/live` SHALL always return HTTP 200 if the process is running
    - `/health/ready` SHALL return HTTP 503 if database is unreachable, HTTP 200 otherwise

    **Validates: Requirements 8.4, 8.5, 8.6, 8.7**
    """

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,  # Disable deadline due to test setup overhead
    )
    @given(num_requests=st.integers(min_value=1, max_value=10))
    @pytest.mark.asyncio
    async def test_liveness_always_returns_200(self, num_requests: int) -> None:
        """Liveness probe always returns HTTP 200 if process is running.

        **Validates: Requirement 8.6**
        """
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            app = create_test_app(session_factory)

            with TestClient(app) as client:
                for _ in range(num_requests):
                    response = client.get("/health/live")
                    assert response.status_code == 200
                    data = response.json()  # pyright: ignore[reportAny]
                    assert data["status"] == "alive"
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,  # Disable deadline due to test setup overhead
    )
    @given(num_requests=st.integers(min_value=1, max_value=10))
    @pytest.mark.asyncio
    async def test_health_returns_200_when_database_healthy(
        self, num_requests: int
    ) -> None:
        """Health endpoint returns HTTP 200 with status "healthy" when database is reachable.

        **Validates: Requirement 8.5**
        """
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            app = create_test_app(session_factory)

            with TestClient(app) as client:
                for _ in range(num_requests):
                    response = client.get("/health")
                    assert response.status_code == 200
                    data = response.json()  # pyright: ignore[reportAny]
                    assert data["status"] == "healthy"
                    assert data["checks"]["database"] is True
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,  # Disable deadline due to test setup overhead
    )
    @given(num_requests=st.integers(min_value=1, max_value=10))
    @pytest.mark.asyncio
    async def test_health_returns_503_when_database_unhealthy(
        self, num_requests: int
    ) -> None:
        """Health endpoint returns HTTP 503 with status "degraded" when database is unreachable.

        **Validates: Requirement 8.4**
        """
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            app = create_test_app(session_factory)

            with TestClient(app) as client:
                # Mock the database check to return False
                with patch.object(
                    HealthController,
                    "_check_database",
                    new_callable=AsyncMock,
                    return_value=False,
                ):
                    for _ in range(num_requests):
                        response = client.get("/health")
                        assert response.status_code == 503
                        data = response.json()  # pyright: ignore[reportAny]
                        assert data["status"] == "degraded"
                        assert data["checks"]["database"] is False
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,  # Disable deadline due to test setup overhead
    )
    @given(num_requests=st.integers(min_value=1, max_value=10))
    @pytest.mark.asyncio
    async def test_readiness_returns_200_when_database_healthy(
        self, num_requests: int
    ) -> None:
        """Readiness probe returns HTTP 200 when database is reachable.

        **Validates: Requirement 8.7**
        """
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            app = create_test_app(session_factory)

            with TestClient(app) as client:
                for _ in range(num_requests):
                    response = client.get("/health/ready")
                    assert response.status_code == 200
                    data = response.json()  # pyright: ignore[reportAny]
                    assert data["status"] == "ready"
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,  # Disable deadline due to test setup overhead
    )
    @given(num_requests=st.integers(min_value=1, max_value=10))
    @pytest.mark.asyncio
    async def test_readiness_returns_503_when_database_unhealthy(
        self, num_requests: int
    ) -> None:
        """Readiness probe returns HTTP 503 when database is unreachable.

        **Validates: Requirement 8.7**
        """
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            app = create_test_app(session_factory)

            with TestClient(app) as client:
                # Mock the database check to return False
                with patch.object(
                    HealthController,
                    "_check_database",
                    new_callable=AsyncMock,
                    return_value=False,
                ):
                    for _ in range(num_requests):
                        response = client.get("/health/ready")
                        assert response.status_code == 503
                        data = response.json()  # pyright: ignore[reportAny]
                        assert data["status"] == "not ready"
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,  # Disable deadline due to test setup overhead
    )
    @given(
        db_healthy=st.booleans(),
        num_requests=st.integers(min_value=1, max_value=5),
    )
    @pytest.mark.asyncio
    async def test_health_status_matches_dependency_state(
        self, db_healthy: bool, num_requests: int
    ) -> None:
        """Health status correctly reflects dependency state.

        **Validates: Requirements 8.4, 8.5**
        """
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            app = create_test_app(session_factory)

            with TestClient(app) as client:
                with patch.object(
                    HealthController,
                    "_check_database",
                    new_callable=AsyncMock,
                    return_value=db_healthy,
                ):
                    for _ in range(num_requests):
                        response = client.get("/health")

                        if db_healthy:
                            assert response.status_code == 200
                            assert response.json()["status"] == "healthy"
                        else:
                            assert response.status_code == 503
                            assert response.json()["status"] == "degraded"

                        # Checks dict always reflects actual state
                        assert response.json()["checks"]["database"] is db_healthy
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,  # Disable deadline due to test setup overhead
    )
    @given(
        db_healthy=st.booleans(),
        num_requests=st.integers(min_value=1, max_value=5),
    )
    @pytest.mark.asyncio
    async def test_readiness_status_matches_database_state(
        self, db_healthy: bool, num_requests: int
    ) -> None:
        """Readiness status correctly reflects database connectivity.

        **Validates: Requirement 8.7**
        """
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            app = create_test_app(session_factory)

            with TestClient(app) as client:
                with patch.object(
                    HealthController,
                    "_check_database",
                    new_callable=AsyncMock,
                    return_value=db_healthy,
                ):
                    for _ in range(num_requests):
                        response = client.get("/health/ready")

                        if db_healthy:
                            assert response.status_code == 200
                            assert response.json()["status"] == "ready"
                        else:
                            assert response.status_code == 503
                            assert response.json()["status"] == "not ready"
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,  # Disable deadline due to test setup overhead
    )
    @given(
        db_healthy=st.booleans(),
    )
    @pytest.mark.asyncio
    async def test_liveness_independent_of_database_state(
        self, db_healthy: bool
    ) -> None:
        """Liveness probe returns 200 regardless of database state.

        **Validates: Requirement 8.6**
        """
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            app = create_test_app(session_factory)

            with TestClient(app) as client:
                # Even with database mocked to fail, liveness should succeed
                with patch.object(
                    HealthController,
                    "_check_database",
                    new_callable=AsyncMock,
                    return_value=db_healthy,
                ):
                    response = client.get("/health/live")
                    # Liveness always returns 200 regardless of db state
                    assert response.status_code == 200
                    assert response.json()["status"] == "alive"
        finally:
            await engine.dispose()
