/**
 * Zod validation schemas for authentication forms.
 */

import { z } from 'zod';

export const loginSchema = z.object({
	username: z.string().min(1, 'Username is required'),
	password: z.string().min(1, 'Password is required')
});

export const setupSchema = z
	.object({
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
			.min(15, 'Password must be at least 15 characters')
			.max(128, 'Password must be at most 128 characters'),
		confirmPassword: z.string(),
		email: z.string().email('Invalid email address').optional().or(z.literal(''))
	})
	.refine((data) => data.password === data.confirmPassword, {
		message: 'Passwords do not match',
		path: ['confirmPassword']
	});

export const totpCodeSchema = z.object({
	code: z
		.string()
		.length(6, 'Code must be 6 digits')
		.regex(/^\d{6}$/, 'Code must contain only digits')
});

export const backupCodeSchema = z.object({
	code: z
		.string()
		.min(1, 'Backup code is required')
		.regex(/^[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}$/, 'Backup code must be in XXXX-XXXX format')
});

export type LoginFormData = z.infer<typeof loginSchema>;
export type SetupFormData = z.infer<typeof setupSchema>;
export type TotpCodeFormData = z.infer<typeof totpCodeSchema>;
export type BackupCodeFormData = z.infer<typeof backupCodeSchema>;
