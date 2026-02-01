"""Base model and mixins for SQLAlchemy 2.0 async models.

Provides:
- Base: DeclarativeBase for all models
- TimestampMixin: created_at and updated_at timestamps with timezone-aware UTC
- UUIDPrimaryKeyMixin: UUID primary key generation

Uses SQLAlchemy 2.0 patterns with mapped_column and Mapped types.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base model for all SQLAlchemy models.

    All models should inherit from this class to share the same metadata
    and registry.
    """


class TimestampMixin:
    """Mixin providing created_at and updated_at timestamps.

    Uses timezone-aware UTC datetimes for consistency across deployments.
    The created_at field is set automatically on insert.
    The updated_at field is set automatically on update.
    """

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None,
        onupdate=lambda: datetime.now(UTC),
    )


class UUIDPrimaryKeyMixin:
    """Mixin providing UUID primary key.

    Generates a new UUID4 for each entity on creation.
    """

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
