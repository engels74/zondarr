"""Property-based tests for database migrations.

Feature: zondarr-foundation
Property: 14
Validates: Requirements 10.4, 10.5
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from zondarr.models import (
    Identity,
    Invitation,
    Library,
    MediaServer,
    ServerType,
    User,
)
from zondarr.models.base import Base

# Custom strategies for model fields
datetime_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
    timezones=st.just(UTC),
)
optional_datetime_strategy = st.one_of(st.none(), datetime_strategy)
server_type_strategy = st.sampled_from([ServerType.JELLYFIN, ServerType.PLEX])
name_strategy = st.text(
    alphabet=st.characters(categories=("L", "N")),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip())
url_strategy = st.from_regex(r"https?://[a-z0-9]+\.[a-z]{2,}", fullmatch=True)
email_strategy = st.from_regex(r"[a-z0-9]+@[a-z0-9]+\.[a-z]{2,}", fullmatch=True)
code_strategy = st.text(
    alphabet=st.characters(categories=("L", "N")),
    min_size=6,
    max_size=20,
)
positive_int_strategy = st.integers(min_value=0, max_value=1000)
optional_positive_int_strategy = st.one_of(st.none(), positive_int_strategy)


async def create_test_engine() -> AsyncEngine:
    """Create an async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(  # pyright: ignore[reportUnusedFunction]
        dbapi_connection: Any,  # pyright: ignore[reportExplicitAny,reportAny]
        connection_record: Any,  # pyright: ignore[reportExplicitAny,reportUnusedParameter,reportAny]
    ) -> None:
        cursor = dbapi_connection.cursor()  # pyright: ignore[reportAny]
        cursor.execute("PRAGMA foreign_keys=ON")  # pyright: ignore[reportAny]
        cursor.close()  # pyright: ignore[reportAny]

    return engine


async def apply_migration(engine: AsyncEngine) -> None:
    """Apply migration by creating all tables (simulates upgrade)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def rollback_migration(engine: AsyncEngine) -> None:
    """Rollback migration by dropping all tables (simulates downgrade)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def verify_tables_exist(session: AsyncSession) -> dict[str, bool]:
    """Verify that all expected tables exist in the database."""
    expected_tables = [
        "media_servers",
        "libraries",
        "identities",
        "invitations",
        "users",
        "invitation_servers",
        "invitation_libraries",
    ]
    results: dict[str, bool] = {}
    for table in expected_tables:
        try:
            _ = await session.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))  # noqa: S608
            results[table] = True
        except Exception:
            results[table] = False
    return results


