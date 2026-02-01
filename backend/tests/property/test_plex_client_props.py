"""Property-based tests for PlexClient.

Feature: plex-integration
Properties: 1, 2, 3
Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 3.2
"""

from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from zondarr.media.types import Capability

# Strategy for valid URLs
url_strategy = st.from_regex(
    r"https?://[a-z0-9.-]+:\d{1,5}",
    fullmatch=True,
).filter(lambda s: len(s) <= 100)

# Strategy for API keys (Plex tokens are typically alphanumeric)
api_key_strategy = st.text(
    alphabet=st.characters(categories=("L", "N"), whitelist_characters="-_"),
    min_size=10,
    max_size=50,
).filter(lambda s: s.strip())

# Strategy for server names
server_name_strategy = st.text(
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip())


class MockPlexServer:
    """Mock PlexServer for testing."""

    url: str
    token: str
    friendlyName: str
    library: MockLibrary

    def __init__(
        self, url: str, token: str, *, friendly_name: str = "Test Server"
    ) -> None:
        self.url = url
        self.token = token
        self.friendlyName = friendly_name
        self.library = MockLibrary()

    def myPlexAccount(self) -> MockMyPlexAccount:
        """Return a mock MyPlexAccount."""
        return MockMyPlexAccount()


class MockMyPlexAccount:
    """Mock MyPlexAccount for testing."""

    pass


class MockLibrary:
    """Mock Plex library for testing."""

    _sections: list[MockLibrarySection]

    def __init__(self) -> None:
        self._sections = []

    def sections(self) -> list[MockLibrarySection]:
        """Return mock library sections."""
        return self._sections


class MockLibrarySection:
    """Mock Plex library section for testing."""

    key: int
    title: str
    type: str

    def __init__(self, *, key: int, title: str, section_type: str) -> None:
        self.key = key
        self.title = title
        self.type = section_type


class TestContextManagerRoundTrip:
    """
    Feature: plex-integration
    Property 1: Context Manager Round-Trip

    For any PlexClient instance with valid URL and API key, entering the async
    context and then exiting should result in the client being in a clean state
    with _server and _account set to None.

    **Validates: Requirements 1.1, 1.2**
    """

    @settings(max_examples=25)
    @given(
        url=url_strategy,
        api_key=api_key_strategy,
        server_name=server_name_strategy,
    )
    @pytest.mark.asyncio
    async def test_context_manager_initializes_and_cleans_up(
        self,
        url: str,
        api_key: str,
        server_name: str,
    ) -> None:
        """Context manager initializes _server and _account on enter, cleans up on exit."""
        from zondarr.media.clients.plex import PlexClient

        # Create mock server that will be returned by PlexServer constructor
        mock_server = MockPlexServer(url, api_key, friendly_name=server_name)

        with patch("zondarr.media.clients.plex.PlexServer", return_value=mock_server):
            client = PlexClient(url=url, api_key=api_key)

            # Before entering context, _server and _account should be None
            assert client._server is None  # pyright: ignore[reportPrivateUsage]
            assert client._account is None  # pyright: ignore[reportPrivateUsage]

            # Enter context
            async with client:
                # Inside context, _server and _account should be set
                assert client._server is not None  # pyright: ignore[reportPrivateUsage]
                assert client._account is not None  # pyright: ignore[reportPrivateUsage]

            # After exiting context, _server and _account should be None
            assert client._server is None  # pyright: ignore[reportPrivateUsage]
            assert client._account is None  # pyright: ignore[reportPrivateUsage]

    @settings(max_examples=25)
    @given(
        url=url_strategy,
        api_key=api_key_strategy,
    )
    @pytest.mark.asyncio
    async def test_context_manager_returns_self(
        self,
        url: str,
        api_key: str,
    ) -> None:
        """Context manager __aenter__ returns self."""
        from zondarr.media.clients.plex import PlexClient

        mock_server = MockPlexServer(url, api_key)

        with patch("zondarr.media.clients.plex.PlexServer", return_value=mock_server):
            client = PlexClient(url=url, api_key=api_key)

            async with client as entered_client:
                assert entered_client is client

    @settings(max_examples=25)
    @given(
        url=url_strategy,
        api_key=api_key_strategy,
    )
    @pytest.mark.asyncio
    async def test_context_manager_cleans_up_on_exception(
        self,
        url: str,
        api_key: str,
    ) -> None:
        """Context manager cleans up _server and _account even when exception occurs."""
        from zondarr.media.clients.plex import PlexClient

        mock_server = MockPlexServer(url, api_key)

        with patch("zondarr.media.clients.plex.PlexServer", return_value=mock_server):
            client = PlexClient(url=url, api_key=api_key)

            with pytest.raises(ValueError, match="test exception"):
                async with client:
                    assert client._server is not None  # pyright: ignore[reportPrivateUsage]
                    raise ValueError("test exception")

            # After exception, _server and _account should still be None
            assert client._server is None  # pyright: ignore[reportPrivateUsage]
            assert client._account is None  # pyright: ignore[reportPrivateUsage]


