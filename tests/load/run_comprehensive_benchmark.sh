#!/usr/bin/env bash
# Jackdaw Sentry — Comprehensive Load Test Runner (All Phases)
#
# Usage:
#   ./tests/load/run_comprehensive_benchmark.sh dev      # baseline: 1 API replica via docker-compose.yml
#   ./tests/load/run_comprehensive_benchmark.sh prod     # scaled:   2 API replicas via docker/docker-compose.prod.yml
#   ./tests/load/run_comprehensive_benchmark.sh ci       # CI gate: lightweight pass/fail check
#   ./tests/load/run_comprehensive_benchmark.sh legacy   # legacy endpoints only
#   ./tests/load/run_comprehensive_benchmark.sh phase4   # Phase 4 endpoints only
#   ./tests/load/run_comprehensive_benchmark.sh comprehensive   # comprehensive endpoints only
#
# Prerequisites:
#   pip install locust
#   docker compose up -d   (or prod equivalent)
#   All modules operational

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPREHENSIVE_LOCUSTFILE="$SCRIPT_DIR/locustfile_comprehensive.py"
RESULTS_DIR="$PROJECT_ROOT/tests/load/results"
mkdir -p "$RESULTS_DIR"

MODE="${1:-dev}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# ── Parameters ────────────────────────────────────────────────────────
USERS=100
SPAWN_RATE=10
DURATION="5m"
HOST=""
LOCUSTFILE="$COMPREHENSIVE_LOCUSTFILE"

case "$MODE" in
  dev)
    HOST="http://localhost:8000"
    USERS=100
    SPAWN_RATE=10
    DURATION="5m"
    echo "▸ Comprehensive benchmark: $USERS users, $DURATION against dev compose ($HOST)"
    ;;
  prod)
    HOST="http://localhost"
    USERS=150
    SPAWN_RATE=15
    DURATION="10m"
    echo "▸ Comprehensive benchmark: $USERS users, $DURATION against prod compose ($HOST)"
    ;;
  ci)
    HOST="http://localhost:8000"
    USERS=30
    SPAWN_RATE=3
    DURATION="2m"
    echo "▸ CI gate: $USERS users, $DURATION against $HOST"
    ;;
  legacy)
    HOST="http://localhost:8000"
    USERS=80
    SPAWN_RATE=8
    DURATION="3m"
    LOCUSTFILE="$SCRIPT_DIR/locustfile_legacy.py"
    echo "▸ Legacy benchmark: $USERS users, $DURATION against dev compose ($HOST)"
    ;;
  phase4)
    HOST="http://localhost:8000"
    USERS=50
    SPAWN_RATE=5
    DURATION="3m"
    LOCUSTFILE="$SCRIPT_DIR/locustfile.py"
    echo "▸ Phase 4 benchmark: $USERS users, $DURATION against dev compose ($HOST)"
    ;;
  comprehensive)
    HOST="http://localhost:8000"
    USERS=100
    SPAWN_RATE=10
    DURATION="5m"
    LOCUSTFILE="$SCRIPT_DIR/locustfile_comprehensive.py"
    echo "▸ Comprehensive benchmark: $USERS users, $DURATION against dev compose ($HOST)"
    ;;
  *)
    echo "Usage: $0 {dev|prod|ci|legacy|phase4|comprehensive}" >&2
    exit 1
    ;;
esac

echo "🚀 Starting Comprehensive Performance Test - Mode: $MODE"
echo "   Users: $USERS, Spawn Rate: $SPAWN_RATE, Duration: $DURATION"
echo "   Host: $HOST"
echo "   Locustfile: $LOCUSTFILE"
echo "   Timestamp: $TIMESTAMP"

# ── Validate Locustfile ──────────────────────────────────────────────────
if [ ! -f "$LOCUSTFILE" ]; then
    echo "❌ Error: Locustfile not found: $LOCUSTFILE"
    exit 1
fi

# ── Run Locust ────────────────────────────────────────────────────────
echo "📊 Running comprehensive load test..."
STATS_FILE="$RESULTS_DIR/comprehensive_${MODE}_${TIMESTAMP}_stats.csv"

locust \
  --headless \
  --users "$USERS" \
  --spawn-rate "$SPAWN_RATE" \
  --run-time "$DURATION" \
  --host "$HOST" \
  --locustfile "$LOCUSTFILE" \
  --csv "$STATS_FILE" \
  --html "$RESULTS_DIR/comprehensive_${MODE}_${TIMESTAMP}_report.html" \
  --logfile "$RESULTS_DIR/comprehensive_${MODE}_${TIMESTAMP}.log"

# ── Check Thresholds ────────────────────────────────────────────────────
echo "📋 Checking performance thresholds..."

# Use appropriate threshold checker based on mode
if [ "$MODE" = "phase4" ]; then
    python3 "$SCRIPT_DIR/check_phase4_thresholds.py" "$STATS_FILE"
else
    python3 "$SCRIPT_DIR/check_thresholds.py" "$STATS_FILE"
fi

# ── Generate Summary Report ───────────────────────────────────────────────
echo "📊 Generating summary report..."
SUMMARY_FILE="$RESULTS_DIR/comprehensive_${MODE}_${TIMESTAMP}_summary.json"

# Extract key metrics from stats CSV
python3 -c "
import csv
import json
import sys

def extract_metrics(csv_path):
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Name', '').strip() == 'Aggregated':
                return {
                    'total_requests': int(row.get('Request Count', 0)),
                    'requests_per_second': float(row.get('Requests/s', 0)),
                    'response_time_avg': float(row.get('Average Response Time', 0)),
                    'response_time_p50': float(row.get('50%', 0)),
                    'response_time_p95': float(row.get('95%', 0)),
                    'response_time_p99': float(row.get('99%', 0)),
                    'failures': int(row.get('Failures', 0)),
                    'error_rate': float(row.get('Error %', 0))
                }
    return None

metrics = extract_metrics('$STATS_FILE')
if metrics:
    summary = {
        'timestamp': '$TIMESTAMP',
        'mode': '$MODE',
        'users': $USERS,
        'spawn_rate': $SPAWN_RATE,
        'duration': '$DURATION',
        'host': '$HOST',
        'metrics': metrics
    }
    
    with open('$SUMMARY_FILE', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f'✅ Summary report saved to: $SUMMARY_FILE')
else:
    print('❌ Could not extract metrics from stats file'
"

echo "✅ Comprehensive Performance Test Complete!"
echo "   Results saved to: $RESULTS_DIR/comprehensive_${MODE}_${TIMESTAMP}_report.html"
echo "   Stats CSV: $STATS_FILE"
echo "   Log file: $RESULTS_DIR/comprehensive_${MODE}_${TIMESTAMP}.log"
echo "   Summary: $SUMMARY_FILE"
