#!/usr/bin/env python3
"""
Jackdaw Sentry — Phase 4 Load Test Threshold Checker

Reads the Locust CSV stats output and checks against Phase 4 specific
performance thresholds for intelligence processing modules.

Phase 4 Thresholds (adjusted for complex intelligence operations):
  - p50  < 100ms (higher due to complex processing)
  - p95  < 500ms (allowing for database queries)
  - p99  < 1000ms (worst-case complex analysis)
  - error rate < 0.5% (higher tolerance for complex operations)
  - RPS  > 200  (lower due to heavier processing)

Usage:
  python check_phase4_thresholds.py results/dev_20240101_120000_stats.csv
"""

import csv
import sys


# ---------------------------------------------------------------------------
# Phase 4 Thresholds
# ---------------------------------------------------------------------------
P50_MS = 100
P95_MS = 500
P99_MS = 1000
MAX_ERROR_RATE = 0.5  # percent
MIN_RPS = 200


def load_aggregated_row(csv_path: str) -> dict:
    """Load the 'Aggregated' row from Locust stats CSV."""
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Name", "").strip() == "Aggregated":
                return row
    raise SystemExit(f"ERROR: No 'Aggregated' row found in {csv_path}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print("Usage: check_phase4_thresholds.py <stats_csv>")
        print("  stats_csv: Path to Locust stats CSV file")
        sys.exit(2 if len(sys.argv) < 2 else 0)

    csv_path = sys.argv[1]
    row = load_aggregated_row(csv_path)

    # Parse metrics
    try:
        p50_ms = float(row["50%"])
        p95_ms = float(row["95%"])
        p99_ms = float(row["99%"])
        error_rate = float(row["Error %"])
        rps = float(row["Requests/s"])
    except (ValueError, KeyError) as e:
        print(f"ERROR: Failed to parse metrics from {csv_path}: {e}")
        sys.exit(1)

    # Check thresholds
    failures = []
    
    if p50_ms > P50_MS:
        failures.append(f"p50 {p50_ms}ms > {P50_MS}ms")
    
    if p95_ms > P95_MS:
        failures.append(f"p95 {p95_ms}ms > {P95_MS}ms")
    
    if p99_ms > P99_MS:
        failures.append(f"p99 {p99_ms}ms > {P99_MS}ms")
    
    if error_rate > MAX_ERROR_RATE:
        failures.append(f"Error rate {error_rate}% > {MAX_ERROR_RATE}%")
    
    if rps < MIN_RPS:
        failures.append(f"RPS {rps} < {MIN_RPS}")

    # Report results
    print(f"Phase 4 Performance Test Results:")
    print(f"  p50: {p50_ms}ms (threshold: {P50_MS}ms)")
    print(f"  p95: {p95_ms}ms (threshold: {P95_MS}ms)")
    print(f"  p99: {p99_ms}ms (threshold: {P99_MS}ms)")
    print(f"  Error rate: {error_rate}% (threshold: {MAX_ERROR_RATE}%)")
    print(f"  RPS: {rps} (threshold: {MIN_RPS})")
    
    if failures:
        print("\n❌ PERFORMANCE THRESHOLDS EXCEEDED:")
        for failure in failures:
            print(f"   - {failure}")
        print(f"\nPhase 4 performance requirements not met!")
        sys.exit(1)
    else:
        print("\n✅ All Phase 4 performance thresholds passed!")
        print("Phase 4 performance requirements met successfully!")


if __name__ == "__main__":
    main()
