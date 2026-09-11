import { cleanup, render } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import LogEntryWrapper from './log-entry-test-wrapper.svelte';

afterEach(cleanup);
it('selects the log row with Enter and Space and exposes selected state', async () => {
	const onSelect = vi.fn();
	const user = userEvent.setup();
	const { getByRole } = render(LogEntryWrapper, { onSelect });
	const row = getByRole('button', { name: /Example log entry/ });
	expect(row).toHaveAttribute('aria-pressed', 'true');
	await user.tab();
	expect(row).toHaveFocus();
	await user.keyboard('{Enter}');
	await user.keyboard(' ');
	expect(onSelect).toHaveBeenCalledTimes(2);
	expect(onSelect).toHaveBeenNthCalledWith(1, 42);
	expect(onSelect).toHaveBeenNthCalledWith(2, 42);
});
