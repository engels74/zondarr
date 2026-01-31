# Tech Stack

## Runtime & Languages

- **Backend**: Python 3.14+ (deferred annotations, PEP 695 type parameter syntax)
- **Frontend**: TypeScript strict mode with Svelte 5 + SvelteKit
- **Package Management**: uv (backend), Bun (frontend)

---

## Backend

### Framework

- **Litestar** (>=2.15) - async web framework with class-based controllers
- **Granian** (>=2.6) - Rust-powered ASGI server (41k+ RPS, lower latency than Uvicorn)
- **msgspec** (>=0.19) - high-performance serialization (10-80x faster than Pydantic)
- **structlog** (>=25.0) - structured logging

### Database

- **SQLAlchemy 2.0** - async ORM with `mapped_column` and `Mapped` types
- **Alembic** (>=1.15) - database migrations
- **aiosqlite** (>=0.21) - async SQLite driver (development)
- **asyncpg** (>=0.30) - async PostgreSQL driver (production)

### Media Server SDKs

- **python-plexapi** (>=4.18) - Plex server communication (sync library, wrap with `asyncio.to_thread()`)
- **jellyfin-sdk** (>=0.3) - Modern Jellyfin SDK (Python 3.13+, native async)

### Dev Tools

- **ruff** (>=0.14) - linting and formatting (line-length 88, py314 target)
- **basedpyright** (>=1.29) - type checking (recommended mode)
- **pytest** (>=8.3) + **pytest-asyncio** (>=0.26) - testing with `asyncio_mode = "auto"`
- **hypothesis** (>=6.130) - property-based testing

---

## Frontend

### Framework

- **Svelte 5** - Runes-only (no legacy stores, no `$:` reactive statements, no `export let`)
- **SvelteKit** - file-based routing, SSR/SSG/CSR support
- **Bun** - runtime, package manager, and build tool

### UI Components

- **shadcn-svelte** - accessible, customizable component library (Svelte 5 port of shadcn/ui)

### Styling

- **UnoCSS** - atomic CSS engine with on-demand generation
  - `presetWind4` - Tailwind CSS 4 compatible utilities
  - `presetShadcn` - shadcn/ui CSS variable and theme support

### Key Libraries

- **openapi-fetch** + **openapi-typescript** - type-safe API client from OpenAPI spec
- **sveltekit-superforms** + **zod** - form validation
- **@sveltejs/enhanced-img** - image optimization

### Dev Tools

- **Vitest** - testing with `@testing-library/svelte`
- **TypeScript** - strict mode with `noUncheckedIndexedAccess`

---

## Common Commands

### Backend

```bash
# Install dependencies
uv sync

# Run development server
granian zondarr.app:app --interface asgi --host 0.0.0.0 --port 8000

# Production server (single worker per container, scale via replicas)
granian zondarr.app:app --interface asgi --workers 1 --runtime-mode st --loop uvloop

# Type checking
basedpyright

# Linting and formatting
ruff check .
ruff format .

# Run tests
pytest

# Run migrations
alembic upgrade head
alembic downgrade -1
```

### Frontend

```bash
# Install dependencies
bun install

# Run development server
bun run dev

# Build for production
bun --bun run vite build

# Run production build
bun ./build/index.js

# Run tests
bun test

# Generate API types from OpenAPI spec
bunx openapi-typescript ./api/openapi.json -o ./src/lib/api/types.d.ts
```

---

## Key Patterns

### Backend: Serialization (msgspec)
- Use `msgspec.Struct` for all request/response models (not Pydantic)
- Use `kw_only=True, forbid_unknown_fields=True` for request structs
- Use `omit_defaults=True` for response structs
- Use `Annotated[T, msgspec.Meta(...)]` for validation constraints

### Backend: Type System
- Use `typing.Protocol` for interfaces (structural subtyping, no inheritance)
- Use PEP 695 type parameter syntax: `class Repository[T: Base]`
- Use `Self` type for method chaining and factory methods
- Use positional-only (`/`) and keyword-only (`*`) parameters where appropriate

### Backend: Database
- Use async context managers for connection lifecycle
- Use `selectinload` for collections, `joined` for single relations
- Use `expire_on_commit=False` in session factory
- Wrap all repository operations in try/except, raise `RepositoryError`

### Backend: Dependency Injection
- Use Litestar's `Provide` system for DI
- Use generator dependencies for session management with auto commit/rollback
- Use lifespan context managers for connection pool management

### Backend: Error Handling
- All domain exceptions inherit from `ZondarrError`
- Include `error_code` and context in all exceptions
- Generate correlation IDs for all error responses
- Never expose internal details (stack traces, file paths) in responses

### Frontend: Svelte 5 Runes
- Use `$state()` for reactive variables (deep proxy by default)
- Use `$derived()` for computed values (not `$effect`)
- Use `$effect()` only for side effects (DOM, subscriptions)
- Use `$props()` with TypeScript interface for component props
- Use `$bindable()` for two-way binding (opt-in only)
- Use snippets (`{#snippet}` / `{@render}`) instead of slots

### Frontend: SvelteKit Data Loading
- Use `+page.server.ts` for sensitive operations (DB, secrets, cookies)
- Use `+page.ts` for external APIs and non-serializable data
- Use `Promise.all()` for parallel data fetching (avoid waterfalls)
- Use `depends()` + `invalidate()` for cache invalidation
- Return promises without `await` for streaming non-critical data

### Frontend: Forms
- Use SvelteKit form actions with `use:enhance` for progressive enhancement
- Use `sveltekit-superforms` + `zod` for validation
- Forms work without JavaScript when using actions

### Frontend: API Integration
- Generate TypeScript types from backend OpenAPI spec
- Use `openapi-fetch` for type-safe API calls
- Define `App.Locals`, `App.Error`, `App.PageData` in `app.d.ts`
