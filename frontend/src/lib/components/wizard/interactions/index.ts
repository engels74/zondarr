/**
 * Wizard Interaction Components
 *
 * Exports all interaction components for wizard steps.
 * Each component handles a specific interaction type.
 *
 * Requirements: 12.1-12.5
 *
 * @module $lib/components/wizard/interactions
 */

// Re-export the StepResponse type for convenience
export type { StepResponse } from './click-interaction.svelte';
export { default as ClickInteraction } from './click-interaction.svelte';
export { default as QuizInteraction } from './quiz-interaction.svelte';
export { default as TextInputInteraction } from './text-input-interaction.svelte';
export { default as TimerInteraction } from './timer-interaction.svelte';
export { default as TosInteraction } from './tos-interaction.svelte';
