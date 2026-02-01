"""Property-based tests for service layer.

Feature: zondarr-foundation
Properties: 10, 11
Validates: Requirements 6.3, 6.5, 6.6
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from zondarr.core.exceptions import NotFoundError, ValidationError
from zondarr.media.registry import ClientRegistry
from zondarr.models import Invitation, ServerType
from zondarr.models.base import Base
from zondarr.repositories.invitation import InvitationRepository
from zondarr.repositories.media_server import MediaServerRepository
from zondarr.services.invitation import (
    InvitationService,
    InvitationValidationFailure,
)
from zondarr.services.media_server import MediaServerService

# Custom strategies for model fields
name_strategy = st.text(
    alphabet=st.characters(categories=("L", "N")),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip())
url_strategy = st.from_regex(r"https?://[a-z0-9]+\.[a-z]{2,}", fullmatch=True)
server_type_strategy = st.sampled_from([ServerType.JELLYFIN, ServerType.PLEX])
code_strategy = st.text(
    alphabet=st.characters(categories=("L", "N")),
    min_size=6,
    max_size=20,
)
positive_int_strategy = st.integers(min_value=0, max_value=1000)


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


class TestServiceValidatesBeforePersisting:
    """
    Feature: zondarr-foundation
    Property 10: Service Validates Before Persisting

    *For any* media server configuration where `test_connection()` returns False,
    the MediaServerService SHALL NOT persist the server to the database and
    SHALL raise a validation error.

    **Validates: Requirements 6.3**
    """

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        name=name_strategy,
        server_type=server_type_strategy,
        url=url_strategy,
        api_key=name_strategy,
    )
    @pytest.mark.asyncio
    async def test_add_server_fails_when_connection_test_fails(
        self,
        name: str,
        server_type: ServerType,
        url: str,
        api_key: str,
    ) -> None:
        """MediaServerService.add raises ValidationError when connection test fails."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = MediaServerRepository(session)

                # Create a mock registry that returns a client with failing connection
                mock_registry = MagicMock(spec=ClientRegistry)
                mock_client = AsyncMock()
                mock_client.test_connection = AsyncMock(return_value=False)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_registry.create_client = MagicMock(return_value=mock_client)

                service = MediaServerService(repo, registry=mock_registry)

                # Attempt to add server - should raise ValidationError
                with pytest.raises(ValidationError) as exc_info:
                    _ = await service.add(
                        name=name,
                        server_type=server_type,
                        url=url,
                        api_key=api_key,
                    )

                # Verify error details
                assert exc_info.value.error_code == "VALIDATION_ERROR"
                assert "url" in exc_info.value.field_errors
                assert "api_key" in exc_info.value.field_errors

                # Verify server was NOT persisted
                all_servers = await repo.get_all()
                assert len(all_servers) == 0
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        name=name_strategy,
        server_type=server_type_strategy,
        url=url_strategy,
        api_key=name_strategy,
    )
    @pytest.mark.asyncio
    async def test_add_server_succeeds_when_connection_test_passes(
        self,
        name: str,
        server_type: ServerType,
        url: str,
        api_key: str,
    ) -> None:
        """MediaServerService.add persists server when connection test passes."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = MediaServerRepository(session)

                # Create a mock registry that returns a client with passing connection
                mock_registry = MagicMock(spec=ClientRegistry)
                mock_client = AsyncMock()
                mock_client.test_connection = AsyncMock(return_value=True)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_registry.create_client = MagicMock(return_value=mock_client)

                service = MediaServerService(repo, registry=mock_registry)

                # Add server - should succeed
                created = await service.add(
                    name=name,
                    server_type=server_type,
                    url=url,
                    api_key=api_key,
                )
                await session.commit()

                # Verify server was persisted
                assert created.id is not None
                assert created.name == name
                assert created.server_type == server_type
                assert created.url == url
                assert created.api_key == api_key

                # Verify server exists in database
                retrieved = await repo.get_by_id(created.id)
                assert retrieved is not None
                assert retrieved.name == name
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        name=name_strategy,
        server_type=server_type_strategy,
        url=url_strategy,
        api_key=name_strategy,
    )
    @pytest.mark.asyncio
    async def test_add_server_fails_when_connection_raises_exception(
        self,
        name: str,
        server_type: ServerType,
        url: str,
        api_key: str,
    ) -> None:
        """MediaServerService.add returns False when connection test raises exception."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = MediaServerRepository(session)

                # Create a mock registry that returns a client that raises exception
                mock_registry = MagicMock(spec=ClientRegistry)
                mock_client = AsyncMock()
                mock_client.test_connection = AsyncMock(
                    side_effect=Exception("Connection failed")
                )
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_registry.create_client = MagicMock(return_value=mock_client)

                service = MediaServerService(repo, registry=mock_registry)

                # Attempt to add server - should raise ValidationError
                with pytest.raises(ValidationError) as exc_info:
                    _ = await service.add(
                        name=name,
                        server_type=server_type,
                        url=url,
                        api_key=api_key,
                    )

                # Verify error details
                assert exc_info.value.error_code == "VALIDATION_ERROR"

                # Verify server was NOT persisted
                all_servers = await repo.get_all()
                assert len(all_servers) == 0
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        new_url=url_strategy,
        new_api_key=name_strategy,
    )
    @pytest.mark.asyncio
    async def test_update_server_validates_when_credentials_change(
        self,
        new_url: str,
        new_api_key: str,
    ) -> None:
        """MediaServerService.update validates connection when url or api_key changes."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = MediaServerRepository(session)

                # Create a mock registry
                mock_registry = MagicMock(spec=ClientRegistry)
                mock_client = AsyncMock()
                # First call succeeds (for initial add), second fails (for update)
                mock_client.test_connection = AsyncMock(side_effect=[True, False])
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_registry.create_client = MagicMock(return_value=mock_client)

                service = MediaServerService(repo, registry=mock_registry)

                # First add a server successfully
                created = await service.add(
                    name="Test Server",
                    server_type=ServerType.JELLYFIN,
                    url="http://original.local",
                    api_key="originalkey",
                )
                await session.commit()

                # Now try to update with new credentials - should fail validation
                with pytest.raises(ValidationError) as exc_info:
                    _ = await service.update(
                        created.id,
                        url=new_url,
                        api_key=new_api_key,
                    )

                assert exc_info.value.error_code == "VALIDATION_ERROR"

                # Verify original server data is unchanged
                retrieved = await repo.get_by_id(created.id)
                assert retrieved is not None
                assert retrieved.url == "http://original.local"
                assert retrieved.api_key == "originalkey"
        finally:
            await engine.dispose()


class TestInvitationValidationChecksAllConditions:
    """
    Feature: zondarr-foundation
    Property 11: Invitation Validation Checks All Conditions

    *For any* invitation redemption attempt, the InvitationService SHALL check:
    (1) enabled status, (2) expiration time, (3) use count vs max_uses.
    If any check fails, it SHALL return a specific error indicating which
    condition failed.

    **Validates: Requirements 6.5, 6.6**
    """

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(code=code_strategy)
    @pytest.mark.asyncio
    async def test_redeem_fails_for_disabled_invitation(self, code: str) -> None:
        """InvitationService.redeem fails with DISABLED for disabled invitations."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = InvitationRepository(session)
                service = InvitationService(repo)

                # Create a disabled invitation
                invitation = Invitation()
                invitation.code = code
                invitation.enabled = False  # Disabled
                invitation.expires_at = None
                invitation.max_uses = None
                invitation.use_count = 0
                _ = await repo.create(invitation)
                await session.commit()

                # Attempt to redeem - should fail with DISABLED
                with pytest.raises(ValidationError) as exc_info:
                    _ = await service.redeem(code)

                assert "disabled" in exc_info.value.message.lower()
                assert "code" in exc_info.value.field_errors
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(code=code_strategy)
    @pytest.mark.asyncio
    async def test_redeem_fails_for_expired_invitation(self, code: str) -> None:
        """InvitationService.redeem fails with EXPIRED for expired invitations."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = InvitationRepository(session)
                service = InvitationService(repo)

                # Create an expired invitation
                invitation = Invitation()
                invitation.code = code
                invitation.enabled = True
                invitation.expires_at = datetime.now(UTC) - timedelta(days=1)  # Expired
                invitation.max_uses = None
                invitation.use_count = 0
                _ = await repo.create(invitation)
                await session.commit()

                # Attempt to redeem - should fail with EXPIRED
                with pytest.raises(ValidationError) as exc_info:
                    _ = await service.redeem(code)

                assert "expired" in exc_info.value.message.lower()
                assert "code" in exc_info.value.field_errors
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        code=code_strategy,
        max_uses=st.integers(min_value=1, max_value=100),
    )
    @pytest.mark.asyncio
    async def test_redeem_fails_for_exhausted_invitation(
        self, code: str, max_uses: int
    ) -> None:
        """InvitationService.redeem fails with MAX_USES_REACHED for exhausted invitations."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = InvitationRepository(session)
                service = InvitationService(repo)

                # Create an exhausted invitation (use_count >= max_uses)
                invitation = Invitation()
                invitation.code = code
                invitation.enabled = True
                invitation.expires_at = None
                invitation.max_uses = max_uses
                invitation.use_count = max_uses  # Already at max
                _ = await repo.create(invitation)
                await session.commit()

                # Attempt to redeem - should fail with MAX_USES_REACHED
                with pytest.raises(ValidationError) as exc_info:
                    _ = await service.redeem(code)

                assert "max" in exc_info.value.message.lower()
                assert "code" in exc_info.value.field_errors
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(code=code_strategy)
    @pytest.mark.asyncio
    async def test_redeem_fails_for_nonexistent_invitation(self, code: str) -> None:
        """InvitationService.redeem fails with NOT_FOUND for nonexistent invitations."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = InvitationRepository(session)
                service = InvitationService(repo)

                # Attempt to redeem nonexistent code - should fail with NotFoundError
                with pytest.raises(NotFoundError) as exc_info:
                    _ = await service.redeem(code)

                assert exc_info.value.error_code == "NOT_FOUND"
                assert exc_info.value.context["resource_type"] == "Invitation"
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(code=code_strategy)
    @pytest.mark.asyncio
    async def test_redeem_succeeds_for_valid_invitation(self, code: str) -> None:
        """InvitationService.redeem succeeds and increments use_count for valid invitations."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = InvitationRepository(session)
                service = InvitationService(repo)

                # Create a valid invitation
                invitation = Invitation()
                invitation.code = code
                invitation.enabled = True
                invitation.expires_at = datetime.now(UTC) + timedelta(days=7)  # Future
                invitation.max_uses = 10
                invitation.use_count = 0
                _ = await repo.create(invitation)
                await session.commit()

                # Redeem - should succeed
                redeemed = await service.redeem(code)
                await session.commit()

                # Verify use_count was incremented
                assert redeemed.use_count == 1
                assert redeemed.code == code

                # Verify in database
                retrieved = await repo.get_by_code(code)
                assert retrieved is not None
                assert retrieved.use_count == 1
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(code=code_strategy)
    @pytest.mark.asyncio
    async def test_validate_returns_correct_failure_reason(self, code: str) -> None:
        """InvitationService.validate returns specific failure reasons."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = InvitationRepository(session)
                service = InvitationService(repo)

                # Test NOT_FOUND
                is_valid, reason = await service.validate(code)
                assert is_valid is False
                assert reason == InvitationValidationFailure.NOT_FOUND

                # Create disabled invitation
                invitation = Invitation()
                invitation.code = code
                invitation.enabled = False
                invitation.expires_at = None
                invitation.max_uses = None
                invitation.use_count = 0
                _ = await repo.create(invitation)
                await session.commit()

                # Test DISABLED
                is_valid, reason = await service.validate(code)
                assert is_valid is False
                assert reason == InvitationValidationFailure.DISABLED
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(code=code_strategy)
    @pytest.mark.asyncio
    async def test_validation_checks_in_order(self, code: str) -> None:
        """InvitationService checks enabled, then expiration, then max_uses."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = InvitationRepository(session)
                service = InvitationService(repo)

                # Create invitation that fails all checks
                invitation = Invitation()
                invitation.code = code
                invitation.enabled = False  # Fails first check
                invitation.expires_at = datetime.now(UTC) - timedelta(days=1)  # Expired
                invitation.max_uses = 1
                invitation.use_count = 1  # Exhausted
                _ = await repo.create(invitation)
                await session.commit()

                # Should fail with DISABLED (first check)
                is_valid, reason = await service.validate(code)
                assert is_valid is False
                assert reason == InvitationValidationFailure.DISABLED

                # Enable it - should now fail with EXPIRED
                invitation.enabled = True
                await session.commit()

                is_valid, reason = await service.validate(code)
                assert is_valid is False
                assert reason == InvitationValidationFailure.EXPIRED

                # Fix expiration - should now fail with MAX_USES_REACHED
                invitation.expires_at = datetime.now(UTC) + timedelta(days=1)
                await session.commit()

                is_valid, reason = await service.validate(code)
                assert is_valid is False
                assert reason == InvitationValidationFailure.MAX_USES_REACHED

                # Fix max_uses - should now be valid
                invitation.use_count = 0
                await session.commit()

                is_valid, reason = await service.validate(code)
                assert is_valid is True
                assert reason is None
        finally:
            await engine.dispose()

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(code=code_strategy)
    @pytest.mark.asyncio
    async def test_invitation_with_no_limits_is_always_valid(self, code: str) -> None:
        """Invitation with no expiration and no max_uses is always valid when enabled."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                repo = InvitationRepository(session)
                service = InvitationService(repo)

                # Create invitation with no limits
                invitation = Invitation()
                invitation.code = code
                invitation.enabled = True
                invitation.expires_at = None  # No expiration
                invitation.max_uses = None  # No max uses
                invitation.use_count = 1000  # High use count doesn't matter
                _ = await repo.create(invitation)
                await session.commit()

                # Should be valid
                is_valid, reason = await service.validate(code)
                assert is_valid is True
                assert reason is None

                # Should be redeemable
                redeemed = await service.redeem(code)
                assert redeemed.use_count == 1001
        finally:
            await engine.dispose()
