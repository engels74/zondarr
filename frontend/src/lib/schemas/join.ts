/**
 * Zod validation schemas for join/registration forms.
 *
 * Provides client-side validation matching backend constraints for:
 * - Jellyfin user registration (username, password, email)
 *
 * @module $lib/schemas/join
 */

import { z } from 'zod';

/**
 * Schema for Jellyfin user registration.
 *
 * Validates:
 * - username: 3-32 chars, lowercase, starts with letter, alphanumeric + underscores
 * - password: minimum 8 characters, maximum 128 characters
 * - email: optional valid email address
 *
 * Requirements: 11.2, 11.3, 11.4, 11.5
 */
export const jellyfinRegistrationSchema = z.object({
	username: z
		.string()
		.min(3, 'Username must be at least 3 characters')
		.max(32, 'Username must be at most 32 characters')
		.regex(
			/^[a-z][a-z0-9_]*$/,
			'Username must start with a lowercase letter and contain only lowercase letters, numbers, and underscores'
		),
	password: z
		.string()
		.min(8, 'Password must be at least 8 characters')
		.max(128, 'Password must be at most 128 characters'),
	email: z.string().email('Invalid email address').optional().or(z.literal(''))
});

export type JellyfinRegistrationInput = z.infer<typeof jellyfinRegistrationSchema>;

/**
 * Transform registration form data to API request format.
 *
 * Converts empty email string to undefined for the API.
 */
export function transformRegistrationFormData(data: JellyfinRegistrationInput) {
	return {
		username: data.username,
		password: data.password,
		email: data.email && data.email !== '' ? data.email : undefined
	};
}
