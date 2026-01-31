# Tech Stack

## Runtime & Languages

- **Backend**: Python 3.14+ (deferred annotations, PEP 695 type parameter syntax)
- **Frontend**: TypeScript strict mode with Svelte 5 + SvelteKit 2
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
- **SvelteKit 2** - file-based routing, SSR/SSG/CSR support
- **Bun** - runtime, package manager, and build tool
- **svelte-adapter-bun** - production adapter for Bun runtime

### UI Components

- **shadcn-svelte** - accessible, customizable component library (Svelte 5 port)
- **bits-ui** - headless component primitives (shadcn-svelte dependency)
- **mode-watcher** - dark mode management
- **@lucide/svelte** - icon library
- **svelte-sonner** - toast notifications

### Styling

- **UnoCSS** - atomic CSS engine with on-demand generation
  - `presetWind4` - Tailwind CSS 4 compatible utilities
  - `presetShadcn` - shadcn/ui CSS variable and theme support
  - `presetIcons` - icon support with on-demand loading
  - `presetAnimations` - animation utilities
  - `transformerVariantGroup` - variant grouping syntax

### Key Libraries

- **openapi-fetch** + **openapi-typescript** - type-safe API client from OpenAPI spec
- **sveltekit-superforms** + **zod** - form validation with progressive enhancement
- **@sveltejs/enhanced-img** - image optimization (AVIF/WebP, responsive srcsets)

### Dev Tools

- **Vitest** - testing with `@testing-library/svelte`
- **Playwright** - E2E testing
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

# Run development server (--bun forces Bun runtime)
bun --bun run dev

# Build for production
bun --bun run build

# Run production build
bun ./build/index.js

# Run tests
bun test

# E2E tests
bunx playwright test

# Generate API types from OpenAPI spec
bunx openapi-typescript ./api/openapi.json -o ./src/lib/api/types.d.ts

# Add shadcn-svelte components
bunx shadcn-svelte@latest add button dialog form
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

Runes are explicit compiler instructions for reactivity, replacing Svelte 4's implicit patterns.

- **`$state()`** - reactive variables with deep proxy by default
  - Use `$state.raw()` for large immutable data (requires full reassignment)
  - Use `$state.snapshot()` to extract plain objects from proxies
- **`$derived()`** - computed values with automatic memoization
  - Use `$derived.by()` for complex multi-statement derivations
  - Never use `$effect` to derive state
- **`$effect()`** - side effects only (DOM, subscriptions, localStorage)
  - Return cleanup function for resource management
- **`$props()`** - type-safe component props with TypeScript interface
  - Use `generics` attribute for generic components
- **`$bindable()`** - explicit opt-in for two-way binding
- **Snippets** - replace slots entirely
  - Use `{#snippet name()}` to define, `{@render name()}` to render
  - Use `children` snippet for default content

### Frontend: Class-Based State

Encapsulate reactive logic in `.svelte.ts` files:

```typescript
// counter.svelte.ts
export class Counter {
  count = $state(0);
  doubled = $derived(this.count * 2);
  increment = () => this.count++;
}
```

### Frontend: SvelteKit Data Loading

- **`+page.server.ts`** - server-only (DB, secrets, cookies, auth)
- **`+page.ts`** - universal load (runs server + client during navigation)
- Use `depends()` + `invalidate()` for cache invalidation
- Return promises without `await` for streaming non-critical data
- Use `error()` and `redirect()` from `@sveltejs/kit` for control flow

### Frontend: Forms with Progressive Enhancement

```svelte
<script lang="ts">
  import { enhance } from '$app/forms';
  let { form } = $props();
</script>

<form method="POST" action="?/create" use:enhance>
  <input name="title" value={form?.title ?? ''} />
  <button>Create</button>
</form>
```

- Use SvelteKit form actions with `use:enhance`
- Use `sveltekit-superforms` + `zod` for validation
- Forms work without JavaScript when using actions

### Frontend: API Integration

- Generate TypeScript types from backend OpenAPI spec
- Use `openapi-fetch` for type-safe API calls
- Define `App.Locals`, `App.Error`, `App.PageData` in `app.d.ts`

### Frontend: State Management Decision Tree

1. **Single component** → `$state()` / `$derived()`
2. **Parent-child** → `$props()` with `$bindable()` if needed
3. **Component subtree** → Context API with `setContext`/`getContext`
4. **Global client-only** → `.svelte.ts` module state
5. **Global with SSR** → Context API initialized in `+layout.svelte`
6. **Persist across refreshes** → localStorage (client) or cookies (SSR)
7. **URL-shareable** → `$page.url.searchParams`

**SSR Warning**: Module-level `$state` is shared between all users on the server. Use context for per-request state.

---

## Anti-Patterns to Avoid

### Frontend (Svelte 5)
- ❌ Using `$:` reactive statements → Use `$derived()`
- ❌ Using `export let` → Use `let { prop } = $props()`
- ❌ Using `<slot>` → Use `{@render children?.()}`
- ❌ Using `writable`/`readable` stores → Use `.svelte.ts` with `$state`
- ❌ Using `$effect` to derive state → Use `$derived`
- ❌ Destructuring reactive proxies → Breaks reactivity
- ❌ `bun run dev` without `--bun` → Still uses Node.js
- ❌ Module-level `$state` with SSR → Shared between users
- ❌ Accessing `localStorage` during SSR → Guard with `browser` check

### Backend
- ❌ Blocking event loop with sync I/O → Use `sync_to_thread=True`
- ❌ Lazy loading in async contexts → Use explicit eager loading
- ❌ Validating msgspec Structs at init → Validation only during decode
- ❌ Sharing database sessions across concurrent tasks → Create per-task sessions
