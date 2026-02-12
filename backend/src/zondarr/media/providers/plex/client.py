"""Plex client re-export.

The actual PlexClient implementation lives in media/clients/plex.py.
This module re-exports it for the provider package structure.
"""

from zondarr.media.clients.plex import PlexClient

__all__ = ["PlexClient"]
