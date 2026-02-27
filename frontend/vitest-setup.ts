import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Mock SvelteKit's $env modules for test environment
vi.mock('$env/dynamic/public', () => ({
	env: {}
}));
vi.mock('$env/dynamic/private', () => ({
	env: {}
}));
