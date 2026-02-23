#!/usr/bin/env bash
# Jackdaw Sentry — Phase 4 Load Test Runner
#
# Usage:
#   ./tests/load/run_phase4_benchmark.sh dev      # baseline: 1 API replica via docker-compose.yml
#   ./tests/load4_benchmark.sh prod     # scaled:   2 API replicas via docker/docker-compose.prod.yml
#   ./tests/load4_benchmark.sh ci       # CI gate: lightweight pass/fail check
#
# Prerequisites:
#   pip install locust
#   docker compose up -d   (or prod equivalent)
#   All Phase 4 modules operational

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOCUSTFILE="$SCRIPT_DIR/locustfile.py"
RESULTS_DIR="$PROJECT_ROOT/tests/load/results"
mkdir -p "$RESULTS_DIR"

MODE="${1:-dev}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# ── Parameters ────────────────────────────────────────────────────────
USERS=50
SPAWN_RATE=5
DURATION="3m"
HOST=""

case "$MODE" in
  dev)
    HOST="http://localhost:8000"
    USERS=50
    SPAWN_RATE=5
    DURATION="3m"
    ;;
  prod)
    HOST="http://localhost"
    USERS=100
    SPAWN_RATE=10
    DURATION="5m"
    ;;
  ci)
    HOST="http://localhost:8000"
    USERS=20
    SPAWN_RATE=2
    DURATION="1m"
    ;;
  *)
    echo "Usage: $0 {dev|prod|ci}"
    echo "  dev  - Development baseline (50 users, 3 min)"
    echo "  prod - Production benchmark (100 users, 5 min)"
    echo "  ci   - CI gate (20 users, 1 min)"
    exit 1
    ;;
esac

echo "🚀 Starting Phase 4 Performance Test - Mode: $MODE"
echo "   Users: $USERS, Spawn Rate: $SPAWN_RATE, Duration: $DURATION"
echo "   Host: $HOST"
echo "   Timestamp: $TIMESTAMP"

# ── Run Locust ────────────────────────────────────────────────────────
echo "📊 Running Phase 4 load test..."
STATS_FILE="$RESULTS_DIR/phase4_${MODE}_${TIMESTAMP}_stats.csv"

locust \
  --headless \
  --users "$USERS" \
  --spawn-rate "$SPAWN_RATE" \
  --run-time "$DURATION" \
  --host "$HOST" \
  --locustfile "$LOCUSTFILE" \
  --csv "$STATS_FILE" \
  --html "$RESULTS_DIR/phase4_${MODE}_${TIMESTAMP}_report.html" \
  --logfile "$RESULTS_DIR/phase4_${MODE}_${TIMESTAMP}.log"

# ── Check Thresholds ────────────────────────────────────────────────────
echo "📋 Checking Phase 4 performance thresholds..."
python3 "$SCRIPT_DIR/check_phase4_thresholds.py" "$STATS_FILE"

echo "✅ Phase 4 Performance Test Complete!"
echo "   Results saved to: $RESULTS_DIR/phase4_${MODE}_${TIMESTAMP}_report.html"
echo "   Stats CSV: $STATS_FILE"
echo "   Log file: $RESULTS_DIR/phase4_${MODE}_${TIMESTAMP}.log"
