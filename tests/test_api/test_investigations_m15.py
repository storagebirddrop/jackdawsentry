"""
Tests for M15 investigation endpoints:
  POST /{id}/narrative
  POST /{id}/graph/annotations
  GET  /{id}/graph/annotations
  DELETE /{id}/graph/annotations/{ann_id}
  GET  /{id}/timeline
Also tests the enhanced PDF (narrative section + page numbers).
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _neo4j_ctx(single_value=None, data_value=None):
    """Build a mock Neo4j session context manager."""
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


def _inv_props(
    inv_id="INV-001",
    title="Test",
    status="open",
    priority="high",
    blockchain="ethereum",
    created_by="admin",
    created_at="2024-01-01T00:00:00",
    description="desc",
    addresses=None,
    risk_score=0.5,
    graph_updated_at=None,
    graph_updated_by=None,
    updated_at=None,
    annotations_json=None,
    annotations_updated_at=None,
):
    """Return a plain dict of investigation properties."""
    return {
        "investigation_id": inv_id,
        "title": title,
        "status": status,
        "priority": priority,
        "blockchain": blockchain,
        "created_by": created_by,
        "created_at": created_at,
        "description": description,
        "addresses": addresses or ["0xabc"],
        "risk_score": risk_score,
        "graph_updated_at": graph_updated_at,
        "graph_updated_by": graph_updated_by,
        "updated_at": updated_at,
        "annotations_json": annotations_json,
        "annotations_updated_at": annotations_updated_at,
    }


def _neo4j_record_with_inv(props, evidence_nodes=None):
    """
    Build a Neo4j-style record where record['i'] → props dict and
    record['evidence_nodes'] → list.  dict(record['i']) must work.
    Uses lambda self, k convention matching the rest of this test suite.
    """
    record = MagicMock()
    _ev = evidence_nodes or []
    record.__getitem__ = lambda self, k: (
        props if k == "i" else
        _ev if k == "evidence_nodes" else
        props.get(k)
    )
    record.__bool__ = lambda self: True
    return record


# ---------------------------------------------------------------------------
# POST /{id}/narrative
# ---------------------------------------------------------------------------


_MOCK_NARRATIVE = {
    "narrative": "A test narrative.",
    "key_findings": ["Finding 1"],
    "risk_assessment": "requires review",
    "source": "template",
    "model": None,
}


class TestNarrativeEndpoint:
    def test_narrative_returns_200(self, client, admin_headers):
        record = _neo4j_record_with_inv(_inv_props())
        ctx = _neo4j_ctx(single_value=record)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx), \
             patch("src.analysis.investigation_narrative.generate_investigation_narrative",
                   new_callable=AsyncMock, return_value=_MOCK_NARRATIVE):
            resp = client.post(
                "/api/v1/investigations/INV-001/narrative",
                headers=admin_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["narrative"] == "A test narrative."

    def test_narrative_returns_required_keys(self, client, admin_headers):
        record = _neo4j_record_with_inv(_inv_props())
        ctx = _neo4j_ctx(single_value=record)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx), \
             patch("src.analysis.investigation_narrative.generate_investigation_narrative",
                   new_callable=AsyncMock, return_value=_MOCK_NARRATIVE):
            resp = client.post("/api/v1/investigations/INV-001/narrative", headers=admin_headers)

        body = resp.json()
        for key in ("narrative", "key_findings", "risk_assessment", "source"):
            assert key in body

    def test_narrative_404_when_not_found(self, client, admin_headers):
        # record["i"] returns None → 404
        record = MagicMock()
        record.__getitem__ = lambda self, k: None
        ctx = _neo4j_ctx(single_value=record)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.post("/api/v1/investigations/MISSING/narrative", headers=admin_headers)

        assert resp.status_code == 404

    def test_narrative_requires_auth(self, client):
        resp = client.post("/api/v1/investigations/INV-001/narrative")
        assert resp.status_code == 403

    def test_narrative_investigator_cannot_access(self, client, auth_headers):
        # auth_headers only has analysis:read/write — lacks investigations:read
        resp = client.post("/api/v1/investigations/INV-001/narrative", headers=auth_headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /{id}/graph/annotations
# ---------------------------------------------------------------------------


class TestAddAnnotation:
    def _setup_add(self, ann_json=None):
        """Return two Neo4j ctxs: one for existence check, one for load+save."""
        exists_record = MagicMock()
        exists_record.__getitem__ = lambda self, k: "INV-001"

        ann_record = MagicMock()
        ann_record.__getitem__ = lambda self, k: ann_json if k == "anns" else None

        call_count = [0]

        run_result_exists = AsyncMock()
        run_result_exists.single = AsyncMock(return_value=exists_record)

        run_result_anns = AsyncMock()
        run_result_anns.single = AsyncMock(return_value=ann_record)

        run_result_set = AsyncMock()
        run_result_set.single = AsyncMock(return_value=None)

        results = [run_result_exists, run_result_anns, run_result_set]

        session = AsyncMock()

        async def _run(*args, **kwargs):
            r = results[call_count[0] % len(results)]
            call_count[0] += 1
            return r

        session.run = _run
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    def test_add_annotation_returns_200(self, client, admin_headers):
        ctx = self._setup_add()
        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.post(
                "/api/v1/investigations/INV-001/graph/annotations",
                json={"target_id": "0xabc", "annotation_type": "note", "content": "Suspicious node"},
                headers=admin_headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "annotation" in body

    def test_add_annotation_returns_annotation_id(self, client, admin_headers):
        ctx = self._setup_add()
        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.post(
                "/api/v1/investigations/INV-001/graph/annotations",
                json={"target_id": "edge1", "annotation_type": "flag", "content": "High value"},
                headers=admin_headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "annotation_id" in body["annotation"]
        assert body["annotation"]["annotation_id"].startswith("ANN-")

    def test_add_annotation_rejects_invalid_type(self, client, admin_headers):
        resp = client.post(
            "/api/v1/investigations/INV-001/graph/annotations",
            json={"target_id": "node1", "annotation_type": "unknown", "content": "Test"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_add_annotation_rejects_empty_content(self, client, admin_headers):
        resp = client.post(
            "/api/v1/investigations/INV-001/graph/annotations",
            json={"target_id": "node1", "annotation_type": "note", "content": "   "},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_add_annotation_requires_admin(self, client, auth_headers):
        resp = client.post(
            "/api/v1/investigations/INV-001/graph/annotations",
            json={"target_id": "n", "annotation_type": "note", "content": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_add_annotation_requires_auth(self, client):
        resp = client.post(
            "/api/v1/investigations/INV-001/graph/annotations",
            json={"target_id": "n", "annotation_type": "note", "content": "x"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /{id}/graph/annotations
# ---------------------------------------------------------------------------


class TestGetAnnotations:
    def test_get_annotations_returns_200(self, client, admin_headers):
        existing = json.dumps([
            {"annotation_id": "ANN-001", "target_id": "0xabc", "annotation_type": "note",
             "content": "test", "created_by": "admin", "created_at": "2024-01-01T00:00:00"},
        ])
        record = MagicMock()
        record.__getitem__ = lambda self, k: existing if k == "anns" else "2024-01-01"
        ctx = _neo4j_ctx(single_value=record)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.get("/api/v1/investigations/INV-001/graph/annotations", headers=admin_headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["annotations"][0]["annotation_id"] == "ANN-001"

    def test_get_annotations_empty_list(self, client, admin_headers):
        record = MagicMock()
        record.__getitem__ = lambda self, k: None
        ctx = _neo4j_ctx(single_value=record)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.get("/api/v1/investigations/INV-001/graph/annotations", headers=admin_headers)

        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_get_annotations_404_when_not_found(self, client, admin_headers):
        ctx = _neo4j_ctx(single_value=None)
        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.get("/api/v1/investigations/MISSING/graph/annotations", headers=admin_headers)
        assert resp.status_code == 404

    def test_get_annotations_requires_auth(self, client):
        resp = client.get("/api/v1/investigations/INV-001/graph/annotations")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /{id}/graph/annotations/{ann_id}
# ---------------------------------------------------------------------------


class TestDeleteAnnotation:
    def _setup_delete(self, ann_json):
        record = MagicMock()
        record.__getitem__ = lambda self, k: ann_json if k == "anns" else None

        run_result_load = AsyncMock()
        run_result_load.single = AsyncMock(return_value=record)

        run_result_save = AsyncMock()
        run_result_save.single = AsyncMock(return_value=None)

        call_count = [0]
        results = [run_result_load, run_result_save]

        session = AsyncMock()

        async def _run(*args, **kwargs):
            r = results[call_count[0] % len(results)]
            call_count[0] += 1
            return r

        session.run = _run
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    def test_delete_annotation_returns_200(self, client, admin_headers):
        existing = json.dumps([
            {"annotation_id": "ANN-XYZ", "target_id": "n", "annotation_type": "note",
             "content": "x", "created_by": "admin", "created_at": "2024-01-01"},
        ])
        ctx = self._setup_delete(existing)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.delete(
                "/api/v1/investigations/INV-001/graph/annotations/ANN-XYZ",
                headers=admin_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted_annotation_id"] == "ANN-XYZ"
        assert body["remaining_count"] == 0

    def test_delete_annotation_404_when_ann_not_found(self, client, admin_headers):
        existing = json.dumps([
            {"annotation_id": "ANN-OTHER", "target_id": "n", "annotation_type": "note",
             "content": "x", "created_by": "admin", "created_at": "2024-01-01"},
        ])
        ctx = self._setup_delete(existing)

        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.delete(
                "/api/v1/investigations/INV-001/graph/annotations/ANN-NOTEXIST",
                headers=admin_headers,
            )

        assert resp.status_code == 404

    def test_delete_annotation_requires_admin(self, client, auth_headers):
        resp = client.delete(
            "/api/v1/investigations/INV-001/graph/annotations/ANN-001",
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_delete_investigation_not_found(self, client, admin_headers):
        ctx = _neo4j_ctx(single_value=None)
        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.delete(
                "/api/v1/investigations/MISSING/graph/annotations/ANN-001",
                headers=admin_headers,
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /{id}/timeline
# ---------------------------------------------------------------------------


class TestTimeline:
    def _setup_timeline(self, props, evidence_records=None):
        """Build a session mock for the timeline endpoint.

        First session.run → single() returns a record where record['i'] = props dict.
        Second session.run → data() returns evidence_records list.
        """
        tl_record = _neo4j_record_with_inv(props)

        inv_run = AsyncMock()
        inv_run.single = AsyncMock(return_value=tl_record)

        evd_run = AsyncMock()
        evd_run.data = AsyncMock(return_value=evidence_records or [])

        call_count = [0]
        results = [inv_run, evd_run]

        session = AsyncMock()

        async def _run(*args, **kwargs):
            r = results[call_count[0] % len(results)]
            call_count[0] += 1
            return r

        session.run = _run
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    def _base_props(self):
        return _inv_props(
            created_at="2024-01-01T00:00:00",
            graph_updated_at=None,
            updated_at=None,
        )

    def test_timeline_returns_200(self, client, admin_headers):
        ctx = self._setup_timeline(self._base_props())
        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.get("/api/v1/investigations/INV-001/timeline", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "events" in body

    def test_timeline_includes_creation_event(self, client, admin_headers):
        ctx = self._setup_timeline(self._base_props())
        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.get("/api/v1/investigations/INV-001/timeline", headers=admin_headers)
        events = resp.json()["events"]
        assert any(e["event_type"] == "investigation_created" for e in events)

    def test_timeline_includes_graph_saved_event(self, client, admin_headers):
        props = _inv_props(
            created_at="2024-01-01T00:00:00",
            graph_updated_at="2024-01-02T12:00:00",
            graph_updated_by="analyst",
            updated_at=None,
        )
        ctx = self._setup_timeline(props)
        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.get("/api/v1/investigations/INV-001/timeline", headers=admin_headers)
        events = resp.json()["events"]
        assert any(e["event_type"] == "graph_saved" for e in events)

    def test_timeline_404_when_not_found(self, client, admin_headers):
        # single() returns None → 404
        ctx = _neo4j_ctx(single_value=None)
        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.get("/api/v1/investigations/MISSING/timeline", headers=admin_headers)
        assert resp.status_code == 404

    def test_timeline_requires_auth(self, client):
        resp = client.get("/api/v1/investigations/INV-001/timeline")
        assert resp.status_code == 403

    def test_timeline_event_count_in_response(self, client, admin_headers):
        ctx = self._setup_timeline(self._base_props())
        with patch("src.api.routers.investigations.get_neo4j_session", return_value=ctx):
            resp = client.get("/api/v1/investigations/INV-001/timeline", headers=admin_headers)
        body = resp.json()
        assert "event_count" in body
        assert body["event_count"] == len(body["events"])


# ---------------------------------------------------------------------------
# Enhanced PDF (narrative + page numbers)
# ---------------------------------------------------------------------------


class TestEnhancedPdf:
    def test_pdf_with_narrative_returns_bytes(self):
        from src.export.pdf_report import generate_investigation_pdf

        investigation = {
            "investigation_id": "INV-NAR-001",
            "title": "Narrative PDF Test",
            "status": "open",
            "priority": "high",
            "blockchain": "ethereum",
            "created_by": "analyst",
            "created_at": "2024-01-01T00:00:00",
            "description": "Testing narrative in PDF.",
            "addresses": ["0xabc"],
            "risk_score": 0.7,
        }
        narrative = "This is a test narrative.\n\nSecond paragraph of the narrative."
        result = generate_investigation_pdf(investigation, [], narrative=narrative)
        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"

    def test_pdf_without_narrative_still_works(self):
        from src.export.pdf_report import generate_investigation_pdf

        investigation = {
            "investigation_id": "INV-NAR-002",
            "title": "No Narrative",
            "status": "open",
            "priority": "medium",
            "blockchain": "bitcoin",
            "created_by": "admin",
            "created_at": "2024-01-01T00:00:00",
            "description": "",
            "addresses": [],
            "risk_score": 0.0,
        }
        result = generate_investigation_pdf(investigation, [], narrative=None)
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_pdf_narrative_makes_pdf_larger(self):
        from src.export.pdf_report import generate_investigation_pdf

        base_inv = {
            "investigation_id": "INV-SIZE",
            "title": "Size test",
            "status": "open",
            "priority": "medium",
            "blockchain": "ethereum",
            "created_by": "admin",
            "created_at": "2024-01-01T00:00:00",
            "description": "desc",
            "addresses": ["0xabc"],
            "risk_score": 0.5,
        }
        without = generate_investigation_pdf(base_inv, [])
        with_narrative = generate_investigation_pdf(
            base_inv, [],
            narrative="A " * 200,  # substantial narrative
        )
        assert len(with_narrative) > len(without)
