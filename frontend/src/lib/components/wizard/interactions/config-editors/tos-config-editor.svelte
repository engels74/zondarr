<script lang="ts">
/**
 * TOS Interaction Config Editor
 *
 * Provides admin UI for configuring Terms of Service interaction settings.
 */
import type { TosConfig } from "$lib/api/client";
import { Input } from "$lib/components/ui/input";
import { Label } from "$lib/components/ui/label";
import type { ConfigEditorProps } from "../registry";

const { config: rawConfig, onConfigChange, errors }: ConfigEditorProps = $props();

const config = $derived(rawConfig as unknown as TosConfig);

function updateField(value: string) {
	onConfigChange({ ...rawConfig, checkbox_label: value });
}
</script>

<div class="flex flex-col gap-2">
	<Label for="checkbox-label" class="text-cr-text">Checkbox Label</Label>
	<Input
		id="checkbox-label"
		value={config?.checkbox_label ?? ''}
		oninput={(e) => updateField(e.currentTarget.value)}
		placeholder="I accept the terms of service"
		class="border-cr-border bg-cr-bg text-cr-text"
	/>
	{#if errors.checkbox_label}
		<p class="text-xs text-destructive">{errors.checkbox_label[0]}</p>
	{/if}
</div>
