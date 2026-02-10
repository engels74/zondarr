import { isRedirect, redirect } from '@sveltejs/kit';
import { getAuthMethods } from '$lib/api/auth';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	try {
		const authMethods = await getAuthMethods(fetch);

		if (!authMethods.setup_required) {
			redirect(302, '/login');
		}
	} catch (e) {
		if (isRedirect(e)) throw e;
		// Backend unreachable — render setup page anyway (submission will fail gracefully)
	}

	return {};
};
