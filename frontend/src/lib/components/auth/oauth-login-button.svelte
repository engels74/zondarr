<script lang="ts">
import { loginExternal } from "$lib/api/auth";
import { Button } from "$lib/components/ui/button";
import { getProviderColor, getProviderIconSvg } from "$lib/stores/providers.svelte";

interface Props {
	method: string;
	displayName: string;
	onsuccess: () => void;
	onerror: (message: string) => void;
}

const { method, displayName, onsuccess, onerror }: Props = $props();

let loading = $state(false);

const color = $derived(getProviderColor(method));
const iconSvg = $derived(getProviderIconSvg(method));

async function handleOAuthLogin() {
	loading = true;
	try {
		const API_BASE_URL = import.meta.env.VITE_API_URL ?? "";
		const pinResponse = await fetch(
			`${API_BASE_URL}/api/v1/join/${method}/oauth/pin`,
			{
				method: "POST",
				credentials: "include",
			},
		);

		if (!pinResponse.ok) {
			onerror(`Failed to start ${displayName} authentication`);
			return;
		}

		const pinData = (await pinResponse.json()) as {
			pin_id: number;
			auth_url: string;
		};

		const popup = window.open(
			pinData.auth_url,
			`${method}-auth`,
			"width=800,height=600",
		);

		const pollInterval = setInterval(async () => {
			try {
				const checkResponse = await fetch(
					`${API_BASE_URL}/api/v1/join/${method}/oauth/pin/${pinData.pin_id}`,
					{ credentials: "include" },
				);

				if (!checkResponse.ok) return;

				const checkData = (await checkResponse.json()) as {
					authenticated: boolean;
					auth_token?: string;
				};

				if (checkData.authenticated && checkData.auth_token) {
					clearInterval(pollInterval);
					popup?.close();

					const result = await loginExternal(method, {
						auth_token: checkData.auth_token,
					});
					if (result.error) {
						const err = result.error as { detail?: string };
						onerror(err.detail ?? `${displayName} login failed`);
					} else {
						onsuccess();
					}
				}
			} catch {
				// Ignore polling errors
			}
		}, 2000);

		// Stop polling after 5 minutes
		setTimeout(() => {
			clearInterval(pollInterval);
			popup?.close();
			loading = false;
		}, 300_000);
	} catch {
		onerror(`Failed to connect to ${displayName}`);
	} finally {
		loading = false;
	}
}
</script>

<Button
	onclick={handleOAuthLogin}
	disabled={loading}
	variant="outline"
	class="w-full border-cr-border bg-cr-bg text-cr-text"
	style="--provider-color: {color}"
>
	<svg class="mr-2 size-4" viewBox="0 0 24 24" fill="currentColor">
		<path d={iconSvg} />
	</svg>
	{#if loading}
		Connecting to {displayName}...
	{:else}
		Sign in with {displayName}
	{/if}
</Button>

<style>
	:global(button[style*="--provider-color"]:hover) {
		background: color-mix(in srgb, var(--provider-color) 10%, transparent) !important;
		color: var(--provider-color) !important;
		border-color: color-mix(in srgb, var(--provider-color) 30%, transparent) !important;
	}
</style>
