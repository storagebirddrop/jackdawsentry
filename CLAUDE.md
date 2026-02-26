# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

**Jackdaw Sentry** is a blockchain on-chain analysis platform for compliance professionals. Core capabilities: multi-chain transaction flow tracking (16 blockchains), stablecoin/bridge/DEX monitoring, EU AMLR/GDPR/DORA/MiCA compliance reporting, ML-powered risk scoring, and sanctions screening.

Primary stack: Python/FastAPI backend, Rust (performance-critical paths), TypeScript/Node.js (tooling/frontend), PostgreSQL + Neo4j + Redis, Nginx proxy.

Reference docs in `docs/`, `src/api/README.md`, `src/database/README.md`, `src/compliance/README.md`.

---

## Development Commands

### Stack management
```bash
make dev                          # Start full dev stack (Neo4j, Postgres, Redis, API, Nginx)
make dev-down                     # Stop dev stack
make compliance                   # Start compliance-only stack
make prod                         # Start production stack
make logs-dev                     # Tail dev logs (last 200 lines, follow)
```

### Testing
```bash
make test                                  # Unit tests only — fast, no external services
pytest -m "not integration"                # Same as above
pytest -m integration                      # Integration tests — requires running stack
pytest tests/path/to/test_file.py          # Single test file
pytest -k "test_name"                      # Tests matching a name pattern
make test-load                             # Load/benchmark tests (CI mode)
```

### Linting & static analysis
```bash
make lint                                  # flake8 src/ — errors only (E9, F63, F7, F82)
black src/                                 # Auto-format (line-length 88)
isort src/                                 # Sort imports (black-compatible profile)
mypy src/                                  # Strict type checking
bandit -r src/                             # Security audit
interrogate src/ --fail-under=90           # Docstring coverage (90% required)
```

### Database migrations (Alembic / PostgreSQL)
```bash
alembic upgrade head                       # Apply all pending migrations
alembic revision --autogenerate -m "msg"   # Generate new migration from model changes
alembic downgrade -1                       # Roll back one migration
```
Migrations live in `src/api/migrations/`. Neo4j schema is managed in `src/database/neo4j_schema.py` (no migration tool — schema is applied at startup).

### E2E tests (requires running stack)
```bash
npm run test:e2e                           # Playwright headless
npm run test:e2e:headed                    # With visible browser
npm run test:e2e:debug                     # Debug mode
```

### Deployment
```bash
./scripts/deploy.sh production             # Production deploy with health checks & rollback
```

### CI pipeline (`.github/workflows/ci.yml`)
Lint → unit tests → Docker build verification. Integration tests are excluded from CI; run them locally.

---

## Environment Setup

Copy `.env.example` to `.env` and generate all required secrets before first run:
```bash
cp .env.example .env
for var in API_SECRET_KEY NEO4J_PASSWORD POSTGRES_PASSWORD REDIS_PASSWORD ENCRYPTION_KEY JWT_SECRET_KEY; do
  echo "$var=$(openssl rand -hex 32)"
done
```
Default seeded admin credentials: `admin` / `Admin123!@#` — change immediately after first login. 
**Security Policy:** Automated agents and scripts must never print, log, store, or transmit the default credential `Admin123!@#` in plaintext; replace with secure secret references during setup and redact in diagnostics.

Key env groups: database URIs, API secrets, per-chain RPC URLs, compliance toggles (sanctions update frequency, GDPR retention), ML thresholds, third-party API keys (Chainalysis, Elliptic, Arkham).

---

## Architecture

### Request flow
```
Browser/client → Nginx (:80/:443) → FastAPI (:8000) → Neo4j / PostgreSQL / Redis
```

### FastAPI (`src/api/main.py`)
16 routers at `/api/v1/`: `auth`, `blockchain`, `analysis`, `intelligence`, `investigations`, `compliance`, `attribution`, `reports`, `analytics`, `competitive`, `forensics`, `mobile`, `admin`, `teams`, `webhooks`, `workflows`.

Middleware order: `AuditMiddleware` (compliance logging) → `SecurityMiddleware` (JWT/CORS) → `RateLimitMiddleware` → `DateTimeMiddleware`.

Startup hooks initialise all three databases. `/health` is the Docker health check endpoint.

### Database responsibilities
| DB | Schema file | Purpose |
|----|-------------|---------|
| **Neo4j** | `src/database/neo4j_schema.py` | Transaction graph — Address, Transaction, Entity, Block, Stablecoin nodes; SENT/CONTAINS/ISSUED_ON edges. Cross-chain flow analysis and pattern detection. |
| **PostgreSQL** | `src/database/postgres_schema.py` | Compliance layer — users, investigations, evidence, audit_logs, sar_reports, sanctions_lists. 7-year AMLR/AMLD retention (GDPR storage‑limitation applies; separate legal‑basis analysis required). |
| **Redis** | — | Session storage, query cache, rate-limit counters, WebSocket broadcast bus. |

