"""Jellyfin client re-export.

The actual JellyfinClient implementation lives in media/clients/jellyfin.py.
This module re-exports it for the provider package structure.
"""

from zondarr.media.clients.jellyfin import JellyfinClient

__all__ = ["JellyfinClient"]
