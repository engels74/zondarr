"""Tests for refresh token replay prevention.

Verifies:
- RefreshTokenRepository.consume_token atomic consumption
- AuthService.consume_refresh_token with replay detection
- Concurrent consume attempts (only one wins)
- Edge cases: expired, revoked, invalid, disabled admin
"""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.conftest import create_test_engine
from zondarr.core.exceptions import AuthenticationError
from zondarr.models.admin import AdminAccount, RefreshToken
from zondarr.repositories.admin import AdminAccountRepository, RefreshTokenRepository
from zondarr.repositories.app_setting import AppSettingRepository
from zondarr.services.auth import AuthService

# =============================================================================
# Helpers
# =============================================================================


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_service(session: AsyncSession) -> AuthService:
    return AuthService(
        admin_repo=AdminAccountRepository(session),
        token_repo=RefreshTokenRepository(session),
        app_setting_repo=AppSettingRepository(session),
    )


async def _create_admin(
    session: AsyncSession,
    *,
    username: str = "testadmin",
    enabled: bool = True,
) -> AdminAccount:
    admin = AdminAccount(
        username=username,
        password_hash="fakehash",
        email=f"{username}@example.com",
        auth_method="local",
        enabled=enabled,
    )
    session.add(admin)
    await session.flush()
    return admin


async def _create_token(
    session: AsyncSession,
    admin: AdminAccount,
    *,
    token_hash: str = "",
    revoked: bool = False,
    expires_at: datetime | None = None,
) -> RefreshToken:
    if not token_hash:
        token_hash = _hash_token("default-raw-token")
    if expires_at is None:
        expires_at = datetime.now(UTC) + timedelta(days=7)
    token = RefreshToken(
        admin_account_id=admin.id,
        token_hash=token_hash,
        expires_at=expires_at,
        revoked=revoked,
    )
    session.add(token)
    await session.flush()
    return token


# =============================================================================
# Repository: consume_token
# =============================================================================


class TestConsumeToken:
    """Tests for RefreshTokenRepository.consume_token."""

    @pytest.mark.asyncio
    async def test_consume_token_success(self) -> None:
        """Valid token is consumed: returns token with revoked=True."""
        engine = await create_test_engine()
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as session:
                admin = await _create_admin(session)
                token_hash = _hash_token("raw-token-1")
                _ = await _create_token(session, admin, token_hash=token_hash)
                await session.commit()

            async with factory() as session:
                repo = RefreshTokenRepository(session)
                now = datetime.now(UTC)
                result = await repo.consume_token(token_hash, now)
                await session.commit()

                assert result is not None
                assert result.token_hash == token_hash
                assert result.revoked is True
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_consume_token_already_revoked(self) -> None:
        """Already-revoked token returns None."""
        engine = await create_test_engine()
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as session:
                admin = await _create_admin(session)
                token_hash = _hash_token("revoked-token")
                _ = await _create_token(
                    session, admin, token_hash=token_hash, revoked=True
                )
                await session.commit()

            async with factory() as session:
                repo = RefreshTokenRepository(session)
                result = await repo.consume_token(token_hash, datetime.now(UTC))
                assert result is None
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_consume_token_expired(self) -> None:
        """Expired token returns None."""
        engine = await create_test_engine()
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as session:
                admin = await _create_admin(session)
                token_hash = _hash_token("expired-token")
                past = datetime.now(UTC) - timedelta(hours=1)
                _ = await _create_token(
                    session, admin, token_hash=token_hash, expires_at=past
                )
                await session.commit()

            async with factory() as session:
                repo = RefreshTokenRepository(session)
                result = await repo.consume_token(token_hash, datetime.now(UTC))
                assert result is None
        finally:
            await engine.dispose()


# =============================================================================
# Service: consume_refresh_token
# =============================================================================


