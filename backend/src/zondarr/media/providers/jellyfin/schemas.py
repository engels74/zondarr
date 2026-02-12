"""Jellyfin-specific API schemas.

Re-exports from api/schemas.py for provider package structure.
"""

from zondarr.api.schemas import JellyfinLoginRequest

__all__ = ["JellyfinLoginRequest"]
