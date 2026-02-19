# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jackdaw Sentry is an enterprise blockchain onchain analysis platform for crypto compliance investigators. It provides cross-chain transaction tracking across 14+ blockchains, AML pattern detection, regulatory compliance (GDPR/DORA/MiCA/AMLR), and graph-based transaction analysis.

## Commands

### Development
```bash
make dev              # Start full Docker stack (Neo4j, Postgres, Redis, API, Nginx, Prometheus, Grafana)
make dev-down         # Stop dev stack
make logs-dev         # Tail dev logs
```

### Testing
```bash
make test                                           # Run all non-integration tests
pytest tests/test_api/test_auth.py                  # Run a specific test file
pytest tests/test_compliance/test_audit_trail.py -k "test_create_entry"  # Run a single test by name
pytest -m "not integration" --tb=short -q           # What `make test` runs
```

Unit/smoke tests run without external services (DB connections are mocked in `tests/conftest.py`). Integration tests (`@pytest.mark.integration`) require running Docker services.

Test markers: `unit`, `integration`, `smoke`, `api`, `database`, `auth`.

### Linting
```bash
make lint             # flake8 on src/ (fatal errors only: E9,F63,F7,F82)
```

Code style tools (not wired into Makefile): `black` (formatter), `isort` (imports), `mypy` (types).

### E2E Tests
```bash
npm run test:e2e      # Playwright (requires full stack running)
```

### Load Testing
```bash
make test-load        # Locust-based benchmarks
```

## Architecture

### Tech Stack
- **Backend**: FastAPI (async Python 3.11+), Uvicorn
- **Databases**: Neo4j 5.14 (graph/transaction flows), PostgreSQL 15 (compliance/users/audit), Redis 7 (cache/rate-limiting)
- **Frontend**: Vanilla HTML/JS with Tailwind CSS (CDN), Chart.js, Cytoscape.js for graph viz
- **Infra**: Docker Compose, Nginx reverse proxy, Prometheus + Grafana monitoring

### Backend Layout (`src/`)

**Entry point**: `src/api/main.py` — FastAPI app with lifespan manager that initializes/closes all DB connections.

**Configuration**: `src/api/config.py` — Pydantic `BaseSettings` loaded from `.env`. All secrets must be >=32 chars.

**Auth**: `src/api/auth.py` — JWT (HS256) + RBAC with 4 roles: `admin`, `analyst`, `investigator`, `viewer`. Uses `get_current_user` / `require_admin` as FastAPI dependencies.

**Routers** (`src/api/routers/`): 19 router modules mounted at `/api/v1/{domain}`. Key routers:
- `auth.py` — login, token generation
- `analysis.py` — address/transaction analysis across chains
- `compliance.py` — compliance checks, case management, risk assessment
- `graph.py` — Neo4j graph exploration endpoints
- `setup.py` — initial admin setup wizard

**Middleware chain** (`src/api/middleware.py`): `SecurityMiddleware` → `AuditMiddleware` → `RateLimitMiddleware`, plus CORS and TrustedHost.

**Core engines** — each domain has a manager + specialized engines:
- `src/analysis/` — `AnalysisManager` orchestrates `CrossChainAnalyzer`, `MLPatternDetector`, `MixerDetector`, `StablecoinFlowTracker`, `MLClusteringEngine`, `BridgeTracker`
- `src/compliance/` — `AuditTrailEngine` (hash-chained immutable logs), `CaseManagementEngine`, `RegulatoryReportingEngine`, `AutomatedRiskAssessmentEngine`
- `src/collectors/` — `CollectorManager` with per-chain collectors inheriting from `BaseCollector`. RPC clients managed by factory pattern in `src/collectors/rpc/factory.py`
- `src/intelligence/` — `IntegrationManager` for Chainalysis/Elliptic/Arkham APIs, OSINT workflows, sanctions screening, dark web monitoring

**Database layer** (`src/database/`): Schema definitions for PostgreSQL (`postgres_schema.py`), Neo4j (`neo4j_schema.py`), plus GDPR compliance utilities (`gdpr_compliance.py`). Connection management lives in `src/api/database.py` using global singleton pools (asyncpg, neo4j async driver, redis.asyncio).

### Frontend Layout (`frontend/`)

9-page SPA-style app (no framework). Each page has a corresponding `frontend/js/<page>.js` file.

- `js/auth.js` — JWT token management in localStorage, `fetchWithAuth()` wrapper that injects bearer tokens and handles 401 redirects
- `js/nav.js` — shared navbar, dark mode toggle
- `js/utils.js` — `JDS` utility module (chart colors, formatters, toast notifications)
- `graph.html` + `js/graph.js` — Neo4j transaction graph explorer using Cytoscape.js

Nginx serves the frontend statically and proxies `/api/` to the FastAPI backend.

### Test Structure (`tests/`)

`tests/conftest.py` provides core fixtures:
- `client` — FastAPI `TestClient` with all DB init/shutdown mocked out
- `make_token` — factory to generate JWT tokens with custom claims
- `auth_headers` / `admin_headers` — pre-built Authorization headers

Test suites: `test_api/` (smoke, auth, integration), `test_analysis/` (engine tests), `test_compliance/` (4 engine test files + workflow + API integration).

### Key Patterns
- **Async-first**: All I/O (database, HTTP, RPC) uses async/await
- **Dual-database**: Neo4j for graph relationships, PostgreSQL for relational compliance data
- **Factory pattern**: RPC client creation with connection pooling per blockchain
- **Manager pattern**: Each domain has a manager class that orchestrates specialized engine instances
- **Pydantic validation**: Request/response models validated via Pydantic BaseModel

## Environment Setup

```bash
cp .env.example .env
# Generate secrets: for var in API_SECRET_KEY NEO4J_PASSWORD POSTGRES_PASSWORD REDIS_PASSWORD ENCRYPTION_KEY JWT_SECRET_KEY; do echo "$var=$(openssl rand -hex 32)"; done
make dev
python scripts/init_databases.py
```
