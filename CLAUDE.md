# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zondarr is a unified invitation and user management system for Plex and Jellyfin media servers. It's a monorepo with a Python backend (Litestar) and a SvelteKit frontend.

## Development Commands

### Quick Start

```bash
# Start both backend and frontend (recommended)
uv run dev_cli

# With options
uv run dev_cli --skip-auth    # Skip authentication (mock admin)
uv run dev_cli --backend-only
uv run dev_cli --frontend-only
uv run dev_cli --open          # Open browser
uv run dev_cli stop            # Stop servers
```

### Backend (Python 3.14+ / Litestar)

```bash
cd backend
uv sync                          # Install dependencies
uv run pytest                    # Run tests (parallel by default via -n auto)
uv run pytest tests/test_foo.py  # Run single test file
uv run pytest -k "test_name"    # Run test by name
uv run basedpyright             # Type checking
uv run ruff check .             # Lint
uv run ruff format .            # Format
alembic upgrade head            # Run migrations
alembic revision --autogenerate -m "description"  # Create migration
```

### Frontend (SvelteKit / Bun)

```bash
cd frontend
bun install                      # Install dependencies
bun run dev                      # Dev server
bun run build                    # Production build
bun run check                    # TypeScript + Svelte type checking
bun run test                     # Run tests (vitest)
bun run test:watch               # Watch mode
bun run generate:api             # Regenerate OpenAPI types from backend
```

### Linting (root)

```bash
# Pre-commit hooks (Ruff for Python, Biome for frontend)
bunx prek run --all-files
```

## Architecture

### Backend (`backend/src/zondarr/`)

Layered architecture with Litestar's dependency injection:

- **`app.py`** — Application factory, middleware registration, lifespan events
- **`config.py`** — Settings via `msgspec.Struct` (loaded from env vars)
- **`api/`** — Route controllers and request/response schemas. Controllers receive dependencies (session, settings) via Litestar DI
- **`models/`** — SQLAlchemy 2.0 async ORM models. Base model provides `id: UUID`, `created_at`, `updated_at`
- **`repositories/`** — Generic repository pattern for data access. Base class provides CRUD with filtering, pagination, sorting
- **`services/`** — Business logic layer
- **`core/`** — Auth (JWT cookies), CSRF, database engine/session, background tasks, log buffer (SSE)
- **`media/`** — Plugin system for media server providers (Plex, Jellyfin). Registry-based with each provider implementing a common protocol

Serialization uses **msgspec** (not Pydantic). Pydantic is only present as a transitive dependency of jellyfin-sdk.

### Frontend (`frontend/src/`)

- **`routes/`** — SvelteKit file-based routing with route groups: `(auth)/` for login/setup, `(public)/` for join pages, `(admin)/` for dashboard
- **`lib/api/client.ts`** — Type-safe API client using `openapi-fetch`. Types auto-generated from backend OpenAPI schema
- **`lib/api/types.d.ts`** — Generated file (run `bun run generate:api` after backend API changes)
- **`lib/stores/`** — Svelte reactive stores (SSE log stream, providers)
- **`lib/components/ui/`** — Bits UI components (shadcn-style accessible components)
- **`lib/schemas/`** — Zod validation schemas
- **`hooks.server.ts`** — Server hooks for auth checking and route protection

Styling: UnoCSS with Tailwind preset + shadcn preset. Component variants via `tailwind-variants`.

### Frontend-Backend Integration

- Backend serves OpenAPI schema at `/docs/openapi.json`
- Frontend generates TypeScript types from it (`bun run generate:api`)
- API calls use `openapi-fetch` with `credentials: 'include'` for JWT cookie auth
- `PUBLIC_API_URL` env var configures the backend URL (dev_cli sets this automatically)

### Key Subsystems

- **Auth**: JWT cookie-based (`zondarr_access_token`). Dev mode supports `DEV_SKIP_AUTH=true` (requires `DEBUG=true`)
- **Media Providers**: Registry pattern in `media/registry.py`. Each provider (Plex, Jellyfin) has its own client, auth, and sync logic
- **Background Tasks**: `BackgroundTaskManager` runs invitation expiration checks and media server sync on configurable intervals
- **Log Streaming**: Structured logs via structlog captured in `log_buffer.py`, streamed to frontend via SSE at `/api/logs/stream`
- **Wizard System**: Configurable multi-step onboarding wizards with various interaction types (click, timer, ToS, text input, quiz)

## Coding Guidelines

**Before making any changes**, read and follow the coding patterns established in:
- Backend: `.augment/rules/backend-dev-pro.md`
- Frontend: `.augment/rules/frontend-dev-pro.md`

## Code Conventions

- Backend: Ruff for linting/formatting (line-length 88), basedpyright for type checking (recommended mode)
- Frontend: Biome for linting/formatting, svelte-check for type checking
- Structured logging: `logger.info("event_name", key="value")` — use structured key-value style
- Pre-commit hooks block direct commits to `main`
- Tests and type checks run as pre-push hooks

## Environment

Copy `.env.example` to `.env`. The only required variable is `SECRET_KEY` (min 32 chars). The dev_cli auto-generates it if not set. Database defaults to SQLite for development.
