import asyncio

import asyncpg
import pytest
from tortoise import Tortoise

from api.misc.config import config


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def drop_database_if_exists():
    # Check if database exists
    connection = await asyncpg.connect(dsn=f"{config.TEST_POSTGRES_BASE_URL}/postgres")
    result = await connection.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = 'testdb'"
    )
    await connection.close()

    # Drop database if it exists
    if result:
        connection = await asyncpg.connect(
            dsn=f"{config.TEST_POSTGRES_BASE_URL}/postgres"
        )
        await connection.execute('DROP DATABASE IF EXISTS "testdb"')
        await connection.close()


@pytest.fixture(autouse=True)
def initialize_test_db(request, event_loop):
    if "use_db" in request.keywords:
        event_loop.run_until_complete(drop_database_if_exists())

        event_loop.run_until_complete(
            Tortoise.init(
                db_url=f"{config.TEST_POSTGRES_BASE_URL}/testdb",
                _create_db=True,
                modules={"models": ["api.data.postgres_models"]},
            )
        )
        event_loop.run_until_complete(Tortoise.generate_schemas())

        request.addfinalizer(
            lambda: event_loop.run_until_complete(Tortoise._drop_databases())
        )