class TestCapabilitiesDeclaration:
    """
    Feature: plex-integration
    Property: Capabilities Declaration

    PlexClient declares CREATE_USER, DELETE_USER, and LIBRARY_ACCESS capabilities.
    It does NOT declare ENABLE_DISABLE_USER or DOWNLOAD_PERMISSION.

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
    """

    def test_capabilities_includes_create_user(self) -> None:
        """PlexClient declares CREATE_USER capability."""
        from zondarr.media.clients.plex import PlexClient

        capabilities = PlexClient.capabilities()
        assert Capability.CREATE_USER in capabilities

    def test_capabilities_includes_delete_user(self) -> None:
        """PlexClient declares DELETE_USER capability."""
        from zondarr.media.clients.plex import PlexClient

        capabilities = PlexClient.capabilities()
        assert Capability.DELETE_USER in capabilities

    def test_capabilities_includes_library_access(self) -> None:
        """PlexClient declares LIBRARY_ACCESS capability."""
        from zondarr.media.clients.plex import PlexClient

        capabilities = PlexClient.capabilities()
        assert Capability.LIBRARY_ACCESS in capabilities

    def test_capabilities_excludes_enable_disable_user(self) -> None:
        """PlexClient does NOT declare ENABLE_DISABLE_USER capability."""
        from zondarr.media.clients.plex import PlexClient

        capabilities = PlexClient.capabilities()
        assert Capability.ENABLE_DISABLE_USER not in capabilities

    def test_capabilities_excludes_download_permission(self) -> None:
        """PlexClient does NOT declare DOWNLOAD_PERMISSION capability."""
        from zondarr.media.clients.plex import PlexClient

        capabilities = PlexClient.capabilities()
        assert Capability.DOWNLOAD_PERMISSION not in capabilities

    def test_capabilities_returns_exactly_three(self) -> None:
        """PlexClient declares exactly 3 capabilities."""
        from zondarr.media.clients.plex import PlexClient

        capabilities = PlexClient.capabilities()
        assert len(capabilities) == 3


class MockPlexServerWithError:
    """Mock PlexServer that raises an error when friendlyName is accessed."""

    url: str
    token: str
    library: MockLibrary
    _error: Exception

    def __init__(self, url: str, token: str, *, error: Exception) -> None:
        self.url = url
        self.token = token
        self.library = MockLibrary()
        self._error = error

    @property
    def friendlyName(self) -> str:
        """Raise the configured error."""
        raise self._error

    def myPlexAccount(self) -> MockMyPlexAccount:
        """Return a mock MyPlexAccount."""
        return MockMyPlexAccount()


