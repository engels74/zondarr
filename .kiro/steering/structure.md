# Project Structure

```
zondarr/
├── backend/
│   ├── src/zondarr/
│   │   ├── __init__.py
│   │   ├── app.py                 # Litestar application factory (create_app)
│   │   ├── config.py              # Settings msgspec.Struct, load_settings()
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── database.py        # Engine creation, session factory, lifespan
│   │   │   ├── exceptions.py      # ZondarrError hierarchy
│   │   │   └── types.py           # Shared type aliases
│   │   │
│   │   ├── media/
│   │   │   ├── __init__.py
│   │   │   ├── protocol.py        # MediaClient Protocol (typing.Protocol)
│   │   │   ├── registry.py        # ClientRegistry singleton
│   │   │   ├── types.py           # Capability enum, LibraryInfo, ExternalUser
│   │   │   ├── exceptions.py      # MediaClientError, UnknownServerTypeError
│   │   │   └── clients/
│   │   │       ├── __init__.py
│   │   │       ├── jellyfin.py    # JellyfinClient (jellyfin-sdk)
│   │   │       └── plex.py        # PlexClient (python-plexapi + asyncio.to_thread)
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Base, TimestampMixin, UUIDPrimaryKeyMixin
│   │   │   ├── media_server.py    # ServerType enum, MediaServer, Library
│   │   │   ├── invitation.py      # Invitation, association tables
│   │   │   └── identity.py        # Identity, User
│   │   │
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Repository[T: Base] generic base
│   │   │   ├── media_server.py    # MediaServerRepository
│   │   │   ├── invitation.py      # InvitationRepository
│   │   │   ├── identity.py        # IdentityRepository
│   │   │   └── user.py            # UserRepository
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── media_server.py    # MediaServerService
│   │   │   └── invitation.py      # InvitationService
│   │   │
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── health.py          # HealthController (/health, /live, /ready)
│   │       ├── schemas.py         # Request/response msgspec Structs
│   │       └── errors.py          # Exception handlers, ErrorResponse
│   │
│   ├── migrations/
│   │   ├── env.py                 # Alembic async config
│   │   └── versions/
│   │       └── 001_initial.py     # Initial schema migration
│   │
│   ├── tests/
│   │   ├── conftest.py            # Shared fixtures
│   │   ├── unit/                  # Unit tests
│   │   ├── property/              # Property-based tests (Hypothesis)
│   │   └── integration/           # Integration tests
│   │
│   ├── alembic.ini
│   └── pyproject.toml
│
└── frontend/
    ├── src/
    │   ├── lib/
    │   │   ├── components/        # Reusable UI components
    │   │   │   └── ui/            # shadcn-svelte components
    │   │   ├── server/            # Server-only code ($lib/server)
    │   │   │   ├── db/
    │   │   │   └── api/
    │   │   ├── api/               # API client (openapi-fetch)
    │   │   │   ├── client.ts
    │   │   │   └── types.d.ts     # Generated from OpenAPI spec
    │   │   ├── stores/            # Reactive state (.svelte.ts files)
    │   │   ├── utils/             # Utility functions
    │   │   └── types/             # Shared TypeScript types
    │   │
    │   ├── routes/
    │   │   ├── +layout.svelte     # Root layout
    │   │   ├── +page.svelte       # Home page
    │   │   ├── (app)/             # Authenticated routes (admin dashboard)
    │   │   │   ├── +layout.svelte
    │   │   │   ├── servers/       # Media server management
    │   │   │   ├── invitations/   # Invitation management
    │   │   │   └── users/         # User/identity management
    │   │   ├── (public)/          # Public routes
    │   │   │   └── invite/[code]/ # Invitation redemption
    │   │   └── api/               # API routes (if needed)
    │   │
    │   ├── app.css                # Global styles (UnoCSS)
    │   ├── app.d.ts               # App-level types (Locals, Error, PageData)
    │   ├── app.html               # HTML template
    │   └── hooks.server.ts        # Server hooks (auth, middleware)
    │
    ├── static/
    ├── tests/
    │   ├── *.svelte.test.ts       # Component tests (Vitest)
    │   └── e2e/                   # E2E tests (Playwright)
    ├── svelte.config.js
    ├── vite.config.ts
    ├── uno.config.ts              # UnoCSS configuration
    ├── tsconfig.json
    ├── bunfig.toml
    └── package.json
```

