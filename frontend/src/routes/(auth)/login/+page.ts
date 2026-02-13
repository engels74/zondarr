import { isRedirect, redirect } from '@sveltejs/kit';
import { getAuthMethods, type ProviderAuthInfo } from '$lib/api/auth';
import { isNetworkError } from '$lib/api/errors';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	try {
		const authMethods = await getAuthMethods(fetch);

		if (authMethods.setup_required) {
			redirect(302, '/setup');
		}

		return {
			methods: authMethods.methods,
			providerAuth: authMethods.provider_auth ?? []
		};
	} catch (e) {
		if (isRedirect(e)) throw e;
		if (!isNetworkError(e)) {
			console.warn('[login loader] unexpected error from getAuthMethods:', e);
		}
		// Backend unreachable or broken — render login with default method
		return {
			methods: ['local'],
			providerAuth: [] as ProviderAuthInfo[]
		};
	}
};
