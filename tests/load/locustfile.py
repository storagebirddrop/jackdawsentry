"""
Jackdaw Sentry — Locust Load Test (M7)

Simulates realistic user traffic against the API:
  - Auth flow: login → get JWT → use for all subsequent requests
  - Read-heavy mix: 60% compliance/statistics, 20% blockchain/statistics,
    10% analysis/statistics, 10% intelligence/alerts
  - Write mix: 5% audit/log, 3% risk/assessments, 2% compliance/cases

Usage:
  # Headless baseline (dev compose — 1 replica)
  locust --headless -u 100 -r 10 -t 5m -H http://localhost:8000

  # Headless benchmark (prod compose — 2 replicas behind Nginx)
  locust --headless -u 100 -r 10 -t 5m -H http://localhost

  # Web UI
  locust -H http://localhost
"""

import os
import uuid
from datetime import datetime, timezone

from locust import HttpUser, between, task


# ---------------------------------------------------------------------------
# Credentials — seeded admin from 002_seed_admin_user.sql
# Override via environment variables for CI / other envs
# ---------------------------------------------------------------------------
USERNAME = os.environ.get("LOCUST_USERNAME", "admin")
PASSWORD = os.environ.get("LOCUST_PASSWORD", "ChangeMe!Admin2024")


class JackdawUser(HttpUser):
    """Simulates an authenticated analyst using the Jackdaw Sentry API."""

    wait_time = between(0.5, 2.0)

    # ── Auth ──────────────────────────────────────────────────────────

    def on_start(self):
        """Login and store JWT for all subsequent requests."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            name="/api/v1/auth/login",
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("access_token", "")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = ""
            self.headers = {}

    # ── Helpers ───────────────────────────────────────────────────────

    def _get(self, path, **kwargs):
        """Authenticated GET."""
        return self.client.get(path, headers=self.headers, **kwargs)

    def _post(self, path, json_body, **kwargs):
        """Authenticated POST with JSON body."""
        return self.client.post(
            path, json=json_body, headers=self.headers, **kwargs
        )

    # ── READ tasks (total weight = 100) ──────────────────────────────

    @task(60)
    def get_compliance_statistics(self):
        """GET /api/v1/compliance/statistics — 60% of reads."""
        self._get("/api/v1/compliance/statistics",
                  name="/api/v1/compliance/statistics")

    @task(20)
    def get_blockchain_statistics(self):
        """GET /api/v1/blockchain/statistics — 20% of reads."""
        self._get("/api/v1/blockchain/statistics",
                  name="/api/v1/blockchain/statistics")

    @task(10)
    def get_analysis_statistics(self):
        """GET /api/v1/analysis/statistics — 10% of reads."""
        self._get("/api/v1/analysis/statistics",
                  name="/api/v1/analysis/statistics")

    @task(10)
    def get_intelligence_alerts(self):
        """GET /api/v1/intelligence/alerts — 10% of reads."""
        self._get("/api/v1/intelligence/alerts",
                  name="/api/v1/intelligence/alerts")

    # ── WRITE tasks (total weight = 10) ──────────────────────────────

    @task(5)
    def post_audit_log(self):
        """POST /api/v1/compliance/audit/log — 5% of writes."""
        self._post(
            "/api/v1/compliance/audit/log",
            json_body={
                "event_type": "USER_ACTION",
                "user_id": "load-test-user",
                "action": "load_test_audit_entry",
                "details": f"Locust load-test entry {uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            name="/api/v1/compliance/audit/log",
        )

    @task(3)
    def post_risk_assessment(self):
        """POST /api/v1/compliance/risk/assessments — 3% of writes."""
        self._post(
            "/api/v1/compliance/risk/assessments",
            json_body={
                "entity_id": f"locust-entity-{uuid.uuid4().hex[:8]}",
                "entity_type": "address",
                "risk_score": 0.42,
                "factors": ["load_test"],
                "notes": "Automated load-test risk assessment",
            },
            name="/api/v1/compliance/risk/assessments",
        )

    @task(2)
    def post_compliance_case(self):
        """POST /api/v1/compliance/cases — 2% of writes."""
        self._post(
            "/api/v1/compliance/cases",
            json_body={
                "title": f"Load-test case {uuid.uuid4().hex[:8]}",
                "description": "Created by Locust load test",
                "priority": "low",
                "case_type": "investigation",
            },
            name="/api/v1/compliance/cases",
        )
