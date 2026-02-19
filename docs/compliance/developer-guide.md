# Compliance System Developer Guide

This guide provides technical documentation for developers working with the Jackdaw Sentry compliance system.

## 🏗️ Architecture Overview

### System Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend UI   │    │   API Gateway   │    │  Load Balancer  │
│   (Dashboard)   │◄──►│   (FastAPI)     │◄──►│   (Nginx)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌─────────────────────────────────┐
                    │      Compliance Services         │
                    │  ┌─────────────┐ ┌─────────────┐ │
                    │  │Regulatory   │ │Case         │ │
                    │  │Reporting    │ │Management   │ │
                    │  │Engine       │ │Engine       │ │
                    │  └─────────────┘ └─────────────┘ │
                    │  ┌─────────────┐ ┌─────────────┐ │
                    │  │Audit Trail  │ │Risk         │ │
                    │  │Engine       │ │Assessment   │ │
                    │  └─────────────┘ └─────────────┘ │
                    └─────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────────────┐
                    │        Data Layer               │
                    │  ┌─────────────┐ ┌─────────────┐ │
                    │  │   Neo4j     │ │   Redis     │ │
                    │  │   Graph DB  │ │   Cache     │ │
                    │  └─────────────┘ └─────────────┘ │
                    │  ┌─────────────┐ ┌─────────────┐ │
                    │  │ PostgreSQL  │ │Elasticsearch│ │
                    │  │   (Audit)   │ │ (Logs)      │ │
                    │  └─────────────┘ └─────────────┘ │
                    └─────────────────────────────────┘
```

### Technology Stack
- **Backend**: Python 3.11+, FastAPI, AsyncIO
- **Database**: Neo4j (Graph), PostgreSQL (Audit), Redis (Cache)
- **Frontend**: HTML5, JavaScript, Tailwind CSS, Chart.js
- **Containerization**: Docker, Docker Compose
- **Monitoring**: Prometheus, Grafana, ELK Stack
- **Security**: JWT Authentication, RBAC, AES-256 Encryption

## 🔧 Development Setup

### Prerequisites
```bash
# Required software versions
Python >= 3.11
Docker >= 20.10
Docker Compose >= 2.0
Git >= 2.30
```

### Environment Setup
```bash
# Clone repository
git clone https://github.com/jackdawsentry/compliance.git
cd compliance

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start development services
docker compose -f docker/compliance-compose.yml up -d
```

### Database Setup
```bash
# Initialize Neo4j schema
python -m src.database.compliance_schema

# Run database migrations
python -m src.database.migrations

# Verify database connectivity
python -c "
from src.database.neo4j_client import get_neo4j_session
import asyncio
async def test():
    session = await get_neo4j_session()
    result = await session.run('RETURN 1 as test')
    print('Neo4j connection successful')
asyncio.run(test())
"
```

## 📁 Project Structure

```
src/
├── compliance/                 # Compliance engines
│   ├── __init__.py
│   ├── regulatory_reporting.py
│   ├── case_management.py
│   ├── audit_trail.py
│   └── automated_risk_assessment.py
├── api/                       # API layer
│   ├── routers/
│   │   ├── compliance.py
│   │   └── admin.py
│   ├── auth.py
│   └── main.py
├── database/                  # Database layer
│   ├── neo4j_client.py
│   ├── postgres_client.py
│   └── compliance_schema.py
├── cache/                     # Caching layer
│   └── compliance_cache.py
├── monitoring/                # Monitoring system
│   └── compliance_monitoring.py
├── scheduling/                # Task scheduling
│   └── compliance_scheduler.py
└── utils/                     # Utilities
    ├── logging.py
    ├── security.py
    └── helpers.py
```

## 🔌 API Development

### Adding New Endpoints

#### 1. Create Route Handler
```python
# src/api/routers/compliance.py
from fastapi import APIRouter, Depends, HTTPException
from src.api.auth import get_current_user, check_permissions

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])

@router.post("/new-endpoint")
async def new_endpoint(
    request_data: NewEndpointRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["write_compliance"]))
):
    """New compliance endpoint"""
    try:
        # Implementation logic
        result = await process_request(request_data)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### 2. Define Request/Response Models
