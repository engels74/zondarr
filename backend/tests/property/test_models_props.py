"""Property-based tests for model serialization.

Feature: zondarr-foundation
Property: 3
Validates: Requirements 2.7
"""

from datetime import UTC, datetime
from uuid import UUID

import msgspec
from hypothesis import given, settings
from hypothesis import strategies as st

from zondarr.models import (
    Identity,
    Invitation,
    Library,
    MediaServer,
    ServerType,
    User,
)

# Type alias for serialized model data
type SerializedData = dict[str, str | int | bool | None]

# Custom strategies for model fields
uuid_strategy = st.uuids()
datetime_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
    timezones=st.just(UTC),
)
optional_datetime_strategy = st.one_of(st.none(), datetime_strategy)
server_type_strategy = st.sampled_from([ServerType.JELLYFIN, ServerType.PLEX])
name_strategy = st.text(
    alphabet=st.characters(categories=("L", "N", "P", "S")),
    min_size=1,
    max_size=100,
).filter(lambda x: x.strip())
url_strategy = st.from_regex(r"https?://[a-z0-9.-]+\.[a-z]{2,}", fullmatch=True)
email_strategy = st.from_regex(r"[a-z0-9]+@[a-z0-9]+\.[a-z]{2,}", fullmatch=True)
code_strategy = st.text(
    alphabet=st.characters(categories=("L", "N")),
    min_size=6,
    max_size=20,
)
positive_int_strategy = st.integers(min_value=0, max_value=1000)
optional_positive_int_strategy = st.one_of(st.none(), positive_int_strategy)


def model_to_dict(model: object) -> SerializedData:
    """Convert a SQLAlchemy model to a dictionary for serialization.

    Converts UUIDs to strings and datetimes to ISO format as per Requirement 2.7.
    """
    result: SerializedData = {}
    for key in dir(model):
        if key.startswith("_") or key in ("metadata", "registry"):
            continue
        try:
            value = getattr(model, key)  # pyright: ignore[reportAny]
            if callable(value):  # pyright: ignore[reportAny]
                continue
            if isinstance(value, UUID):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, ServerType):
                result[key] = value.value
            elif isinstance(value, list):
                # Skip relationship collections for basic serialization test
                continue
            elif isinstance(value, (str, int, bool)) or value is None:
                result[key] = value
        except (AttributeError, TypeError):
            # Skip attributes that can't be accessed or have incompatible types
            continue
    return result


def decode_json(json_bytes: bytes) -> SerializedData:
    """Decode JSON bytes to SerializedData with proper typing."""
    result = msgspec.json.decode(json_bytes)  # pyright: ignore[reportAny]
    if not isinstance(result, dict):
        msg = "Expected dict from JSON decode"
        raise TypeError(msg)
    # Cast to SerializedData - we know the structure from our encoding
    return dict(result)  # pyright: ignore[reportUnknownArgumentType]


