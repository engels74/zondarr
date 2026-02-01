"""Generic repository base class for data access abstraction.

Provides common CRUD operations with error wrapping for all entity types.
Uses PEP 695 type parameter syntax for generic repository pattern.

All repository operations wrap database exceptions in RepositoryError
for consistent error handling across the application.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zondarr.core.exceptions import RepositoryError
from zondarr.models.base import Base


class Repository[T: Base](ABC):
    """Generic repository providing common CRUD operations.

    Uses PEP 695 type parameter syntax: class Repository[T: Base]
    T is bounded to Base model type.

    All operations wrap database exceptions in RepositoryError with
    operation context for debugging and traceability.

    Subclasses must implement the `_model_class` property to return
    the SQLAlchemy model class they manage.

    Attributes:
        session: The async database session for executing queries.
    """

    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a database session.

        Args:
            session: The async database session for executing queries.
        """
        self.session = session

    @property
    @abstractmethod
    def _model_class(self) -> type[T]:
        """Return the model class this repository manages.

        Subclasses must implement this property to return their
        specific model class.

        Returns:
            The SQLAlchemy model class.
        """
        ...

    async def get_by_id(self, id: UUID) -> T | None:
        """Retrieve an entity by its UUID primary key.

        Args:
            id: The UUID of the entity to retrieve.

        Returns:
            The entity if found, None otherwise.

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            return await self.session.get(self._model_class, id)
        except Exception as e:
            raise RepositoryError(
                f"Failed to get {self._model_class.__name__} by id",
                operation="get_by_id",
                original=e,
            ) from e

    async def get_all(self) -> Sequence[T]:
        """Retrieve all entities of this type.

        Returns:
            A sequence of all entities.

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            result = await self.session.scalars(select(self._model_class))
            return result.all()
        except Exception as e:
            raise RepositoryError(
                f"Failed to get all {self._model_class.__name__}",
                operation="get_all",
                original=e,
            ) from e

    async def create(self, entity: T) -> T:
        """Persist a new entity to the database.

        The entity is added to the session and flushed to generate
        any database-side defaults (like auto-generated IDs).

        Args:
            entity: The entity instance to persist.

        Returns:
            The persisted entity with any generated values populated.

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            self.session.add(entity)
            await self.session.flush()
            return entity
        except Exception as e:
            raise RepositoryError(
                f"Failed to create {self._model_class.__name__}",
                operation="create",
                original=e,
            ) from e

    async def delete(self, entity: T) -> None:
        """Remove an entity from the database.

        The entity is marked for deletion and the session is flushed
        to execute the delete operation.

        Args:
            entity: The entity instance to delete.

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            await self.session.delete(entity)
            await self.session.flush()
        except Exception as e:
            raise RepositoryError(
                f"Failed to delete {self._model_class.__name__}",
                operation="delete",
                original=e,
            ) from e
