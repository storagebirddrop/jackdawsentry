#!/usr/bin/env python3
"""
Jackdaw Sentry — Load Test Threshold Checker (M7)

Reads the Locust CSV stats output and checks against industry-standard
performance thresholds. Exits non-zero if any threshold is exceeded.

Thresholds (Google/AWS standards for internal API tooling):
  - p50  < 50ms
  - p95  < 100ms
  - p99  < 200ms
  - error rate < 0.1%
  - RPS  > 500  (for 100-user baseline; scaled proportionally for CI)

Usage:
  python check_thresholds.py results/dev_20240101_120000_stats.csv
"""

import csv
import sys


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
P50_MS = 50
P95_MS = 100
P99_MS = 200
MAX_ERROR_RATE = 0.1  # percent
MIN_RPS = 500


def load_aggregated_row(csv_path: str) -> dict:
    """Load the 'Aggregated' row from Locust stats CSV."""
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Name", "").strip() == "Aggregated":
                return row
    raise SystemExit(f"ERROR: No 'Aggregated' row found in {csv_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: check_thresholds.py <stats_csv>")
        sys.exit(2)

    csv_path = sys.argv[1]
    row = load_aggregated_row(csv_path)

    # Parse values (Locust CSV column names)
    total_requests = int(row.get("Request Count", 0))
    total_failures = int(row.get("Failure Count", 0))
    rps = float(row.get("Requests/s", 0))

    # Percentile columns vary by Locust version; try common names
    p50 = float(row.get("50%", 0) or row.get("Median Response Time", 0))
    p95 = float(row.get("95%", 0) or 0)
    p99 = float(row.get("99%", 0) or 0)

    error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0.0

    print(f"  Total requests : {total_requests}")
    print(f"  Failures       : {total_failures}")
    print(f"  Error rate     : {error_rate:.3f}%")
    print(f"  RPS            : {rps:.1f}")
    print(f"  p50            : {p50:.0f} ms")
    print(f"  p95            : {p95:.0f} ms")
    print(f"  p99            : {p99:.0f} ms")
    print()

    failures = []

    if p50 > P50_MS:
        failures.append(f"p50 {p50:.0f}ms > {P50_MS}ms")
    if p95 > P95_MS:
        failures.append(f"p95 {p95:.0f}ms > {P95_MS}ms")
    if p99 > P99_MS:
        failures.append(f"p99 {p99:.0f}ms > {P99_MS}ms")
    if error_rate > MAX_ERROR_RATE:
        failures.append(f"error rate {error_rate:.3f}% > {MAX_ERROR_RATE}%")
    if rps < MIN_RPS:
        failures.append(f"RPS {rps:.1f} < {MIN_RPS}")

    if failures:
        print("  ❌ FAILED thresholds:")
        for f in failures:
            print(f"     - {f}")
        sys.exit(1)
    else:
        print("  ✅ All thresholds passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