```python
# src/api/models/compliance.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class NewEndpointRequest(BaseModel):
    field1: str = Field(..., description="Field 1 description")
    field2: Optional[int] = Field(None, description="Field 2 description")
    metadata: Optional[Dict[str, Any]] = None

class NewEndpointResponse(BaseModel):
    result_id: str
    status: str
    created_at: datetime
```

#### 3. Add Authentication & Authorization
```python
# src/api/auth.py
from fastapi import Depends, HTTPException, status
from src.api.models.auth import User
from src.api.permissions import PERMISSIONS

def check_permissions(required_permissions: List[str]):
    def permission_checker(current_user: User = Depends(get_current_user)):
        for permission in required_permissions:
            if permission not in current_user.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission required: {permission}"
                )
        return current_user
    return permission_checker
```

### Error Handling
```python
# src/api/exceptions.py
from fastapi import HTTPException
from typing import Any, Dict, Optional

class ComplianceException(Exception):
    """Base compliance exception"""
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

class ValidationError(ComplianceException):
    """Validation error"""
    pass

class DatabaseError(ComplianceException):
    """Database operation error"""
    pass

# Exception handler
from fastapi.responses import JSONResponse

async def compliance_exception_handler(request, exc: ComplianceException):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )
```

## 🗄️ Database Development

### Neo4j Schema Development

#### 1. Define Node and Relationship Models
```python
# src/database/models/compliance.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ComplianceNode(BaseModel):
    """Base compliance node model"""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class CaseNode(ComplianceNode):
    """Case node model"""
    title: str
    description: str
    case_type: str
    status: str
    priority: str
    assigned_to: Optional[str] = None
    created_by: str

class EvidenceNode(ComplianceNode):
    """Evidence node model"""
    case_id: str
    evidence_type: str
    description: str
    content: Dict[str, Any]
    status: str
    collected_by: str
    collected_at: datetime
```

#### 2. Database Operations
```python
# src/database/operations/case_operations.py
from neo4j import AsyncSession
from typing import List, Optional

class CaseOperations:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_case(self, case_data: Dict[str, Any]) -> str:
        """Create a new case node"""
        query = """
        CREATE (c:Case {
            case_id: $case_id,
            title: $title,
            description: $description,
            case_type: $case_type,
            status: $status,
            priority: $priority,
            assigned_to: $assigned_to,
            created_by: $created_by,
            created_at: datetime(),
            updated_at: datetime()
        })
        RETURN c.case_id as case_id
        """
        
        result = await self.session.run(query, **case_data)
        record = await result.single()
        return record["case_id"]

    async def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get case by ID"""
        query = """
        MATCH (c:Case {case_id: $case_id})
        RETURN c
        """
        
        result = await self.session.run(query, case_id=case_id)
        record = await result.single()
        
        if record:
            return dict(record["c"])
        return None

    async def update_case_status(self, case_id: str, status: str, updated_by: str) -> bool:
        """Update case status"""
        query = """
        MATCH (c:Case {case_id: $case_id})
        SET c.status = $status,
            c.updated_at = datetime(),
            c.updated_by = $updated_by
        RETURN c
        """
        
        result = await self.session.run(query, case_id=case_id, status=status, updated_by=updated_by)
        record = await result.single()
        return record is not None
```

### Database Migrations
```python
# src/database/migrations/migration_001_initial_schema.py
from src.database.migration import Migration

class Migration001InitialSchema(Migration):
    """Initial compliance schema migration"""
    
    async def up(self, session: AsyncSession):
        """Apply migration"""
        constraints = [
            "CREATE CONSTRAINT case_id_unique FOR (c:Case) REQUIRE c.case_id IS UNIQUE",
            "CREATE CONSTRAINT evidence_id_unique FOR (e:Evidence) REQUIRE e.evidence_id IS UNIQUE",
            "CREATE CONSTRAINT report_id_unique FOR (r:RegulatoryReport) REQUIRE r.report_id IS UNIQUE"
        ]
        
        for constraint in constraints:
            await session.run(constraint)
    
    async def down(self, session: AsyncSession):
        """Rollback migration"""
        constraints = [
            "DROP CONSTRAINT case_id_unique",
            "DROP CONSTRAINT evidence_id_unique",
            "DROP CONSTRAINT report_id_unique"
        ]
        
        for constraint in constraints:
            await session.run(constraint)
```

