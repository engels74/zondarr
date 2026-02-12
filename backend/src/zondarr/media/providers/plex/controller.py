"""Plex-specific route handlers.

Re-exports the PlexOAuthController. The PlexLoginController is part
of the main AuthController for now (extracted in Phase 2).
"""

from zondarr.api.plex_oauth import PlexOAuthController

__all__ = ["PlexOAuthController"]