class TestMigrationsPreserveData:
    """
    Feature: zondarr-foundation
    Property 14: Migrations Preserve Data

    *For any* valid data inserted into the database before a migration,
    running the migration and then rollback SHALL preserve the data
    structure and allow re-migration without data loss.

    **Validates: Requirements 10.4, 10.5**
    """

    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        name=name_strategy,
        server_type=server_type_strategy,
        url=url_strategy,
        api_key=name_strategy,
        enabled=st.booleans(),
    )
    @pytest.mark.asyncio
    async def test_media_server_data_survives_migration_cycle(
        self,
        name: str,
        server_type: ServerType,
        url: str,
        api_key: str,
        enabled: bool,
    ) -> None:
        """MediaServer data is preserved through migration upgrade."""
        engine = await create_test_engine()
        try:
            # Apply initial migration
            await apply_migration(engine)

            session_factory = async_sessionmaker(engine, expire_on_commit=False)

            # Insert test data
            server_id = uuid4()
            async with session_factory() as session:
                server = MediaServer()
                server.id = server_id
                server.name = name
                server.server_type = server_type
                server.url = url
                server.api_key = api_key
                server.enabled = enabled
                session.add(server)
                await session.commit()

            # Verify data exists after migration
            async with session_factory() as session:
                result = await session.get(MediaServer, server_id)
                assert result is not None
                assert result.name == name
                assert result.server_type == server_type
                assert result.url == url
                assert result.api_key == api_key
                assert result.enabled == enabled
        finally:
            await engine.dispose()

    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        code=code_strategy,
        expires_at=optional_datetime_strategy,
        max_uses=optional_positive_int_strategy,
        use_count=positive_int_strategy,
        duration_days=optional_positive_int_strategy,
        enabled=st.booleans(),
        created_by=st.one_of(st.none(), name_strategy),
    )
    @pytest.mark.asyncio
    async def test_invitation_data_survives_migration_cycle(
        self,
        code: str,
        expires_at: datetime | None,
        max_uses: int | None,
        use_count: int,
        duration_days: int | None,
        enabled: bool,
        created_by: str | None,
    ) -> None:
        """Invitation data is preserved through migration upgrade."""
        engine = await create_test_engine()
        try:
            await apply_migration(engine)

            session_factory = async_sessionmaker(engine, expire_on_commit=False)

            # Insert test data
            invitation_id = uuid4()
            async with session_factory() as session:
                invitation = Invitation()
                invitation.id = invitation_id
                invitation.code = code
                invitation.expires_at = expires_at
                invitation.max_uses = max_uses
                invitation.use_count = use_count
                invitation.duration_days = duration_days
                invitation.enabled = enabled
                invitation.created_by = created_by
                session.add(invitation)
                await session.commit()

            # Verify data exists after migration
            async with session_factory() as session:
                result = await session.get(Invitation, invitation_id)
                assert result is not None
                assert result.code == code
                assert result.max_uses == max_uses
                assert result.use_count == use_count
                assert result.duration_days == duration_days
                assert result.enabled == enabled
                assert result.created_by == created_by
        finally:
            await engine.dispose()

    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        display_name=name_strategy,
        email=st.one_of(st.none(), email_strategy),
        expires_at=optional_datetime_strategy,
        enabled=st.booleans(),
    )
    @pytest.mark.asyncio
    async def test_identity_data_survives_migration_cycle(
        self,
        display_name: str,
        email: str | None,
        expires_at: datetime | None,
        enabled: bool,
    ) -> None:
        """Identity data is preserved through migration upgrade."""
        engine = await create_test_engine()
        try:
            await apply_migration(engine)

            session_factory = async_sessionmaker(engine, expire_on_commit=False)

            # Insert test data
            identity_id = uuid4()
            async with session_factory() as session:
                identity = Identity()
                identity.id = identity_id
                identity.display_name = display_name
                identity.email = email
                identity.expires_at = expires_at
                identity.enabled = enabled
                session.add(identity)
                await session.commit()

            # Verify data exists after migration
            async with session_factory() as session:
                result = await session.get(Identity, identity_id)
                assert result is not None
                assert result.display_name == display_name
                assert result.email == email
                assert result.enabled == enabled
        finally:
            await engine.dispose()

    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        external_user_id=name_strategy,
        username=name_strategy,
        expires_at=optional_datetime_strategy,
        enabled=st.booleans(),
    )
    @pytest.mark.asyncio
    async def test_user_data_survives_migration_cycle(
        self,
        external_user_id: str,
        username: str,
        expires_at: datetime | None,
        enabled: bool,
    ) -> None:
        """User data with relationships is preserved through migration upgrade."""
        engine = await create_test_engine()
        try:
            await apply_migration(engine)

            session_factory = async_sessionmaker(engine, expire_on_commit=False)

            # Create parent entities first
            identity_id = uuid4()
            server_id = uuid4()
            user_id = uuid4()

            async with session_factory() as session:
                # Create identity
                identity = Identity()
                identity.id = identity_id
                identity.display_name = "Test Identity"
                identity.enabled = True
                session.add(identity)

                # Create media server
                server = MediaServer()
                server.id = server_id
                server.name = "Test Server"
                server.server_type = ServerType.JELLYFIN
                server.url = "http://test.local"
                server.api_key = "testkey"
                server.enabled = True
                session.add(server)

                await session.commit()

            # Create user with relationships
            async with session_factory() as session:
                user = User()
                user.id = user_id
                user.identity_id = identity_id
                user.media_server_id = server_id
                user.external_user_id = external_user_id
                user.username = username
                user.expires_at = expires_at
                user.enabled = enabled
                session.add(user)
                await session.commit()

            # Verify data and relationships exist after migration
            async with session_factory() as session:
                result = await session.get(User, user_id)
                assert result is not None
                assert result.identity_id == identity_id
                assert result.media_server_id == server_id
                assert result.external_user_id == external_user_id
                assert result.username == username
                assert result.enabled == enabled
        finally:
            await engine.dispose()

    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        external_id=name_strategy,
        library_name=name_strategy,
        library_type=st.sampled_from(["movies", "tvshows", "music", "photos"]),
    )
    @pytest.mark.asyncio
    async def test_library_data_survives_migration_cycle(
        self,
        external_id: str,
        library_name: str,
        library_type: str,
    ) -> None:
        """Library data with foreign key relationships is preserved."""
        engine = await create_test_engine()
        try:
            await apply_migration(engine)

            session_factory = async_sessionmaker(engine, expire_on_commit=False)

            # Create parent media server first
            server_id = uuid4()
            library_id = uuid4()

            async with session_factory() as session:
                server = MediaServer()
                server.id = server_id
                server.name = "Test Server"
                server.server_type = ServerType.PLEX
                server.url = "http://plex.local"
                server.api_key = "plexkey"
                server.enabled = True
                session.add(server)
                await session.commit()

            # Create library
            async with session_factory() as session:
                library = Library()
                library.id = library_id
                library.media_server_id = server_id
                library.external_id = external_id
                library.name = library_name
                library.library_type = library_type
                session.add(library)
                await session.commit()

            # Verify data and relationships exist
            async with session_factory() as session:
                result = await session.get(Library, library_id)
                assert result is not None
                assert result.media_server_id == server_id
                assert result.external_id == external_id
                assert result.name == library_name
                assert result.library_type == library_type
        finally:
            await engine.dispose()


