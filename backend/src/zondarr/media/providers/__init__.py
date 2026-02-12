"""Media server provider registration.

Imports and registers all available provider implementations.
Called during application startup before settings are loaded.
"""

import warnings

from zondarr.media.registry import registry

from .jellyfin import JellyfinProvider
from .plex import PlexProvider


def register_all_providers() -> None:
    """Register all media server provider implementations.

    Also suppresses Pydantic v1 compatibility warning on Python 3.14+.
    Pydantic is a transitive dep of jellyfin-sdk, not used by Zondarr.
    """
    warnings.filterwarnings(
        "ignore",
        message="Core Pydantic V1 functionality isn't compatible with Python 3.14",
        category=UserWarning,
    )

    registry.register(PlexProvider())
    registry.register(JellyfinProvider())
