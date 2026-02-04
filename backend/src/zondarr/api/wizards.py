"""WizardController for wizard management endpoints.

Provides REST endpoints for wizard CRUD operations:
- POST /api/v1/wizards - Create a new wizard
- GET /api/v1/wizards - List wizards with pagination
- GET /api/v1/wizards/{id} - Get wizard details with steps
- PATCH /api/v1/wizards/{id} - Update a wizard
- DELETE /api/v1/wizards/{id} - Delete a wizard
- POST /api/v1/wizards/{id}/steps - Create a step
- PATCH /api/v1/wizards/{id}/steps/{step_id} - Update a step
- DELETE /api/v1/wizards/{id}/steps/{step_id} - Delete a step
- POST /api/v1/wizards/{id}/steps/{step_id}/reorder - Reorder a step
- POST /api/v1/wizards/validate-step - Validate step completion (public)

Uses Litestar Controller pattern with dependency injection for services.
Implements Requirements 2.1-2.6, 3.1-3.5, 9.1-9.6.
"""

from collections.abc import Mapping, Sequence
from typing import Annotated
from uuid import UUID

from litestar import Controller, delete, get, patch, post
from litestar.di import Provide
from litestar.params import Parameter
from litestar.status_codes import HTTP_201_CREATED, HTTP_204_NO_CONTENT
from litestar.types import AnyCallable
from sqlalchemy.ext.asyncio import AsyncSession

from zondarr.models.wizard import Wizard, WizardStep
from zondarr.repositories.wizard import WizardRepository
from zondarr.repositories.wizard_step import WizardStepRepository
from zondarr.services.wizard import WizardService

from .schemas import (
    StepReorderRequest,
    StepValidationRequest,
    StepValidationResponse,
    WizardCreate,
    WizardDetailResponse,
    WizardListResponse,
    WizardResponse,
    WizardStepCreate,
    WizardStepResponse,
    WizardStepUpdate,
    WizardUpdate,
)


async def provide_wizard_repository(
    session: AsyncSession,
) -> WizardRepository:
    """Provide WizardRepository instance.

    Args:
        session: Database session from DI.

    Returns:
        Configured WizardRepository instance.
    """
    return WizardRepository(session)


async def provide_wizard_step_repository(
    session: AsyncSession,
) -> WizardStepRepository:
    """Provide WizardStepRepository instance.

    Args:
        session: Database session from DI.

    Returns:
        Configured WizardStepRepository instance.
    """
    return WizardStepRepository(session)


async def provide_wizard_service(
    wizard_repository: WizardRepository,
    step_repository: WizardStepRepository,
) -> WizardService:
    """Provide WizardService instance.

    Args:
        wizard_repository: WizardRepository from DI.
        step_repository: WizardStepRepository from DI.

    Returns:
        Configured WizardService instance.
    """
    return WizardService(wizard_repository, step_repository)


