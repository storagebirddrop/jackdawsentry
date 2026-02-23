"""
Auto-generated Database Tests
Generated on: 2026-02-23T18:37:57.655703+00:00
"""

import pytest
import asyncio
import time
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

# Helper functions for token creation
def create_test_token(role: str = "viewer") -> str:
    """Create test JWT token for given role"""
    import jwt
    from datetime import datetime, timezone, timedelta
    import os
    
    payload = {
        "sub": "test_viewer",
        "user_id": "test_user_viewer",
        "role": "viewer",
        "permissions": ["test_permission"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    return jwt.encode(payload, os.getenv("TEST_JWT_SECRET", "test_secret"), algorithm="HS256")

def create_expired_token() -> str:
    """Create expired JWT token"""
    import jwt
    from datetime import datetime, timezone, timedelta
    import os
    
    payload = {
        "sub": "test_user",
        "user_id": "test_user",
        "role": "viewer",
        "permissions": ["test_permission"],
        "exp": datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
    }
    
    return jwt.encode(payload, os.getenv("TEST_JWT_SECRET", "test_secret"), algorithm="HS256")



def test_database_connection_pooling():
    """Test database connection pooling under load"""
    import asyncio
    from src.api.database import get_postgres_connection
    
    async def test_concurrent_connections():
        tasks = []
        for i in range(50):
            task = asyncio.create_task(test_single_query())
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return all(results)
    
    async def test_single_query():
        async with get_postgres_connection() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    
    # Run the test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(test_concurrent_connections())
    loop.close()
    
    assert result is True



def test_database_transaction_handling():
    """Test database transaction rollback and commit"""
    from src.api.database import get_postgres_connection
    
    async def test_transaction():
        async with get_postgres_connection() as conn:
            async with conn.transaction():
                # Insert test data
                await conn.execute("""
                    INSERT INTO test_table (id, data) 
                    VALUES ($1, $2)
                """, "test_id", "test_data")
                
                # This should be rolled back
                raise Exception("Test rollback")
    
    # Verify rollback worked
    async def verify_rollback():
        async with get_postgres_connection() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM test_table WHERE id = $1", 
                "test_id"
            )
            return result == 0
    
    # Run tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(test_transaction())
    except Exception:
        pass  # Expected rollback
    
    result = loop.run_until_complete(verify_rollback())
    loop.close()
    
    assert result is True



def test_neo4j_query_optimization():
    """Test Neo4j query performance and optimization"""
    from src.api.database import get_neo4j_session
    
    async def test_query_performance():
        session = get_neo4j_session()
        
        # Test simple query
        start_time = time.time()
        result = await session.run("MATCH (n) RETURN count(n) as count")
        count = await result.single()
        simple_time = time.time() - start_time
        
        # Test complex query
        start_time = time.time()
        result = await session.run("""
            MATCH (a:Address)-[:SENT]->(b:Address)
            WHERE a.blockchain = 'bitcoin'
            RETURN count(*) as transactions
        """)
        transactions = await result.single()
        complex_time = time.time() - start_time
        
        # Both should complete reasonably fast
        assert simple_time < 1.0
        assert complex_time < 2.0
        
        return True
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(test_query_performance())
    loop.close()
    
    assert result is True



def test_redis_caching():
    """Test Redis caching functionality"""
    from src.api.database import get_redis_connection
    
    async def test_cache_operations():
        redis = await get_redis_connection()
        
        # Test set/get
        await redis.set("test_key", "test_value", ex=60)
        value = await redis.get("test_key")
        assert value.decode() == "test_value"
        
        # Test expiration
        await redis.set("expire_key", "expire_value", ex=1)
        await asyncio.sleep(2)
        expired = await redis.get("expire_key")
        assert expired is None
        
        # Test cache invalidation
        await redis.set("invalidate_key", "value")
        await redis.delete("invalidate_key")
        deleted = await redis.get("invalidate_key")
        assert deleted is None
        
        return True
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(test_cache_operations())
    loop.close()
    
    assert result is True

