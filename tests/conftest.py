"""Pytest configuration and fixtures for tests."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession
from sqlalchemy.orm import Session, SessionTransaction

from app.app import create_app
from app.config import app_settings
from app.kit.db.postgres import create_async_engine, create_async_sessionmaker
from app.postgres import AsyncSessionMaker


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a test database engine."""
    engine = create_async_engine(
        dsn=str(app_settings.get_postgres_dsn("asyncpg")),
        application_name="test",
        debug=app_settings.SQLALCHEMY_DEBUG,
        pool_size=5,
        pool_recycle=app_settings.DATABASE_POOL_RECYCLE_SECONDS,
        command_timeout=app_settings.DATABASE_COMMAND_TIMEOUT_SECONDS,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def connection(engine: AsyncEngine) -> AsyncGenerator[AsyncConnection, None]:
    """Create a test database connection."""
    async with engine.begin() as connection:
        yield connection


@pytest_asyncio.fixture
async def session(connection: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session with automatic rollback.

    Each test gets a fresh session that is rolled back after the test completes,
    ensuring test isolation.
    """
    # Start a transaction
    transaction = await connection.begin_nested()

    # Create session
    sessionmaker = create_async_sessionmaker(connection)  # type: ignore[arg-type]
    session = sessionmaker()

    # Setup savepoint support for nested transactions
    @event.listens_for(session.sync_session, "after_transaction_end")
    def restart_savepoint(session: Session, transaction: SessionTransaction) -> None:
        if transaction.nested and not transaction._parent.nested:
            # Ensure a new savepoint is created after the previous one is released
            session.begin_nested()

    yield session

    # Rollback the transaction
    await session.close()
    await transaction.rollback()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create a test HTTP client with database session override.

    The client automatically uses the test database session for all requests.
    """
    app = create_app()

    # Override the lifespan to inject test dependencies
    async def override_lifespan(app: Any) -> AsyncGenerator[dict[str, Any], None]:
        # Create a sessionmaker that returns our test session
        async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
            yield session

        # Create a mock sessionmaker
        class TestSessionMaker:
            async def __aenter__(self) -> AsyncSession:
                return session

            async def __aexit__(self, *args: Any) -> None:
                pass

            def __call__(self) -> "TestSessionMaker":
                return self

        test_sessionmaker = TestSessionMaker()

        yield {
            "async_sessionmaker": test_sessionmaker,
            "async_session": session,
        }

    # Replace the lifespan
    app.router.lifespan_context = override_lifespan  # type: ignore[assignment]

    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        yield client

