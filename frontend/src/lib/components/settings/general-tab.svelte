<script lang="ts">
import { Lock, Shield, ShieldCheck, TestTube } from '@lucide/svelte';
import {
	type CsrfOriginTestResponse,
	setCsrfOrigin,
	setSecureCookies,
	testCsrfOrigin
} from '$lib/api/client';
import { Badge } from '$lib/components/ui/badge';
import { Button } from '$lib/components/ui/button';
import * as Card from '$lib/components/ui/card';
import { Input } from '$lib/components/ui/input';
import { Label } from '$lib/components/ui/label';
import { Switch } from '$lib/components/ui/switch';
import { csrfOriginSchema } from '$lib/schemas/setup';
import { showApiError, showError, showSuccess } from '$lib/utils/toast';

interface Props {
	csrfOrigin: string | null;
	isLocked: boolean;
	secureCookies: boolean;
	secureCookiesLocked: boolean;
}

let { csrfOrigin, isLocked, secureCookies, secureCookiesLocked }: Props = $props();

// svelte-ignore state_referenced_locally — intentionally captures initial value for editing
let origin = $state(csrfOrigin ?? '');
let saving = $state(false);
let testing = $state(false);
let testResult = $state<CsrfOriginTestResponse | null>(null);

// svelte-ignore state_referenced_locally — intentionally captures initial value for editing
let secureCookiesEnabled = $state(secureCookies);
let savingSecureCookies = $state(false);

async function handleSave() {
	const parsed = csrfOriginSchema.safeParse({ origin });
	if (!parsed.success) {
		showError(parsed.error.issues[0]?.message ?? 'Invalid origin');
		return;
	}

	saving = true;
	try {
		const result = await setCsrfOrigin({ csrf_origin: origin || null });
		if (result.error) {
			showApiError(result.error);
		} else {
			showSuccess('CSRF origin saved');
		}
	} finally {
		saving = false;
	}
}

async function handleTest() {
	if (!origin) {
		showError('Enter an origin to test');
		return;
	}

	testing = true;
	testResult = null;
	try {
		const result = await testCsrfOrigin(origin);
		if (result.error) {
			showApiError(result.error);
		} else if (result.data) {
			testResult = result.data;
			if (result.data.success) {
				showSuccess(result.data.message);
			} else {
				showError(result.data.message);
			}
		}
	} finally {
		testing = false;
	}
}

async function handleSecureCookiesToggle(checked: boolean) {
	savingSecureCookies = true;
	try {
		const result = await setSecureCookies(checked);
		if (result.error) {
			showApiError(result.error);
			secureCookiesEnabled = !checked;
		} else {
			secureCookiesEnabled = checked;
			showSuccess(checked ? 'Secure cookies enabled' : 'Secure cookies disabled');
		}
	} finally {
		savingSecureCookies = false;
	}
}
</script>

<div class="space-y-6">
	<Card.Root>
		<Card.Header>
			<div class="flex items-center gap-2">
				<Shield class="size-5 text-cr-accent" />
				<Card.Title>CSRF Origin</Card.Title>
				{#if isLocked}
					<Badge variant="secondary" class="gap-1">
						<Lock class="size-3" />
						Environment Variable
					</Badge>
				{/if}
			</div>
			<Card.Description>
				The trusted origin for CSRF protection. This should match the URL you use to access Zondarr
				(e.g., https://zondarr.example.com).
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="space-y-4">
				<div class="space-y-2">
					<Label for="csrf-origin">Origin URL</Label>
					<Input
						id="csrf-origin"
						type="url"
						placeholder="https://zondarr.example.com"
						bind:value={origin}
						disabled={isLocked}
					/>
				</div>
				{#if testResult && !testResult.success}
					<p class="text-sm text-destructive">{testResult.message}</p>
				{/if}
				<div class="flex gap-2">
					<Button onclick={handleSave} disabled={isLocked || saving}>
						{saving ? 'Saving...' : 'Save'}
					</Button>
					<Button variant="outline" onclick={handleTest} disabled={isLocked || testing}>
						<TestTube class="size-4 mr-1.5" />
						{testing ? 'Testing...' : 'Test'}
					</Button>
				</div>
			</div>
		</Card.Content>
	</Card.Root>

	<Card.Root>
		<Card.Header>
			<div class="flex items-center gap-2">
				<ShieldCheck class="size-5 text-cr-accent" />
				<Card.Title>Secure Cookies</Card.Title>
				{#if secureCookiesLocked}
					<Badge variant="secondary" class="gap-1">
						<Lock class="size-3" />
						Environment Variable
					</Badge>
				{/if}
			</div>
			<Card.Description>
				When enabled, cookies are sent only over HTTPS connections. Enable this if you serve Zondarr
				behind HTTPS (recommended for production).
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="flex items-center gap-3">
				<Switch
					checked={secureCookiesEnabled}
					onCheckedChange={handleSecureCookiesToggle}
					disabled={secureCookiesLocked || savingSecureCookies}
					id="secure-cookies"
				/>
				<Label for="secure-cookies" class="text-sm">
					{secureCookiesEnabled ? 'Enabled' : 'Disabled'}
				</Label>
			</div>
		</Card.Content>
	</Card.Root>
</div>
