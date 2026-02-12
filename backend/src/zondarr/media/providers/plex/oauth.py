"""Plex OAuth service re-export.

The actual PlexOAuthService lives in services/plex_oauth.py.
This module re-exports it for the provider package structure.
"""

from zondarr.services.plex_oauth import PlexOAuthError, PlexOAuthService

__all__ = ["PlexOAuthError", "PlexOAuthService"]
