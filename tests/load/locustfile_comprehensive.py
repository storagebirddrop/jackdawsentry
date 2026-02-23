"""
Jackdaw Sentry — Comprehensive Locust Load Test (M7) - All Phases

Simulates realistic user traffic against the entire API:
  - Auth flow: login → get JWT → use for all subsequent requests
  - Combined traffic mix (weights): 25% Phase 4, 20% compliance, 15% blockchain,
    10% analysis, 5% intelligence, 25% write operations
  - Write mix: 10% Phase 4, 5% compliance, 3% analysis, 2% blockchain, 5% other
  - Total weight = 100 → 75% reads, 25% writes

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

    # ── READ tasks (total weight = 75) ──────────────────────────────

    # Phase 4 Intelligence Modules (25% weight)
    @task(10)
    def get_victim_reports(self):
        """GET /api/v1/intelligence/victim-reports/ — weight 10."""
        self._get("/api/v1/intelligence/victim-reports/",
                  name="/api/v1/intelligence/victim-reports/")

    @task(7)
    def get_threat_feeds(self):
        """GET /api/v1/intelligence/threat-feeds/ — weight 7."""
        self._get("/api/v1/intelligence/threat-feeds/",
                  name="/api/v1/intelligence/threat-feeds/")

    @task(5)
    def get_attribution(self):
        """GET /api/v1/attribution/ — weight 5."""
        self._get("/api/v1/attribution/",
                  name="/api/v1/attribution/")

    @task(2)
    def get_professional_services(self):
        """GET /api/v1/intelligence/professional-services/services — weight 2."""
        self._get("/api/v1/intelligence/professional-services/services",
                  name="/api/v1/intelligence/professional-services/services")

    @task(1)
    def get_forensics_cases(self):
        """GET /api/v1/forensics/cases — weight 1."""
        self._get("/api/v1/forensics/cases",
                  name="/api/v1/forensics/cases")

    # Core Modules (50% weight)
    @task(20)
    def get_compliance_statistics(self):
        """GET /api/v1/compliance/statistics — weight 20."""
        self._get("/api/v1/compliance/statistics",
                  name="/api/v1/compliance/statistics")

    @task(15)
    def get_blockchain_statistics(self):
        """GET /api/v1/blockchain/statistics — weight 15."""
        self._get("/api/v1/blockchain/statistics",
                  name="/api/v1/blockchain/statistics")

    @task(10)
    def get_analysis_statistics(self):
        """GET /api/v1/analysis/statistics — weight 10."""
        self._get("/api/v1/analysis/statistics",
                  name="/api/v1/analysis/statistics")

    @task(5)
    def get_intelligence_alerts(self):
        """GET /api/v1/intelligence/alerts — weight 5."""
        self._get("/api/v1/intelligence/alerts",
                  name="/api/v1/intelligence/alerts")

    # ── WRITE tasks (total weight = 25) ──────────────────────────────

    # Phase 4 Write Operations (10% weight)
    @task(3)
    def create_victim_report(self):
        """POST /api/v1/intelligence/victim-reports/ — weight 3."""
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

    @task(2)
    def create_threat_feed(self):
        """POST /api/v1/intelligence/threat-feeds/ — weight 2."""
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

    @task(1)
    def create_forensic_case(self):
        """POST /api/v1/forensics/cases — weight 1."""
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

    # Core Module Write Operations (15% weight)
    @task(5)
    def post_audit_log(self):
        """POST /api/v1/compliance/audit/log — weight 5."""
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
        """POST /api/v1/compliance/risk/assessments — weight 3."""
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
        """POST /api/v1/compliance/cases — weight 2."""
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

    @task(3)
    def analyze_address(self):
        """POST /api/v1/analysis/address — weight 3."""
        self._post(
            "/api/v1/analysis/address",
            json_body={
                "address": f"0x{uuid.uuid4().hex[:40]}",
                "blockchain": "ethereum",
                "include_risk_analysis": True,
                "include_pattern_detection": True,
                "include_graph_analysis": True
            },
            name="/api/v1/analysis/address",
        )

    @task(2)
    def trace_transaction(self):
        """POST /api/v1/blockchain/trace — weight 2."""
        self._post(
            "/api/v1/blockchain/trace",
            json_body={
                "transaction_hash": f"0x{uuid.uuid4().hex[:64]}",
                "blockchain": "ethereum",
                "include_analysis": True,
                "max_depth": 5
            },
            name="/api/v1/blockchain/trace",
        )
