"""Plex-specific API schemas.

Re-exports from api/schemas.py for provider package structure.
"""

from zondarr.api.schemas import (
    PlexLoginRequest,
    PlexOAuthCheckResponse,
    PlexOAuthPinResponse,
)

__all__ = ["PlexLoginRequest", "PlexOAuthCheckResponse", "PlexOAuthPinResponse"]
