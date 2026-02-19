"""
Case Management Engine Tests — rewritten to match actual CaseManagementEngine API.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.compliance.case_management import (
    CaseManagementEngine,
    CaseStatus,
    CasePriority,
    CaseType,
    EvidenceType,
    EvidenceStatus,
    Case,
    Evidence,
    CaseWorkflow,
)


class TestCaseManagementEngine:
    """Test suite for CaseManagementEngine"""

    @pytest.fixture
    def engine(self):
        return CaseManagementEngine()

    # ---- Initialization ----

    def test_engine_initializes(self, engine):
        # Verify the engine exposes workflows for known case types via public cache
        assert engine.cache_ttl == 3600
        wf_sa = engine.workflows_cache.get(CaseType.SUSPICIOUS_ACTIVITY)
        wf_ml = engine.workflows_cache.get(CaseType.MONEY_LAUNDERING)
        assert wf_sa is not None
        assert wf_ml is not None

    def test_workflows_populated(self, engine):
        wf_sa = engine.workflows_cache.get(CaseType.SUSPICIOUS_ACTIVITY)
        wf_ml = engine.workflows_cache.get(CaseType.MONEY_LAUNDERING)
        assert isinstance(wf_sa, CaseWorkflow)
        assert isinstance(wf_ml, CaseWorkflow)
        assert len(wf_sa.steps) > 0
        assert len(wf_ml.steps) > 0

    # ---- Enum values ----

    def test_case_status_values(self):
        assert CaseStatus.OPEN.value == "open"
        assert CaseStatus.IN_PROGRESS.value == "in_progress"
        assert CaseStatus.CLOSED.value == "closed"

    def test_case_priority_values(self):
        assert CasePriority.LOW.value == "low"
        assert CasePriority.HIGH.value == "high"
        assert CasePriority.URGENT.value == "urgent"

    def test_case_type_values(self):
        assert CaseType.SUSPICIOUS_ACTIVITY.value == "suspicious_activity"
        assert CaseType.MONEY_LAUNDERING.value == "money_laundering"
        assert CaseType.SANCTIONS_VIOLATION.value == "sanctions_violation"

    def test_evidence_type_values(self):
        assert EvidenceType.TRANSACTION_DATA.value == "transaction_data"
        assert EvidenceType.ADDRESS_ANALYSIS.value == "address_analysis"

    # ---- create_case (mocked DB) ----

    @pytest.mark.asyncio
    async def test_create_case_returns_case(self, engine):
        with patch.object(engine, '_store_case', new_callable=AsyncMock):
            case = await engine.create_case(
                title="Suspicious Activity",
                description="Unusual transaction pattern detected",
                case_type=CaseType.SUSPICIOUS_ACTIVITY,
                priority=CasePriority.HIGH,
                assigned_to="investigator_1",
                created_by="system",
            )
            assert isinstance(case, Case)
            assert case.title == "Suspicious Activity"
            assert case.case_type == CaseType.SUSPICIOUS_ACTIVITY
            assert case.priority == CasePriority.HIGH
            assert case.status == CaseStatus.OPEN
            assert case.case_id.startswith("case_")

    @pytest.mark.asyncio
    async def test_create_case_with_targets(self, engine):
        with patch.object(engine, '_store_case', new_callable=AsyncMock):
            case = await engine.create_case(
                title="AML Investigation",
                description="Potential money laundering",
                case_type=CaseType.MONEY_LAUNDERING,
                priority=CasePriority.URGENT,
                assigned_to="inv_2",
                created_by="analyst_1",
                targets=["0xabc", "0xdef"],
            )
            assert case.targets == ["0xabc", "0xdef"]

    @pytest.mark.asyncio
    async def test_create_case_with_metadata(self, engine):
        with patch.object(engine, '_store_case', new_callable=AsyncMock):
            case = await engine.create_case(
                title="Sanctions Case",
                description="Sanctions screening hit",
                case_type=CaseType.SANCTIONS_VIOLATION,
                priority=CasePriority.HIGH,
                assigned_to="inv_3",
                created_by="system",
                metadata={"source": "screening_engine"},
            )
            assert case.metadata == {"source": "screening_engine"}

    @pytest.mark.asyncio
    async def test_create_case_assigns_workflow(self, engine):
        with patch.object(engine, '_store_case', new_callable=AsyncMock):
            case = await engine.create_case(
                title="Test",
                description="Test case",
                case_type=CaseType.SUSPICIOUS_ACTIVITY,
                priority=CasePriority.MEDIUM,
                assigned_to="inv_1",
                created_by="sys",
            )
            assert len(case.workflow_steps) > 0

    @pytest.mark.asyncio
    async def test_create_case_stores_to_db(self, engine):
        mock_store = AsyncMock()
        with patch.object(engine, '_store_case', mock_store):
            await engine.create_case(
                title="Test",
                description="Desc",
                case_type=CaseType.SUSPICIOUS_ACTIVITY,
                priority=CasePriority.LOW,
                assigned_to="inv",
                created_by="sys",
            )
            mock_store.assert_awaited_once()

    # ---- add_evidence (mocked DB) ----

    @pytest.mark.asyncio
    async def test_add_evidence_returns_evidence(self, engine):
        with patch.object(engine, '_store_evidence', new_callable=AsyncMock):
            with patch.object(engine, '_update_case_evidence_count', new_callable=AsyncMock):
                evidence = await engine.add_evidence(
                    case_id="case_123",
                    evidence_type=EvidenceType.TRANSACTION_DATA,
                    title="Suspicious Transaction",
                    description="Large transfer detected",
                    source="blockchain_monitor",
                    collected_by="analyst_1",
                    data={"tx_hash": "0xabc", "amount": 50000},
                )
                assert isinstance(evidence, Evidence)
                assert evidence.case_id == "case_123"
                assert evidence.evidence_type == EvidenceType.TRANSACTION_DATA
                assert evidence.status == EvidenceStatus.COLLECTED

    @pytest.mark.asyncio
    async def test_add_evidence_has_hash(self, engine):
        with patch.object(engine, '_store_evidence', new_callable=AsyncMock):
            with patch.object(engine, '_update_case_evidence_count', new_callable=AsyncMock):
                evidence = await engine.add_evidence(
                    case_id="case_123",
                    evidence_type=EvidenceType.ADDRESS_ANALYSIS,
                    title="Address Report",
                    description="Analysis results",
                    source="analysis_engine",
                    collected_by="system",
                    data={"address": "0xdef"},
                )
                h = evidence.calculate_hash()
                assert len(h) == 64  # sha256 hex

    # ---- update_case_status (mocked DB) ----

    @pytest.mark.asyncio
    async def test_update_case_status_success(self, engine):
        mock_case = Case(
            case_id="case_123",
            title="Test",
            description="Test case",
            case_type=CaseType.SUSPICIOUS_ACTIVITY,
            priority=CasePriority.HIGH,
            status=CaseStatus.OPEN,
            assigned_to="inv_1",
            created_by="sys",
        )
        with patch.object(engine, '_get_case', new_callable=AsyncMock, return_value=mock_case):
            with patch.object(engine, '_store_case', new_callable=AsyncMock):
                result = await engine.update_case_status(
                    case_id="case_123",
                    new_status=CaseStatus.IN_PROGRESS,
                    updated_by="inv_1",
                    notes="Starting investigation",
                )
                assert result is True

    @pytest.mark.asyncio
    async def test_update_case_status_not_found(self, engine):
        with patch.object(engine, '_get_case', new_callable=AsyncMock, return_value=None):
            result = await engine.update_case_status(
                case_id="nonexistent",
                new_status=CaseStatus.CLOSED,
                updated_by="inv_1",
            )
            assert result is False

    # ---- get_case_summary (mocked DB) ----

    @pytest.mark.asyncio
    async def test_get_case_summary_returns_dict(self, engine):
        mock_case = Case(
            case_id="case_123",
            title="Test",
            description="Test case",
            case_type=CaseType.SUSPICIOUS_ACTIVITY,
            priority=CasePriority.HIGH,
            status=CaseStatus.OPEN,
            assigned_to="inv_1",
            created_by="sys",
            created_at=datetime.now(timezone.utc),  # tz-aware to avoid subtraction error
        )
        with patch.object(engine, '_get_case', new_callable=AsyncMock, return_value=mock_case):
            with patch.object(engine, '_get_case_evidence', new_callable=AsyncMock, return_value=[]):
                summary = await engine.get_case_summary("case_123")
                assert isinstance(summary, dict)
                assert summary['case']['case_id'] == "case_123"
                assert summary['case']['title'] == "Test"

    @pytest.mark.asyncio
    async def test_get_case_summary_not_found(self, engine):
        with patch.object(engine, '_get_case', new_callable=AsyncMock, return_value=None):
            with pytest.raises(Exception):
                await engine.get_case_summary("nonexistent")

    # ---- search_cases (mocked DB) ----

    @pytest.mark.asyncio
    async def test_search_cases_by_status(self, engine):
        mock_cases = [
            Case(
                case_id="c1", title="Open Case", description="d",
                case_type=CaseType.SUSPICIOUS_ACTIVITY, priority=CasePriority.HIGH,
                status=CaseStatus.OPEN, assigned_to="inv", created_by="sys",
            )
        ]
        with patch.object(engine, '_get_all_cases', new_callable=AsyncMock, return_value=mock_cases):
            results = await engine.search_cases(status=CaseStatus.OPEN)
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_cases_empty(self, engine):
        with patch.object(engine, '_get_all_cases', new_callable=AsyncMock, return_value=[]):
            results = await engine.search_cases()
            assert results == []

    # ---- advance_case_workflow (mocked DB) ----

    @pytest.mark.asyncio
    async def test_advance_workflow_no_case(self, engine):
        with patch.object(engine, '_get_case', new_callable=AsyncMock, return_value=None):
            result = await engine.advance_case_workflow("nonexistent", "inv_1")
            assert result.get('success') is False

    @pytest.mark.asyncio
    async def test_advance_workflow_success(self, engine):
        mock_case = Case(
            case_id="case_123",
            title="Test Advance",
            description="Test advancing workflow",
            case_type=CaseType.SUSPICIOUS_ACTIVITY,
            priority=CasePriority.HIGH,
            status=CaseStatus.IN_PROGRESS,
            assigned_to="inv_1",
            created_by="sys",
            current_step=0,
        )
        # Build mock evidence matching the first step's required_evidence
        workflow = engine.workflows_cache[CaseType.SUSPICIOUS_ACTIVITY]
        first_step = workflow.steps[0]
        required = first_step.get('required_evidence', [])
        mock_evidence = []
        for req in required:
            ev = MagicMock()
            ev.evidence_type.value = req
            mock_evidence.append(ev)

        mock_store = AsyncMock()
        with patch.object(engine, '_get_case', new_callable=AsyncMock, return_value=mock_case):
            with patch.object(engine, '_get_case_evidence', new_callable=AsyncMock, return_value=mock_evidence):
                with patch.object(engine, '_store_case', mock_store):
                    result = await engine.advance_case_workflow("case_123", "inv_1")
                    assert result.get('success') is True
                    mock_store.assert_awaited_once()

    # ---- Evidence dataclass ----

    def test_evidence_calculate_hash(self):
        ev = Evidence(
            evidence_id="ev_1",
            case_id="case_1",
            evidence_type=EvidenceType.TRANSACTION_DATA,
            title="TX Data",
            description="Test",
            source="monitor",
            collected_by="sys",
            collected_at=datetime.now(timezone.utc),
            data={"tx": "0xabc"},
        )
        h = ev.calculate_hash()
        assert len(h) == 64  # sha256 hex

    # ---- CaseWorkflow dataclass ----

    def test_default_workflow_structure(self, engine):
        wf = engine.workflows_cache.get(CaseType.SUSPICIOUS_ACTIVITY)
        assert isinstance(wf, CaseWorkflow)
        assert wf.name != ""
        assert len(wf.steps) > 0
