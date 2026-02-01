"""InvitationService for invitation business logic orchestration.

Provides methods to create, validate, and redeem invitations.
Implements Property 11: Invitation Validation Checks All Conditions -
for any invitation redemption attempt, the service SHALL check:
(1) enabled status, (2) expiration time, (3) use count vs max_uses.
If any check fails, it SHALL return a specific error indicating
which condition failed.
"""

import secrets
import string
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from zondarr.core.exceptions import NotFoundError, ValidationError
from zondarr.models.invitation import Invitation
from zondarr.models.media_server import Library, MediaServer
from zondarr.repositories.invitation import InvitationRepository


class InvitationValidationFailure(StrEnum):
    """Specific reasons why invitation validation can fail.

    Used to provide clear, actionable error messages to users
    attempting to redeem invitations.
    """

    DISABLED = "disabled"
    EXPIRED = "expired"
    MAX_USES_REACHED = "max_uses_reached"
    NOT_FOUND = "not_found"


class InvitationService:
    """Service for managing invitation operations.

    Orchestrates business logic for invitation management including:
    - Creating new invitations with configurable limits
    - Validating invitations before redemption
    - Redeeming invitations and tracking usage

    All redemption operations validate the invitation state before
    incrementing usage to ensure only valid invitations are redeemed.

    Attributes:
        repository: The InvitationRepository for data access.
    """

    repository: InvitationRepository

    def __init__(self, repository: InvitationRepository, /) -> None:
        """Initialize the InvitationService.

        Args:
            repository: The InvitationRepository for data access (positional-only).
        """
        self.repository = repository

    async def create(
        self,
        *,
        expires_at: datetime | None = None,
        max_uses: int | None = None,
        duration_days: int | None = None,
        target_servers: Sequence[MediaServer] | None = None,
        allowed_libraries: Sequence[Library] | None = None,
        created_by: str | None = None,
    ) -> Invitation:
        """Create a new invitation with the specified configuration.

        Generates a unique invitation code and creates an invitation
        entity with the provided settings.

        Args:
            expires_at: Optional expiration timestamp (keyword-only).
            max_uses: Optional maximum number of redemptions (keyword-only).
            duration_days: Optional duration in days for user access (keyword-only).
            target_servers: Optional list of media servers to grant access to (keyword-only).
            allowed_libraries: Optional list of specific libraries to grant access to (keyword-only).
            created_by: Optional identifier of who created the invitation (keyword-only).

        Returns:
            The created Invitation entity with generated code.

        Raises:
            RepositoryError: If the database operation fails.
        """
        # Generate a unique invitation code
        code = self._generate_code()

        # Create the invitation entity
        invitation = Invitation(
            code=code,
            expires_at=expires_at,
            max_uses=max_uses,
            duration_days=duration_days,
            created_by=created_by,
        )

        # Add target servers if provided
        if target_servers:
            invitation.target_servers = list(target_servers)

        # Add allowed libraries if provided
        if allowed_libraries:
            invitation.allowed_libraries = list(allowed_libraries)

        return await self.repository.create(invitation)

    async def validate(
        self, code: str, /
    ) -> tuple[bool, InvitationValidationFailure | None]:
        """Validate an invitation code without redeeming it.

        Checks all validation conditions:
        1. Invitation exists
        2. Invitation is enabled
        3. Invitation has not expired
        4. Invitation has not reached max uses

        Args:
            code: The invitation code to validate (positional-only).

        Returns:
            A tuple of (is_valid, failure_reason). If valid, failure_reason is None.
            If invalid, failure_reason indicates which condition failed.

        Raises:
            RepositoryError: If the database operation fails.
        """
        invitation = await self.repository.get_by_code(code)

        if invitation is None:
            return False, InvitationValidationFailure.NOT_FOUND

        return self._check_invitation_validity(invitation)

    async def redeem(self, code: str, /) -> Invitation:
        """Redeem an invitation, incrementing its use count.

        Validates the invitation and increments the use count if valid.
        This is the primary method for processing invitation redemptions.

        Implements Property 11: Invitation Validation Checks All Conditions.

        Args:
            code: The invitation code to redeem (positional-only).

        Returns:
            The redeemed Invitation with updated use_count.

        Raises:
            NotFoundError: If the invitation does not exist.
            ValidationError: If the invitation is invalid (disabled, expired, or exhausted).
            RepositoryError: If the database operation fails.
        """
        invitation = await self.repository.get_by_code(code)

        if invitation is None:
            raise NotFoundError("Invitation", code)

        # Check all validation conditions (Property 11)
        is_valid, failure_reason = self._check_invitation_validity(invitation)

        if not is_valid:
            error_messages = self._get_validation_error_messages(failure_reason)
            raise ValidationError(
                f"Invitation cannot be redeemed: {failure_reason}",
                field_errors=error_messages,
            )

        # Increment use count
        return await self.repository.increment_use_count(invitation)

    async def get_by_id(self, invitation_id: UUID, /) -> Invitation:
        """Retrieve an invitation by ID.

        Args:
            invitation_id: The UUID of the invitation to retrieve (positional-only).

        Returns:
            The Invitation entity.

        Raises:
            NotFoundError: If the invitation does not exist.
            RepositoryError: If the database operation fails.
        """
        invitation = await self.repository.get_by_id(invitation_id)
        if invitation is None:
            raise NotFoundError("Invitation", str(invitation_id))
        return invitation

    async def get_by_code(self, code: str, /) -> Invitation:
        """Retrieve an invitation by its code.

        Args:
            code: The invitation code to look up (positional-only).

        Returns:
            The Invitation entity.

        Raises:
            NotFoundError: If the invitation does not exist.
            RepositoryError: If the database operation fails.
        """
        invitation = await self.repository.get_by_code(code)
        if invitation is None:
            raise NotFoundError("Invitation", code)
        return invitation

    async def get_all(self) -> Sequence[Invitation]:
        """Retrieve all invitations.

        Returns:
            A sequence of all Invitation entities.

        Raises:
            RepositoryError: If the database operation fails.
        """
        return await self.repository.get_all()

    async def get_active(self) -> Sequence[Invitation]:
        """Retrieve all active invitations.

        Returns invitations that are enabled, not expired, and not exhausted.

        Returns:
            A sequence of active Invitation entities.

        Raises:
            RepositoryError: If the database operation fails.
        """
        return await self.repository.get_active()

    async def disable(self, invitation_id: UUID, /) -> Invitation:
        """Disable an invitation, preventing further redemptions.

        Args:
            invitation_id: The UUID of the invitation to disable (positional-only).

        Returns:
            The disabled Invitation entity.

        Raises:
            NotFoundError: If the invitation does not exist.
            RepositoryError: If the database operation fails.
        """
        invitation = await self.repository.get_by_id(invitation_id)
        if invitation is None:
            raise NotFoundError("Invitation", str(invitation_id))

        return await self.repository.disable(invitation)

    async def calculate_user_expiration(
        self, invitation: Invitation, /
    ) -> datetime | None:
        """Calculate the expiration date for a user created from this invitation.

        If the invitation has a duration_days value, calculates the expiration
        date from the current time. Otherwise returns None (no expiration).

        Args:
            invitation: The invitation being redeemed (positional-only).

        Returns:
            The calculated expiration datetime, or None if no duration is set.
        """
        if invitation.duration_days is None:
            return None

        return datetime.now(UTC) + timedelta(days=invitation.duration_days)

    def _generate_code(self, length: int = 12) -> str:
        """Generate a unique invitation code.

        Creates a cryptographically secure random code using uppercase
        letters and digits, excluding ambiguous characters (0, O, I, L).

        Args:
            length: The length of the code to generate. Defaults to 12.

        Returns:
            A random invitation code string.
        """
        # Exclude ambiguous characters: 0, O, I, L
        alphabet = "".join(
            c for c in string.ascii_uppercase + string.digits if c not in "0OIL"
        )
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _check_invitation_validity(
        self, invitation: Invitation, /
    ) -> tuple[bool, InvitationValidationFailure | None]:
        """Check all validity conditions for an invitation.

        Implements Property 11: Invitation Validation Checks All Conditions.
        Checks in order:
        1. Enabled status
        2. Expiration time
        3. Use count vs max_uses

        Args:
            invitation: The invitation to validate (positional-only).

        Returns:
            A tuple of (is_valid, failure_reason). If valid, failure_reason is None.
        """
        # Check 1: Enabled status
        if not invitation.enabled:
            return False, InvitationValidationFailure.DISABLED

        # Check 2: Expiration time
        if invitation.expires_at is not None:
            now = datetime.now(UTC)
            if invitation.expires_at <= now:
                return False, InvitationValidationFailure.EXPIRED

        # Check 3: Use count vs max_uses
        if invitation.max_uses is not None:
            if invitation.use_count >= invitation.max_uses:
                return False, InvitationValidationFailure.MAX_USES_REACHED

        return True, None

    def _get_validation_error_messages(
        self, failure_reason: InvitationValidationFailure | None, /
    ) -> dict[str, list[str]]:
        """Get field-level error messages for a validation failure.

        Args:
            failure_reason: The reason validation failed (positional-only).

        Returns:
            A dictionary mapping field names to lists of error messages.
        """
        match failure_reason:
            case InvitationValidationFailure.DISABLED:
                return {"code": ["This invitation has been disabled"]}
            case InvitationValidationFailure.EXPIRED:
                return {"code": ["This invitation has expired"]}
            case InvitationValidationFailure.MAX_USES_REACHED:
                return {
                    "code": ["This invitation has reached its maximum number of uses"]
                }
            case InvitationValidationFailure.NOT_FOUND:
                return {"code": ["Invalid invitation code"]}
            case _:
                return {"code": ["Invitation validation failed"]}
