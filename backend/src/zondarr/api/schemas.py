"""API request/response schemas using msgspec Structs.

Provides:
- ErrorResponse: Standard error response structure
- MediaServerCreate/Response: Media server CRUD schemas
- LibraryResponse: Library response schema
- InvitationCreate/Response: Invitation CRUD schemas
- IdentityCreate/Response: Identity CRUD schemas
- UserResponse: User response schema
- HealthCheckResponse: Health endpoint response schema

Uses msgspec.Struct for high-performance serialization (10-80x faster than Pydantic).
Validation constraints are defined via Meta annotations.

Request structs use:
- kw_only=True: All fields must be passed as keyword arguments
- forbid_unknown_fields=True: Reject payloads with extra fields

Response structs use:
- omit_defaults=True: Exclude fields with default values from JSON output
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

import msgspec

# =============================================================================
# Reusable Constrained Types
# =============================================================================

# Non-empty string with max length for names and identifiers
NonEmptyStr = Annotated[str, msgspec.Meta(min_length=1, max_length=255)]

# URL string with reasonable max length
UrlStr = Annotated[str, msgspec.Meta(min_length=1, max_length=2048)]

# API key string (may be longer for some services)
ApiKeyStr = Annotated[str, msgspec.Meta(min_length=1, max_length=512)]

# Invitation code (short, unique identifier)
InvitationCode = Annotated[str, msgspec.Meta(min_length=1, max_length=20)]

# Email address (basic pattern validation)
EmailStr = Annotated[
    str, msgspec.Meta(pattern=r"^[\w.-]+@[\w.-]+\.\w+$", max_length=255)
]

# Positive integer for counts and limits
PositiveInt = Annotated[int, msgspec.Meta(gt=0)]

# Non-negative integer for use counts
NonNegativeInt = Annotated[int, msgspec.Meta(ge=0)]


# =============================================================================
# Error Response Schemas
# =============================================================================


class ErrorResponse(msgspec.Struct, kw_only=True):
    """Standard error response structure.

    All API errors return this structure for consistent client handling.

    Attributes:
        detail: Human-readable error description.
        error_code: Machine-readable error code for programmatic handling.
        timestamp: When the error occurred (UTC).
        correlation_id: Optional unique ID for tracing errors in logs.
    """

    detail: str
    error_code: str
    timestamp: datetime
    correlation_id: str | None = None


class FieldError(msgspec.Struct, kw_only=True):
    """Field-level validation error detail.

    Attributes:
        field: Name of the field that failed validation.
        messages: List of validation error messages for this field.
    """

    field: str
    messages: list[str]


class ValidationErrorResponse(msgspec.Struct, kw_only=True):
    """Validation error response with field-level details.

    Extends ErrorResponse with field-specific error information.

    Attributes:
        detail: Human-readable error description.
        error_code: Always "VALIDATION_ERROR" for this type.
        timestamp: When the error occurred (UTC).
        correlation_id: Optional unique ID for tracing errors in logs.
        field_errors: List of field-level validation errors.
    """

    detail: str
    error_code: str
    timestamp: datetime
    correlation_id: str | None = None
    field_errors: list[FieldError]


# =============================================================================
# Media Server Schemas
# =============================================================================


class MediaServerCreate(msgspec.Struct, kw_only=True, forbid_unknown_fields=True):
    """Request to create a media server.

    Attributes:
        name: Human-readable name for the server.
        server_type: Type of media server ("jellyfin" or "plex").
        url: Base URL for the media server API.
        api_key: Authentication token for the media server.
    """

    name: NonEmptyStr
    server_type: Annotated[str, msgspec.Meta(pattern=r"^(jellyfin|plex)$")]
    url: UrlStr
    api_key: ApiKeyStr


class MediaServerUpdate(msgspec.Struct, kw_only=True, forbid_unknown_fields=True):
    """Request to update a media server.

    All fields are optional - only provided fields will be updated.

    Attributes:
        name: Human-readable name for the server.
        url: Base URL for the media server API.
        api_key: Authentication token for the media server.
        enabled: Whether the server is active for user management.
    """

    name: NonEmptyStr | None = None
    url: UrlStr | None = None
    api_key: ApiKeyStr | None = None
    enabled: bool | None = None


class MediaServerResponse(msgspec.Struct, omit_defaults=True):
    """Media server response.

    Attributes:
        id: Unique identifier for the server.
        name: Human-readable name for the server.
        server_type: Type of media server ("jellyfin" or "plex").
        url: Base URL for the media server API.
        enabled: Whether the server is active for user management.
        created_at: When the server was added.
        updated_at: When the server was last modified.
    """

    id: UUID
    name: str
    server_type: str
    url: str
    enabled: bool
    created_at: datetime
    updated_at: datetime | None = None


# =============================================================================
# Library Schemas
# =============================================================================


class LibraryResponse(msgspec.Struct, omit_defaults=True):
    """Library response.

    Attributes:
        id: Unique identifier for the library.
        name: Human-readable name of the library.
        library_type: Type of content (movies, tvshows, music, etc.).
        external_id: The library's ID on the media server.
        created_at: When the library was synced.
        updated_at: When the library was last synced.
    """

    id: UUID
    name: str
    library_type: str
    external_id: str
    created_at: datetime
    updated_at: datetime | None = None


class MediaServerWithLibrariesResponse(msgspec.Struct, omit_defaults=True):
    """Media server response including libraries.

    Attributes:
        id: Unique identifier for the server.
        name: Human-readable name for the server.
        server_type: Type of media server ("jellyfin" or "plex").
        url: Base URL for the media server API.
        enabled: Whether the server is active for user management.
        created_at: When the server was added.
        updated_at: When the server was last modified.
        libraries: List of libraries on this server.
    """

    id: UUID
    name: str
    server_type: str
    url: str
    enabled: bool
    created_at: datetime
    libraries: list[LibraryResponse]
    updated_at: datetime | None = None


# =============================================================================
# Invitation Schemas
# =============================================================================


class InvitationCreate(msgspec.Struct, kw_only=True, forbid_unknown_fields=True):
    """Request to create an invitation.

    Attributes:
        code: Unique invitation code (if not provided, one will be generated).
        expires_at: Optional expiration timestamp.
        max_uses: Optional maximum number of redemptions.
        duration_days: Optional duration in days for user access after redemption.
        server_ids: List of media server IDs this invitation grants access to.
        library_ids: Optional list of specific library IDs to grant access to.
    """

    code: InvitationCode | None = None
    expires_at: datetime | None = None
    max_uses: PositiveInt | None = None
    duration_days: PositiveInt | None = None
    server_ids: list[UUID]
    library_ids: list[UUID] | None = None


class InvitationUpdate(msgspec.Struct, kw_only=True, forbid_unknown_fields=True):
    """Request to update an invitation.

    All fields are optional - only provided fields will be updated.

    Attributes:
        expires_at: Optional expiration timestamp.
        max_uses: Optional maximum number of redemptions.
        duration_days: Optional duration in days for user access after redemption.
        enabled: Whether the invitation is currently active.
    """

    expires_at: datetime | None = None
    max_uses: PositiveInt | None = None
    duration_days: PositiveInt | None = None
    enabled: bool | None = None


class InvitationResponse(msgspec.Struct, omit_defaults=True):
    """Invitation response.

    Attributes:
        id: Unique identifier for the invitation.
        code: Unique invitation code.
        expires_at: Optional expiration timestamp.
        max_uses: Optional maximum number of redemptions.
        use_count: Current number of times the invitation has been redeemed.
        duration_days: Optional duration in days for user access after redemption.
        enabled: Whether the invitation is currently active.
        created_by: Optional identifier of who created the invitation.
        created_at: When the invitation was created.
        updated_at: When the invitation was last modified.
    """

    id: UUID
    code: str
    use_count: int
    enabled: bool
    created_at: datetime
    expires_at: datetime | None = None
    max_uses: int | None = None
    duration_days: int | None = None
    created_by: str | None = None
    updated_at: datetime | None = None


class InvitationDetailResponse(msgspec.Struct, omit_defaults=True):
    """Detailed invitation response including related servers and libraries.

    Attributes:
        id: Unique identifier for the invitation.
        code: Unique invitation code.
        expires_at: Optional expiration timestamp.
        max_uses: Optional maximum number of redemptions.
        use_count: Current number of times the invitation has been redeemed.
        duration_days: Optional duration in days for user access after redemption.
        enabled: Whether the invitation is currently active.
        created_by: Optional identifier of who created the invitation.
        created_at: When the invitation was created.
        updated_at: When the invitation was last modified.
        target_servers: List of media servers this invitation grants access to.
        allowed_libraries: List of specific libraries this invitation grants access to.
    """

    id: UUID
    code: str
    use_count: int
    enabled: bool
    created_at: datetime
    target_servers: list[MediaServerResponse]
    allowed_libraries: list[LibraryResponse]
    expires_at: datetime | None = None
    max_uses: int | None = None
    duration_days: int | None = None
    created_by: str | None = None
    updated_at: datetime | None = None


# =============================================================================
# Identity Schemas
# =============================================================================


class IdentityCreate(msgspec.Struct, kw_only=True, forbid_unknown_fields=True):
    """Request to create an identity.

    Attributes:
        display_name: Human-readable name for the identity.
        email: Optional email address for notifications.
        expires_at: Optional expiration timestamp.
    """

    display_name: NonEmptyStr
    email: EmailStr | None = None
    expires_at: datetime | None = None


class IdentityUpdate(msgspec.Struct, kw_only=True, forbid_unknown_fields=True):
    """Request to update an identity.

    All fields are optional - only provided fields will be updated.

    Attributes:
        display_name: Human-readable name for the identity.
        email: Optional email address for notifications.
        expires_at: Optional expiration timestamp.
        enabled: Whether the identity is currently active.
    """

    display_name: NonEmptyStr | None = None
    email: EmailStr | None = None
    expires_at: datetime | None = None
    enabled: bool | None = None


class IdentityResponse(msgspec.Struct, omit_defaults=True):
    """Identity response.

    Attributes:
        id: Unique identifier for the identity.
        display_name: Human-readable name for the identity.
        email: Optional email address for notifications.
        expires_at: Optional expiration timestamp.
        enabled: Whether the identity is currently active.
        created_at: When the identity was created.
        updated_at: When the identity was last modified.
    """

    id: UUID
    display_name: str
    enabled: bool
    created_at: datetime
    email: str | None = None
    expires_at: datetime | None = None
    updated_at: datetime | None = None


# =============================================================================
# User Schemas
# =============================================================================


class UserResponse(msgspec.Struct, omit_defaults=True):
    """User response.

    Attributes:
        id: Unique identifier for the user.
        identity_id: ID of the parent identity.
        media_server_id: ID of the media server.
        external_user_id: The user's ID on the media server.
        username: The username on the media server.
        expires_at: Optional expiration timestamp.
        enabled: Whether the user account is currently active.
        created_at: When the user was created.
        updated_at: When the user was last modified.
    """

    id: UUID
    identity_id: UUID
    media_server_id: UUID
    external_user_id: str
    username: str
    enabled: bool
    created_at: datetime
    expires_at: datetime | None = None
    updated_at: datetime | None = None


class IdentityWithUsersResponse(msgspec.Struct, omit_defaults=True):
    """Identity response including linked users.

    Attributes:
        id: Unique identifier for the identity.
        display_name: Human-readable name for the identity.
        email: Optional email address for notifications.
        expires_at: Optional expiration timestamp.
        enabled: Whether the identity is currently active.
        created_at: When the identity was created.
        updated_at: When the identity was last modified.
        users: List of media server accounts linked to this identity.
    """

    id: UUID
    display_name: str
    enabled: bool
    created_at: datetime
    users: list[UserResponse]
    email: str | None = None
    expires_at: datetime | None = None
    updated_at: datetime | None = None


# =============================================================================
# Health Check Schemas
# =============================================================================


class HealthCheckResponse(msgspec.Struct, kw_only=True):
    """Health check response.

    Attributes:
        status: Overall health status ("healthy" or "degraded").
        checks: Individual dependency check results.
    """

    status: str
    checks: dict[str, bool]


class LivenessResponse(msgspec.Struct, kw_only=True):
    """Liveness probe response.

    Attributes:
        status: Always "alive" if the process is running.
    """

    status: str


class ReadinessResponse(msgspec.Struct, kw_only=True):
    """Readiness probe response.

    Attributes:
        status: "ready" if the application can serve traffic, "not ready" otherwise.
    """

    status: str


# =============================================================================
# Connection Test Schemas
# =============================================================================


class ConnectionTestRequest(msgspec.Struct, kw_only=True, forbid_unknown_fields=True):
    """Request to test a media server connection.

    Attributes:
        server_type: Type of media server ("jellyfin" or "plex").
        url: Base URL for the media server API.
        api_key: Authentication token for the media server.
    """

    server_type: Annotated[str, msgspec.Meta(pattern=r"^(jellyfin|plex)$")]
    url: UrlStr
    api_key: ApiKeyStr


class ConnectionTestResponse(msgspec.Struct, kw_only=True):
    """Response from a media server connection test.

    Attributes:
        success: Whether the connection test succeeded.
        message: Human-readable result message.
        server_name: Name of the server (if connection succeeded).
        version: Server version (if connection succeeded).
    """

    success: bool
    message: str
    server_name: str | None = None
    version: str | None = None