## Backend Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│  API Layer (Litestar Controllers)                           │
│  - HTTP request/response handling                           │
│  - Input validation (msgspec)                               │
│  - OpenAPI documentation                                    │
├─────────────────────────────────────────────────────────────┤
│  Service Layer                                              │
│  - Business logic orchestration                             │
│  - Transaction management                                   │
│  - Cross-cutting concerns                                   │
├─────────────────────────────────────────────────────────────┤
│  Repository Layer                                           │
│  - Data access abstraction                                  │
│  - Query building                                           │
│  - Error wrapping (RepositoryError)                         │
├─────────────────────────────────────────────────────────────┤
│  Media Layer                                                │
│  - Protocol-based client abstraction                        │
│  - Registry pattern for client lookup                       │
│  - External media server communication                      │
├─────────────────────────────────────────────────────────────┤
│  Data Layer (SQLAlchemy Models)                             │
│  - Entity definitions                                       │
│  - Relationships                                            │
│  - Database connection management                           │
└─────────────────────────────────────────────────────────────┘
```

## Frontend Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Routes (+page.svelte, +layout.svelte)                      │
│  - File-based routing with route groups                     │
│  - SSR/SSG/CSR per route                                    │
│  - Form actions with progressive enhancement                │
├─────────────────────────────────────────────────────────────┤
│  Load Functions (+page.ts, +page.server.ts)                 │
│  - Data fetching with streaming support                     │
│  - Server-only for sensitive ops (DB, secrets, cookies)     │
│  - Universal load for external APIs                         │
├─────────────────────────────────────────────────────────────┤
│  Components ($lib/components)                               │
│  - Svelte 5 Runes ($state, $derived, $props, $bindable)     │
│  - Snippets for composition ({#snippet}, {@render})         │
│  - shadcn-svelte components + UnoCSS utilities              │
├─────────────────────────────────────────────────────────────┤
│  Reactive State ($lib/stores/*.svelte.ts)                   │
│  - Class-based state with $state and $derived               │
│  - Context API for component subtrees                       │
│  - No legacy stores (writable/readable)                     │
├─────────────────────────────────────────────────────────────┤
│  API Client ($lib/api)                                      │
│  - openapi-fetch for type-safe calls                        │
│  - Types generated from OpenAPI spec                        │
├─────────────────────────────────────────────────────────────┤
│  Server Hooks (hooks.server.ts)                             │
│  - Authentication middleware                                │
│  - Protected route guards                                   │
│  - Error handling                                           │
└─────────────────────────────────────────────────────────────┘
```

Dependencies flow downward only. Upper layers depend on abstractions (protocols) of lower layers.

## Naming Conventions

### Backend

| Type | Convention | Example |
|------|------------|---------|
| Models | Singular PascalCase | `MediaServer`, `User` |
| Tables | Plural snake_case | `media_servers`, `users` |
| Repositories | `{Model}Repository` | `MediaServerRepository` |
| Services | `{Domain}Service` | `InvitationService` |
| Controllers | `{Domain}Controller` | `HealthController` |
| Enums | PascalCase with UPPER values | `ServerType.JELLYFIN` |
| Association tables | `{entity1}_{entity2}` | `invitation_servers` |

### Frontend

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase `.svelte` | `ServerCard.svelte` |
| Routes | kebab-case folders | `media-servers/[id]/` |
| Route groups | `(groupname)` | `(app)/`, `(public)/` |
| Reactive modules | camelCase `.svelte.ts` | `createCounter.svelte.ts` |
| Types | PascalCase | `MediaServer`, `Invitation` |
| API client | `$lib/api/client.ts` | - |
| Snippets | camelCase | `{#snippet headerContent()}` |
| Props interface | PascalCase | `interface Props { ... }` |

## Database Models

| Model | Table | Key Fields |
|-------|-------|------------|
| MediaServer | `media_servers` | id, name, server_type, url, api_key, enabled |
| Library | `libraries` | id, media_server_id, external_id, name, library_type |
| Invitation | `invitations` | id, code, expires_at, max_uses, use_count, enabled |
| Identity | `identities` | id, display_name, email, expires_at, enabled |
| User | `users` | id, identity_id, media_server_id, external_user_id, username |

## Frontend Routes

| Route | Purpose |
|-------|---------|
| `/` | Landing/home page |
| `/(app)/servers` | Media server management |
| `/(app)/invitations` | Invitation management |
| `/(app)/users` | User/identity management |
| `/(public)/invite/[code]` | Invitation redemption (public) |

## Testing Organization

### Backend
- `tests/unit/` - Specific examples, edge cases, mocked dependencies
- `tests/property/` - Hypothesis property tests (100+ iterations per property)
- `tests/integration/` - Full stack tests, migration tests

### Frontend
- `tests/` - Vitest + @testing-library/svelte
- Use `flushSync()` when testing reactive updates in `.svelte.ts` modules
- Files using Runes in tests must have `.svelte.test.ts` extension
- E2E tests with Playwright in `tests/e2e/`
