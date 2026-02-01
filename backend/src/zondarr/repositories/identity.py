"""IdentityRepository for identity data access operations.

Provides specialized repository methods for Identity entities,
including update operations. Extends the generic Repository base
class with Identity-specific functionality.
"""

from typing import override

from zondarr.core.exceptions import RepositoryError
from zondarr.models.identity import Identity
from zondarr.repositories.base import Repository


class IdentityRepository(Repository[Identity]):
    """Repository for Identity entity operations.

    Extends the generic Repository with Identity-specific operations
    such as update. Inherits get_by_id, get_all, create, and delete
    from the base Repository class.

    Attributes:
        session: The async database session for executing queries.
    """

    @property
    @override
    def _model_class(self) -> type[Identity]:
        """Return the Identity model class.

        Returns:
            The Identity SQLAlchemy model class.
        """
        return Identity

    async def update(self, identity: Identity) -> Identity:
        """Update an existing identity.

        Flushes changes to the database to persist modifications
        made to the identity entity.

        Args:
            identity: The identity entity with updated values.

        Returns:
            The updated Identity entity.

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            await self.session.flush()
            return identity
        except Exception as e:
            raise RepositoryError(
                "Failed to update identity",
                operation="update",
                original=e,
            ) from e
