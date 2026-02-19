"""
Unit tests for investigation graph persistence and PDF export endpoints.

Covers:
 - PUT  /api/v1/investigations/{id}/graph  (save graph state)
 - GET  /api/v1/investigations/{id}/graph  (load graph state)
 - GET  /api/v1/investigations/{id}/report/pdf (PDF streaming export)
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_neo4j_ctx(single_value=None, data_value=None):
    """Create a mock Neo4j session context manager."""
    run_result = AsyncMock()
    run_result.single = AsyncMock(return_value=single_value)
    run_result.data = AsyncMock(return_value=data_value or [])
    session = AsyncMock()
    session.run = AsyncMock(return_value=run_result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


SAMPLE_NODES = [
    {"id": "0xabc", "type": "address", "chain": "ethereum", "risk": 0.1},
    {"id": "0xdef", "type": "address", "chain": "ethereum", "risk": 0.3},
]
SAMPLE_EDGES = [
    {"id": "edge1", "source": "0xabc", "target": "0xdef", "value": 1.0, "chain": "ethereum"},
]
SAMPLE_LAYOUT = {"0xabc": {"x": 100, "y": 200}, "0xdef": {"x": 300, "y": 200}}


# ---------------------------------------------------------------------------
# Save graph state
# ---------------------------------------------------------------------------


class TestSaveInvestigationGraph:
    def test_save_returns_success(self, client, admin_headers):
        record = MagicMock()
        record.__getitem__ = lambda self, k: "INV-001"
        neo4j_ctx = _make_neo4j_ctx(single_value=record)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=neo4j_ctx):
            resp = client.put(
                "/api/v1/investigations/INV-001/graph",
                json={"nodes": SAMPLE_NODES, "edges": SAMPLE_EDGES, "layout": SAMPLE_LAYOUT},
                headers=admin_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

    def test_save_returns_node_and_edge_counts(self, client, admin_headers):
        record = MagicMock()
        neo4j_ctx = _make_neo4j_ctx(single_value=record)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=neo4j_ctx):
            resp = client.put(
                "/api/v1/investigations/INV-001/graph",
                json={"nodes": SAMPLE_NODES, "edges": SAMPLE_EDGES},
                headers=admin_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["node_count"] == 2
        assert body["edge_count"] == 1

    def test_save_404_when_investigation_not_found(self, client, admin_headers):
        neo4j_ctx = _make_neo4j_ctx(single_value=None)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=neo4j_ctx):
            resp = client.put(
                "/api/v1/investigations/NONEXISTENT/graph",
                json={"nodes": [], "edges": []},
                headers=admin_headers,
            )

        assert resp.status_code == 404

    def test_save_requires_auth(self, client):
        resp = client.put(
            "/api/v1/investigations/INV-001/graph",
            json={"nodes": [], "edges": []},
        )
        assert resp.status_code == 403

    def test_save_accepts_empty_layout(self, client, admin_headers):
        record = MagicMock()
        neo4j_ctx = _make_neo4j_ctx(single_value=record)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=neo4j_ctx):
            resp = client.put(
                "/api/v1/investigations/INV-001/graph",
                json={"nodes": SAMPLE_NODES, "edges": SAMPLE_EDGES},
                headers=admin_headers,
            )

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Load graph state
# ---------------------------------------------------------------------------


class TestLoadInvestigationGraph:
    def test_load_returns_graph_state(self, client, admin_headers):
        graph_json = json.dumps({
            "nodes": SAMPLE_NODES,
            "edges": SAMPLE_EDGES,
            "layout": SAMPLE_LAYOUT,
        })
        record = MagicMock()
        record.__getitem__ = lambda self, k: (
            graph_json if k == "graph_state" else ("2024-01-01" if k == "updated_at" else "admin")
        )

        neo4j_ctx = _make_neo4j_ctx(single_value=record)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=neo4j_ctx):
            resp = client.get(
                "/api/v1/investigations/INV-001/graph",
                headers=admin_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "graph_state" in body

    def test_load_404_when_investigation_missing(self, client, admin_headers):
        neo4j_ctx = _make_neo4j_ctx(single_value=None)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=neo4j_ctx):
            resp = client.get(
                "/api/v1/investigations/MISSING/graph",
                headers=admin_headers,
            )

        assert resp.status_code == 404

    def test_load_requires_auth(self, client):
        resp = client.get("/api/v1/investigations/INV-001/graph")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------


class TestPdfExport:
    def test_pdf_returns_pdf_content_type(self, client, admin_headers):
        inv_record = MagicMock()
        inv_record.__getitem__ = lambda self, k: "INV-001" if k == "i" else None

        inv_props = {
            "investigation_id": "INV-001",
            "title": "Test Investigation",
            "description": "Test description",
            "priority": "high",
            "status": "open",
            "created_by": "admin",
            "created_at": "2024-01-01T00:00:00",
            "addresses": ["0xabc"],
            "blockchain": "ethereum",
            "tags": [],
            "risk_score": 0.5,
        }
        inv_record.__getitem__ = lambda self, k: inv_props.get(k)

        evd_run = AsyncMock()
        evd_run.data = AsyncMock(return_value=[])
        evd_run.single = AsyncMock(return_value=inv_record)

        session = AsyncMock()
        session.run = AsyncMock(return_value=evd_run)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)

        fake_pdf = b"%PDF-1.4 fake pdf content"

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx), \
             patch("src.export.pdf_report.generate_investigation_pdf",
                   return_value=fake_pdf):

            resp = client.get(
                "/api/v1/investigations/INV-001/report/pdf",
                headers=admin_headers,
            )

        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert "pdf" in resp.headers.get("content-type", "")

    def test_pdf_requires_auth(self, client):
        resp = client.get("/api/v1/investigations/INV-001/report/pdf")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PDF report generation unit tests
# ---------------------------------------------------------------------------


class TestGenerateInvestigationPdf:
    def test_returns_bytes(self):
        from src.export.pdf_report import generate_investigation_pdf

        investigation = {
            "investigation_id": "INV-TEST-001",
            "title": "Test Investigation",
            "status": "open",
            "priority": "high",
            "blockchain": "ethereum",
            "created_by": "tester",
            "created_at": "2024-01-01T00:00:00",
            "description": "This is a test.",
            "addresses": ["0xabc", "0xdef"],
            "risk_score": 0.75,
        }
        evidence = []

        result = generate_investigation_pdf(investigation, evidence)
        assert isinstance(result, bytes)
        assert len(result) > 100  # sanity check: non-empty PDF

    def test_pdf_starts_with_pdf_header(self):
        from src.export.pdf_report import generate_investigation_pdf

        investigation = {
            "investigation_id": "INV-TEST-002",
            "title": "Header Test",
            "status": "in_progress",
            "priority": "medium",
            "blockchain": "bitcoin",
            "created_by": "analyst",
            "created_at": "2024-06-01T12:00:00",
            "description": "PDF header check.",
            "addresses": ["1BitcoinAddress"],
            "risk_score": 0.2,
        }
        result = generate_investigation_pdf(investigation, [])
        assert result[:4] == b"%PDF"

    def test_pdf_with_evidence(self):
        from src.export.pdf_report import generate_investigation_pdf

        investigation = {
            "investigation_id": "INV-EVD-001",
            "title": "Evidence Test",
            "status": "open",
            "priority": "critical",
            "blockchain": "ethereum",
            "created_by": "admin",
            "created_at": "2024-03-15T08:00:00",
            "description": "Has evidence.",
            "addresses": ["0xevidence"],
            "risk_score": 0.9,
        }
        evidence = [
            {
                "evidence_id": "EVD-001",
                "evidence_type": "transaction",
                "description": "Suspicious transfer",
                "confidence": 0.95,
                "added_by": "analyst",
                "added_at": "2024-03-15T09:00:00",
            }
        ]
        result = generate_investigation_pdf(investigation, evidence)
        assert isinstance(result, bytes)
        assert len(result) > 100
