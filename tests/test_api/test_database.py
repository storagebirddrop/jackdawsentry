from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from neo4j.exceptions import ServiceUnavailable

from src.api import database


@pytest.mark.asyncio
async def test_init_neo4j_retries_until_success():
    failed_driver = MagicMock()
    failed_driver.close = AsyncMock()
    healthy_driver = MagicMock()
    healthy_driver.close = AsyncMock()
    verify = AsyncMock(side_effect=[ServiceUnavailable("Neo4j not ready"), None])

    with (
        patch.object(
            database,
            "_build_neo4j_driver",
            side_effect=[failed_driver, healthy_driver],
        ),
        patch.object(database, "_verify_neo4j_driver", verify),
        patch("src.api.database.asyncio.sleep", new_callable=AsyncMock) as sleep,
        patch.object(database, "NEO4J_CONNECT_MAX_ATTEMPTS", 2),
        patch.object(database, "NEO4J_CONNECT_RETRY_DELAY_SECONDS", 0),
    ):
        previous_driver = database._neo4j_driver
        database._neo4j_driver = None
        try:
            await database.init_neo4j()
            assert database._neo4j_driver is healthy_driver
        finally:
            database._neo4j_driver = previous_driver

    failed_driver.close.assert_awaited_once()
    sleep.assert_awaited_once()
    assert verify.await_count == 2


@pytest.mark.asyncio
async def test_init_neo4j_raises_after_exhausting_retries():
    first_driver = MagicMock()
    first_driver.close = AsyncMock()
    second_driver = MagicMock()
    second_driver.close = AsyncMock()
    verify = AsyncMock(side_effect=ServiceUnavailable("still unavailable"))

    with (
        patch.object(
            database,
            "_build_neo4j_driver",
            side_effect=[first_driver, second_driver],
        ),
        patch.object(database, "_verify_neo4j_driver", verify),
        patch("src.api.database.asyncio.sleep", new_callable=AsyncMock) as sleep,
        patch.object(database, "NEO4J_CONNECT_MAX_ATTEMPTS", 2),
        patch.object(database, "NEO4J_CONNECT_RETRY_DELAY_SECONDS", 0),
    ):
        previous_driver = database._neo4j_driver
        database._neo4j_driver = None
        try:
            with pytest.raises(ServiceUnavailable):
                await database.init_neo4j()
            assert database._neo4j_driver is None
        finally:
            database._neo4j_driver = previous_driver

    assert first_driver.close.await_count == 1
    assert second_driver.close.await_count == 1
    sleep.assert_awaited_once()
    assert verify.await_count == 2