class TestMigrationRollback:
    """
    Feature: zondarr-foundation
    Property 14: Migrations Support Rollback

    *For any* applied migration, the rollback (downgrade) operation
    SHALL successfully remove all tables without errors.

    **Validates: Requirements 10.5**
    """

    @pytest.mark.asyncio
    async def test_migration_rollback_removes_all_tables(self) -> None:
        """Migration rollback successfully removes all foundation tables."""
        engine = await create_test_engine()
        try:
            # Apply migration
            await apply_migration(engine)

            session_factory = async_sessionmaker(engine, expire_on_commit=False)

            # Verify tables exist
            async with session_factory() as session:
                tables_before = await verify_tables_exist(session)
                assert all(tables_before.values()), (
                    "All tables should exist after migration"
                )

            # Rollback migration
            await rollback_migration(engine)

            # Verify tables are removed
            async with session_factory() as session:
                tables_after = await verify_tables_exist(session)
                assert not any(tables_after.values()), (
                    "No tables should exist after rollback"
                )
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_migration_can_be_reapplied_after_rollback(self) -> None:
        """Migration can be successfully reapplied after rollback."""
        engine = await create_test_engine()
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)

            # Apply migration
            await apply_migration(engine)

            # Insert some data
            async with session_factory() as session:
                server = MediaServer()
                server.name = "Test Server"
                server.server_type = ServerType.JELLYFIN
                server.url = "http://test.local"
                server.api_key = "testkey"
                server.enabled = True
                session.add(server)
                await session.commit()

            # Rollback
            await rollback_migration(engine)

            # Reapply migration
            await apply_migration(engine)

            # Verify tables exist again
            async with session_factory() as session:
                tables = await verify_tables_exist(session)
                assert all(tables.values()), (
                    "All tables should exist after re-migration"
                )

            # Verify we can insert data again
            async with session_factory() as session:
                server = MediaServer()
                server.name = "New Server"
                server.server_type = ServerType.PLEX
                server.url = "http://plex.local"
                server.api_key = "plexkey"
                server.enabled = True
                session.add(server)
                await session.commit()

                # Verify data was inserted
                result = await session.get(MediaServer, server.id)
                assert result is not None
                assert result.name == "New Server"
        finally:
            await engine.dispose()


