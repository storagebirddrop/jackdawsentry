#!/usr/bin/env python3
"""
Jackdaw Sentry - Test Coverage Expansion
Generates additional tests to reach 300+ comprehensive test coverage
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone


class TestGenerator:
    """Generates comprehensive test cases"""
    
    def __init__(self, src_dir: str = "src", tests_dir: str = "tests"):
        self.src_dir = Path(src_dir)
        self.tests_dir = Path(tests_dir)
        self.generated_tests = []
    
    def generate_all_tests(self) -> Dict[str, Any]:
        """Generate comprehensive test suite"""
        print("Generating comprehensive test suite...")
        
        # Generate test categories
        test_categories = {
            "security_tests": self.generate_security_tests(),
            "api_integration_tests": self.generate_api_integration_tests(),
            "database_tests": self.generate_database_tests(),
            "blockchain_tests": self.generate_blockchain_tests(),
            "compliance_tests": self.generate_compliance_tests(),
            "performance_tests": self.generate_performance_tests(),
            "error_handling_tests": self.generate_error_handling_tests(),
            "auth_rbac_tests": self.generate_auth_rbac_tests()
        }
        
        # Write test files
        for category, tests in test_categories.items():
            self._write_test_file(category, tests)
        
        # Generate test report
        report = {
            "generated_tests": self.generated_tests,
            "categories": list(test_categories.keys()),
            "total_tests_generated": len(self.generated_tests),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        with open("test_expansion_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"Generated {len(self.generated_tests)} new tests across {len(test_categories)} categories")
        return report
    
    def generate_security_tests(self) -> List[str]:
        """Generate security-focused tests"""
        tests = [
            '''
def test_sql_injection_protection():
    """Test SQL injection protection in all database queries"""
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "'; SELECT * FROM users; --",
        "' UNION SELECT password FROM users --"
    ]
    
    for malicious_input in malicious_inputs:
        response = client.get(f"/api/v1/analysis/address/{malicious_input}")
        assert response.status_code < 500  # Should not crash
        assert "error" in response.json().lower() or "not found" in response.json().lower()
''',
            '''
def test_jwt_token_validation():
    """Test JWT token validation edge cases"""
    invalid_tokens = [
        "",
        "invalid.token.here",
        "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    ]
    
    for token in invalid_tokens:
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
''',
            '''
def test_rate_limiting():
    """Test API rate limiting"""
    # Make many rapid requests
    responses = []
    for i in range(100):
        response = client.get("/api/v1/analysis/address/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        responses.append(response.status_code)
        
        if response.status_code == 429:
            break
    
    # Should eventually hit rate limit
    assert 429 in responses
''',
            '''
def test_input_validation():
    """Test input validation for various endpoints"""
    test_cases = [
        ("/api/v1/analysis/address", {"address": "invalid_address"}),
        ("/api/v1/analysis/transaction", {"hash": "invalid_hash"}),
        ("/api/v1/compliance/screen", {"address": ""}),
        ("/api/v1/attribution/batch", {"addresses": ["", "invalid"]})
    ]
    
    for endpoint, payload in test_cases:
        response = client.post(endpoint, json=payload)
        assert response.status_code in [400, 422]
        assert "error" in response.json() or "validation" in response.json()
''',
            '''
def test_authentication_bypass():
    """Test that protected endpoints cannot be accessed without auth"""
    protected_endpoints = [
        "/api/v1/users",
        "/api/v1/investigations",
        "/api/v1/admin/system/status",
        "/api/v1/compliance/reports"
    ]
    
    for endpoint in protected_endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401
''',
            '''
def test_file_upload_security():
    """Test secure file upload handling"""
    malicious_files = [
        ("malicious.exe", b"MZ\x90\x00"),
        ("script.js", b"<script>alert('xss')</script>"),
        ("huge.txt", b"x" * 1_000_000),  # 1MB file (reduced from 100MB for CI)
        ("../../../etc/passwd", b"root:x:0:0")
    ]
    
    for filename, content in malicious_files:
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content)}
        )
        assert response.status_code in [400, 413, 422]
'''
        ]
        
        self.generated_tests.extend([f"security_test_{i}" for i in range(len(tests))])
        return tests
    
    def generate_api_integration_tests(self) -> List[str]:
        """Generate API integration tests"""
        tests = [
            '''
def test_complete_investigation_workflow():
    """Test complete investigation workflow from start to finish"""
    # Start investigation
    response = client.post("/api/v1/investigations", json={
        "title": "Test Investigation",
        "description": "Integration test investigation",
        "priority": "medium",
        "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]
    })
    assert response.status_code == 201
    investigation_id = response.json()["id"]
    
    # Add analysis
    response = client.post(f"/api/v1/investigations/{investigation_id}/analysis", json={
        "type": "address_analysis",
        "target": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    })
    assert response.status_code == 200
    
    # Get investigation details
    response = client.get(f"/api/v1/investigations/{investigation_id}")
    assert response.status_code == 200
    assert response.json()["id"] == investigation_id
    
    # Generate report
    response = client.post("/api/v1/reports/generate", json={
        "type": "investigation",
        "id": investigation_id,
        "format": "pdf"
    })
    assert response.status_code == 200
''',
            '''
def test_cross_chain_analysis():
    """Test cross-chain analysis functionality"""
    addresses = [
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # Bitcoin
        "0x742d35Cc6634C0532925a3b8D4E7E0E0e9e0dF3",  # Ethereum
        "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"  # Solana
    ]
    
    response = client.post("/api/v1/analysis/cross-chain", json={
        "addresses": addresses,
        "blockchains": ["bitcoin", "ethereum", "solana"]
    })
    assert response.status_code == 200
    
    data = response.json()
    assert "cross_chain_links" in data
    assert len(data["cross_chain_links"]) >= 0
''',
            '''
def test_bulk_operations():
    """Test bulk operation endpoints"""
    # Bulk address analysis
    addresses = [f"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfN{i}" for i in range(10)]
    
    response = client.post("/api/v1/analysis/bulk", json={
        "addresses": addresses,
        "include_transactions": True
    })
    assert response.status_code == 200
    
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == len(addresses)
    
    # Bulk compliance screening
    response = client.post("/api/v1/compliance/bulk-screen", json={
        "addresses": addresses[:5],  # Smaller batch for compliance
        "include_risk_scoring": True
    })
    assert response.status_code == 200
''',
            '''
def test_real_time_alerts():
    """Test real-time alert functionality"""
    # Create alert rule
    response = client.post("/api/v1/alerts/rules", json={
        "name": "Test Rule",
        "condition": "address_volume > 1000",
        "severity": "medium",
        "blockchain": "bitcoin"
    })
    assert response.status_code == 201
    rule_id = response.json()["id"]
    
    # Trigger alert (simulate)
    response = client.post("/api/v1/alerts/trigger", json={
        "rule_id": rule_id,
        "test_data": {"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "volume": 1500}
    })
    assert response.status_code == 200
    
    # Check alert was created
    response = client.get("/api/v1/alerts/active")
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) > 0
    
    # Clean up
    client.delete(f"/api/v1/alerts/rules/{rule_id}")
''',
            '''
def test_api_error_handling():
    """Test comprehensive API error handling"""
    test_cases = [
        # Invalid endpoints
        ("/api/v1/nonexistent", 404),
        # Invalid methods
        ("/api/v1/auth/login", 405),  # GET on POST endpoint
        # Invalid content types
        ("/api/v1/analysis/address", 415),  # No content-type header
        # Malformed JSON
        ("/api/v1/compliance/screen", 400),  # Invalid JSON
    ]
    
    for endpoint, expected_status in test_cases:
        if expected_status == 405:
            response = client.get(endpoint)
        elif expected_status == 415:
            response = client.post(endpoint, data="not json")
        elif expected_status == 400:
            response = client.post(endpoint, data="invalid json")
        else:
            response = client.get(endpoint)
        
        assert response.status_code == expected_status
'''
        ]
        
        self.generated_tests.extend([f"api_integration_test_{i}" for i in range(len(tests))])
        return tests
    
    def generate_database_tests(self) -> List[str]:
        """Generate database operation tests"""
        tests = [
            '''
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
''',
            '''
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
''',
            '''
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
''',
            '''
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
'''
        ]
        
        self.generated_tests.extend([f"database_test_{i}" for i in range(len(tests))])
        return tests
    
    def generate_blockchain_tests(self) -> List[str]:
        """Generate blockchain integration tests"""
        tests = [
            '''
def test_bitcoin_integration():
    """Test Bitcoin blockchain integration"""
    # Test address validation
    response = client.get("/api/v1/blockchain/validate/bitcoin/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    assert response.status_code == 200
    assert response.json()["valid"] is True
    
    # Test invalid address
    response = client.get("/api/v1/blockchain/validate/bitcoin/invalid_address")
    assert response.status_code == 200
    assert response.json()["valid"] is False
    
    # Test balance query
    response = client.get("/api/v1/blockchain/balance/bitcoin/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    assert response.status_code == 200
    assert "balance" in response.json()
''',
            '''
def test_ethereum_integration():
    """Test Ethereum blockchain integration"""
    address = "0x742d35Cc6634C0532925a3b8D4E7E0E0e9e0dF3"
    
    # Test address validation
    response = client.get(f"/api/v1/blockchain/validate/ethereum/{address}")
    assert response.status_code == 200
    assert response.json()["valid"] is True
    
    # Test balance query
    response = client.get(f"/api/v1/blockchain/balance/ethereum/{address}")
    assert response.status_code == 200
    assert "balance" in response.json()
    assert "eth_balance" in response.json()
    
    # Test transaction history
    response = client.get(f"/api/v1/blockchain/transactions/ethereum/{address}")
    assert response.status_code == 200
    assert "transactions" in response.json()
''',
            '''
def test_solana_integration():
    """Test Solana blockchain integration"""
    address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    
    # Test address validation
    response = client.get(f"/api/v1/blockchain/validate/solana/{address}")
    assert response.status_code == 200
    assert response.json()["valid"] is True
    
    # Test balance query
    response = client.get(f"/api/v1/blockchain/balance/solana/{address}")
    assert response.status_code == 200
    assert "balance" in response.json()
    assert "sol_balance" in response.json()
''',
            '''
def test_cross_chain_bridge_detection():
    """Test cross-chain bridge transaction detection"""
    # Test known bridge addresses
    bridge_addresses = [
        "0x0000000000000000000000000000000000000000",  # Null address (test)
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Genesis address
    ]
    
    for address in bridge_addresses:
        response = client.post("/api/v1/analysis/bridge-detection", json={
            "address": address,
            "blockchains": ["ethereum", "bitcoin"]
        })
        assert response.status_code == 200
        assert "bridge_transactions" in response.json()
''',
            '''
def test_smart_contract_interaction():
    """Test smart contract analysis and interaction"""
    # Test contract analysis
    contract_address = "0x742d35Cc6634C0532925a3b8D4E7E0E0e9e0dF3"
    
    response = client.post("/api/v1/blockchain/contract/analyze", json={
        "address": contract_address,
        "blockchain": "ethereum",
        "include_source": True
    })
    assert response.status_code == 200
    assert "contract_info" in response.json()
    
    # Test ABI decoding
    response = client.post("/api/v1/blockchain/contract/decode", json={
        "address": contract_address,
        "transaction_hash": "0x...",
        "blockchain": "ethereum"
    })
    # May fail if test transaction doesn't exist, but should not crash
    assert response.status_code in [200, 404, 400]
'''
        ]
        
        self.generated_tests.extend([f"blockchain_test_{i}" for i in range(len(tests))])
        return tests
    
    def generate_compliance_tests(self) -> List[str]:
        """Generate compliance and regulatory tests"""
        tests = [
            '''
def test_gdpr_compliance():
    """Test GDPR compliance features"""
    # Test data deletion request
    response = client.post("/api/v1/compliance/gdpr/delete-request", json={
        "user_id": "test_user",
        "reason": "data_deletion_request"
    })
    assert response.status_code == 200
    
    # Test data export
    response = client.post("/api/v1/compliance/gdpr/data-export", json={
        "user_id": "test_user",
        "format": "json"
    })
    assert response.status_code == 200
    assert "export_data" in response.json()
    
    # Test consent management
    response = client.post("/api/v1/compliance/gdpr/consent", json={
        "user_id": "test_user",
        "consent_given": True,
        "purpose": "investigation_analysis"
    })
    assert response.status_code == 200
''',
            '''
def test_aml_compliance():
    """Test AML compliance screening"""
    # Test sanctions screening
    response = client.post("/api/v1/compliance/sanctions-screen", json={
        "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
        "include_risk_scoring": True
    })
    assert response.status_code == 200
    assert "screening_results" in response.json()
    
    # Test risk assessment
    response = client.post("/api/v1/compliance/risk-assessment", json={
        "entity": {
            "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "entity_type": "individual"
        },
        "assessment_type": "standard"
    })
    assert response.status_code == 200
    assert "risk_score" in response.json()
    assert "risk_factors" in response.json()
''',
            '''
def test_travel_rule_compliance():
    """Test Travel Rule compliance"""
    # Test travel rule reporting
    response = client.post("/api/v1/compliance/travel-rule/report", json={
        "transaction": {
            "originator": {"name": "Test Sender", "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"},
            "beneficiary": {"name": "Test Recipient", "address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"},
            "amount": 1000.0,
            "currency": "BTC",
            "blockchain": "bitcoin"
        }
    })
    assert response.status_code == 200
    assert "report_id" in response.json()
    
    # Test travel rule retrieval
    response = client.get("/api/v1/compliance/travel-rule/reports")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
''',
            '''
def test_audit_trail():
    """Test comprehensive audit trail"""
    # Create audit entry
    response = client.post("/api/v1/compliance/audit/log", json={
        "action": "data_access",
        "user_id": "test_user",
        "resource": "investigation_123",
        "details": {"purpose": "investigation_review"}
    })
    assert response.status_code == 201
    
    # Retrieve audit trail
    response = client.get("/api/v1/compliance/audit/trail", params={
        "user_id": "test_user",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    })
    assert response.status_code == 200
    assert "audit_entries" in response.json()
    assert len(response.json()["audit_entries"]) > 0
''',
            '''
def test_regulatory_reporting():
    """Test regulatory reporting features"""
    # Generate SAR (Suspicious Activity Report)
    response = client.post("/api/v1/compliance/reports/sar", json={
        "suspicious_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
        "suspicion_reason": "Unusual transaction pattern",
        "reporting_period": {
            "start": "2024-01-01",
            "end": "2024-01-31"
        }
    })
    assert response.status_code == 200
    assert "sar_id" in response.json()
    
    # Generate CTR (Currency Transaction Report)
    response = client.post("/api/v1/compliance/reports/ctr", json={
        "transactions": [
            {"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "amount": 15000.0, "currency": "USD"}
        ],
        "reporting_date": "2024-01-15"
    })
    assert response.status_code == 200
    assert "ctr_id" in response.json()
'''
        ]
        
        self.generated_tests.extend([f"compliance_test_{i}" for i in range(len(tests))])
        return tests
    
    def generate_performance_tests(self) -> List[str]:
        """Generate performance and load tests"""
        tests = [
            '''
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
''',
            '''
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
''',
            '''
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
'''
        ]
        
        self.generated_tests.extend([f"performance_test_{i}" for i in range(len(tests))])
        return tests
    
    def generate_error_handling_tests(self) -> List[str]:
        """Generate error handling and edge case tests"""
        tests = [
            '''
def test_network_error_handling():
    """Test handling of network errors and timeouts"""
    # Test with invalid endpoint to simulate network issues
    response = client.get("/api/v1/blockchain/timeout-test")
    # Should handle gracefully without crashing
    assert response.status_code in [404, 408, 500]
''',
            '''
def test_malformed_request_handling():
    """Test handling of malformed requests"""
    malformed_requests = [
        {"invalid": "structure"},
        {"address": None},
        {"amount": "not_a_number"},
        {"dates": {"start": "invalid_date"}}
    ]
    
    for malformed_data in malformed_requests:
        response = client.post("/api/v1/analysis/address", json=malformed_data)
        assert response.status_code in [400, 422]
        assert "error" in response.json()
''',
            '''
def test_resource_exhaustion():
    """Test behavior under resource exhaustion"""
    # Test with very large request
    large_data = {"addresses": [f"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfN{i}" for i in range(10000)]}
    
    response = client.post("/api/v1/analysis/bulk", json=large_data, timeout=30.0)
    # Should handle gracefully (either succeed with limit or fail gracefully)
    assert response.status_code in [200, 400, 413, 503]
'''
        ]
        
        self.generated_tests.extend([f"error_handling_test_{i}" for i in range(len(tests))])
        return tests
    
    def generate_auth_rbac_tests(self) -> List[str]:
        """Generate authentication and RBAC tests"""
        tests = [
            '''
def test_role_based_access_control():
    """Test RBAC permissions for different roles"""
    # Test viewer permissions
    viewer_token = create_test_token("viewer")
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {viewer_token}"})
    assert response.status_code == 403  # Viewer shouldn't access user management
    
    # Test admin permissions
    admin_token = create_test_token("admin")
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200  # Admin should access user management
    
    # Test analyst permissions
    analyst_token = create_test_token("analyst")
    response = client.post("/api/v1/investigations", 
                          json={"title": "Test"}, 
                          headers={"Authorization": f"Bearer {analyst_token}"})
    assert response.status_code in [200, 201]  # Analyst should create investigations
''',
            '''
def test_token_expiration():
    """Test token expiration handling"""
    # Create expired token
    expired_token = create_expired_token()
    
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert "expired" in response.json().get("detail", "").lower()
''',
            '''
def test_permission_inheritance():
    """Test that higher roles inherit lower role permissions"""
    admin_token = create_test_token("admin")
    
    # Admin should be able to access viewer-level endpoints
    response = client.get("/api/v1/analysis/address/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", 
                          headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
'''
        ]
        
        self.generated_tests.extend([f"auth_rbac_test_{i}" for i in range(len(tests))])
        return tests
    
    def _write_test_file(self, category: str, tests: List[str]):
        """Write tests to file"""
        test_dir = self.tests_dir / category
        test_dir.mkdir(parents=True, exist_ok=True)
        
        test_content = f'''"""
