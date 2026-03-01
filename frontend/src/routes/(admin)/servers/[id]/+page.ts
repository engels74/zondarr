/**
 * Server detail page load function.
 *
 * Fetches a single server by ID from the detail endpoint,
 * plus credential lock status for env-var indicators.
 *
 * @module routes/(admin)/servers/[id]/+page
 */

import {
	type CredentialLockStatus,
	createScopedClient,
	getCredentialLocks,
	getServer,
	type MediaServerDetailResponse
} from '$lib/api/client';
import { ApiError, asErrorResponse } from '$lib/api/errors';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
	const client = createScopedClient(fetch);
	const { id } = params;

	try {
		const [serverResult, locksResult] = await Promise.all([
			getServer(id, client),
			getCredentialLocks(id, client)
		]);

		if (serverResult.data) {
			return {
				server: serverResult.data,
				credentialLocks: locksResult.data ?? null,
				error: null as Error | null
			};
		}

		// Handle error response
		const status = serverResult.response?.status ?? 500;
		const errorBody = asErrorResponse(serverResult.error);
		return {
			server: null as MediaServerDetailResponse | null,
			credentialLocks: null as CredentialLockStatus | null,
			error: new ApiError(
				status,
				errorBody?.error_code ?? 'UNKNOWN_ERROR',
				errorBody?.detail ?? 'An error occurred'
			)
		};
	} catch (err) {
		// Handle network errors
		return {
			server: null as MediaServerDetailResponse | null,
			credentialLocks: null as CredentialLockStatus | null,
			error: err instanceof Error ? err : new Error('Failed to load server')
		};
	}
};
