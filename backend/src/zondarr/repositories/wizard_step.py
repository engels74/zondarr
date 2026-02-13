"""WizardStepRepository for wizard step data access operations.

Provides specialized repository methods for WizardStep entities,
including step reordering and auto-assignment of step order.
Extends the generic Repository base class with WizardStep-specific queries.
"""

from collections.abc import Sequence
from typing import override
from uuid import UUID

from sqlalchemy import func, select, update

from zondarr.core.exceptions import RepositoryError
from zondarr.models.wizard import WizardStep
from zondarr.repositories.base import Repository


class WizardStepRepository(Repository[WizardStep]):
    """Repository for WizardStep entity operations.

    Extends the generic Repository with WizardStep-specific queries
    such as reordering steps and auto-assignment of step order.

    Attributes:
        session: The async database session for executing queries.
    """

    @property
    @override
    def _model_class(self) -> type[WizardStep]:
        """Return the WizardStep model class.

        Returns:
            The WizardStep SQLAlchemy model class.
        """
        return WizardStep

    async def get_by_wizard_id(self, wizard_id: UUID, /) -> Sequence[WizardStep]:
        """Retrieve all steps for a wizard, ordered by step_order.

        Args:
            wizard_id: The UUID of the wizard (positional-only).

        Returns:
            A sequence of WizardStep entities ordered by step_order.

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            result = await self.session.scalars(
                select(WizardStep)
                .where(WizardStep.wizard_id == wizard_id)
                .order_by(WizardStep.step_order)
            )
            return result.all()
        except Exception as e:
            raise RepositoryError(
                "Failed to get steps by wizard_id",
                operation="get_by_wizard_id",
                original=e,
            ) from e

    async def get_max_order(self, wizard_id: UUID, /) -> int:
        """Get the maximum step_order for a wizard.

        Used for auto-assignment of step_order when creating new steps.

        Args:
            wizard_id: The UUID of the wizard (positional-only).

        Returns:
            The maximum step_order value, or -1 if no steps exist.

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            result = await self.session.scalar(
                select(func.max(WizardStep.step_order)).where(
                    WizardStep.wizard_id == wizard_id
                )
            )
            return result if result is not None else -1
        except Exception as e:
            raise RepositoryError(
                "Failed to get max step order",
                operation="get_max_order",
                original=e,
            ) from e

    async def reorder_steps(
        self, wizard_id: UUID, step_id: UUID, new_order: int, /
    ) -> None:
        """Reorder a step to a new position, maintaining contiguous ordering.

        Moves the specified step to the new position and shifts other steps
        to maintain contiguous ordering (0, 1, 2, ..., N-1).

        Args:
            wizard_id: The UUID of the wizard (positional-only).
            step_id: The UUID of the step to move (positional-only).
            new_order: The new position for the step (positional-only).

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            # Get the current step
            step = await self.session.get(WizardStep, step_id)
            if step is None or step.wizard_id != wizard_id:
                raise RepositoryError(
                    "Step not found or does not belong to wizard",
                    operation="reorder_steps",
                    original=None,
                )

            old_order = step.step_order

            if old_order == new_order:
                return  # No change needed

            # Move step out of the way to avoid unique constraint violation
            step.step_order = -1
            await self.session.flush()

            # Shift other steps to make room
            if old_order < new_order:
                # Moving down: shift steps between old and new positions up
                _ = await self.session.execute(
                    update(WizardStep)
                    .where(
                        WizardStep.wizard_id == wizard_id,
                        WizardStep.step_order > old_order,
                        WizardStep.step_order <= new_order,
                    )
                    .values(step_order=WizardStep.step_order - 1)
                )
            else:
                # Moving up: shift steps between new and old positions down
                _ = await self.session.execute(
                    update(WizardStep)
                    .where(
                        WizardStep.wizard_id == wizard_id,
                        WizardStep.step_order >= new_order,
                        WizardStep.step_order < old_order,
                    )
                    .values(step_order=WizardStep.step_order + 1)
                )

            # Set final position
            step.step_order = new_order
            await self.session.flush()
        except RepositoryError:
            raise
        except Exception as e:
            raise RepositoryError(
                "Failed to reorder steps",
                operation="reorder_steps",
                original=e,
            ) from e

    async def normalize_order(self, wizard_id: UUID, /) -> None:
        """Normalize step_order values to be contiguous starting from 0.

        Used after step deletion to maintain contiguous ordering.
        Uses a two-pass approach to avoid unique constraint violations:
        1. First, set all step_orders to negative values (temporary)
        2. Then, set them to their final contiguous values

        Args:
            wizard_id: The UUID of the wizard (positional-only).

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            # Get all steps ordered by current step_order
            steps = await self.get_by_wizard_id(wizard_id)

            if not steps:
                return

            # First pass: set all to negative values to avoid conflicts
            for index, step in enumerate(steps):
                step.step_order = -(index + 1)  # -1, -2, -3, ...

            await self.session.flush()

            # Second pass: set to final contiguous values
            for index, step in enumerate(steps):
                step.step_order = index  # 0, 1, 2, ...

            await self.session.flush()
        except RepositoryError:
            raise
        except Exception as e:
            raise RepositoryError(
                "Failed to normalize step order",
                operation="normalize_order",
                original=e,
            ) from e

    async def update(self, step: WizardStep, /) -> WizardStep:
        """Persist changes to a wizard step.

        Flushes any pending changes to the step entity to the database.

        Args:
            step: The step with updated fields (positional-only).

        Returns:
            The updated WizardStep entity.

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            await self.session.flush()
            return step
        except Exception as e:
            raise RepositoryError(
                "Failed to update wizard step",
                operation="update",
                original=e,
            ) from e
