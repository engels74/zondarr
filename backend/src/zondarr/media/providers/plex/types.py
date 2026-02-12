"""Plex-specific types.

Provides PlexUserType enum for Plex user creation methods.
"""

from enum import StrEnum


class PlexUserType(StrEnum):
    """Type of Plex user to create.

    Plex supports two distinct user types with different creation methods
    and capabilities.

    Attributes:
        FRIEND: External Plex.tv account invited via inviteFriend().
        HOME: Managed user within Plex Home via createHomeUser().
    """

    FRIEND = "friend"
    HOME = "home"
