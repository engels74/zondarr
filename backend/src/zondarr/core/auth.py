"""JWT cookie authentication infrastructure.

Provides:
- AdminUser: Lightweight struct stored in request.user after JWT validation
- retrieve_user_handler: Verifies admin exists and is enabled
- create_jwt_auth: Factory for configured JWTCookieAuth instance
"""

from typing import Any
from uuid import UUID

import msgspec
import structlog
from litestar.connection import ASGIConnection
from litestar.security.jwt import JWTCookieAuth, Token
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from zondarr.config import Settings
from zondarr.repositories.admin import AdminAccountRepository

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)  # pyright: ignore[reportAny]

# Paths excluded from JWT auth
AUTH_EXCLUDE_PATHS = [
    "/api/auth/",
    "/api/v1/join/",
    "/api/health",
    "/health",
    "/docs",
    "/swagger",
    "/scalar",
    "/schema",
]


class AdminUser(msgspec.Struct):
    """Lightweight admin user data stored in request.user after JWT validation.

    Attributes:
        id: Admin account UUID.
        username: Admin username.
        email: Optional admin email.
        auth_method: How this admin authenticated.
    """

    id: UUID
    username: str
    email: str | None = None
    auth_method: str = "local"


async def retrieve_user_handler(
    token: Token,
    connection: ASGIConnection[Any, Any, Any, Any],
) -> AdminUser | None:
    """Retrieve and verify admin user from JWT token.

    Called by JWTCookieAuth on every authenticated request.
    Queries the database to verify the admin still exists and is enabled.

    Args:
        token: The decoded JWT token.
        connection: The ASGI connection.

    Returns:
        AdminUser if valid, None if the admin doesn't exist or is disabled.
    """
    try:
        admin_id = UUID(token.sub)
    except ValueError, TypeError:
        return None

    try:
        session_factory: async_sessionmaker[AsyncSession] = (
            connection.app.state.session_factory  # pyright: ignore[reportAny]
        )
        async with session_factory() as session:
            repo = AdminAccountRepository(session)
            admin = await repo.get_by_id(admin_id)

            if admin is None or not admin.enabled:
                return None

            return AdminUser(
                id=admin.id,
                username=admin.username,
                email=admin.email,
                auth_method=admin.auth_method.value,
            )
    except Exception:
        logger.exception("Failed to retrieve admin user from token")
        return None


def create_jwt_auth(settings: Settings) -> JWTCookieAuth[AdminUser]:
    """Create a configured JWTCookieAuth instance.

    Args:
        settings: Application settings containing secret_key.

    Returns:
        Configured JWTCookieAuth instance.
    """
    return JWTCookieAuth[AdminUser](
        retrieve_user_handler=retrieve_user_handler,
        token_secret=settings.secret_key,
        key="zondarr_access_token",
        exclude=AUTH_EXCLUDE_PATHS,
    )
