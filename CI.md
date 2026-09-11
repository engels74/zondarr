# CI and dependency maintenance

All pull requests and default-branch pushes run Python, frontend, production
integration and hygiene checks. `ci / required` requires exactly those jobs and the
dispatch guard. Missing, skipped, failed or cancelled jobs block merging. Review every expected job and the exact PR head/base before merging through
the maintainer merge function. GitHub branch protections and rulesets are not
configured. Validation is read-only, bounded by timeouts and concurrency, uses
full version tags, and rejects tracked-file mutation.

## Local commands and coverage

Use Python 3.14, uv and Bun 1.4.2. Frozen installs and `uv lock --check` validate the
committed resolution. `bash .github/scripts/check-python.sh` runs locked Ruff across
backend, migrations, the development launcher and CI helpers; recommended
basedpyright across backend and launcher; all backend tests with four workers; the
launcher's 39 tests; and Python wheel/source builds. The same locked Ruff drives
prek, removing the separate hook-version mismatch. Launcher security-lint exceptions
identify existing developer-PATH subprocesses, internal assertions and synthetic
test credentials at their narrow source/file scope.

`bun install --cwd frontend --frozen-lockfile` prepares SvelteKit types. Run
`bun run --cwd frontend check:biome`, `check`, and `test`; Vitest is bounded to four
workers. Biome is aligned with the existing 2.5.8 schema instead of running the older
2.4.14 CLI. The full root-aware check also covers the API-check helper. Existing
custom ARIA groups/radios/checkboxes, drag containers and dismiss overlay have
localized explanations for keeping their established controls/layout. Log selection
now uses a real button with keyboard activation and a selected-state announcement;
its component test exercises Enter and Space. Standalone SVGs have accessible titles.
One pre-existing unused snippet parameter warning and four style advisories remain
visible; Svelte/TypeScript and Python types must have zero errors and warnings.

Integration builds the frontend once, runs `bun .github/scripts/check-api.ts`, then
`python .github/scripts/smoke.py`. The API check generates declarations from the
actual backend OpenAPI schema and compares parsed declarations without comments,
because Litestar's illustrative example dates vary. It never rewrites tracked API
types. The smoke applies real Alembic migrations to a temporary database, starts
Granian via the repaired installed `zondarr` entry point and the built Bun server,
and verifies database readiness, API proxy parity, setup SSR and bootstrap-token
handoff over loopback. Both processes and all temporary data are cleaned up.

## Renovate and remaining limits

The shared default/mixed presets handle Python/uv, Bun, actions, hooks and Biome
schema/package versions, grouping non-major updates by ecosystem. TypeScript stays
below 7 until the Svelte compiler API is compatible. Automerge stays off during
adoption; dependency PRs require the same full CI review.

Biome repair installs from the frontend package directory and migrates both configs.
It computes with read-only permissions; a separate publisher writes allowlisted
frontend changes and explicitly dispatches full CI for the exact repaired SHA.
CI helper changes and repairs beyond shared size limits need manual handling.
Shared releases reach consumers through Renovate PRs using immutable full tags.

Tests use SQLite and fixture media clients, not live Plex/Jellyfin or PostgreSQL.
Browser visual/accessibility coverage is limited to component tests and server smoke;
there is no real-browser E2E suite here. The dev launcher retains its existing
all-interface backend listener. Backend tests expose an existing coroutine cleanup
warning in a mocked probe; it is visible in CI logs. External container packaging
and deployments remain separate from these development gates.
