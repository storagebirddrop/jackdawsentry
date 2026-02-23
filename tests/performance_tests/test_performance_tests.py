"""
Auto-generated Performance Tests
Generated on: 2026-02-23T18:37:57.657291+00:00
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



def test_concurrent_requests():
    """Test API performance under concurrent load"""
    import asyncio
    import aiohttp
    
    async def make_request(session, url):
        start_time = time.time()
        async with session.get(url) as response:
            await response.text()
            return time.time() - start_time
    
    async def test_concurrent_load():
        connector = aiohttp.TCPConnector(limit=100)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for i in range(50):
                task = make_request(session, "http://localhost:8000/api/v1/health")
                tasks.append(task)
            
            response_times = await asyncio.gather(*tasks)
            
            # Performance assertions
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
            
            assert avg_time < 0.5  # Average under 500ms
            assert max_time < 2.0   # Max under 2s
            assert p95_time < 1.0   # P95 under 1s
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_concurrent_load())
    loop.close()



def test_memory_usage():
    """Test memory usage during operations"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Perform memory-intensive operations
    for i in range(100):
        response = client.get("/api/v1/analysis/address/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        assert response.status_code == 200
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    # Memory increase should be reasonable (< 100MB)
    assert memory_increase < 100



def test_database_connection_pool_efficiency():
    """Test database connection pool efficiency"""
    from src.api.database import get_postgres_connection
    
    async def test_pool_efficiency():
        pool_stats_before = {}
        pool_stats_after = {}
        
        # Get initial pool stats
        async with get_postgres_connection() as conn:
            pool_stats_before = {
                "size": conn._pool.size,
                "idle": len(conn._pool._queue._queue)
            }
        
        # Perform many operations
        tasks = []
        for i in range(20):
            task = asyncio.create_task(test_db_operation())
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Get final pool stats
        async with get_postgres_connection() as conn:
            pool_stats_after = {
                "size": conn._pool.size,
                "idle": len(conn._pool._queue._queue)
            }
        
        # Pool should be efficiently managed
        assert pool_stats_after["size"] <= pool_stats_before["size"] + 5
        assert pool_stats_after["idle"] >= pool_stats_before["idle"]
    
    async def test_db_operation():
        async with get_postgres_connection() as conn:
            await conn.fetchval("SELECT 1")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_pool_efficiency())
    loop.close()

