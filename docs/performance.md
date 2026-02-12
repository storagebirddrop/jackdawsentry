# Performance Benchmarking & Scaling — M7

This document describes the load-testing methodology, performance thresholds,
tuning decisions, and how to reproduce benchmarks for Jackdaw Sentry.

---

## 1. Tooling

| Tool | Purpose | Location |
|---|---|---|
| **Locust 2.24** | HTTP load generation | `tests/load/locustfile.py` |
| **py-spy** | CPU flame-graph profiling | `requirements.txt` (already present) |
| **memory-profiler** | Memory usage tracking | `requirements.txt` (already present) |
| **check_thresholds.py** | CI pass/fail gate | `tests/load/check_thresholds.py` |
| **run_benchmark.sh** | One-command runner | `tests/load/run_benchmark.sh` |

---

## 2. Performance Thresholds

Industry-standard targets for internal compliance tooling backed by
in-memory/local-DB queries (Google/AWS benchmarks):

| Metric | Threshold | Rationale |
|---|---|---|
| **p50 latency** | < 50 ms | Median should feel instant |
| **p95 latency** | < 100 ms | Tail should remain sub-100ms |
| **p99 latency** | < 200 ms | Worst-case still responsive |
| **Error rate** | < 0.1% | Near-zero failures under load |
| **RPS** | > 500 | 100 concurrent users, sustained 5 min |

---

## 3. Load Test Profile

### Traffic mix (weights)

```
READ  (90% of requests):
  60%  GET /api/v1/compliance/statistics
  20%  GET /api/v1/blockchain/statistics
  10%  GET /api/v1/analysis/statistics
  10%  GET /api/v1/intelligence/alerts

WRITE (10% of requests):
   5%  POST /api/v1/compliance/audit/log
   3%  POST /api/v1/compliance/risk/assessments
   2%  POST /api/v1/compliance/cases
```

### User behaviour

- Each simulated user logs in once (`POST /api/v1/auth/login`) on start
- JWT token is reused for all subsequent requests
- Think time: 0.5–2.0 seconds between requests

---

## 4. Running Benchmarks

### Prerequisites

```bash
pip install locust
# Stack must be running:
docker compose up -d              # dev (1 replica)
# or
docker compose -f docker/docker-compose.prod.yml up -d  # prod (2 replicas)
```

### Dev baseline (1 API replica)

```bash
./tests/load/run_benchmark.sh dev
# or manually:
locust --headless -u 100 -r 10 -t 5m \
  -H http://localhost:8000 \
  -f tests/load/locustfile.py \
  --csv tests/load/results/dev --html tests/load/results/dev.html \
  --only-summary
```

### Prod benchmark (2 API replicas behind Nginx)

```bash
./tests/load/run_benchmark.sh prod
# or manually:
locust --headless -u 100 -r 10 -t 5m \
  -H http://localhost \
  -f tests/load/locustfile.py \
  --csv tests/load/results/prod --html tests/load/results/prod.html \
  --only-summary
```

### CI gate (lightweight)

```bash
./tests/load/run_benchmark.sh ci
# 20 users, 1 min, auto-checks thresholds
```

---

## 5. Bottleneck Identification

### CPU profiling with py-spy

```bash
# Attach to running API container
docker compose exec api py-spy record -o profile.svg --pid 1 -d 60

# Or during a load test:
./tests/load/run_benchmark.sh dev &
docker compose exec api py-spy top --pid 1
```

### Memory profiling

```bash
docker compose exec api python -m memory_profiler src/api/main.py
```

### Key areas to check

1. **Neo4j query times** — slow Cypher queries show up as high p95/p99
2. **Redis hit rate** — cache misses cause DB round-trips
3. **Postgres connection pool** — exhaustion causes queuing
4. **Python GIL contention** — shows as CPU-bound in flame graph

---

## 6. Connection Pool Tuning

### asyncpg (Postgres)

```python
# src/api/database.py — pool settings
pool = await asyncpg.create_pool(
    min_size=5,       # keep 5 warm connections
    max_size=20,      # scale up to 20 under load
    max_inactive_connection_lifetime=300,
)
```

**Tuning guidance:**
- `max_size` should be ≤ `max_connections` in `postgresql.conf` divided by number of API replicas
- For 2 replicas: if Postgres allows 100 connections, set `max_size=40` per replica
- Monitor with `SELECT count(*) FROM pg_stat_activity`

### Neo4j

```python
# Neo4j driver pool settings
driver = GraphDatabase.driver(
    uri,
    auth=(user, password),
    max_connection_pool_size=50,
    connection_acquisition_timeout=30,
)
```

**Tuning guidance:**
- Default pool size (100) is usually fine for 2 replicas
- If p99 spikes on Neo4j queries, increase `max_connection_pool_size`
- Monitor with `:sysinfo` in Neo4j Browser

### Redis

```python
# Redis connection pool
pool = redis.ConnectionPool(
    max_connections=50,
    decode_responses=True,
)
```

**Tuning guidance:**
- Redis is single-threaded; pool size mostly limits client-side concurrency
- 50 connections per replica is generous for cache reads
- Monitor with `redis-cli INFO clients`

---

## 7. Nginx Tuning

Current config (`docker/nginx.conf`):

```nginx
events {
    worker_connections 1024;
}

upstream jackdawsentry_backend {
    least_conn;
    server api:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
```

### Tuning recommendations based on load test results

| Setting | Current | Recommended (if bottleneck) | Why |
|---|---|---|---|
| `worker_connections` | 1024 | 2048–4096 | If hitting connection limits |
| `keepalive` | 32 | 64–128 | Reduce TCP handshake overhead to upstream |
| `rate=10r/s` | 10r/s | 50r/s | Current limit is aggressive for load tests |
| `burst=20` | 20 | 50–100 | Allow short traffic spikes |
| `proxy_connect_timeout` | 30s | 10s | Fail fast on unhealthy backends |
| `gzip_comp_level` | 6 | 4 | Trade CPU for throughput at high RPS |

**Important**: For load testing, temporarily raise or disable rate limits:
```nginx
# Temporarily for benchmarks:
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
limit_req zone=api_limit burst=200 nodelay;
```

---

## 8. Benchmark Results Template

After running benchmarks, record results here:

### Dev Baseline (1 replica)

| Metric | Value | Threshold | Status |
|---|---|---|---|
| p50 | _TBD_ | < 50ms | ⬜ |
| p95 | _TBD_ | < 100ms | ⬜ |
| p99 | _TBD_ | < 200ms | ⬜ |
| Error rate | _TBD_ | < 0.1% | ⬜ |
| RPS | _TBD_ | > 500 | ⬜ |

### Prod Benchmark (2 replicas)

| Metric | Value | Threshold | Status |
|---|---|---|---|
| p50 | _TBD_ | < 50ms | ⬜ |
| p95 | _TBD_ | < 100ms | ⬜ |
| p99 | _TBD_ | < 200ms | ⬜ |
| Error rate | _TBD_ | < 0.1% | ⬜ |
| RPS | _TBD_ | > 500 | ⬜ |

### Tuning applied

_Document any changes made after analyzing results._

---

## 9. Scope & Limitations

- **API layer only** — no horizontal DB scaling
- **Local data** — real blockchain RPC calls are out of scope; all Neo4j queries use local data
- **Single-node Docker** — benchmarks run on single Docker host, not distributed
- `py-spy` and `memory-profiler` are already in `requirements.txt`
- Prod compose uses `deploy.replicas: 2` with resource limits (1 CPU, 2 GB per replica)