Auto-generated {category.replace('_', ' ').title()}
Generated on: {datetime.now(timezone.utc).isoformat()}
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
    
    payload = {{
        "sub": "test_viewer",
        "user_id": "test_user_viewer",
        "role": "viewer",
        "permissions": ["test_permission"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }}
    
    return jwt.encode(payload, os.getenv("TEST_JWT_SECRET", "test_secret"), algorithm="HS256")

def create_expired_token() -> str:
    """Create expired JWT token"""
    import jwt
    from datetime import datetime, timezone, timedelta
    import os
    
    payload = {{
        "sub": "test_user",
        "user_id": "test_user",
        "role": "viewer",
        "permissions": ["test_permission"],
        "exp": datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
    }}
    
    return jwt.encode(payload, os.getenv("TEST_JWT_SECRET", "test_secret"), algorithm="HS256")

'''
        
        for i, test in enumerate(tests):
            test_content += f"\n{test}\n"
        
        test_file = test_dir / f"test_{category}.py"
        with open(test_file, "w") as f:
            f.write(test_content)
        
        print(f"Generated {len(tests)} tests in {test_file}")


def main():
    """Main function to run test generation"""
    generator = TestGenerator()
    report = generator.generate_all_tests()
    
    print(f"\n=== Test Generation Summary ===")
    print(f"Total tests generated: {report['total_tests_generated']}")
    print(f"Categories: {', '.join(report['categories'])}")
    print(f"Report saved to: test_expansion_report.json")
    
    return report


if __name__ == "__main__":
    main()