## 🚀 Compliance Engine Development

### Creating a New Compliance Engine

#### 1. Engine Base Class
```python
# src/compliance/base_engine.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseComplianceEngine(ABC):
    """Base class for compliance engines"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the engine"""
        try:
            await self._setup()
            self.initialized = True
            self.logger.info(f"{self.__class__.__name__} initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.__class__.__name__}: {e}")
            return False
    
    @abstractmethod
    async def _setup(self):
        """Setup engine-specific configuration"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check engine health"""
        pass
```

#### 2. Custom Engine Implementation
```python
# src/compliance/custom_engine.py
from src.compliance.base_engine import BaseComplianceEngine
from typing import Dict, Any, List

class CustomComplianceEngine(BaseComplianceEngine):
    """Custom compliance engine implementation"""
    
    async def _setup(self):
        """Setup custom engine"""
        # Initialize database connections
        # Setup configuration
        # Validate dependencies
        pass
    
    async def custom_operation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Custom compliance operation"""
        if not self.initialized:
            raise RuntimeError("Engine not initialized")
        
        try:
            # Implementation logic
            result = await self._process_data(data)
            return {"success": True, "result": result}
        except Exception as e:
            self.logger.error(f"Custom operation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def health_check(self) -> bool:
        """Check engine health"""
        try:
            # Perform health checks
            return True
        except Exception:
            return False
```

### Risk Assessment Engine Development

#### Risk Factor Implementation
```python
# src/compliance/risk_factors/base_factor.py
from abc import ABC, abstractmethod
from typing import Dict, Any
from enum import Enum

class RiskCategory(Enum):
    TRANSACTION_VOLUME = "transaction_volume"
    ADDRESS_RISK = "address_risk"
    AMOUNT_ANOMALY = "amount_anomaly"
    GEOGRAPHIC_RISK = "geographic_risk"
    COUNTERPARTY_RISK = "counterparty_risk"

class BaseRiskFactor(ABC):
    """Base class for risk factors"""
    
    def __init__(self, category: RiskCategory, weight: float):
        self.category = category
        self.weight = weight
    
    @abstractmethod
    async def calculate_score(self, entity_id: str, entity_type: str) -> float:
        """Calculate risk score for entity"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get factor description"""
        pass

# Example implementation
class TransactionVolumeFactor(BaseRiskFactor):
    """Transaction volume risk factor"""
    
    def __init__(self, weight: float = 0.25):
        super().__init__(RiskCategory.TRANSACTION_VOLUME, weight)
    
    async def calculate_score(self, entity_id: str, entity_type: str) -> float:
        """Calculate transaction volume risk score"""
        # Get transaction history
        # Analyze volume patterns
        # Calculate risk score (0.0 to 1.0)
        volume = await self._get_transaction_volume(entity_id)
        
        # Risk increases with volume (simplified)
        if volume > 1000000:  # > $1M
            return 0.9
        elif volume > 100000:  # > $100K
            return 0.7
        elif volume > 10000:   # > $10K
            return 0.5
        else:
            return 0.2
    
    def get_description(self) -> str:
        return "Transaction volume analysis"
    
    async def _get_transaction_volume(self, entity_id: str) -> float:
        """Get total transaction volume for entity"""
        # Implementation to query blockchain data
        return 0.0  # Placeholder
```

## 🔄 Testing Development