class TestModelSerializationRoundTrip:
    """
    Feature: zondarr-foundation
    Property 3: Model Serialization Round-Trip

    *For any* valid database model instance (MediaServer, Library, Invitation,
    Identity, User), serializing to JSON and deserializing back SHALL produce
    an equivalent object with UUIDs as strings and datetimes in ISO format.

    **Validates: Requirements 2.7**
    """

    @settings(max_examples=100)
    @given(
        id=uuid_strategy,
        name=name_strategy,
        server_type=server_type_strategy,
        url=url_strategy,
        api_key=name_strategy,
        enabled=st.booleans(),
        created_at=datetime_strategy,
        updated_at=optional_datetime_strategy,
    )
    def test_media_server_serialization_round_trip(
        self,
        id: UUID,
        name: str,
        server_type: ServerType,
        url: str,
        api_key: str,
        enabled: bool,
        created_at: datetime,
        updated_at: datetime | None,
    ) -> None:
        """MediaServer serializes with UUIDs as strings and datetimes as ISO."""
        # Create model instance
        server = MediaServer()
        server.id = id
        server.name = name
        server.server_type = server_type
        server.url = url
        server.api_key = api_key
        server.enabled = enabled
        server.created_at = created_at
        server.updated_at = updated_at

        # Serialize to dict
        data = model_to_dict(server)

        # Verify UUID is serialized as string
        assert isinstance(data["id"], str)
        assert data["id"] == str(id)

        # Verify datetime is serialized as ISO format string
        assert isinstance(data["created_at"], str)
        assert data["created_at"] == created_at.isoformat()

        if updated_at is not None:
            assert isinstance(data["updated_at"], str)
            assert data["updated_at"] == updated_at.isoformat()

        # Verify server_type is serialized as string value
        assert isinstance(data["server_type"], str)
        assert data["server_type"] == server_type.value

        # Serialize to JSON and back
        json_bytes = msgspec.json.encode(data)
        decoded = decode_json(json_bytes)

        # Verify round-trip preserves values
        assert decoded["id"] == str(id)
        assert decoded["name"] == name
        assert decoded["server_type"] == server_type.value
        assert decoded["url"] == url
        assert decoded["api_key"] == api_key
        assert decoded["enabled"] == enabled
        assert decoded["created_at"] == created_at.isoformat()

    @settings(max_examples=100)
    @given(
        id=uuid_strategy,
        media_server_id=uuid_strategy,
        external_id=name_strategy,
        name=name_strategy,
        library_type=st.sampled_from(["movies", "tvshows", "music", "photos"]),
        created_at=datetime_strategy,
        updated_at=optional_datetime_strategy,
    )
    def test_library_serialization_round_trip(
        self,
        id: UUID,
        media_server_id: UUID,
        external_id: str,
        name: str,
        library_type: str,
        created_at: datetime,
        updated_at: datetime | None,
    ) -> None:
        """Library serializes with UUIDs as strings and datetimes as ISO."""
        # Create model instance
        library = Library()
        library.id = id
        library.media_server_id = media_server_id
        library.external_id = external_id
        library.name = name
        library.library_type = library_type
        library.created_at = created_at
        library.updated_at = updated_at

        # Serialize to dict
        data = model_to_dict(library)

        # Verify UUIDs are serialized as strings
        assert isinstance(data["id"], str)
        assert data["id"] == str(id)
        assert isinstance(data["media_server_id"], str)
        assert data["media_server_id"] == str(media_server_id)

        # Verify datetime is serialized as ISO format string
        assert isinstance(data["created_at"], str)
        assert data["created_at"] == created_at.isoformat()

        # Serialize to JSON and back
        json_bytes = msgspec.json.encode(data)
        decoded = decode_json(json_bytes)

        # Verify round-trip preserves values
        assert decoded["id"] == str(id)
        assert decoded["media_server_id"] == str(media_server_id)
        assert decoded["external_id"] == external_id
        assert decoded["name"] == name
        assert decoded["library_type"] == library_type

    @settings(max_examples=100)
    @given(
        id=uuid_strategy,
        code=code_strategy,
        expires_at=optional_datetime_strategy,
        max_uses=optional_positive_int_strategy,
        use_count=positive_int_strategy,
        duration_days=optional_positive_int_strategy,
        enabled=st.booleans(),
        created_by=st.one_of(st.none(), name_strategy),
        created_at=datetime_strategy,
        updated_at=optional_datetime_strategy,
    )
    def test_invitation_serialization_round_trip(
        self,
        id: UUID,
        code: str,
        expires_at: datetime | None,
        max_uses: int | None,
        use_count: int,
        duration_days: int | None,
        enabled: bool,
        created_by: str | None,
        created_at: datetime,
        updated_at: datetime | None,
    ) -> None:
        """Invitation serializes with UUIDs as strings and datetimes as ISO."""
        # Create model instance
        invitation = Invitation()
        invitation.id = id
        invitation.code = code
        invitation.expires_at = expires_at
        invitation.max_uses = max_uses
        invitation.use_count = use_count
        invitation.duration_days = duration_days
        invitation.enabled = enabled
        invitation.created_by = created_by
        invitation.created_at = created_at
        invitation.updated_at = updated_at

        # Serialize to dict
        data = model_to_dict(invitation)

        # Verify UUID is serialized as string
        assert isinstance(data["id"], str)
        assert data["id"] == str(id)

        # Verify datetime is serialized as ISO format string
        assert isinstance(data["created_at"], str)
        assert data["created_at"] == created_at.isoformat()

        if expires_at is not None:
            assert isinstance(data["expires_at"], str)
            assert data["expires_at"] == expires_at.isoformat()

        # Serialize to JSON and back
        json_bytes = msgspec.json.encode(data)
        decoded = decode_json(json_bytes)

        # Verify round-trip preserves values
        assert decoded["id"] == str(id)
        assert decoded["code"] == code
        assert decoded["use_count"] == use_count
        assert decoded["enabled"] == enabled

    @settings(max_examples=100)
    @given(
        id=uuid_strategy,
        display_name=name_strategy,
        email=st.one_of(st.none(), email_strategy),
        expires_at=optional_datetime_strategy,
        enabled=st.booleans(),
        created_at=datetime_strategy,
        updated_at=optional_datetime_strategy,
    )
    def test_identity_serialization_round_trip(
        self,
        id: UUID,
        display_name: str,
        email: str | None,
        expires_at: datetime | None,
        enabled: bool,
        created_at: datetime,
        updated_at: datetime | None,
    ) -> None:
        """Identity serializes with UUIDs as strings and datetimes as ISO."""
        # Create model instance
        identity = Identity()
        identity.id = id
        identity.display_name = display_name
        identity.email = email
        identity.expires_at = expires_at
        identity.enabled = enabled
        identity.created_at = created_at
        identity.updated_at = updated_at

        # Serialize to dict
        data = model_to_dict(identity)

        # Verify UUID is serialized as string
        assert isinstance(data["id"], str)
        assert data["id"] == str(id)

        # Verify datetime is serialized as ISO format string
        assert isinstance(data["created_at"], str)
        assert data["created_at"] == created_at.isoformat()

        # Serialize to JSON and back
        json_bytes = msgspec.json.encode(data)
        decoded = decode_json(json_bytes)

        # Verify round-trip preserves values
        assert decoded["id"] == str(id)
        assert decoded["display_name"] == display_name
        assert decoded["email"] == email
        assert decoded["enabled"] == enabled

    @settings(max_examples=100)
    @given(
        id=uuid_strategy,
        identity_id=uuid_strategy,
        media_server_id=uuid_strategy,
        external_user_id=name_strategy,
        username=name_strategy,
        expires_at=optional_datetime_strategy,
        enabled=st.booleans(),
        created_at=datetime_strategy,
        updated_at=optional_datetime_strategy,
    )
    def test_user_serialization_round_trip(
        self,
        id: UUID,
        identity_id: UUID,
        media_server_id: UUID,
        external_user_id: str,
        username: str,
        expires_at: datetime | None,
        enabled: bool,
        created_at: datetime,
        updated_at: datetime | None,
    ) -> None:
        """User serializes with UUIDs as strings and datetimes as ISO."""
        # Create model instance
        user = User()
        user.id = id
        user.identity_id = identity_id
        user.media_server_id = media_server_id
        user.external_user_id = external_user_id
        user.username = username
        user.expires_at = expires_at
        user.enabled = enabled
        user.created_at = created_at
        user.updated_at = updated_at

        # Serialize to dict
        data = model_to_dict(user)

        # Verify UUIDs are serialized as strings
        assert isinstance(data["id"], str)
        assert data["id"] == str(id)
        assert isinstance(data["identity_id"], str)
        assert data["identity_id"] == str(identity_id)
        assert isinstance(data["media_server_id"], str)
        assert data["media_server_id"] == str(media_server_id)

        # Verify datetime is serialized as ISO format string
        assert isinstance(data["created_at"], str)
        assert data["created_at"] == created_at.isoformat()

        # Serialize to JSON and back
        json_bytes = msgspec.json.encode(data)
        decoded = decode_json(json_bytes)

        # Verify round-trip preserves values
        assert decoded["id"] == str(id)
        assert decoded["identity_id"] == str(identity_id)
        assert decoded["media_server_id"] == str(media_server_id)
        assert decoded["external_user_id"] == external_user_id
        assert decoded["username"] == username
        assert decoded["enabled"] == enabled