class WizardController(Controller):
    """Controller for wizard management endpoints.

    Provides CRUD operations for wizards and steps, plus a public
    validation endpoint for step completion verification.
    """

    path: str = "/api/v1/wizards"
    tags: Sequence[str] | None = ["Wizards"]
    dependencies: Mapping[str, Provide | AnyCallable] | None = {
        "wizard_repository": Provide(provide_wizard_repository),
        "step_repository": Provide(provide_wizard_step_repository),
        "wizard_service": Provide(provide_wizard_service),
    }

    # ==================== Wizard CRUD ====================

    @post(
        "/",
        status_code=HTTP_201_CREATED,
        summary="Create wizard",
        description="Create a new wizard with configurable settings.",
    )
    async def create_wizard(
        self,
        data: WizardCreate,
        wizard_service: WizardService,
    ) -> WizardResponse:
        """Create a new wizard.

        Args:
            data: The wizard creation request.
            wizard_service: WizardService from DI.

        Returns:
            The created wizard.

        Raises:
            ValidationError: If the name is empty.
        """
        wizard = await wizard_service.create_wizard(
            name=data.name,
            description=data.description,
            enabled=data.enabled,
        )
        return self._to_response(wizard)

    @get(
        "/",
        summary="List wizards",
        description="List wizards with pagination and filtering.",
    )
    async def list_wizards(
        self,
        wizard_service: WizardService,
        page: Annotated[
            int,
            Parameter(
                ge=1,
                description="Page number (1-indexed)",
            ),
        ] = 1,
        page_size: Annotated[
            int,
            Parameter(
                ge=1,
                le=100,
                description="Number of items per page (max 100)",
            ),
        ] = 50,
        enabled: Annotated[
            bool | None,
            Parameter(description="Filter by enabled status"),
        ] = None,
    ) -> WizardListResponse:
        """List wizards with pagination.

        Args:
            wizard_service: WizardService from DI.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            enabled: Filter by enabled status.

        Returns:
            Paginated list of wizards.
        """
        items, total = await wizard_service.list_wizards(
            page=page,
            page_size=page_size,
            enabled=enabled,
        )

        response_items = [self._to_response(wizard) for wizard in items]

        return WizardListResponse(
            items=response_items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    @get(
        "/{wizard_id:uuid}",
        summary="Get wizard details",
        description="Retrieve complete details for a wizard including all steps.",
    )
    async def get_wizard(
        self,
        wizard_id: Annotated[
            UUID,
            Parameter(description="Wizard UUID"),
        ],
        wizard_service: WizardService,
    ) -> WizardDetailResponse:
        """Get wizard details by ID.

        Args:
            wizard_id: The UUID of the wizard.
            wizard_service: WizardService from DI.

        Returns:
            Complete wizard details including steps.

        Raises:
            NotFoundError: If the wizard does not exist.
        """
        wizard = await wizard_service.get_wizard(wizard_id)
        return self._to_detail_response(wizard)

    @patch(
        "/{wizard_id:uuid}",
        summary="Update wizard",
        description="Update mutable fields of a wizard.",
    )
    async def update_wizard(
        self,
        wizard_id: Annotated[
            UUID,
            Parameter(description="Wizard UUID"),
        ],
        data: WizardUpdate,
        wizard_service: WizardService,
    ) -> WizardResponse:
        """Update a wizard.

        Args:
            wizard_id: The UUID of the wizard.
            data: The update request with fields to modify.
            wizard_service: WizardService from DI.

        Returns:
            The updated wizard.

        Raises:
            NotFoundError: If the wizard does not exist.
            ValidationError: If the name is empty.
        """
        wizard = await wizard_service.update_wizard(
            wizard_id,
            name=data.name,
            description=data.description,
            enabled=data.enabled,
        )
        return self._to_response(wizard)

    @delete(
        "/{wizard_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
        summary="Delete wizard",
        description="Delete a wizard and all its steps.",
    )
    async def delete_wizard(
        self,
        wizard_id: Annotated[
            UUID,
            Parameter(description="Wizard UUID"),
        ],
        wizard_service: WizardService,
    ) -> None:
        """Delete a wizard.

        Removes the wizard and all associated steps from the database.

        Args:
            wizard_id: The UUID of the wizard.
            wizard_service: WizardService from DI.

        Raises:
            NotFoundError: If the wizard does not exist.
        """
        await wizard_service.delete_wizard(wizard_id)

    # ==================== Step CRUD ====================

    @post(
        "/{wizard_id:uuid}/steps",
        status_code=HTTP_201_CREATED,
        summary="Create step",
        description="Create a new step in a wizard.",
    )
    async def create_step(
        self,
        wizard_id: Annotated[
            UUID,
            Parameter(description="Wizard UUID"),
        ],
        data: WizardStepCreate,
        wizard_service: WizardService,
    ) -> WizardStepResponse:
        """Create a new wizard step.

        If step_order is not provided, the step is appended to the end.

        Args:
            wizard_id: The UUID of the wizard.
            data: The step creation request.
            wizard_service: WizardService from DI.

        Returns:
            The created step.

        Raises:
            NotFoundError: If the wizard does not exist.
            ValidationError: If the interaction type or config is invalid.
        """
        step = await wizard_service.create_step(
            wizard_id,
            interaction_type=data.interaction_type,
            title=data.title,
            content_markdown=data.content_markdown,
            config=data.config,
            step_order=data.step_order,
        )
        return self._to_step_response(step)

    @patch(
        "/{wizard_id:uuid}/steps/{step_id:uuid}",
        summary="Update step",
        description="Update mutable fields of a wizard step.",
    )
    async def update_step(
        self,
        wizard_id: Annotated[
            UUID,
            Parameter(description="Wizard UUID"),
        ],
        step_id: Annotated[
            UUID,
            Parameter(description="Step UUID"),
        ],
        data: WizardStepUpdate,
        wizard_service: WizardService,
    ) -> WizardStepResponse:
        """Update a wizard step.

        Args:
            wizard_id: The UUID of the wizard.
            step_id: The UUID of the step.
            data: The update request with fields to modify.
            wizard_service: WizardService from DI.

        Returns:
            The updated step.

        Raises:
            NotFoundError: If the wizard or step does not exist.
            ValidationError: If the config is invalid.
        """
        step = await wizard_service.update_step(
            wizard_id,
            step_id,
            title=data.title,
            content_markdown=data.content_markdown,
            config=data.config,
        )
        return self._to_step_response(step)

    @delete(
        "/{wizard_id:uuid}/steps/{step_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
        summary="Delete step",
        description="Delete a wizard step and normalize remaining step orders.",
    )
    async def delete_step(
        self,
        wizard_id: Annotated[
            UUID,
            Parameter(description="Wizard UUID"),
        ],
        step_id: Annotated[
            UUID,
            Parameter(description="Step UUID"),
        ],
        wizard_service: WizardService,
    ) -> None:
        """Delete a wizard step.

        Removes the step and normalizes remaining step orders to maintain
        contiguous ordering.

        Args:
            wizard_id: The UUID of the wizard.
            step_id: The UUID of the step.
            wizard_service: WizardService from DI.

        Raises:
            NotFoundError: If the wizard or step does not exist.
        """
        await wizard_service.delete_step(wizard_id, step_id)

    @post(
        "/{wizard_id:uuid}/steps/{step_id:uuid}/reorder",
        summary="Reorder step",
        description="Move a step to a new position in the wizard.",
    )
    async def reorder_step(
        self,
        wizard_id: Annotated[
            UUID,
            Parameter(description="Wizard UUID"),
        ],
        step_id: Annotated[
            UUID,
            Parameter(description="Step UUID"),
        ],
        data: StepReorderRequest,
        wizard_service: WizardService,
    ) -> WizardStepResponse:
        """Reorder a wizard step.

        Moves the step to the new position and shifts other steps to
        maintain contiguous ordering.

        Args:
            wizard_id: The UUID of the wizard.
            step_id: The UUID of the step.
            data: The reorder request with new position.
            wizard_service: WizardService from DI.

        Returns:
            The reordered step.

        Raises:
            NotFoundError: If the wizard or step does not exist.
            ValidationError: If the new_order is invalid.
        """
        step = await wizard_service.reorder_step(wizard_id, step_id, data.new_order)
        return self._to_step_response(step)

    # ==================== Step Validation ====================

    @post(
        "/validate-step",
        summary="Validate step completion",
        description="Validate a step completion response. Public endpoint.",
        exclude_from_auth=True,
    )
    async def validate_step(
        self,
        data: StepValidationRequest,
        wizard_service: WizardService,
    ) -> StepValidationResponse:
        """Validate a step completion.

        Validates the user's response for a wizard step:
        - Click: Requires acknowledged=true
        - Timer: Requires elapsed time >= duration_seconds
        - TOS: Requires accepted=true
        - Text Input: Validates required, min_length, max_length
        - Quiz: Requires correct answer_index

        This endpoint is publicly accessible without authentication.

        Args:
            data: The validation request with step_id and response.
            wizard_service: WizardService from DI.

        Returns:
            Validation result with completion token if valid.

        Raises:
            NotFoundError: If the step does not exist.
        """
        is_valid, error, token = await wizard_service.validate_step(
            data.step_id,
            data.response,
            started_at=data.started_at,
        )

        return StepValidationResponse(
            valid=is_valid,
            completion_token=token,
            error=error,
        )

    # ==================== Response Helpers ====================

    def _to_response(self, wizard: Wizard, /) -> WizardResponse:
        """Convert a Wizard entity to WizardResponse.

        Args:
            wizard: The Wizard entity.

        Returns:
            WizardResponse without steps.
        """
        return WizardResponse(
            id=wizard.id,
            name=wizard.name,
            enabled=wizard.enabled,
            created_at=wizard.created_at,
            description=wizard.description,
            updated_at=wizard.updated_at,
        )

    def _to_detail_response(self, wizard: Wizard, /) -> WizardDetailResponse:
        """Convert a Wizard entity to WizardDetailResponse.

        Args:
            wizard: The Wizard entity with steps.

        Returns:
            WizardDetailResponse with steps.
        """
        steps = [self._to_step_response(step) for step in wizard.steps]

        return WizardDetailResponse(
            id=wizard.id,
            name=wizard.name,
            enabled=wizard.enabled,
            created_at=wizard.created_at,
            steps=steps,
            description=wizard.description,
            updated_at=wizard.updated_at,
        )

    def _to_step_response(self, step: WizardStep, /) -> WizardStepResponse:
        """Convert a WizardStep entity to WizardStepResponse.

        Args:
            step: The WizardStep entity.

        Returns:
            WizardStepResponse.
        """
        return WizardStepResponse(
            id=step.id,
            wizard_id=step.wizard_id,
            step_order=step.step_order,
            interaction_type=step.interaction_type.value,
            title=step.title,
            content_markdown=step.content_markdown,
            config=step.config,
            created_at=step.created_at,
            updated_at=step.updated_at,
        )
