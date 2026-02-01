"""Plex media server client.

Provides the PlexClient class that implements the MediaClient protocol
for communicating with Plex media servers.

Uses python-plexapi (PlexAPI v4.18+) for server communication.
PlexAPI is synchronous, so operations use asyncio.to_thread() to avoid
blocking the event loop.

Uses Python 3.14 features:
- Deferred annotations (no forward reference quotes needed)
- Self type for proper return type in context manager
"""

import asyncio
from collections.abc import Sequence
from typing import Self

import structlog
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer

from zondarr.media.exceptions import MediaClientError
from zondarr.media.types import Capability, ExternalUser, LibraryInfo, PlexUserType

log: structlog.stdlib.BoundLogger = structlog.get_logger()  # pyright: ignore[reportAny]


class PlexClient:
    """Plex media server client.

    Implements the MediaClient protocol for Plex servers.
    Uses python-plexapi for server communication.

    PlexAPI is synchronous, so all operations use asyncio.to_thread()
    to run without blocking the event loop.

    Attributes:
        url: The Plex server URL.
        api_key: The API key (X-Plex-Token) for authentication.
    """

    url: str
    api_key: str
    _server: PlexServer | None
    _account: MyPlexAccount | None

    def __init__(self, *, url: str, api_key: str) -> None:
        """Initialize a PlexClient.

        Args:
            url: The Plex server URL (keyword-only).
            api_key: The API key (X-Plex-Token) for authentication (keyword-only).
        """
        self.url = url
        self.api_key = api_key
        self._server = None
        self._account = None

    @classmethod
    def capabilities(cls) -> set[Capability]:
        """Return the set of capabilities this client supports.

        Plex supports user creation, deletion, and library access
        configuration. Note that Plex does not support enable/disable
        user functionality directly.

        Returns:
            A set of Capability enum values indicating supported features.
        """
        return {
            Capability.CREATE_USER,
            Capability.DELETE_USER,
            Capability.LIBRARY_ACCESS,
        }

    async def __aenter__(self) -> Self:
        """Enter async context, establishing connection.

        Initializes the PlexServer and MyPlexAccount connections using
        asyncio.to_thread() since python-plexapi is synchronous.

        Returns:
            Self for use in async with statements.
        """

        def _connect() -> tuple[PlexServer, MyPlexAccount]:
            server = PlexServer(self.url, self.api_key)
            # plexapi lacks type stubs, myPlexAccount returns MyPlexAccount
            account: MyPlexAccount = server.myPlexAccount()  # pyright: ignore[reportUnknownVariableType]
            return server, account  # pyright: ignore[reportUnknownVariableType]

        log.info("plex_client_connecting", url=self.url)
        self._server, self._account = await asyncio.to_thread(_connect)
        log.info("plex_client_connected", url=self.url)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context, cleaning up resources.

        Releases the PlexServer and MyPlexAccount instances.

        Args:
            exc_type: The exception type if an exception was raised, None otherwise.
            exc_val: The exception instance if an exception was raised, None otherwise.
            exc_tb: The traceback if an exception was raised, None otherwise.
        """
        log.info("plex_client_disconnecting", url=self.url)
        self._server = None
        self._account = None

    async def test_connection(self) -> bool:
        """Test connectivity to the Plex server.

        Verifies that the server is reachable and the API key is valid
        by querying server information via python-plexapi.

        Returns:
            True if the connection is successful and authenticated,
            False otherwise. Never raises exceptions for connection failures.
        """
        if self._server is None:
            return False

        try:

            def _query_server_info() -> str:
                # Access server friendlyName to verify connectivity
                # This requires a valid connection and token
                assert self._server is not None  # noqa: S101
                # plexapi lacks type stubs, friendlyName is str
                name: str = self._server.friendlyName  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                return name  # pyright: ignore[reportUnknownVariableType]

            server_name = await asyncio.to_thread(_query_server_info)
            log.info("plex_connection_test_success", url=self.url, server=server_name)
            return True
        except Exception as exc:
            log.warning("plex_connection_test_failed", url=self.url, error=str(exc))
            return False

    async def get_libraries(self) -> Sequence[LibraryInfo]:
        """Retrieve all libraries (sections) from the Plex server.

        Fetches the list of content libraries (movies, TV shows, music, etc.)
        available on the server via python-plexapi's library.sections().

        Maps Plex section attributes to LibraryInfo:
        - key → external_id
        - title → name
        - type → library_type (movie, show, artist, photo, etc.)

        Returns:
            A sequence of LibraryInfo objects describing each library.

        Raises:
            MediaClientError: If the client is not initialized (use async context manager).
            MediaClientError: If library retrieval fails due to connection or API errors.
        """
        if self._server is None:
            raise MediaClientError(
                "Client not initialized - use async context manager",
                operation="get_libraries",
                server_url=self.url,
                cause="API client is None - __aenter__ was not called",
            )

        try:

            def _get_sections() -> list[LibraryInfo]:
                assert self._server is not None  # noqa: S101
                # plexapi lacks type stubs, sections() returns list of LibrarySection
                sections = self._server.library.sections()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                return [
                    LibraryInfo(
                        external_id=str(section.key),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                        name=section.title,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                        library_type=section.type,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                    )
                    for section in sections  # pyright: ignore[reportUnknownVariableType]
                ]

            libraries = await asyncio.to_thread(_get_sections)
            log.info(
                "plex_libraries_retrieved",
                url=self.url,
                count=len(libraries),
            )
            return libraries

        except MediaClientError:
            raise
        except Exception as exc:
            raise MediaClientError(
                f"Failed to retrieve libraries from Plex server: {exc}",
                operation="get_libraries",
                server_url=self.url,
                cause=str(exc),
            ) from exc

    async def create_user(
        self,
        _username: str,
        _password: str,
        /,
        *,
        _email: str | None = None,
        _plex_user_type: PlexUserType = PlexUserType.FRIEND,
    ) -> ExternalUser:
        """Create a new user on the Plex server.

        Creates a user account via Plex.tv. For Friends, sends an invitation
        to an existing Plex.tv account. For Home Users, creates a managed
        user within the Plex Home.

        Note: The password parameter is ignored for Plex since authentication
        is handled through Plex.tv accounts or managed Home Users.

        Args:
            _username: The username for the new account (positional-only).
            _password: Ignored for Plex (positional-only).
            _email: Email address for Friend invitations (keyword-only).
            _plex_user_type: Type of user to create - FRIEND or HOME (keyword-only).

        Returns:
            An ExternalUser object with the created user's details.

        Raises:
            MediaClientError: If the client is not initialized.
            MediaClientError: If user_type is FRIEND but no email is provided.
            MediaClientError: If the user already exists.
            MediaClientError: If user creation fails for other reasons.
        """
        # Stub - will be implemented in task 4
        raise NotImplementedError("Plex create_user implementation in task 4")

    async def delete_user(self, _external_user_id: str, /) -> bool:
        """Delete a user from the Plex server.

        Removes the user account identified by the external user ID.
        For Friends, uses removeFriend(). For Home Users, uses the
        appropriate removal method.

        Args:
            _external_user_id: The user's unique identifier on the server
                (positional-only).

        Returns:
            True if the user was successfully deleted, False if the user
            was not found.

        Raises:
            MediaClientError: If the client is not initialized.
            MediaClientError: If deletion fails for reasons other than user not found.
        """
        # Stub - will be implemented in task 5
        raise NotImplementedError("Plex delete_user implementation in task 5")

    async def set_user_enabled(
        self,
        _external_user_id: str,
        /,
        *,
        _enabled: bool,
    ) -> bool:
        """Enable or disable a user on the Plex server.

        Note: Plex does not support enable/disable functionality.
        This method always returns False and logs a warning.

        Args:
            _external_user_id: The user's unique identifier on the server
                (positional-only).
            _enabled: Whether the user should be enabled (keyword-only).

        Returns:
            False always - Plex does not support this operation.
        """
        # Stub - will be implemented in task 5
        raise NotImplementedError("Plex set_user_enabled implementation in task 5")

    async def set_library_access(
        self,
        _external_user_id: str,
        _library_ids: Sequence[str],
        /,
    ) -> bool:
        """Set which libraries a user can access on the Plex server.

        Configures the user's library permissions via updateFriend()
        for Friends or appropriate method for Home Users.

        Args:
            _external_user_id: The user's unique identifier on the server
                (positional-only).
            _library_ids: Sequence of library section keys to grant access to
                (positional-only). An empty sequence revokes all access.

        Returns:
            True if permissions were successfully updated, False if the user
            was not found.

        Raises:
            MediaClientError: If the client is not initialized.
            MediaClientError: If the library access update fails for reasons
                other than user not found.
        """
        # Stub - will be implemented in task 5
        raise NotImplementedError("Plex set_library_access implementation in task 5")

    async def update_permissions(
        self,
        _external_user_id: str,
        /,
        *,
        _permissions: dict[str, bool],
    ) -> bool:
        """Update user permissions on the Plex server.

        Maps universal permissions to Plex-specific settings where applicable.
        Currently supports can_download → allowSync mapping.

        Args:
            _external_user_id: The user's unique identifier on the server
                (positional-only).
            _permissions: Dictionary mapping universal permission names to boolean
                values (keyword-only). Only provided keys are updated.

        Returns:
            True if permissions were successfully updated, False if the user
            was not found.

        Raises:
            MediaClientError: If the client is not initialized.
            MediaClientError: If the permission update fails for reasons
                other than user not found.
        """
        # Stub - will be implemented in task 5
        raise NotImplementedError("Plex update_permissions implementation in task 5")

    async def list_users(self) -> Sequence[ExternalUser]:
        """List all users with access to the Plex server.

        Retrieves all Friends and Home Users from the Plex account
        and maps them to ExternalUser structs.

        Returns:
            A sequence of ExternalUser objects with external_user_id,
            username, and email (if available).

        Raises:
            MediaClientError: If the client is not initialized.
            MediaClientError: If user listing fails due to connection or API errors.
        """
        # Stub - will be implemented in task 5
        raise NotImplementedError("Plex list_users implementation in task 5")
