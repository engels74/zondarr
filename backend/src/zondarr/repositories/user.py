"""UserRepository for user data access operations.

Provides specialized repository methods for User entities,
including queries by identity and media server. Extends the generic
Repository base class with User-specific functionality.
"""

from collections.abc import Sequence
from typing import override
from uuid import UUID

from sqlalchemy import select

from zondarr.core.exceptions import RepositoryError
from zondarr.models.identity import User
from zondarr.repositories.base import Repository


class UserRepository(Repository[User]):
    """Repository for User entity operations.

    Extends the generic Repository with User-specific queries
    such as filtering by identity or media server. Inherits
    get_by_id, get_all, create, and delete from the base
    Repository class.

    Attributes:
        session: The async database session for executing queries.
    """

    @property
    @override
    def _model_class(self) -> type[User]:
        """Return the User model class.

        Returns:
            The User SQLAlchemy model class.
        """
        return User

    async def get_by_identity(self, identity_id: UUID) -> Sequence[User]:
        """Retrieve all users belonging to a specific identity.

        Args:
            identity_id: The UUID of the identity to filter by.

        Returns:
            A sequence of User entities linked to the identity.

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            result = await self.session.scalars(
                select(User).where(User.identity_id == identity_id)
            )
            return result.all()
        except Exception as e:
            raise RepositoryError(
                "Failed to get users by identity",
                operation="get_by_identity",
                original=e,
            ) from e

    async def get_by_server(self, media_server_id: UUID) -> Sequence[User]:
        """Retrieve all users on a specific media server.

        Args:
            media_server_id: The UUID of the media server to filter by.

        Returns:
            A sequence of User entities on the media server.

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            result = await self.session.scalars(
                select(User).where(User.media_server_id == media_server_id)
            )
            return result.all()
        except Exception as e:
            raise RepositoryError(
                "Failed to get users by server",
                operation="get_by_server",
                original=e,
            ) from e

    async def update(self, user: User) -> User:
        """Update an existing user.

        Flushes changes to the database to persist modifications
        made to the user entity.

        Args:
            user: The user entity with updated values.

        Returns:
            The updated User entity.

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            await self.session.flush()
            return user
        except Exception as e:
            raise RepositoryError(
                "Failed to update user",
                operation="update",
                original=e,
            ) from e
