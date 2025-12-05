import asyncio

import asyncpg
import pytest
from tortoise import Tortoise

from api.misc.config import config


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the test session.

    This fixture is required for pytest-asyncio to work properly
    with newer versions that don't provide event_loop by default.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def drop_database_if_exists():
    """Drop the testdb database if it exists."""
    connection = await asyncpg.connect(dsn=f"{config.TEST_POSTGRES_BASE_URL}/tasks")

    # Check if testdb exists
    result = await connection.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = 'testdb'"
    )
    if result:
        await connection.execute('DROP DATABASE IF EXISTS "testdb"')
    await connection.close()


@pytest.fixture(autouse=True)
def initialize_test_db(request, event_loop):
    """
    Initialize test database for tests marked with @pytest.mark.use_db

    This fixture automatically runs for all tests. It checks if the test is marked
    with 'use_db' and if so, creates a test database with the schema.

    Usage in tests:
        @pytest.mark.asyncio
        @pytest.mark.use_db
        async def test_something():
            # Test has access to test database
            pass
    """
    if "use_db" in request.keywords:
        # Drop the database first to ensure clean state
        event_loop.run_until_complete(drop_database_if_exists())

        event_loop.run_until_complete(
            Tortoise.init(
                db_url=f"{config.TEST_POSTGRES_BASE_URL}/testdb",
                _create_db=True,
                modules={"models": ["api.data.postgres_models"]},
            )
        )
        event_loop.run_until_complete(Tortoise.generate_schemas())

        # Use addfinalizer to ensure cleanup happens
        request.addfinalizer(
            lambda: event_loop.run_until_complete(Tortoise._drop_databases())
        )
