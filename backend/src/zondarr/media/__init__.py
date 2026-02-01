"""Media module - client protocol, registry, and implementations.

Provides:
- MediaClient: Protocol defining the interface for media server clients
- Capability: StrEnum for features that media clients may support
- LibraryInfo: msgspec Struct for library information from media servers
- ExternalUser: msgspec Struct for user information from media servers
- MediaClientError: Exception for media client operation failures
- UnknownServerTypeError: Exception for unknown server types
"""

from .exceptions import MediaClientError, UnknownServerTypeError
from .protocol import MediaClient
from .types import Capability, ExternalUser, LibraryInfo

__all__ = [
    "Capability",
    "ExternalUser",
    "LibraryInfo",
    "MediaClient",
    "MediaClientError",
    "UnknownServerTypeError",
]
