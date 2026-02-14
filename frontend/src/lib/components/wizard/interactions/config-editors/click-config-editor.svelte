<script lang="ts">
/**
 * Click Interaction Config Editor
 *
 * Provides admin UI for configuring click interaction settings.
 */
import type { ClickConfig } from "$lib/api/client";
import { Input } from "$lib/components/ui/input";
import { Label } from "$lib/components/ui/label";
import type { ConfigEditorProps } from "../registry";

const { config: rawConfig, onConfigChange, errors }: ConfigEditorProps = $props();

const config = $derived(rawConfig as unknown as ClickConfig);

function updateField(value: string) {
	onConfigChange({ ...rawConfig, button_text: value });
}
</script>

<div class="flex flex-col gap-2">
	<Label for="button-text" class="text-cr-text">Button Text</Label>
	<Input
		id="button-text"
		value={config?.button_text ?? ''}
		oninput={(e) => updateField(e.currentTarget.value)}
		placeholder="I Understand"
		class="border-cr-border bg-cr-bg text-cr-text"
	/>
	{#if errors.button_text}
		<p class="text-xs text-destructive">{errors.button_text[0]}</p>
	{/if}
</div>