class TestConsumeRefreshToken:
    """Tests for AuthService.consume_refresh_token."""

    @pytest.mark.asyncio
    async def test_consume_refresh_token_service_success(self) -> None:
        """Full service flow: create token, consume it, get admin back."""
        engine = await create_test_engine()
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as session:
                admin = await _create_admin(session)
                service = _make_service(session)
                raw_token = await service.create_refresh_token(admin)
                await session.commit()

            async with factory() as session:
                service = _make_service(session)
                result_admin = await service.consume_refresh_token(raw_token)
                await session.commit()

                assert result_admin.id == admin.id
                assert result_admin.username == admin.username
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_consume_refresh_token_replay_revokes_all(self) -> None:
        """Replay attempt raises TOKEN_REVOKED and revokes ALL admin tokens."""
        engine = await create_test_engine()
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)

            # Create admin and two tokens
            async with factory() as session:
                admin = await _create_admin(session)
                service = _make_service(session)
                raw_token = await service.create_refresh_token(admin)
                raw_token_2 = await service.create_refresh_token(admin)
                await session.commit()

            # First consume succeeds
            async with factory() as session:
                service = _make_service(session)
                _ = await service.consume_refresh_token(raw_token)
                await session.commit()

            # Replay same token — should fail and revoke all
            async with factory() as session:
                service = _make_service(session)
                with pytest.raises(AuthenticationError, match="revoked") as exc_info:
                    _ = await service.consume_refresh_token(raw_token)
                assert exc_info.value.error_code == "TOKEN_REVOKED"
                await session.commit()

            # Verify ALL tokens for this admin are revoked (including token_2)
            async with factory() as session:
                repo = RefreshTokenRepository(session)
                token_2_hash = _hash_token(raw_token_2)
                token_2 = await repo.get_by_token_hash(token_2_hash)
                assert token_2 is not None
                assert token_2.revoked is True

                # Also verify the replayed token is still revoked
                token_1_hash = _hash_token(raw_token)
                token_1 = await repo.get_by_token_hash(token_1_hash)
                assert token_1 is not None
                assert token_1.revoked is True
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_consume_refresh_token_invalid_token(self) -> None:
        """Nonexistent token raises INVALID_TOKEN."""
        engine = await create_test_engine()
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as session:
                service = _make_service(session)
                with pytest.raises(AuthenticationError) as exc_info:
                    _ = await service.consume_refresh_token("nonexistent-token")
                assert exc_info.value.error_code == "INVALID_TOKEN"
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_consume_refresh_token_disabled_admin(self) -> None:
        """Consuming a token for a disabled admin raises ACCOUNT_DISABLED."""
        engine = await create_test_engine()
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)

            async with factory() as session:
                admin = await _create_admin(session, enabled=True)
                service = _make_service(session)
                raw_token = await service.create_refresh_token(admin)
                await session.commit()
                admin_id = admin.id

            # Disable the admin
            async with factory() as session:
                repo = AdminAccountRepository(session)
                admin = await repo.get_by_id(admin_id)
                assert admin is not None
                admin.enabled = False
                await session.commit()

            # Try to consume — should fail with ACCOUNT_DISABLED
            async with factory() as session:
                service = _make_service(session)
                with pytest.raises(AuthenticationError) as exc_info:
                    _ = await service.consume_refresh_token(raw_token)
                assert exc_info.value.error_code == "ACCOUNT_DISABLED"
        finally:
            await engine.dispose()


# =============================================================================
# Concurrency: only one consume wins
# =============================================================================


class TestConcurrentConsume:
    """Tests for concurrent token consumption."""

    @pytest.mark.asyncio
    async def test_concurrent_consume_only_one_wins(self) -> None:
        """Two sessions consuming the same token: exactly one succeeds."""
        engine = await create_test_engine()
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)

            # Create admin + token
            async with factory() as session:
                admin = await _create_admin(session)
                token_hash = _hash_token("race-token")
                _ = await _create_token(session, admin, token_hash=token_hash)
                await session.commit()

            # Open two separate sessions and try to consume the same token
            async with factory() as session_a, factory() as session_b:
                repo_a = RefreshTokenRepository(session_a)
                repo_b = RefreshTokenRepository(session_b)
                now = datetime.now(UTC)

                result_a = await repo_a.consume_token(token_hash, now)
                result_b = await repo_b.consume_token(token_hash, now)

                await session_a.commit()
                await session_b.commit()

            results = [result_a, result_b]
            successes = [r for r in results if r is not None]
            failures = [r for r in results if r is None]

            assert len(successes) == 1
            assert len(failures) == 1
            assert successes[0].revoked is True
        finally:
            await engine.dispose()