### Unit Tests
```python
# tests/test_compliance/test_custom_engine.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from src.compliance.custom_engine import CustomComplianceEngine

class TestCustomComplianceEngine:
    """Test suite for CustomComplianceEngine"""
    
    @pytest.fixture
    async def engine(self):
        """Create test engine instance"""
        engine = CustomComplianceEngine()
        await engine.initialize()
        yield engine
        # Cleanup if needed
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, engine):
        """Test engine initialization"""
        assert engine.initialized is True
    
    @pytest.mark.asyncio
    async def test_custom_operation_success(self, engine):
        """Test successful custom operation"""
        data = {"test": "data"}
        result = await engine.custom_operation(data)
        
        assert result["success"] is True
        assert "result" in result
    
    @pytest.mark.asyncio
    async def test_custom_operation_failure(self, engine):
        """Test custom operation failure"""
        with patch.object(engine, '_process_data', side_effect=Exception("Test error")):
            data = {"test": "data"}
            result = await engine.custom_operation(data)
            
            assert result["success"] is False
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_health_check(self, engine):
        """Test health check"""
        health = await engine.health_check()
        assert isinstance(health, bool)
```

### Integration Tests
```python
# tests/test_integration/test_compliance_api.py
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

class TestComplianceAPIIntegration:
    """Test suite for compliance API integration"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for authentication"""
        return {
            "id": 1,
            "username": "test_user",
            "permissions": ["read_compliance", "write_compliance"]
        }
    
    def test_create_case_endpoint(self, client, mock_user):
        """Test case creation endpoint"""
        with patch('src.api.auth.get_current_user', return_value=mock_user):
            response = client.post(
                "/api/v1/compliance/cases",
                json={
                    "title": "Test Case",
                    "description": "Test description",
                    "case_type": "suspicious_activity",
                    "priority": "medium",
                    "assigned_to": "investigator"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "case_id" in data
```

### Performance Tests
```python
# tests/test_performance/test_risk_assessment.py
import pytest
import asyncio
import time
from src.compliance.automated_risk_assessment import AutomatedRiskAssessmentEngine

class TestRiskAssessmentPerformance:
    """Performance tests for risk assessment"""
    
    @pytest.mark.asyncio
    async def test_bulk_assessment_performance(self):
        """Test bulk risk assessment performance"""
        engine = AutomatedRiskAssessmentEngine()
        await engine.initialize()
        
        # Create 100 assessments concurrently
        tasks = []
        start_time = time.time()
        
        for i in range(100):
            task = engine.create_risk_assessment(
                entity_id=f"entity_{i}",
                entity_type="address",
                trigger_type="automatic"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Performance assertions
        assert len(results) == 100
        assert duration < 10.0  # Should complete within 10 seconds
        assert all(r.assessment_id is not None for r in results)
```

## 📊 Monitoring Development

### Custom Metrics
```python
# src/monitoring/custom_metrics.py
from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Any

class ComplianceMetrics:
    """Custom compliance metrics collection"""
    
    def __init__(self):
        # Define custom metrics
        self.case_creation_counter = Counter(
            'compliance_case_creation_total',
            'Total number of cases created',
            ['case_type', 'priority']
        )
        
        self.assessment_duration_histogram = Histogram(
            'compliance_assessment_duration_seconds',
            'Duration of risk assessments',
            ['entity_type', 'risk_level']
        )
        
        self.active_cases_gauge = Gauge(
            'compliance_active_cases',
            'Number of active cases',
            ['status']
        )
    
    def record_case_creation(self, case_type: str, priority: str):
        """Record case creation metric"""
        self.case_creation_counter.labels(
            case_type=case_type,
            priority=priority
        ).inc()
    
    def record_assessment_duration(self, duration: float, entity_type: str, risk_level: str):
        """Record assessment duration"""
        self.assessment_duration_histogram.labels(
            entity_type=entity_type,
            risk_level=risk_level
        ).observe(duration)
    
    def update_active_cases(self, status: str, count: int):
        """Update active cases gauge"""
        self.active_cases_gauge.labels(status=status).set(count)
```

