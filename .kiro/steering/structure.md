# Project Structure

```
zondarr/
├── backend/                    # Python API backend
│   ├── src/zondarr/           # Main package
│   │   ├── api/               # HTTP layer (controllers, schemas, error handlers)
│   │   ├── core/              # Shared infrastructure (database, exceptions, types)
│   │   ├── media/             # Media server abstraction layer
│   │   │   ├── clients/       # Platform implementations (jellyfin.py, plex.py)
│   │   │   ├── protocol.py    # MediaClient Protocol definition
│   │   │   ├── registry.py    # Client registration and factory
│   │   │   └── types.py       # Shared types (Capability, LibraryInfo, etc.)
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── repositories/      # Data access layer
│   │   ├── services/          # Business logic layer
│   │   ├── app.py             # Litestar application factory
│   │   └── config.py          # Settings management
│   ├── tests/                 # Test suite
│   │   └── property/          # Property-based tests (hypothesis)
│   ├── migrations/            # Alembic database migrations
│   └── pyproject.toml         # Python project config
│
├── frontend/                   # SvelteKit frontend (planned)
│   └── biome.json             # Linting config
│
├── docs/                       # Documentation
│   └── zondarr-plan-prompt.md # Full system specification
│
├── .kiro/                      # Kiro configuration
│   ├── specs/                 # Feature specifications
│   └── steering/              # AI assistant guidelines
│
└── .augment/rules/            # Detailed coding guidelines
    ├── backend-dev-pro.md     # Python/Litestar patterns
    └── frontend-dev-pro.md    # Svelte 5/SvelteKit patterns
```

## Key Architectural Patterns

### Media Client Abstraction
- Protocol-based interface (`MediaClient`) for all media server integrations
- Registry pattern for runtime client discovery and instantiation
- Each platform (Plex, Jellyfin) implements the protocol independently
- Capability declaration allows querying supported operations per platform

### Backend Layering
1. **Controllers** (api/) - HTTP handling, OpenAPI docs
2. **Services** - Business logic, orchestration
3. **Repositories** - Data access abstraction
4. **Models** - SQLAlchemy entities with mixins (UUID, timestamps)

### Configuration
- Environment variables loaded via `load_settings()`
- msgspec.Struct for validation
- App factory pattern (`create_app()`) for testing flexibility
