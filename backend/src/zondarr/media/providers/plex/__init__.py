"""Plex media server provider.

Implements ProviderDescriptor for Plex, declaring metadata,
client class, admin auth, join flow, and OAuth support.
"""

from typing import TYPE_CHECKING

from zondarr.media.provider import (
    AdminAuthDescriptor,
    AuthFlowType,
    JoinFlowDescriptor,
    JoinFlowType,
    MediaClientClass,
    OAuthCheckResult,
    OAuthPinResult,
    ProviderMetadata,
)

from .auth import PlexAdminAuth
from .client import PlexClient
from .oauth_service import PlexOAuthError, PlexOAuthService

if TYPE_CHECKING:
    from zondarr.config import Settings

# Plex logo SVG path (simplified play button triangle)
_PLEX_ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M5.5 3L18.5 12L5.5 21V3Z"/>'
    "</svg>"
)

# Default client identifier for Plex OAuth
_DEFAULT_PLEX_CLIENT_ID = "zondarr-oauth-client"


class _PlexOAuthFlowAdapter:
    """Adapts PlexOAuthService to the OAuthFlowProvider protocol."""

    _service: PlexOAuthService

    def __init__(self, service: PlexOAuthService) -> None:
        self._service = service

    async def create_pin(self) -> OAuthPinResult:
        """Generate a Plex OAuth PIN."""
        pin = await self._service.create_pin()
        return OAuthPinResult(
            pin_id=pin.pin_id,
            code=pin.code,
            auth_url=pin.auth_url,
            expires_at=pin.expires_at,
        )

    async def check_pin(self, pin_id: int, /) -> OAuthCheckResult:
        """Check if a Plex PIN has been authenticated."""
        try:
            result = await self._service.check_pin(pin_id)
            return OAuthCheckResult(
                authenticated=result.authenticated,
                auth_token=result.auth_token,
                email=result.email,
                error=result.error,
            )
        except PlexOAuthError as exc:
            return OAuthCheckResult(
                authenticated=False,
                error=exc.message,
            )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._service.close()


class PlexProvider:
    """Plex ProviderDescriptor implementation."""

    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            server_type="plex",
            display_name="Plex",
            color="#E5A00D",
            icon_svg=_PLEX_ICON_SVG,
            env_url_var="PLEX_URL",
            env_api_key_var="PLEX_TOKEN",
            api_key_help_text="Plex authentication token (X-Plex-Token)",
        )

    @property
    def client_class(self) -> MediaClientClass:
        return PlexClient

    @property
    def admin_auth(self) -> AdminAuthDescriptor:
        return AdminAuthDescriptor(
            method_name="plex",
            display_name="Plex",
            flow_type=AuthFlowType.OAUTH,
        )

    @property
    def admin_auth_provider(self) -> PlexAdminAuth:
        return PlexAdminAuth()

    @property
    def join_flow(self) -> JoinFlowDescriptor:
        return JoinFlowDescriptor(flow_type=JoinFlowType.OAUTH_LINK)

    @property
    def route_handlers(self) -> None:
        return None

    def create_oauth_flow_provider(self, settings: Settings) -> _PlexOAuthFlowAdapter:
        """Create a Plex OAuth flow provider."""
        client_id_attr: object = getattr(settings, "plex_client_id", None)
        client_id: str = (
            client_id_attr
            if isinstance(client_id_attr, str)
            else _DEFAULT_PLEX_CLIENT_ID
        )
        service = PlexOAuthService(client_id=client_id)
        return _PlexOAuthFlowAdapter(service)