### Health Checks
```python
# src/monitoring/health_checks.py
from typing import Dict, Any
from datetime import datetime
import asyncio

class HealthCheckManager:
    """Health check management"""
    
    def __init__(self):
        self.checks = {}
    
    def register_check(self, name: str, check_func):
        """Register a health check"""
        self.checks[name] = check_func
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            "overall_status": "healthy",
            "checks": {},
            "timestamp": datetime.utcnow().isoformat(),
            "issues": []
        }
        
        for name, check_func in self.checks.items():
            try:
                result = await check_func()
                results["checks"][name] = {
                    "status": "healthy" if result else "unhealthy",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if not result:
                    results["overall_status"] = "unhealthy"
                    results["issues"].append(f"Health check failed: {name}")
                    
            except Exception as e:
                results["checks"][name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                results["overall_status"] = "error"
                results["issues"].append(f"Health check error: {name} - {e}")
        
        return results

# Example health check
async def database_health_check() -> bool:
    """Database connectivity health check"""
    try:
        from src.database.neo4j_client import get_neo4j_session
        session = await get_neo4j_session()
        result = await session.run("RETURN 1")
        record = await result.single()
        return record is not None
    except Exception:
        return False
```

## 🔧 Configuration Management

### Environment Configuration
```python
# src/config/compliance_config.py
from pydantic import BaseSettings, Field
from typing import Optional

class ComplianceConfig(BaseSettings):
    """Compliance system configuration"""
    
    # Database Configuration
    neo4j_uri: str = Field(..., env="NEO4J_URI")
    neo4j_user: str = Field(..., env="NEO4J_USER")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")
    neo4j_database: str = Field("compliance", env="NEO4J_DATABASE")
    
    # Redis Configuration
    redis_host: str = Field("localhost", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    redis_db: int = Field(0, env="REDIS_DB")
    
    # Compliance Configuration
    regulatory_reporting_enabled: bool = Field(True, env="REGULATORY_REPORTING_ENABLED")
    case_management_enabled: bool = Field(True, env="CASE_MANAGEMENT_ENABLED")
    audit_trail_enabled: bool = Field(True, env="AUDIT_TRAIL_ENABLED")
    risk_assessment_enabled: bool = Field(True, env="RISK_ASSESSMENT_ENABLED")
    
    # Performance Configuration
    cache_ttl: int = Field(3600, env="COMPLIANCE_CACHE_TTL")
    batch_size: int = Field(100, env="COMPLIANCE_BATCH_SIZE")
    max_concurrent_assessments: int = Field(10, env="MAX_CONCURRENT_ASSESSMENTS")
    
    # Security Configuration
    jwt_secret: str = Field(..., env="JWT_SECRET")
    session_timeout: int = Field(3600, env="SESSION_TIMEOUT")
    max_login_attempts: int = Field(5, env="MAX_LOGIN_ATTEMPTS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global configuration instance
config = ComplianceConfig()
```

## 🚀 Deployment

### Docker Development
```dockerfile
# Dockerfile.dev
FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy application code
COPY . .

# Development-specific settings
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV COMPLIANCE_LOG_LEVEL=DEBUG

# Expose port
EXPOSE 8001

# Run development server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload", "--log-level", "debug"]
```

### Development Scripts
```bash
#!/bin/bash
# scripts/dev-setup.sh

echo "Setting up compliance development environment..."

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Setup pre-commit hooks
pre-commit install

# Run database migrations
python -m src.database.migrations

# Start development services
docker compose -f docker/compliance-compose.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Run health checks
python -c "
import asyncio
from src.monitoring.health_checks import HealthCheckManager
async def main():
    manager = HealthCheckManager()
    results = await manager.run_all_checks()
    print(f'Health check results: {results}')
asyncio.run(main())
"

echo "Development environment setup complete!"
echo "Dashboard: http://localhost:8001"
echo "API Docs: http://localhost:8001/docs"
```

## 📚 Best Practices

### Code Quality
- Use type hints for all function signatures
- Follow PEP 8 style guidelines
- Write comprehensive docstrings
- Use async/await for I/O operations
- Implement proper error handling

### Security
- Validate all input data
- Use parameterized queries
- Implement proper authentication
- Log security events
- Follow principle of least privilege

### Performance
- Use connection pooling
- Implement caching strategies
- Optimize database queries
- Monitor performance metrics
- Use async operations

### Testing
- Write unit tests for all functions
- Create integration tests for APIs
- Add performance tests for critical paths
- Use test fixtures and mocks
- Maintain high test coverage

---

**Last Updated**: 2024-01-15
**Version**: 1.5.0
**For Developers**: jackdawsentry.support@dawgus.com
