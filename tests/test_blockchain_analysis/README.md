# Blockchain Analysis Test Suite

## Overview

This comprehensive test suite validates Jackdaw Sentry's blockchain analysis functionality across all supported blockchains and analysis types.

## Test Structure

### Core Analysis Tests
- **`test_address_analysis.py`** - Address-level analysis, risk scoring, entity attribution
- **`test_transaction_analysis.py`** - Transaction parsing, cross-chain tracking, smart contract analysis
- **`test_pattern_detection.py`** - 15+ money laundering pattern detection algorithms
- **`test_cross_chain_analysis.py`** - Bridge detection, stablecoin flows, entity linking
- **`test_graph_visualization.py`** - Graph generation, visualization, analysis features
- **`test_alert_system.py`** - Real-time alerts, notifications, rule management

### Integration Tests
- **`test_integration.py`** - End-to-end workflows, multi-blockchain analysis, compliance workflows

## Running Tests

### Quick Start

```bash
# Run smoke tests (quick validation)
python scripts/run_blockchain_tests.py --smoke

# Run all tests
python scripts/run_blockchain_tests.py --all

# Run specific test suite
python scripts/run_blockchain_tests.py --suite address_analysis

# Run with coverage
python scripts/run_blockchain_tests.py --all --coverage

# Run integration tests (requires blockchain connections)
python scripts/run_blockchain_tests.py --integration
```

### Individual Test Execution

```bash
# Run specific test file
pytest tests/test_blockchain_analysis/test_address_analysis.py -v

# Run specific test class
pytest tests/test_blockchain_analysis/test_address_analysis.py::TestAddressAnalysis -v

# Run specific test method
pytest tests/test_blockchain_analysis/test_address_analysis.py::TestAddressAnalysis::test_address_analysis_risk_scoring -v
```

### Performance Testing

```bash
# Run performance tests
python scripts/run_blockchain_tests.py --performance

# Run with pytest markers
pytest tests/test_blockchain_analysis/ -m performance -v
```

## Test Categories

### Unit Tests
- **Marker**: `unit`
- **Purpose**: Test individual components in isolation
- **Dependencies**: Mocked external services
- **Speed**: Fast (< 1 second per test)

### Integration Tests
- **Marker**: `integration`
- **Purpose**: Test real blockchain interactions
- **Dependencies**: Active blockchain nodes required
- **Speed**: Slower (10-60 seconds per test)

### Performance Tests
- **Marker**: `performance`
- **Purpose**: Validate performance characteristics
- **Dependencies**: Realistic data volumes
- **Speed**: Variable (1-300 seconds per test)

### Smoke Tests
- **Marker**: `smoke`
- **Purpose**: Quick validation of core functionality
- **Dependencies**: Minimal
- **Speed**: Very fast (< 30 seconds total)

## Test Data

### Known Test Addresses
- **Bitcoin Genesis**: `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa`
- **Bitcoin Mixer**: `bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh`
- **Exchange Hot Wallet**: `1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2`
- **Ethereum Contract**: `0x8894E0a0c962CB7185c1888beBB3a4618a7730D6`

### Test Scenarios
- **Pattern Detection**: Peeling chains, mixing, layering, bridge hopping
- **Cross-Chain**: Bitcoin ↔ Ethereum, stablecoin flows, entity linking
- **Risk Scoring**: Low/medium/high/critical risk levels
- **Graph Visualization**: Small/medium/large graph performance

## Configuration

### Environment Variables
```bash
# Test configuration
TESTING=true
LOG_LEVEL=WARNING
API_SECRET_KEY=test-secret-key-for-testing-only-1234
JWT_SECRET_KEY=test-jwt-secret-key-for-testing-ok

# Database connections (for integration tests)
NEO4J_URI=bolt://localhost:7687
POSTGRES_HOST=localhost
REDIS_HOST=localhost

# Blockchain RPC (for integration tests)
BITCOIN_RPC_URL=http://localhost:8332
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/your-project-id
```

### Test Configuration Files
- **`pytest.ini`**: pytest configuration
- **`conftest.py`**: Test fixtures and setup
- **`.env.test`**: Test environment variables