### Domain modules (`src/`)
| Directory | Responsibility |
|-----------|----------------|
| `analysis/` | 20+ pattern detectors (peeling chains, layering, synchronized transfers) |
| `intelligence/` | ML risk scoring, sanctions screening, dark web feed integration |
| `compliance/` | EU AMLR / GDPR / DORA / MiCA report generation, audit trails |
| `attribution/` | Entity clustering, VASP database (50+ entities), graph algorithms |
| `collectors/` | Live RPC collectors for 16 blockchains (Bitcoin, EVM chains, Solana, Tron, XRP, etc.) |
| `patterns/` | Low-level graph pattern library shared by `analysis/` |
| `forensics/` | Court-defensible evidence chains, advanced investigation tools |
| `automation/` | Webhooks, Travel Rule automation, scheduled bulk screening |

### Authentication
JWT tokens, roles: `admin` / `analyst` / `viewer`. RBAC enforced on all endpoints via `SecurityMiddleware`.

### Supported chains & stablecoins
16 blockchains: Ethereum, Bitcoin + Lightning, Solana, Tron, XRP, BSC, Polygon, Arbitrum, Base, Avalanche, Optimism, Starknet, Injective, Cosmos, Sui.
13 stablecoins tracked: USDT, USDC, USDe, EURC, and others.

---

## Task & Session Files

Maintain these files consistently (create if missing):
- `tasks/todo.md` — active plan + checklist (mark items ✓ as done)
- `tasks/lessons.md` — accumulated rules from corrections; **read at the start of every session**
- `tasks/review.md` — optional post-task notes and metrics

---

## Operating Rules

### 1. Plan first
For any non-trivial task (≥ 3 logical steps, architecture decisions, risk of regression, touches multiple files): write the plan to `tasks/todo.md` before writing any code. Plan structure: goal + acceptance criteria, numbered steps, files to touch, risks, verification approach, assumptions. If behavior surprises you mid-task → stop, re-plan.

**Safety valve**: Confirm with the user before any action that is unclear, high-risk, or could cause data loss or production impact.

### 2. Verification gate
A task is not done until proven working. Before calling anything complete: run relevant tests, show a meaningful diff, demonstrate the behavior change (logs, curl, DB state). Ask yourself: "Would a staff engineer merge and deploy this without hesitation?" If not — keep refining.

### 3. Simplicity & elegance
Minimize code changed, new concepts, and cognitive load. Prefer boring and readable over clever. No band-aids — fix root causes. Minimal blast radius — touch only what is strictly necessary. For non-trivial changes, ask yourself whether there is a cleaner, more idiomatic solution before committing.

### 3.1 Code style
- **DRY**: extract repeated logic into shared helpers only when it genuinely improves clarity.
- **SOLID** (pragmatic): single responsibility, composition over inheritance, depend on abstractions.
- **Docstrings required** on every public function, method, class, and FastAPI route (Google or NumPy style). Private helpers: only if logic is non-trivial.
- **Comments only** for non-obvious compliance rules, complex algorithms, or temporary workarounds (include deletion plan + ticket ref).
- Functions < 30–40 lines; type hints everywhere; named constants over magic values; early returns over deep nesting; structured logging — never log sensitive data.

### 4. Language choices
Use the primary stack (Python/FastAPI, Rust, TypeScript/Node.js, PostgreSQL/Neo4j/Redis). Introducing a new language or framework requires explicit justification of concrete advantages + trade-offs + user confirmation before writing any code.

### 5. Bug fixing
Read logs, stack traces, test output, and DB/cache state first. Fix the root cause. Add or strengthen a test that would have caught it. Commit format: `fix: <area> – <short description> (#ref)`.

### 6. Self-improvement
After any correction or repeated mistake: update `tasks/lessons.md` immediately with date, what went wrong, root cause, and an actionable rule to prevent recurrence.

### 7. Code review / refactor / debug protocol
For every file in scope, output a structured block covering: security issues, bugs/logic errors (with line numbers), readability problems, performance concerns, test coverage gaps, cleanup opportunities, proposed refactor steps, docstring gaps. Only mark a file as reviewed after listing all points and showing a proposed diff (or explaining why no change is needed). No summary verdicts like "looks clean" without the per-file breakdown first.

### 8. Full codebase overhaul
Stay in Plan Mode for all discovery and planning. Never make changes until the user types `GO Act - Phase X`. Maintain `OVERHAUL-PLAN.md` at project root with 100% file coverage. Archive folder: `docs/archive/2026-02-full-overhaul/`. One logical change per approved action.

### 9. Subagents
Prefer delegating specialized subtasks to keep the main context clean:
- **debugger** — errors, logs, stack traces, root-cause fixes
- **refactorer** — readability/performance improvements without behavior changes
- **test-writer** — unit/integration/e2e tests (pytest, cargo test, Jest/Vitest)
- **api-designer** — endpoint design, schemas, security, caching
- **coder** — focused production-ready implementation
- **code-reviewer** — final quality/security/perf review

### 10. MCP tools
Use only when necessary (real-time DB state, external docs, live cache). Prefer local knowledge and subagents first. Never expose sensitive data via MCP without explicit approval.

### Core mantra
Plan deeply · Code lightly · Verify ruthlessly · Simplify relentlessly · Learn continuously · Confirm when stakes are high.
