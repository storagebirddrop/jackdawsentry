# Tomorrow's Work Queue

## 1. Fix test suite — ~265 failures, ~699 errors [HIGH PRIORITY]

Two root causes affect ~25 test files:

### Root cause A: `_AsyncGeneratorContextManager` not awaitable
Tests mock `get_redis_connection()` / `get_neo4j_session()` / `get_postgres_connection()`
with plain `MagicMock()` instead of `AsyncMock`. Fix via shared `conftest.py` async fixtures.

Affected test files (sample):
- `tests/test_analytics/test_analytics_engine.py`
- `tests/test_analytics/test_pathfinding.py`
- `tests/test_attribution/test_attribution_engine.py`
- `tests/test_attribution/test_vasp_registry.py`
- `tests/test_patterns/test_detection_engine.py`
- `tests/test_forensics/test_forensic_engine.py`
- `tests/test_forensics/test_evidence_manager.py`
- `tests/test_forensics/test_court_defensible.py`
- `tests/test_forensics/test_report_generator.py`
- `tests/test_intelligence/test_cross_platform.py`
- `tests/test_compliance/test_analysis_compliance.py`
- `tests/test_compliance/test_blockchain_compliance.py`
- `tests/test_api/test_cross_platform.py`

### Root cause B: Constructor signature drift
`ThreatIntelligenceManager(db_pool)` — tests pass a db pool arg the class no longer accepts.
Fix: drop positional arg from test instantiation.

Affected:
- `tests/test_intelligence/test_threat_feeds.py`
- `tests/test_intelligence/test_victim_reports.py`
- `tests/test_intelligence/test_professional_services.py`
- `tests/test_api/test_threat_feeds.py`
- `tests/test_api/test_victim_reports.py`
- `tests/test_api/test_professional_services.py`

### Root cause C: Wrong patch path
`src.forensics.forensic_engine.get_postgres_connection` — attribute doesn't exist in module
(function imported under a different name or from a different path).
Affected: `tests/test_forensics/test_forensic_engine.py`

### Baseline (before fix)
```
566 passed, 265 failed, 699 errors, 20 deselected
```
Target: eliminate errors and failures caused by A/B/C above.

---

## 2. Fix Pydantic `regex=` deprecation [LOW — 5 min]

`src/api/routers/competitive.py` lines 268, 308, 429:
Change `Query(..., regex="...")` → `Query(..., pattern="...")`

---

## 3. E2E smoke test Intelligence Hub [NEEDS RUNNING STACK]

Only remaining item from Intelligence Hub todo. Requires `make dev`.
- All 5 tabs load data
- CRUD operations for each module
- Modal open/close/submit flows

---

## State at shutdown
- `make lint` → 0 errors ✓
- Last commit: `46edad4` fix: resolve all F821 undefined name lint errors
- Branch: main (2 commits ahead of origin/main)
- AnChain.ai integration: complete, 15/15 tests passing ✓
- Intelligence Hub dashboard: complete ✓
