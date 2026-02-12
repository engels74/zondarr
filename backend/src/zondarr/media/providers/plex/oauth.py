"""Plex OAuth service re-export.

Re-exports from the local oauth_service module for backwards compatibility.
"""

from zondarr.media.providers.plex.oauth_service import PlexOAuthError, PlexOAuthService

__all__ = ["PlexOAuthError", "PlexOAuthService"]