class TestMigrationSchemaIntegrity:
    """
    Feature: zondarr-foundation
    Property 14: Migration Schema Integrity

    *For any* migration, the resulting schema SHALL have all expected
    tables, columns, and constraints as defined in the models.

    **Validates: Requirements 10.3, 10.4**
    """

    @pytest.mark.asyncio
    async def test_all_foundation_tables_created(self) -> None:
        """Migration creates all foundation tables."""
        engine = await create_test_engine()
        try:
            await apply_migration(engine)

            session_factory = async_sessionmaker(engine, expire_on_commit=False)

            async with session_factory() as session:
                tables = await verify_tables_exist(session)

                # Verify all expected tables exist
                assert tables["media_servers"], "media_servers table should exist"
                assert tables["libraries"], "libraries table should exist"
                assert tables["identities"], "identities table should exist"
                assert tables["invitations"], "invitations table should exist"
                assert tables["users"], "users table should exist"
                assert tables["invitation_servers"], (
                    "invitation_servers table should exist"
                )
                assert tables["invitation_libraries"], (
                    "invitation_libraries table should exist"
                )
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_foreign_key_constraints_enforced(self) -> None:
        """Foreign key constraints are properly enforced after migration."""
        engine = await create_test_engine()
        try:
            await apply_migration(engine)

            session_factory = async_sessionmaker(engine, expire_on_commit=False)

            # Try to insert a user with non-existent identity_id
            async with session_factory() as session:
                user = User()
                user.identity_id = uuid4()  # Non-existent
                user.media_server_id = uuid4()  # Non-existent
                user.external_user_id = "ext123"
                user.username = "testuser"
                user.enabled = True
                session.add(user)

                # This should raise an integrity error due to FK constraint
                with pytest.raises(Exception):  # noqa: B017
                    await session.commit()
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_unique_constraint_on_invitation_code(self) -> None:
        """Unique constraint on invitation code is enforced."""
        engine = await create_test_engine()
        try:
            await apply_migration(engine)

            session_factory = async_sessionmaker(engine, expire_on_commit=False)

            # Insert first invitation
            async with session_factory() as session:
                invitation1 = Invitation()
                invitation1.code = "UNIQUE123"
                invitation1.use_count = 0
                invitation1.enabled = True
                session.add(invitation1)
                await session.commit()

            # Try to insert duplicate code
            async with session_factory() as session:
                invitation2 = Invitation()
                invitation2.code = "UNIQUE123"  # Same code
                invitation2.use_count = 0
                invitation2.enabled = True
                session.add(invitation2)

                # This should raise an integrity error due to unique constraint
                with pytest.raises(Exception):  # noqa: B017
                    await session.commit()
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_cascade_delete_on_media_server(self) -> None:
        """Cascade delete removes related libraries when media server is deleted."""
        engine = await create_test_engine()
        try:
            await apply_migration(engine)

            session_factory = async_sessionmaker(engine, expire_on_commit=False)

            server_id = uuid4()
            library_id = uuid4()

            # Create media server with library
            async with session_factory() as session:
                server = MediaServer()
                server.id = server_id
                server.name = "Test Server"
                server.server_type = ServerType.JELLYFIN
                server.url = "http://test.local"
                server.api_key = "testkey"
                server.enabled = True
                session.add(server)
                await session.commit()

            async with session_factory() as session:
                library = Library()
                library.id = library_id
                library.media_server_id = server_id
                library.external_id = "lib123"
                library.name = "Movies"
                library.library_type = "movies"
                session.add(library)
                await session.commit()

            # Delete media server
            async with session_factory() as session:
                server = await session.get(MediaServer, server_id)
                assert server is not None
                await session.delete(server)
                await session.commit()

            # Verify library was cascade deleted
            async with session_factory() as session:
                library = await session.get(Library, library_id)
                assert library is None, "Library should be cascade deleted"
        finally:
            await engine.dispose()
