"""
Jackdaw Sentry - Integration Test Stubs (M5.4)
These tests require running PostgreSQL, Neo4j, and Redis.
Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import pytest


pytestmark = pytest.mark.integration


class TestPostgresIntegration:
    """PostgreSQL integration tests — require a running Postgres instance."""

    @pytest.mark.database
    async def test_postgres_connection(self):
        """Verify asyncpg can connect to the test database."""
        import asyncpg

        conn = await asyncpg.connect(
            host="localhost", port=5432, user="test", password="test", database="test"
        )
        try:
            result = await conn.fetchval("SELECT 1")
            assert result == 1
        finally:
            await conn.close()

    @pytest.mark.database
    async def test_migrations_apply(self):
        """Verify the initial schema migration applies without error."""
        import asyncpg
        from pathlib import Path

        conn = await asyncpg.connect(
            host="localhost", port=5432, user="test", password="test", database="test"
        )
        try:
            schema_path = (
                Path(__file__).parent.parent.parent
                / "src/api/migrations/001_initial_schema.sql"
            )
            sql = schema_path.read_text()
            await conn.execute(sql)

            # Verify key tables exist
            tables = await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            table_names = {r["tablename"] for r in tables}
            for expected in ("users", "investigations", "evidence", "audit_logs"):
                assert expected in table_names, f"Missing table: {expected}"
        finally:
            await conn.close()

    @pytest.mark.database
    async def test_seed_admin_user(self):
        """Verify 002_seed_admin_user.sql inserts the default admin."""
        import asyncpg
        from pathlib import Path

        conn = await asyncpg.connect(
            host="localhost", port=5432, user="test", password="test", database="test"
        )
        try:
            seed_path = (
                Path(__file__).parent.parent.parent
                / "src/api/migrations/002_seed_admin_user.sql"
            )
            sql = seed_path.read_text()
            await conn.execute(sql)

            row = await conn.fetchrow(
                "SELECT username, role FROM users WHERE username = 'admin'"
            )
            assert row is not None
            assert row["role"] == "admin"
        finally:
            await conn.close()


class TestRedisIntegration:
    """Redis integration tests — require a running Redis instance."""

    @pytest.mark.database
    async def test_redis_ping(self):
        """Verify Redis is reachable."""
        import redis.asyncio as aioredis

        r = aioredis.from_url("redis://localhost:6379/1", decode_responses=True)
        try:
            assert await r.ping() is True
        finally:
            await r.aclose()

    @pytest.mark.database
    async def test_redis_set_get(self):
        """Verify basic set/get round-trip."""
        import redis.asyncio as aioredis

        r = aioredis.from_url("redis://localhost:6379/1", decode_responses=True)
        try:
            await r.set("test:key", "hello", ex=10)
            val = await r.get("test:key")
            assert val == "hello"
            await r.delete("test:key")
        finally:
            await r.aclose()
