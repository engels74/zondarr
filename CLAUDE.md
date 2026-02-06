# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zondarr is a unified invitation and user management system for Plex and Jellyfin media servers. It's a monorepo with a Python async backend and a Svelte 5 frontend.

## Commands

### Backend (from `backend/`)

```bash
uv sync                              # Install dependencies
uv run granian zondarr.app:app --interface asgi --host 0.0.0.0 --port 8000  # Dev server
pytest                               # Run all tests (parallel by default via -n auto)
pytest tests/property/               # Property tests only
pytest tests/path/to/test.py::test_name  # Single test
ruff check .                         # Lint
ruff format .                        # Format
uv run basedpyright                  # Type checking (strict)
uv run alembic upgrade head          # Run migrations
uv run alembic revision --autogenerate -m "description"  # Create migration
```

### Frontend (from `frontend/`)

```bash
bun install                          # Install dependencies
bun run dev                          # Dev server (Vite, port 5173)
bun test                             # Run tests (vitest, single run)
bun test:watch                       # Tests in watch mode
bunx biome check --write             # Lint + format
bun run check                        # TypeScript/Svelte type checking
bun run generate:api                 # Regenerate API types from running backend OpenAPI
```

### Workspace root

```bash
prek install                         # Install pre-commit hooks
prek run --all-files                 # Run all linters
```

## Architecture

### Backend — Python 3.14, Litestar, msgspec, Granian

- **Framework:** Litestar (async web framework) served by Granian (Rust ASGI server)
- **Serialization:** msgspec Structs (not Pydantic) — used for both API schemas and config
- **Database:** SQLAlchemy 2.0 async with aiosqlite (default) or asyncpg (PostgreSQL). Migrations via Alembic
- **App factory:** `create_app()` in `app.py`, returns a `Litestar` instance. `app = create_app()` is the module-level instance for Granian
- **Configuration:** `Settings` msgspec Struct loaded from env vars via `load_settings()`. Only required env var: `SECRET_KEY` (min 32 chars)

**Layer structure:**
- `api/` — Litestar Controllers (route handlers). Each controller maps to a resource (invitations, users, servers, wizards, join, plex_oauth, health)
- `repositories/` — Data access layer using repository pattern. `BaseRepository` generic base class
- `models/` — SQLAlchemy ORM models. All use `UUIDPrimaryKeyMixin` and `TimestampMixin` from `models/base.py`
- `media/` — Media server integrations (Plex, Jellyfin). Uses a `registry` service locator pattern — clients implement a protocol and are registered in `app.py`
- `core/` — Database engine/session factory (`database.py`), domain exceptions (`exceptions.py`), background tasks (`tasks.py`)

**DI:** Database sessions are injected via `provide_db_session` generator dependency. Sessions auto-commit on success, rollback on exception.

**API base path:** `/api/v1/`. OpenAPI docs at `/docs`, Swagger at `/swagger`, Scalar at `/scalar`.

### Frontend — Svelte 5, SvelteKit 2, Bun

- **Reactivity:** Svelte 5 Runes only (`$state`, `$derived`, `$effect`, `$props`) — no legacy Svelte 4 patterns
- **Styling:** UnoCSS (atomic CSS) with shadcn-svelte component library (bits-ui)
- **API client:** `openapi-fetch` with types auto-generated from backend OpenAPI schema (`src/lib/api/types.d.ts`)
- **Forms:** sveltekit-superforms with Zod validation schemas (in `src/lib/schemas/`)
- **Linting/Formatting:** Biome — tabs, single quotes, no trailing commas, 100 char line width

**Route groups:**
- `(public)/` — Public-facing routes (e.g., `join/[code]` for invitation redemption)
- `(admin)/` — Admin dashboard routes (dashboard, wizards, servers, users)

**Key directories:**
- `src/lib/api/` — API client, error handling, generated types
- `src/lib/components/ui/` — shadcn-svelte UI components
- `src/lib/schemas/` — Zod validation schemas
- `src/lib/stores/` — Svelte reactive stores (`.svelte.ts` files)

### Testing

- **Backend:** pytest with pytest-asyncio (auto mode), pytest-xdist (parallel), Hypothesis (property-based). Tests use in-memory SQLite. Hypothesis profiles: `default` (15 examples), `fast` (5), `debug` (100)
- **Frontend:** Vitest with @testing-library/svelte and jsdom. fast-check for property testing

### Pre-commit Hooks

Hooks run automatically via `prek` (pre-commit alternative):
- **On commit:** trailing whitespace, file validation, ruff (lint+format), biome (lint+format)
- **On push:** basedpyright, svelte-check, pytest, vitest

## Key Technical Choices

- **msgspec over Pydantic** for serialization — Pydantic is only a transitive dependency via jellyfin-sdk, not used directly
- **Python 3.14** — uses deferred annotations (no `from __future__ import annotations`), generic type syntax (`class Repo[T, ID=int]`), template strings
- **Ruff** config: line-length 88, rules include bugbear (B), security (S), comprehensions (C4), ruff-specific (RUF). Security rules (S101, S106) disabled in tests
- **basedpyright** in recommended mode for type checking
