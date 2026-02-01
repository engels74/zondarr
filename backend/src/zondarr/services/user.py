"""UserService for user and identity business logic orchestration.

Provides methods to create, manage, and delete users and identities.
Handles the relationship between local Identity/User records and
external media server accounts.

Implements Property 19: Enable/Disable Atomicity -
if the Jellyfin API call fails, the local User.enabled field
should remain unchanged.

Implements Property 20: User Deletion Atomicity -
if the Jellyfin API call fails, the local User record should still exist.

Implements Property 21: Last User Deletion Cascades to Identity -
deleting the last User for an Identity should also delete the Identity.
"""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from zondarr.core.exceptions import NotFoundError, ValidationError
from zondarr.media.exceptions import MediaClientError
from zondarr.media.registry import registry
from zondarr.media.types import ExternalUser
from zondarr.models.identity import Identity, User
from zondarr.models.media_server import MediaServer
from zondarr.repositories.identity import IdentityRepository
from zondarr.repositories.user import UserRepository


class UserService:
    """Service for managing user and identity operations.

    Orchestrates business logic for user management including:
    - Creating identities with linked users across media servers
    - Enabling/disabling users with atomicity guarantees
    - Deleting users with cascade to identity when appropriate

    All operations that modify external media servers ensure atomicity
    by only updating local records after successful external operations.

    Attributes:
        user_repository: The UserRepository for user data access.
        identity_repository: The IdentityRepository for identity data access.
    """

    user_repository: UserRepository
    identity_repository: IdentityRepository

    def __init__(
        self,
        user_repository: UserRepository,
        identity_repository: IdentityRepository,
        /,
    ) -> None:
        """Initialize the UserService.

        Args:
            user_repository: The UserRepository for user data access (positional-only).
            identity_repository: The IdentityRepository for identity data access
                (positional-only).
        """
        self.user_repository = user_repository
        self.identity_repository = identity_repository

    async def create_identity_with_users(
        self,
        *,
        display_name: str,
        email: str | None = None,
        expires_at: datetime | None = None,
        external_users: Sequence[tuple[MediaServer, ExternalUser]],
        invitation_id: UUID | None = None,
    ) -> tuple[Identity, list[User]]:
        """Create an Identity with linked User records for each media server.

        Creates a new Identity and User records for each external user account
        that was created on media servers during invitation redemption.

        Args:
            display_name: Human-readable name for the identity (keyword-only).
            email: Optional email address (keyword-only).
            expires_at: Optional expiration timestamp (keyword-only).
            external_users: Sequence of (MediaServer, ExternalUser) tuples
                representing the accounts created on each server (keyword-only).
            invitation_id: Optional UUID of the invitation that created these
                users (keyword-only).

        Returns:
            A tuple of (Identity, list of Users) created.

        Raises:
            RepositoryError: If the database operation fails.
        """
        # Create the identity
        identity = Identity(
            display_name=display_name,
            email=email,
            expires_at=expires_at,
            enabled=True,
        )
        identity = await self.identity_repository.create(identity)

        # Create user records for each external user
        users: list[User] = []
        for server, external_user in external_users:
            user = User(
                identity_id=identity.id,
                media_server_id=server.id,
                invitation_id=invitation_id,
                external_user_id=external_user.external_user_id,
                username=external_user.username,
                expires_at=expires_at,
                enabled=True,
            )
            user = await self.user_repository.create(user)
            users.append(user)

        return identity, users

    async def get_by_id(self, user_id: UUID, /) -> User:
        """Retrieve a user by ID.

        Args:
            user_id: The UUID of the user to retrieve (positional-only).

        Returns:
            The User entity.

        Raises:
            NotFoundError: If the user does not exist.
            RepositoryError: If the database operation fails.
        """
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", str(user_id))
        return user

    async def get_by_identity(self, identity_id: UUID, /) -> Sequence[User]:
        """Retrieve all users belonging to an identity.

        Args:
            identity_id: The UUID of the identity (positional-only).

        Returns:
            A sequence of User entities linked to the identity.

        Raises:
            RepositoryError: If the database operation fails.
        """
        return await self.user_repository.get_by_identity(identity_id)

    async def get_by_server(self, media_server_id: UUID, /) -> Sequence[User]:
        """Retrieve all users on a specific media server.

        Args:
            media_server_id: The UUID of the media server (positional-only).

        Returns:
            A sequence of User entities on the media server.

        Raises:
            RepositoryError: If the database operation fails.
        """
        return await self.user_repository.get_by_server(media_server_id)

    async def set_enabled(
        self,
        user_id: UUID,
        /,
        *,
        enabled: bool,
    ) -> User:
        """Enable or disable a user with atomicity guarantees.

        Updates the user's enabled status on the external media server first,
        then updates the local record only if the external operation succeeds.

        Implements Property 19: Enable/Disable Atomicity.

        Args:
            user_id: The UUID of the user to update (positional-only).
            enabled: Whether the user should be enabled (keyword-only).

        Returns:
            The updated User entity.

        Raises:
            NotFoundError: If the user does not exist.
            ValidationError: If the external media server operation fails.
            RepositoryError: If the database operation fails.
        """
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", str(user_id))

        # Update external media server first (atomicity guarantee)
        server = user.media_server
        client = registry.create_client(
            server.server_type,
            url=server.url,
            api_key=server.api_key,
        )

        try:
            async with client:
                success = await client.set_user_enabled(
                    user.external_user_id,
                    enabled=enabled,
                )
                if not success:
                    raise ValidationError(
                        f"User not found on media server: {user.external_user_id}",
                        field_errors={"user_id": ["User not found on media server"]},
                    )
        except MediaClientError as e:
            raise ValidationError(
                f"Failed to update user on media server: {e}",
                field_errors={"user_id": [str(e)]},
            ) from e

        # Only update local record after successful external operation
        user.enabled = enabled
        return await self.user_repository.update(user)

    async def delete(self, user_id: UUID, /) -> None:
        """Delete a user with atomicity and cascade guarantees.

        Deletes the user from the external media server first, then deletes
        the local record only if the external operation succeeds. If this
        is the last user for an identity, the identity is also deleted.

        Implements Property 20: User Deletion Atomicity.
        Implements Property 21: Last User Deletion Cascades to Identity.

        Args:
            user_id: The UUID of the user to delete (positional-only).

        Raises:
            NotFoundError: If the user does not exist.
            ValidationError: If the external media server operation fails.
            RepositoryError: If the database operation fails.
        """
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", str(user_id))

        identity_id = user.identity_id

        # Delete from external media server first (atomicity guarantee)
        server = user.media_server
        client = registry.create_client(
            server.server_type,
            url=server.url,
            api_key=server.api_key,
        )

        try:
            async with client:
                # delete_user returns False if user not found, which is acceptable
                _ = await client.delete_user(user.external_user_id)
        except MediaClientError as e:
            raise ValidationError(
                f"Failed to delete user from media server: {e}",
                field_errors={"user_id": [str(e)]},
            ) from e

        # Delete local user record after successful external operation
        await self.user_repository.delete(user)

        # Check if this was the last user for the identity (cascade)
        remaining_users = await self.user_repository.get_by_identity(identity_id)
        if len(remaining_users) == 0:
            identity = await self.identity_repository.get_by_id(identity_id)
            if identity is not None:
                await self.identity_repository.delete(identity)

    async def get_identity_by_id(self, identity_id: UUID, /) -> Identity:
        """Retrieve an identity by ID.

        Args:
            identity_id: The UUID of the identity to retrieve (positional-only).

        Returns:
            The Identity entity.

        Raises:
            NotFoundError: If the identity does not exist.
            RepositoryError: If the database operation fails.
        """
        identity = await self.identity_repository.get_by_id(identity_id)
        if identity is None:
            raise NotFoundError("Identity", str(identity_id))
        return identity
