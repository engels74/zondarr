# Technology Stack

## Backend
- **Runtime**: Python 3.14+
- **Framework**: Litestar (controller-based, async)
- **Server**: Granian (Rust-based ASGI)
- **Serialization**: msgspec (Structs for DTOs, validation via Meta annotations)
- **Database**: SQLAlchemy 2.0 async (SQLite dev / PostgreSQL prod)
- **Migrations**: Alembic
- **Logging**: structlog
- **HTTP Client**: httpx
- **Media APIs**: plexapi, jellyfin-sdk

## Frontend (planned)
- **Runtime**: Bun
- **Framework**: Svelte 5 (Runes-only) + SvelteKit
- **Styling**: UnoCSS (presetWind4 + presetShadcn)
- **Components**: shadcn-svelte
- **Forms**: Superforms + Formsnap
- **API Client**: openapi-fetch (generated from OpenAPI spec)

## Development Tools
- **Package Manager**: uv (backend), bun (frontend)
- **Type Checking**: basedpyright (strict)
- **Linting/Formatting**: ruff
- **Testing**: pytest, pytest-asyncio, hypothesis (property-based)
- **Pre-commit**: prek

## Common Commands

### Backend (from `backend/` directory)
```bash
# Install dependencies
uv sync

# Run development server
granian zondarr.app:app --interface asgi --host 0.0.0.0 --port 8000

# Type checking
basedpyright

# Linting and formatting
ruff check .
ruff format .

# Run tests
pytest

# Run tests with coverage
pytest --cov

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Frontend (from `frontend/` directory, when implemented)
```bash
# Install dependencies
bun install

# Development (must use --bun flag)
bun --bun run dev

# Build
bun --bun run build
```

### Root workspace
```bash
# Run pre-commit hooks
bun run lint
```
