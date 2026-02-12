/**
 * Provider metadata store.
 *
 * Holds metadata for registered media server providers (color, label, icon, etc.)
 * Pre-populated with known defaults; can be updated from the backend API.
 *
 * @module $lib/stores/providers
 */

// =============================================================================
// Types
// =============================================================================

export interface ProviderMeta {
	server_type: string;
	display_name: string;
	color: string;
	icon_svg: string;
	api_key_help_text: string;
	join_flow_type: string | null;
	capabilities: string[];
	supported_permissions: string[];
}

// =============================================================================
// Known provider defaults (used before API fetch or as fallback)
// =============================================================================

const PROVIDER_DEFAULTS: Record<string, ProviderMeta> = {
	plex: {
		server_type: 'plex',
		display_name: 'Plex',
		color: '#E5A00D',
		icon_svg: 'M11.643 0H4.68l7.679 12-7.679 12h6.963L19.32 12z',
		api_key_help_text: 'Find your Plex token in account settings or use a Plex Pass API token',
		join_flow_type: 'oauth_link',
		capabilities: [],
		supported_permissions: []
	},
	jellyfin: {
		server_type: 'jellyfin',
		display_name: 'Jellyfin',
		color: '#00A4DC',
		icon_svg:
			'M12 .002C5.375.002 0 5.377 0 12.002c0 6.624 5.375 12 12 12s12-5.376 12-12c0-6.625-5.375-12-12-12zm0 2.5a9.5 9.5 0 0 1 9.5 9.5 9.5 9.5 0 0 1-9.5 9.5 9.5 9.5 0 0 1-9.5-9.5 9.5 9.5 0 0 1 9.5-9.5z',
		api_key_help_text: 'Create an API key in Jellyfin: Dashboard > API Keys',
		join_flow_type: 'credential_create',
		capabilities: [],
		supported_permissions: []
	}
};

// =============================================================================
// State
// =============================================================================

let providers = $state<Map<string, ProviderMeta>>(new Map(Object.entries(PROVIDER_DEFAULTS)));

// =============================================================================
// API
// =============================================================================

/**
 * Replace provider metadata with data from the backend API.
 */
export function setProviders(list: ProviderMeta[]): void {
	const map = new Map<string, ProviderMeta>();
	for (const p of list) {
		map.set(p.server_type, p);
	}
	providers = map;
}

/**
 * Get metadata for a specific provider type.
 */
export function getProvider(serverType: string): ProviderMeta | undefined {
	return providers.get(serverType);
}

/**
 * Get display name for a provider type, falling back to the raw type string.
 */
export function getProviderLabel(serverType: string): string {
	return providers.get(serverType)?.display_name ?? serverType;
}

/**
 * Get brand color hex for a provider type.
 */
export function getProviderColor(serverType: string): string {
	return providers.get(serverType)?.color ?? '#6b7280';
}

/**
 * Get SVG path data for a provider's icon.
 */
export function getProviderIconSvg(serverType: string): string {
	return providers.get(serverType)?.icon_svg ?? '';
}

/**
 * Get all registered providers.
 */
export function getAllProviders(): ProviderMeta[] {
	return Array.from(providers.values());
}

// =============================================================================
// Style helpers
// =============================================================================

function hexToRgba(hex: string, alpha: number): string {
	const r = parseInt(hex.slice(1, 3), 16);
	const g = parseInt(hex.slice(3, 5), 16);
	const b = parseInt(hex.slice(5, 7), 16);
	return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Get inline CSS style string for a provider badge.
 *
 * Returns background, color, and border-color as inline styles,
 * which avoids UnoCSS build-time limitations with dynamic classes.
 */
export function getProviderBadgeStyle(serverType: string): string {
	const color = getProviderColor(serverType);
	return `background: ${hexToRgba(color, 0.15)}; color: ${color}; border-color: ${hexToRgba(color, 0.3)}`;
}

/**
 * Get inline CSS style for a provider toggle button in active state.
 */
export function getProviderActiveToggleStyle(serverType: string): string {
	const color = getProviderColor(serverType);
	return `background: ${hexToRgba(color, 0.2)}; color: ${color}; border-color: ${hexToRgba(color, 0.3)}`;
}

/**
 * Get inline CSS style for hover effects on a provider element.
 */
export function getProviderHoverVars(serverType: string): string {
	const color = getProviderColor(serverType);
	return `--provider-color: ${color}; --provider-bg: ${hexToRgba(color, 0.1)}; --provider-border: ${hexToRgba(color, 0.3)}`;
}
