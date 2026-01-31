# Requirements Document

## Introduction

This document specifies the requirements for the Zondarr Foundation phase - a unified invitation and user management system for media servers (Plex, Jellyfin). The foundation phase establishes the core infrastructure including project scaffolding, database models, media client protocol/registry, and a basic Litestar application with health endpoints.

Zondarr enables administrators to generate secure invitation codes that users can redeem to gain access to one or more media servers. The system supports multiple media server types through a pluggable client architecture.

The implementation targets Python 3.14+ with Litestar framework, msgspec for serialization, SQLAlchemy 2.0 async, and Granian server.

## Glossary

- **Media_Server**: A Plex or Jellyfin instance that Zondarr manages user access for
- **Media_Client**: A protocol-based abstraction that communicates with a specific media server type
- **Client_Registry**: A singleton registry that manages available media client implementations
- **Invitation**: A secure, time-limited code that grants access to one or more media servers
- **Identity**: A user's account within Zondarr that links to accounts on media servers
- **Library**: A content collection within a media server (movies, TV shows, music)
- **Capability**: A feature that a media client may or may not support (e.g., library restrictions, download permissions)
- **Health_Endpoint**: An API endpoint that reports system and dependency status
- **Repository**: A data access layer component that handles database operations for a specific entity
- **Service**: A business logic layer component that orchestrates operations across repositories

## Requirements

### Requirement 1: Project Structure and Configuration

**User Story:** As a developer, I want a well-organized project structure with proper configuration, so that I can develop and maintain the codebase efficiently.

#### Acceptance Criteria

1. THE Project SHALL use a feature-based modular organization under `src/zondarr/`
2. THE Project SHALL include separate modules for `core`, `media`, `invitations`, `users`, and `api`
3. THE Configuration_Module SHALL load settings from environment variables with sensible defaults
4. THE Configuration_Module SHALL support both SQLite and PostgreSQL database URLs
5. THE Configuration_Module SHALL validate required settings at startup
6. IF a required configuration value is missing, THEN THE Application SHALL fail fast with a descriptive error message

### Requirement 2: Database Models and Schema

**User Story:** As a developer, I want well-defined database models, so that I can persist and query application data reliably.

#### Acceptance Criteria

1. THE Database_Module SHALL define a MediaServer model with fields: id (UUID), name, server_type (enum: plex/jellyfin), url, api_key (encrypted), enabled, created_at, updated_at
2. THE Database_Module SHALL define a Library model with fields: id (UUID), media_server_id (FK), external_id, name, library_type, created_at
3. THE Database_Module SHALL define an Invitation model with fields: id (UUID), code (unique), expires_at (nullable), max_uses (nullable), use_count, duration_days (nullable), enabled, created_at, created_by
4. THE Database_Module SHALL define an Identity model with fields: id (UUID), display_name, email (nullable), created_at, expires_at (nullable), enabled
5. THE Database_Module SHALL define a User model with fields: id (UUID), identity_id (FK), media_server_id (FK), external_user_id, username, created_at, expires_at (nullable), enabled
6. THE Database_Module SHALL define invitation_servers (many-to-many) and invitation_libraries (many-to-many) association tables
7. WHEN a model is serialized, THE Database_Module SHALL convert UUIDs to strings and datetimes to ISO format
8. THE Database_Module SHALL use SQLAlchemy 2.0 async patterns with mapped_column and Mapped types

### Requirement 3: Media Client Protocol

**User Story:** As a developer, I want a protocol-based abstraction for media clients, so that I can add support for new media server types without modifying existing code.

#### Acceptance Criteria

1. THE Media_Client_Protocol SHALL define an async method `test_connection() -> bool` to verify server connectivity
2. THE Media_Client_Protocol SHALL define an async method `get_libraries() -> list[LibraryInfo]` to retrieve available libraries
3. THE Media_Client_Protocol SHALL define an async method `create_user(username, password, email) -> ExternalUser` to create a user on the media server
4. THE Media_Client_Protocol SHALL define an async method `delete_user(external_user_id) -> bool` to remove a user from the media server
5. THE Media_Client_Protocol SHALL define an async method `set_user_enabled(external_user_id, enabled) -> bool` to enable or disable a user
6. THE Media_Client_Protocol SHALL define an async method `set_library_access(external_user_id, library_ids) -> bool` to configure library permissions
7. THE Media_Client_Protocol SHALL define a class method `capabilities() -> set[Capability]` to declare supported features
8. THE Media_Client_Protocol SHALL use Python's typing.Protocol for structural subtyping without inheritance requirements
9. WHEN a media client method fails, THE Media_Client SHALL raise a MediaClientError with context about the failure
10. THE Media_Client_Protocol SHALL support async context manager pattern for connection lifecycle management

### Requirement 4: Client Registry

**User Story:** As a developer, I want a registry for media clients, so that I can dynamically instantiate the correct client for each media server type.

#### Acceptance Criteria

