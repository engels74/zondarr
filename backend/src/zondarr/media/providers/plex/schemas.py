"""Plex-specific API schemas."""

from datetime import datetime

import msgspec


class PlexOAuthPinResponse(msgspec.Struct, omit_defaults=True, kw_only=True):
    """Response from Plex OAuth PIN creation.

    Attributes:
        pin_id: The PIN identifier for status checking.
        code: The PIN code to display to the user.
        auth_url: URL where user authenticates (plex.tv/link).
        expires_at: When the PIN expires.
    """

    pin_id: int
    code: str
    auth_url: str
    expires_at: datetime


class PlexOAuthCheckResponse(msgspec.Struct, omit_defaults=True, kw_only=True):
    """Response from Plex OAuth PIN status check.

    Attributes:
        authenticated: Whether the PIN has been authenticated.
        auth_token: Plex auth token (only if authenticated).
        email: User's Plex email (only if authenticated).
        error: Error message (only if failed).
    """

    authenticated: bool
    auth_token: str | None = None
    email: str | None = None
    error: str | None = None
