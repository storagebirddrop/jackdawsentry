#!/usr/bin/env bash
# Jackdaw Sentry — Load Test Runner (M7)
#
# Usage:
#   ./tests/load/run_benchmark.sh dev      # baseline: 1 API replica via docker-compose.yml
#   ./tests/load/run_benchmark.sh prod     # scaled:   2 API replicas via docker/docker-compose.prod.yml
#   ./tests/load/run_benchmark.sh ci       # CI gate:  lightweight pass/fail check
#
# Prerequisites:
#   pip install locust
#   docker compose up -d   (or prod equivalent)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOCUSTFILE="$SCRIPT_DIR/locustfile.py"
RESULTS_DIR="$PROJECT_ROOT/tests/load/results"
mkdir -p "$RESULTS_DIR"

MODE="${1:-dev}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# ── Parameters ────────────────────────────────────────────────────────
USERS=100
SPAWN_RATE=10
DURATION="5m"

case "$MODE" in
  dev)
    HOST="http://localhost:8000"
    TAG="dev"
    echo "▸ Baseline benchmark: $USERS users, $DURATION against dev compose ($HOST)"
    ;;
  prod)
    HOST="http://localhost"
    TAG="prod"
    echo "▸ Prod benchmark: $USERS users, $DURATION against prod compose ($HOST)"
    ;;
  ci)
    HOST="${CI_HOST:-http://localhost:8000}"
    TAG="ci"
    USERS=20
    SPAWN_RATE=5
    DURATION="1m"
    echo "▸ CI gate: $USERS users, $DURATION against $HOST"
    ;;
  *)
    echo "Usage: $0 {dev|prod|ci}" >&2
    exit 1
    ;;
esac

CSV_PREFIX="$RESULTS_DIR/${TAG}_${TIMESTAMP}"
HTML_REPORT="$RESULTS_DIR/${TAG}_${TIMESTAMP}_report.html"

# ── Run Locust ────────────────────────────────────────────────────────
locust \
  --locustfile "$LOCUSTFILE" \
  --headless \
  --users "$USERS" \
  --spawn-rate "$SPAWN_RATE" \
  --run-time "$DURATION" \
  --host "$HOST" \
  --csv "$CSV_PREFIX" \
  --html "$HTML_REPORT" \
  --print-stats \
  --only-summary

echo ""
echo "▸ Results saved:"
echo "  CSV:  ${CSV_PREFIX}_stats.csv"
echo "  HTML: $HTML_REPORT"

# ── CI gate check (exit non-zero if thresholds exceeded) ──────────────
if [ "$MODE" = "ci" ]; then
  echo ""
  echo "▸ Checking CI thresholds..."
  python3 "$SCRIPT_DIR/check_thresholds.py" "${CSV_PREFIX}_stats.csv"
fi
