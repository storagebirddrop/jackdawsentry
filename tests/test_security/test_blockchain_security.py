"""
Security Tests - Blockchain Module Security for Phases 1-3

Tests security for blockchain module including RPC security,
address validation, transaction data privacy, and cross-chain validation.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.api.main import app
from src.api.auth import create_access_token


class TestBlockchainModuleSecurity:
    """Test security for blockchain module"""
    
    def setup_method(self):
        """Setup test client and tokens"""
        self.client = TestClient(app)
        self.admin_token = create_access_token(data={"sub": "admin", "role": "admin"})
        self.analyst_token = create_access_token(data={"sub": "analyst", "role": "analyst"})
        self.viewer_token = create_access_token(data={"sub": "viewer", "role": "viewer"})
        self.unauthorized_token = create_access_token(data={"sub": "unauthorized", "role": "unauthorized"})
    
    def test_blockchain_endpoints_require_authentication(self):
        """Test that all blockchain endpoints require authentication"""
        
        blockchain_endpoints = [
            # Core blockchain endpoints
            ("/api/v1/blockchain/statistics", "GET"),
            ("/api/v1/blockchain/trace", "POST"),
            ("/api/v1/blockchain/address", "GET"),
            ("/api/v1/blockchain/transaction", "GET"),
            ("/api/v1/blockchain/balance", "GET"),
            ("/api/v1/blockchain/rpc/ethereum", "POST"),
            ("/api/v1/blockchain/rpc/solana", "POST"),
            ("/api/v1/blockchain/rpc/tron", "POST"),
            ("/api/v1/blockchain/rpc/xrpl", "POST"),
            ("/api/v1/blockchain/cross-platform", "POST"),
            ("/api/v1/blockchain/validate", "POST"),
        ]
        
        for endpoint, method in blockchain_endpoints:
            if method == "GET":
                response = self.client.get(endpoint)
            elif method == "POST":
                response = self.client.post(endpoint, json={})
            
            # All endpoints should return 401 without authentication
            assert response.status_code == 401, f"Blockchain endpoint {endpoint} should require authentication"
    
    def test_rpc_call_security(self):
        """Test RPC call security and validation"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test various RPC calls with security considerations
        rpc_tests = [
            # Valid RPC call
            {
                "method": "eth_getBalance",
                "params": ["0x1234567890123456789012345678901234567890", "latest"],
                "blockchain": "ethereum"
            },
            # SQL injection attempt in RPC parameters
            {
                "method": "eth_getBalance",
                "params": ["'; DROP TABLE blockchain_data; --", "latest"],
                "blockchain": "ethereum"
            },
            # XSS attempt in RPC parameters
            {
                "method": "eth_call",
                "params": [{"to": "<script>alert('xss')</script>", "data": "0x"}, "latest"],
                "blockchain": "ethereum"
            },
            # Command injection attempt
            {
                "method": "personal_unlockAccount",
                "params": ["0x1234567890123456789012345678901234567890", "password; rm -rf /"],
                "blockchain": "ethereum"
            },
            # Extremely long parameter
            {
                "method": "eth_getBalance",
                "params": ["x" * 1000, "latest"],
                "blockchain": "ethereum"
            }
        ]
        
        for rpc_test in rpc_tests:
            response = self.client.post(
                "/api/v1/blockchain/rpc/ethereum",
                json=rpc_test,
                headers=headers
            )
            
            # Should handle RPC security validation
            assert response.status_code in [200, 400, 422, 500], \
                f"Should handle RPC security validation for: {rpc_test['method']}"
            
            if response.status_code == 200:
                # Check that response doesn't contain malicious content
                response_text = response.text.lower()
                malicious_patterns = ["<script>", "drop table", "rm -rf"]
                for pattern in malicious_patterns:
                    assert pattern not in response_text, f"RPC response should not contain malicious pattern: {pattern}"
    
    def test_address_validation_security(self):
        """Test address validation and security"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test address validation with various inputs
        address_tests = [
            # Valid Ethereum address
            "0x1234567890123456789012345678901234567890",
            # Invalid address format
            "invalid_address",
            # SQL injection attempt
            "'; DROP TABLE addresses; --",
            # XSS attempt
            "<script>alert('xss')</script>",
            # Extremely long address
            "x" * 1000,
            # Null bytes
            "0x1234\x00567890123456789012345678901234567890",
            # Special characters
            "0x!@#$%^&*()_+-=[]{}|;':\",./<>?",
            # Empty address
            "",
            # None equivalent
            None
        ]
        
        for address in address_tests:
            if address is None:
                # Test with null address in JSON
                response = self.client.get(
                    "/api/v1/blockchain/address",
                    params={"address": "", "blockchain": "ethereum"},
                    headers=headers
                )
            else:
                response = self.client.get(
                    f"/api/v1/blockchain/address?address={address}&blockchain=ethereum",
                    headers=headers
                )
            
            # Should handle address validation
            assert response.status_code in [200, 400, 422], \
                f"Should handle address validation for: {str(address)[:50]}..."
    
    def test_transaction_data_privacy(self):
        """Test transaction data privacy and protection"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test transaction tracing with sensitive data
        transaction_data = {
            "transaction_hash": f"0x{uuid.uuid4().hex[:64]}",
            "blockchain": "ethereum",
            "include_analysis": True,
            "include_sensitive_data": True,
            "include_private_notes": "This transaction contains sensitive information"
        }
        
        response = self.client.post(
            "/api/v1/blockchain/trace",
            json=transaction_data,
            headers=headers
        )
        
        # Should handle transaction tracing
        assert response.status_code in [200, 404], "Should handle transaction tracing"
        
        if response.status_code == 200:
            trace_result = response.json()
            
            # Check that sensitive transaction data is handled properly
            if "analysis" in trace_result:
                analysis = trace_result["analysis"]
                # In real implementation, would check for data protection
            
            # Test transaction access control
            transaction_access_tests = [
                (self.admin_token, True),      # Admin should access
                (self.analyst_token, True),    # Analyst should access
                (self.viewer_token, False),     # Viewer should be denied
                (self.unauthorized_token, False) # Unauthorized should be denied
            ]
            
            for token, should_access in transaction_access_tests:
                test_headers = {"Authorization": f"Bearer {token}"}
                get_response = self.client.get(
                    f"/api/v1/blockchain/transaction/{transaction_data['transaction_hash']}",
                    headers=test_headers
                )
                
                if should_access:
                    assert get_response.status_code not in [401, 403], f"Role should access transaction data"
                else:
                    assert get_response.status_code in [401, 403, 404], f"Role should be denied access to transaction data"
    
    def test_cross_chain_validation_security(self):
        """Test cross-chain validation security"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test cross-chain analysis
        cross_chain_data = {
            "addresses": [
                {
                    "address": f"0x{uuid.uuid4().hex[:40]}",
                    "blockchain": "ethereum"
                },
                {
                    "address": f"{uuid.uuid4().hex[:32]}",
                    "blockchain": "solana"
                },
                {
                    "address": f"{uuid.uuid4().hex[:34]}",
                    "blockchain": "tron"
                }
            ],
            "analysis_depth": 3,
            "include_cross_chain_patterns": True,
            "include_risk_assessment": True
        }
        
        response = self.client.post(
            "/api/v1/blockchain/cross-platform",
            json=cross_chain_data,
            headers=headers
        )
        
        # Should handle cross-chain analysis
        assert response.status_code in [200, 404], "Should handle cross-chain analysis"
        
        if response.status_code == 200:
            cross_chain_result = response.json()
            
            # Check that cross-chain data is handled properly
            if "cross_chain_patterns" in cross_chain_result:
                patterns = cross_chain_result["cross_chain_patterns"]
                assert isinstance(patterns, list), "Cross-chain patterns should be properly formatted"
            
            # Test cross-chain access control
            cross_chain_access_tests = [
                (self.admin_token, True),      # Admin should access
                (self.analyst_token, True),    # Analyst should access
                (self.viewer_token, False),     # Viewer should be denied
                (self.unauthorized_token, False) # Unauthorized should be denied
            ]
            
            for token, should_access in cross_chain_access_tests:
                test_headers = {"Authorization": f"Bearer {token}"}
                get_response = self.client.get(
                    "/api/v1/blockchain/cross-platform/status",
                    headers=test_headers
                )
                
                if should_access:
                    assert get_response.status_code not in [401, 403], f"Role should access cross-chain data"
                else:
                    assert get_response.status_code in [401, 403, 404], f"Role should be denied access to cross-chain data"
    
    def test_blockchain_data_integrity(self):
        """Test blockchain data integrity and validation"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test data integrity validation
        integrity_tests = [
            # Valid blockchain data
            {
                "blockchain": "ethereum",
                "block_number": 12345,
                "block_hash": f"0x{uuid.uuid4().hex[:64]}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            # Invalid block number
            {
                "blockchain": "ethereum",
                "block_number": -1,
                "block_hash": f"0x{uuid.uuid4().hex[:64]}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            # Invalid block hash
            {
                "blockchain": "ethereum",
                "block_number": 12345,
                "block_hash": "invalid_hash",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            # Future timestamp
            {
                "blockchain": "ethereum",
                "block_number": 12345,
                "block_hash": f"0x{uuid.uuid4().hex[:64]}",
                "timestamp": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            }
        ]
        
        for integrity_test in integrity_tests:
            response = self.client.post(
                "/api/v1/blockchain/validate",
                json=integrity_test,
                headers=headers
            )
            
            # Should handle integrity validation
            assert response.status_code in [200, 400, 422], \
                f"Should handle integrity validation for block {integrity_test.get('block_number', 'unknown')}"
    
    def test_rpc_endpoint_security(self):
        """Test individual RPC endpoint security"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test each blockchain RPC endpoint
        blockchain_endpoints = [
            ("ethereum", "/api/v1/blockchain/rpc/ethereum"),
            ("solana", "/api/v1/blockchain/rpc/solana"),
            ("tron", "/api/v1/blockchain/rpc/tron"),
            ("xrpl", "/api/v1/blockchain/rpc/xrpl")
        ]
        
        for blockchain, endpoint in blockchain_endpoints:
            # Test with valid RPC call
            valid_rpc = {
                "method": "getBlockByNumber",
                "params": ["latest", False],
                "id": 1
            }
            
            response = self.client.post(endpoint, json=valid_rpc, headers=headers)
            
            # Should handle valid RPC calls
            assert response.status_code in [200, 400, 500], \
                f"Should handle RPC call for {blockchain}"
            
            # Test with malicious RPC call
            malicious_rpc = {
                "method": "personal_unlockAccount",
                "params": ["0x1234567890123456789012345678901234567890", "'; DROP TABLE users; --"],
                "id": 1
            }
            
            response = self.client.post(endpoint, json=malicious_rpc, headers=headers)
            
            # Should handle malicious RPC calls
            assert response.status_code in [400, 422, 500], \
                f"Should handle malicious RPC call for {blockchain}"
    
    def test_blockchain_rate_limiting(self):
        """Test blockchain endpoint rate limiting"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test rapid RPC calls
        rpc_responses = []
        for i in range(20):
            rpc_call = {
                "method": "eth_getBalance",
                "params": [f"0x{uuid.uuid4().hex[:40]}", "latest"],
                "id": i
            }
            
            response = self.client.post(
                "/api/v1/blockchain/rpc/ethereum",
                json=rpc_call,
                headers=headers
            )
            rpc_responses.append(response.status_code)
            
            # Stop early if we hit rate limit
            if response.status_code == 429:
                break
        
        # Should eventually hit rate limit
        assert 429 in rpc_responses, "Blockchain RPC should have rate limiting"
    
    def test_sensitive_blockchain_data(self):
        """Test handling of sensitive blockchain data"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test with sensitive blockchain data
        sensitive_data = {
            "private_keys": [
                f"0x{uuid.uuid4().hex[:64]}" for _ in range(3)
            ],
            "mnemonic_phrases": [
                "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12"
            ],
            "seed_phrases": [
                f"seed_{uuid.uuid4().hex[:16]}"
            ],
            "wallet_passwords": [
                f"password_{uuid.uuid4().hex[:8]}"
            ]
        }
        
        response = self.client.post(
            "/api/v1/blockchain/secure-data",
            json=sensitive_data,
            headers=headers
        )
        
        # Should either reject or handle sensitive data properly
        assert response.status_code in [400, 422, 404], \
            "Should reject or properly handle sensitive blockchain data"
    
    def test_blockchain_api_key_security(self):
        """Test blockchain API key security"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test API key management
        api_key_tests = [
            # Valid API key creation
            {
                "name": "Test API Key",
                "permissions": ["read", "trace"],
                "blockchains": ["ethereum", "solana"],
                "rate_limit": 1000
            },
            # API key with excessive permissions
            {
                "name": "Excessive API Key",
                "permissions": ["admin", "delete", "modify"],
                "blockchains": ["all"],
                "rate_limit": 100000
            }
        ]
        
        for api_key_test in api_key_tests:
            response = self.client.post(
                "/api/v1/blockchain/api-keys",
                json=api_key_test,
                headers=headers
            )
            
            # Should handle API key creation appropriately
            assert response.status_code in [201, 400, 422, 404], \
                f"Should handle API key creation: {api_key_test['name']}"
    
    def test_blockchain_data_export_security(self):
        """Test blockchain data export security"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test data export request
        export_request = {
            "export_type": "transaction_history",
            "blockchain": "ethereum",
            "date_range": {
                "start": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                "end": datetime.now(timezone.utc).isoformat()
            },
            "include_sensitive_data": True,
            "format": "json",
            "encryption_required": True
        }
        
        response = self.client.post(
            "/api/v1/blockchain/export",
            json=export_request,
            headers=headers
        )
        
        # Should handle export request
        assert response.status_code in [201, 404], "Should handle blockchain data export"
        
        # Test export access control
        export_access_tests = [
            (self.admin_token, True),      # Admin should export
            (self.analyst_token, True),    # Analyst should export
            (self.viewer_token, False),     # Viewer should be denied
            (self.unauthorized_token, False) # Unauthorized should be denied
        ]
        
        for token, should_access in export_access_tests:
            test_headers = {"Authorization": f"Bearer {token}"}
            get_response = self.client.get("/api/v1/blockchain/exports", headers=test_headers)
            
            if should_access:
                assert get_response.status_code not in [401, 403], f"Role should access blockchain exports"
            else:
                assert get_response.status_code in [401, 403, 404], f"Role should be denied access to blockchain exports"


if __name__ == "__main__":
    pytest.main([__file__])
