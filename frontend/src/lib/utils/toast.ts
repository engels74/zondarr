import { toast } from 'svelte-sonner';

/**
 * Display a success toast notification.
 */
export function showSuccess(message: string, description?: string) {
	toast.success(message, { description });
}

/**
 * Display an error toast notification.
 */
export function showError(message: string, description?: string) {
	toast.error(message, { description });
}

/**
 * Display an error toast from an API error response.
 */
export function showApiError(error: unknown) {
	if (error && typeof error === 'object' && 'detail' in error) {
		const apiError = error as { detail: string; error_code?: string };
		toast.error(apiError.detail, {
			description: apiError.error_code ? `Error code: ${apiError.error_code}` : undefined
		});
	} else if (error instanceof Error) {
		toast.error('An error occurred', { description: error.message });
	} else {
		toast.error('An unexpected error occurred');
	}
}

/**
 * Display a network error toast with retry guidance.
 */
export function showNetworkError() {
	toast.error('Network error', {
		description: 'Please check your connection and try again.'
	});
}

/**
 * Display an info toast notification.
 */
export function showInfo(message: string, description?: string) {
	toast.info(message, { description });
}

/**
 * Display a warning toast notification.
 */
export function showWarning(message: string, description?: string) {
	toast.warning(message, { description });
}
