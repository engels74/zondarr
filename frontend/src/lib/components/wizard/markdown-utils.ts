/**
 * Shared markdown rendering and sanitization configuration.
 *
 * Single source of truth for DOMPurify ALLOWED_TAGS / ALLOWED_ATTR
 * used by wizard-shell, markdown-editor, and sanitization tests.
 *
 * @module $lib/components/wizard/markdown-utils
 */

import DOMPurify from 'dompurify';
import { marked } from 'marked';

export const ALLOWED_TAGS = [
	'h1',
	'h2',
	'h3',
	'h4',
	'h5',
	'h6',
	'p',
	'br',
	'strong',
	'em',
	'u',
	'a',
	'ul',
	'ol',
	'li',
	'blockquote',
	'code',
	'pre',
	'img',
	'hr'
] as const;

export const ALLOWED_ATTR = ['href', 'target', 'rel', 'src', 'alt', 'width', 'height'] as const;

/**
 * Render markdown to sanitized HTML.
 *
 * Uses `marked.parse()` for markdown→HTML conversion and `DOMPurify.sanitize()`
 * with the shared allowlist to strip unsafe tags/attributes.
 */
export function renderMarkdown(source: string): string {
	const rawHtml = marked.parse(source, { async: false }) as string;
	return DOMPurify.sanitize(rawHtml, {
		ALLOWED_TAGS: [...ALLOWED_TAGS],
		ALLOWED_ATTR: [...ALLOWED_ATTR]
	});
}