1. THE Client_Registry SHALL provide a `register(server_type, client_class)` method to register client implementations
2. THE Client_Registry SHALL provide a `get_client(media_server) -> MediaClient` method to instantiate a client for a server
3. THE Client_Registry SHALL provide a `get_capabilities(server_type) -> set[Capability]` method to query supported features
4. IF an unregistered server type is requested, THEN THE Client_Registry SHALL raise an UnknownServerTypeError
5. THE Client_Registry SHALL be implemented as a singleton accessible throughout the application
6. WHEN the application starts, THE Client_Registry SHALL have Jellyfin and Plex client types registered (as stubs initially)

### Requirement 5: Repository Layer

**User Story:** As a developer, I want a repository layer for data access, so that I can separate database operations from business logic.

#### Acceptance Criteria

1. THE Repository_Layer SHALL define a base Repository class with common CRUD operations
2. THE MediaServerRepository SHALL provide methods: get_by_id, get_all, get_enabled, create, update, delete
3. THE InvitationRepository SHALL provide methods: get_by_id, get_by_code, get_active, create, increment_use_count, disable
4. THE IdentityRepository SHALL provide methods: get_by_id, get_all, create, update, delete
5. THE UserRepository SHALL provide methods: get_by_id, get_by_identity, get_by_server, create, update, delete
6. WHEN a repository method fails due to database error, THE Repository SHALL raise a RepositoryError with the original exception

### Requirement 6: Service Layer

**User Story:** As a developer, I want a service layer for business logic, so that I can orchestrate complex operations across multiple repositories.

#### Acceptance Criteria

1. THE MediaServerService SHALL provide methods to add, update, remove, and test media server connections
2. THE MediaServerService SHALL sync libraries from a media server when requested
3. WHEN a media server is added, THE MediaServerService SHALL validate the connection before persisting
4. THE InvitationService SHALL provide methods to create, validate, and redeem invitations
5. WHEN an invitation is redeemed, THE InvitationService SHALL check expiration, use count, and enabled status
6. IF an invitation validation fails, THEN THE InvitationService SHALL return a specific error indicating the failure reason

### Requirement 7: Litestar Application Setup

**User Story:** As a developer, I want a properly configured Litestar application, so that I can build a high-performance API.

#### Acceptance Criteria

1. THE Application SHALL use Litestar framework with async request handling
2. THE Application SHALL configure dependency injection for database sessions, repositories, and services using Litestar's Provide system
3. THE Application SHALL use msgspec.Struct for all request/response serialization with validation constraints via Meta annotations
4. THE Application SHALL configure OpenAPI 3.1 documentation at `/docs` with Swagger and Scalar render plugins
5. THE Application SHALL use lifespan context managers for database connection pool management
6. THE Application SHALL configure structured logging with structlog plugin
7. THE Application SHALL be deployable with Granian server using ASGI interface
8. WHEN the application starts, THE Application SHALL run database migrations automatically

### Requirement 8: Health Endpoints

**User Story:** As an operator, I want health check endpoints, so that I can monitor the application's status and integrate with orchestration systems.

#### Acceptance Criteria

1. THE Health_Controller SHALL expose a `GET /health` endpoint returning overall system status
2. THE Health_Controller SHALL expose a `GET /health/live` endpoint for Kubernetes liveness probes
3. THE Health_Controller SHALL expose a `GET /health/ready` endpoint for Kubernetes readiness probes
4. WHEN the database is unreachable, THE `/health` endpoint SHALL return status "degraded" with HTTP 503
5. WHEN all dependencies are healthy, THE `/health` endpoint SHALL return status "healthy" with HTTP 200
6. THE `/health/live` endpoint SHALL always return HTTP 200 if the process is running
7. THE `/health/ready` endpoint SHALL return HTTP 503 if the database connection fails

### Requirement 9: Error Handling

**User Story:** As a developer, I want consistent error handling, so that API consumers receive predictable error responses.

#### Acceptance Criteria

1. THE Application SHALL define a standard error response structure with fields: detail, error_code, timestamp
2. WHEN a validation error occurs, THE Application SHALL return HTTP 400 with field-level error details
3. WHEN a resource is not found, THE Application SHALL return HTTP 404 with the resource type and identifier
4. WHEN an internal error occurs, THE Application SHALL return HTTP 500 with an error reference ID
5. THE Application SHALL log all errors with correlation IDs for traceability
6. THE Application SHALL NOT expose internal implementation details in error responses

### Requirement 10: Database Migrations

**User Story:** As a developer, I want database migrations, so that I can evolve the schema safely over time.

#### Acceptance Criteria

1. THE Migration_System SHALL use Alembic for database schema migrations
2. THE Migration_System SHALL support both SQLite and PostgreSQL databases
3. THE Migration_System SHALL include an initial migration creating all foundation tables
4. WHEN migrations are run, THE Migration_System SHALL apply them in order without data loss
5. THE Migration_System SHALL support rollback of migrations