class TestConnectionTestReturnValues:
    """
    Feature: plex-integration
    Property 2: Connection Test Return Value Correctness

    For any PlexClient instance, test_connection() should return True if and only
    if the server is reachable and the token is valid; otherwise it should return
    False without raising an exception.

    **Validates: Requirements 1.3, 1.4, 1.5**
    """

    @settings(max_examples=25)
    @given(
        url=url_strategy,
        api_key=api_key_strategy,
        server_name=server_name_strategy,
    )
    @pytest.mark.asyncio
    async def test_connection_returns_true_on_success(
        self,
        url: str,
        api_key: str,
        server_name: str,
    ) -> None:
        """test_connection returns True when server is reachable and token is valid."""
        from zondarr.media.clients.plex import PlexClient

        mock_server = MockPlexServer(url, api_key, friendly_name=server_name)

        with patch("zondarr.media.clients.plex.PlexServer", return_value=mock_server):
            client = PlexClient(url=url, api_key=api_key)

            async with client:
                result = await client.test_connection()
                assert result is True

    @settings(max_examples=25)
    @given(
        url=url_strategy,
        api_key=api_key_strategy,
    )
    @pytest.mark.asyncio
    async def test_connection_returns_false_when_not_initialized(
        self,
        url: str,
        api_key: str,
    ) -> None:
        """test_connection returns False when client is not initialized (outside context)."""
        from zondarr.media.clients.plex import PlexClient

        client = PlexClient(url=url, api_key=api_key)

        # Without entering context, _server is None
        result = await client.test_connection()
        assert result is False

    @settings(max_examples=25)
    @given(
        url=url_strategy,
        api_key=api_key_strategy,
        error_message=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
    )
    @pytest.mark.asyncio
    async def test_connection_returns_false_on_exception(
        self,
        url: str,
        api_key: str,
        error_message: str,
    ) -> None:
        """test_connection returns False (not raises) when server query fails."""
        from zondarr.media.clients.plex import PlexClient

        # Create a mock server that raises an exception when friendlyName is accessed
        mock_server = MockPlexServerWithError(
            url, api_key, error=ConnectionError(error_message)
        )

        with patch("zondarr.media.clients.plex.PlexServer", return_value=mock_server):
            client = PlexClient(url=url, api_key=api_key)

            async with client:
                # Should return False, not raise
                result = await client.test_connection()
                assert result is False

    @settings(max_examples=25)
    @given(
        url=url_strategy,
        api_key=api_key_strategy,
    )
    @pytest.mark.asyncio
    async def test_connection_never_raises_exception(
        self,
        url: str,
        api_key: str,
    ) -> None:
        """test_connection never raises exceptions, always returns bool."""
        from zondarr.media.clients.plex import PlexClient

        # Create a mock server that raises a RuntimeError
        mock_server = MockPlexServerWithError(
            url, api_key, error=RuntimeError("Server error")
        )

        with patch("zondarr.media.clients.plex.PlexServer", return_value=mock_server):
            client = PlexClient(url=url, api_key=api_key)

            async with client:
                # Should not raise, should return False
                result = await client.test_connection()
                assert isinstance(result, bool)
                assert result is False


# Valid Plex library types
VALID_PLEX_LIBRARY_TYPES = [
    "movie",
    "show",
    "artist",
    "photo",
]

# Strategy for library section keys (positive integers)
section_key_strategy = st.integers(min_value=1, max_value=10000)

# Strategy for library titles
library_title_strategy = st.text(
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip())

# Strategy for library types
library_type_strategy = st.sampled_from(VALID_PLEX_LIBRARY_TYPES)


