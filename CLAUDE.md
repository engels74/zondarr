# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zondarr is a unified invitation and user management system for media servers (Plex, Jellyfin). It enables administrators to create time-limited, configurable invitation codes for granting users access to media server libraries.

## Tech Stack

- **Backend**: Python 3.14+, Litestar 2.15+, msgspec (not Pydantic), Granian, SQLAlchemy 2.0 async, Alembic
- **Frontend**: Bun, TypeScript, SvelteKit 2, Svelte 5 (Runes-only), UnoCSS, shadcn-svelte
- **Testing**: pytest, pytest-asyncio, Hypothesis (property-based)
- **Linting**: Ruff (Python), Biome (JS/TS/Svelte)
- **Type Checking**: basedpyright (Python), TypeScript strict mode

## Common Commands

### Backend (from `backend/` directory)

```bash
uv sync                                              # Install dependencies
uv run granian zondarr.app:app --interface asgi      # Run dev server
uv run basedpyright                                  # Type check
uv run ruff check . --fix && uv run ruff format .    # Lint and format
uv run pytest                                        # Run all tests
uv run pytest -k "test_name"                         # Run specific test
uv run pytest tests/property/                        # Property-based tests only
uv run alembic upgrade head                          # Apply migrations
uv run alembic revision --autogenerate -m "msg"      # Generate migration
```

### Frontend (from `frontend/` directory)

```bash
bun install                    # Install dependencies
bun --bun run dev              # Dev server (--bun forces Bun runtime)
bun --bun run build            # Production build
```

### Root Workspace

```bash
bun run lint                   # Run all linters via prek
bun run lint:staged            # Lint staged files (pre-commit)
```

## Architecture

### Backend Layering (Bottom-Up)

1. **Core** (`core/`) — Database connections, configuration, base exceptions
2. **Models** (`models/`) — SQLAlchemy ORM entities
3. **Repositories** (`repositories/`) — Async data access with pagination/filtering
4. **Services** (`services/`) — Business logic, transactions, rollback support
5. **API** (`api/`) — Litestar controllers and msgspec DTOs
6. **Media Clients** (`media/`) — Protocol-based integrations (Plex, Jellyfin)

### Key Patterns

- **All DTOs use `msgspec.Struct`** — Validation occurs during `msgspec.convert()`, not on `__init__`
- **Protocol-based abstraction** — Media clients implement `MediaClient` protocol (structural typing)
- **Repository pattern** — Async-first, composable queries
- **Service layer** — Encapsulates transactions with atomicity guarantees and rollback support

### Frontend Patterns

- **Runes-only** — `$state()`, `$derived()`, `$effect()`, `$props()`, `$bindable()`
- **No slots** — Replaced with `{@render children?.()}`
- **No `$:` statements or writable stores** — Use Runes exclusively

## Code Conventions

### Python

- Async-first for all database and external API calls
- Python 3.14 deferred annotations (no string quotes for forward refs)
- Double quotes for all strings (Ruff standard)
- structlog for logging (not print statements)
- Custom exception hierarchy with error codes

### TypeScript/Svelte

- Tab indentation, single quotes, no trailing commas (Biome config)
- TypeScript strict mode enabled
- Always use `--bun` flag with `bun run` to avoid Node.js fallback

## Pre-commit Hooks

- **Pre-commit stage**: Formatting/linting only (Ruff, Biome)
- **Pre-push stage**: Type checking and tests run here

## Environment Variables

```bash
SECRET_KEY="your-32-char-minimum-key"  # Required for JWT
DATABASE_URL="sqlite+aiosqlite:///./zondarr.db"  # Optional
DEBUG="true"  # Optional
```

## Adding Media Server Support

New media servers require implementing the `MediaClient` protocol in `media/protocol.py` and registering in `media/registry.py`.
