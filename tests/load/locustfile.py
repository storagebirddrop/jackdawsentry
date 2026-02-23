"""
Jackdaw Sentry — Locust Load Test (M7) - Phase 4 Performance Tests

Simulates realistic user traffic against Phase 4 intelligence modules:
  - Auth flow: login → get JWT → use for all subsequent requests
  - Read-heavy mix (weights): 30 victim-reports, 20 threat-feeds, 15 attribution,
    10 professional-services, 10 forensics
  - Write mix (weights): 5 victim-reports, 4 threat-feeds, 3 attribution,
    2 forensics, 1 professional-services
  - Total weight = 100 → 85% reads, 15% writes

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
PASSWORD = os.environ.get("LOCUST_PASSWORD", "Admin123!@#")


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
            resp.failure(f"Login failed: {resp.status_code}")
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

    # ── READ tasks (total weight = 85) ──────────────────────────────

    @task(30)
    def get_victim_reports(self):
        """GET /api/v1/intelligence/victim-reports/ — weight 30."""
        self._get("/api/v1/intelligence/victim-reports/",
                  name="/api/v1/intelligence/victim-reports/")

    @task(20)
    def get_threat_feeds(self):
        """GET /api/v1/intelligence/threat-feeds/ — weight 20."""
        self._get("/api/v1/intelligence/threat-feeds/",
                  name="/api/v1/intelligence/threat-feeds/")

    @task(15)
    def get_attribution(self):
        """GET /api/v1/attribution/ — weight 15."""
        self._get("/api/v1/attribution/",
                  name="/api/v1/attribution/")

    @task(10)
    def get_professional_services(self):
        """GET /api/v1/intelligence/professional-services/services — weight 10."""
        self._get("/api/v1/intelligence/professional-services/services",
                  name="/api/v1/intelligence/professional-services/services")

    @task(10)
    def get_forensics_cases(self):
        """GET /api/v1/forensics/cases — weight 10."""
        self._get("/api/v1/forensics/cases",
                  name="/api/v1/forensics/cases")

    # ── WRITE tasks (total weight = 15) ──────────────────────────────

    @task(5)
    def create_victim_report(self):
        """POST /api/v1/intelligence/victim-reports/ — weight 5."""
        self._post(
            "/api/v1/intelligence/victim-reports/",
            json_body={
                "report_type": "phishing",
                "victim_contact": f"load-test-victim-{uuid.uuid4().hex[:8]}@example.com",
                "incident_date": datetime.now(timezone.utc).isoformat(),
                "amount_lost": 1000.0,
                "currency": "USD",
                "description": f"Load test victim report {uuid.uuid4().hex[:8]}",
                "related_addresses": [f"0x{uuid.uuid4().hex[:40]}"],
                "related_transactions": [f"0x{uuid.uuid4().hex[:64]}"],
                "severity": "medium",
                "source_ip": "192.168.1.100",
                "source_platform": "email"
            },
            name="/api/v1/intelligence/victim-reports/",
        )

    @task(4)
    def create_threat_feed(self):
        """POST /api/v1/intelligence/threat-feeds/ — weight 4."""
        self._post(
            "/api/v1/intelligence/threat-feeds/",
            json_body={
                "name": f"Load-test Feed {uuid.uuid4().hex[:8]}",
                "url": "https://example.com/threat-feed",
                "feed_type": "ioc",
                "format": "json",
                "update_frequency": "hourly",
                "is_active": True,
                "description": "Load test threat intelligence feed"
            },
            name="/api/v1/intelligence/threat-feeds/",
        )

    @task(3)
    def attribute_address(self):
        """POST /api/v1/attribution/attribute-address — weight 3."""
        self._post(
            "/api/v1/attribution/attribute-address",
            json_body={
                "addresses": [f"0x{uuid.uuid4().hex[:40]}"],
                "include_vasp_info": True,
                "include_risk_assessment": True
            },
            name="/api/v1/attribution/attribute-address",
        )

    @task(2)
    def create_forensic_case(self):
        """POST /api/v1/forensics/cases — weight 2."""
        self._post(
            "/api/v1/forensics/cases",
            json_body={
                "title": f"Load-test Case {uuid.uuid4().hex[:8]}",
                "description": "Created by Locust load test",
                "case_type": "investigation",
                "priority": "medium",
                "assigned_to": "load-test-analyst",
                "status": "open"
            },
            name="/api/v1/forensics/cases",
        )

    @task(1)
    def create_service_request(self):
        """POST /api/v1/intelligence/professional-services/services — weight 1."""
        self._post(
            "/api/v1/intelligence/professional-services/services",
            json_body={
                "service_type": "investigation",
                "title": f"Load-test Service {uuid.uuid4().hex[:8]}",
                "description": "Created by Locust load test",
                "priority": "medium",
                "client_contact": f"load-test-client-{uuid.uuid4().hex[:8]}@example.com",
                "estimated_duration": "2 hours"
            },
            name="/api/v1/intelligence/professional-services/services",
        )