## Coverage Reports

Coverage reports are generated in `test_results/` when using `--coverage` flag:

- **HTML Report**: `test_results/htmlcov/index.html`
- **JSON Report**: `test_results/coverage.json`
- **Terminal Report**: Shown in console output

## Test Results

Results are saved to `test_results/` directory:

- **Individual Suites**: `test_results/test_results_<suite>.json`
- **Performance**: `test_results/performance_test_results.json`
- **Integration**: `test_results/integration_test_results.json`
- **Smoke**: `test_results/smoke_test_results.json`
- **Overall**: `test_results/overall_test_report.json`

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're in the project directory
   ```bash
   cd /path/to/jackdawsentry
   python scripts/run_blockchain_tests.py --smoke
   ```

2. **Database Connection**: Verify database services are running
   ```bash
   docker-compose up -d postgres neo4j redis
   ```

3. **Blockchain Nodes**: Integration tests require active node connections
   ```bash
   # Check Bitcoin node
   bitcoin-cli getblockchaininfo
   
   # Check Ethereum node
   curl -X POST -H "Content-Type: application/json" \
        --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":["0x1"],"id":1}' \
        http://localhost:8545
   ```

4. **Permission Errors**: Ensure test files are executable
   ```bash
   chmod +x scripts/run_blockchain_tests.py
   ```

### Debug Mode

Run tests with debug output:
```bash
python scripts/run_blockchain_tests.py --suite address_analysis --verbose
```

### Test Isolation

Tests use pytest fixtures for isolation:
- **Client**: FastAPI TestClient with mocked databases
- **Database**: In-memory or mocked database connections
- **Blockchain**: Mocked RPC clients for unit tests

## Contributing

### Adding New Tests

1. Create test file in `tests/test_blockchain_analysis/`
2. Follow naming convention: `test_<feature>.py`
3. Use appropriate markers (`unit`, `integration`, `performance`)
4. Include comprehensive test cases
5. Add documentation for complex scenarios

### Test Structure Template

```python
"""
Test <Feature> Description
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

class Test<Feature>:
    """Test <feature> functionality"""
    
    def test_<scenario>(self, client):
        """Test <scenario> description"""
        response = client.post("/api/v1/<endpoint>", json={
            # Test data
        })
        
        assert response.status_code == 200
        data = response.json()
        # Assertions
    
    @pytest.mark.parametrize("param,value", [
        ("test1", "expected1"),
        ("test2", "expected2")
    ])
    def test_<parameterized_scenario>(self, client, param, value):
        """Test parameterized scenario"""
        # Test implementation
    
    @pytest.mark.integration
    def test_<integration_scenario>(self, client):
        """Test integration scenario"""
        # Requires real blockchain connections
```

## Performance Benchmarks

### Target Performance
- **Address Analysis**: < 200ms
- **Pattern Detection**: < 500ms
- **Graph Generation**: < 2s (500 nodes)
- **Alert Creation**: < 100ms
- **Cross-Chain Analysis**: < 3s

### Load Testing
- **Concurrent Requests**: 100 simultaneous analyses
- **Large Datasets**: 1000 addresses in < 30s
- **Memory Usage**: < 4GB peak memory
- **Graph Rendering**: < 5s for 1000 nodes

## Security Considerations

### Test Data
- **No Real User Data**: Use test addresses only
- **No Private Keys**: Never include private keys in tests
- **Anonymization**: Ensure test data is anonymized
- **GDPR Compliance**: Test data handling complies with GDPR

### Test Environment
- **Isolated**: Tests run in isolated environment
- **Clean State**: Each test starts with clean state
- **No Production Data**: Tests never access production data
- **Secure Connections**: Use secure test connections

## Maintenance

### Regular Updates
- **Monthly**: Review and update test cases
- **Quarterly**: Update test data and scenarios
- **Annually**: Review test architecture and tools

### Test Quality
- **Coverage**: Maintain >90% test coverage
- **Flaky Tests**: Identify and fix flaky tests
- **Performance**: Monitor test execution times
- **Reliability**: Ensure consistent test results