class TestLibraryRetrievalProducesValidStructs:
    """
    Feature: plex-integration
    Property 3: Library Retrieval Produces Valid Structs

    For any connected PlexClient with accessible libraries, get_libraries()
    should return a sequence where each element is a valid LibraryInfo with
    non-empty external_id, name, and library_type fields.

    **Validates: Requirements 3.1, 3.2**
    """

    @settings(max_examples=25)
    @given(
        url=url_strategy,
        api_key=api_key_strategy,
        sections=st.lists(
            st.tuples(
                section_key_strategy, library_title_strategy, library_type_strategy
            ),
            min_size=0,
            max_size=10,
        ),
    )
    @pytest.mark.asyncio
    async def test_get_libraries_returns_valid_library_info(
        self,
        url: str,
        api_key: str,
        sections: list[tuple[int, str, str]],
    ) -> None:
        """get_libraries returns valid LibraryInfo structs for each section."""
        from zondarr.media.clients.plex import PlexClient
        from zondarr.media.types import LibraryInfo

        mock_server = MockPlexServer(url, api_key)
        mock_server.library._sections = [  # pyright: ignore[reportPrivateUsage]
            MockLibrarySection(key=key, title=title, section_type=lib_type)
            for key, title, lib_type in sections
        ]

        with patch("zondarr.media.clients.plex.PlexServer", return_value=mock_server):
            client = PlexClient(url=url, api_key=api_key)

            async with client:
                libraries = await client.get_libraries()

                # Should return same number of libraries as sections
                assert len(libraries) == len(sections)

                # Each library should be a valid LibraryInfo
                for lib in libraries:
                    assert isinstance(lib, LibraryInfo)
                    assert lib.external_id  # non-empty
                    assert lib.name  # non-empty
                    assert lib.library_type  # non-empty

    @settings(max_examples=25)
    @given(
        url=url_strategy,
        api_key=api_key_strategy,
        key=section_key_strategy,
        title=library_title_strategy,
        lib_type=library_type_strategy,
    )
    @pytest.mark.asyncio
    async def test_get_libraries_maps_fields_correctly(
        self,
        url: str,
        api_key: str,
        key: int,
        title: str,
        lib_type: str,
    ) -> None:
        """get_libraries maps section key→external_id, title→name, type→library_type."""
        from zondarr.media.clients.plex import PlexClient

        mock_server = MockPlexServer(url, api_key)
        mock_server.library._sections = [  # pyright: ignore[reportPrivateUsage]
            MockLibrarySection(key=key, title=title, section_type=lib_type)
        ]

        with patch("zondarr.media.clients.plex.PlexServer", return_value=mock_server):
            client = PlexClient(url=url, api_key=api_key)

            async with client:
                libraries = await client.get_libraries()

                assert len(libraries) == 1
                lib = libraries[0]
                assert lib.external_id == str(key)
                assert lib.name == title
                assert lib.library_type == lib_type

    @settings(max_examples=25)
    @given(
        url=url_strategy,
        api_key=api_key_strategy,
    )
    @pytest.mark.asyncio
    async def test_get_libraries_returns_empty_for_no_sections(
        self,
        url: str,
        api_key: str,
    ) -> None:
        """get_libraries returns empty sequence when server has no sections."""
        from zondarr.media.clients.plex import PlexClient

        mock_server = MockPlexServer(url, api_key)
        mock_server.library._sections = []  # pyright: ignore[reportPrivateUsage]

        with patch("zondarr.media.clients.plex.PlexServer", return_value=mock_server):
            client = PlexClient(url=url, api_key=api_key)

            async with client:
                libraries = await client.get_libraries()
                assert len(libraries) == 0

    @settings(max_examples=25)
    @given(
        url=url_strategy,
        api_key=api_key_strategy,
    )
    @pytest.mark.asyncio
    async def test_get_libraries_raises_when_not_initialized(
        self,
        url: str,
        api_key: str,
    ) -> None:
        """get_libraries raises MediaClientError when client is not initialized."""
        from zondarr.media.clients.plex import PlexClient
        from zondarr.media.exceptions import MediaClientError

        client = PlexClient(url=url, api_key=api_key)

        # Without entering context, _server is None
        with pytest.raises(MediaClientError) as exc_info:
            _ = await client.get_libraries()

        assert exc_info.value.operation == "get_libraries"
        assert exc_info.value.server_url == url
