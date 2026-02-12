"""
Audit Trail Engine Tests — rewritten to match actual AuditTrailEngine API.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.compliance.audit_trail import (
    AuditTrailEngine,
    AuditEventType,
    AuditSeverity,
    ComplianceCategory,
    AuditEvent,
    AuditReport,
)


class TestAuditTrailEngine:
    """Test suite for AuditTrailEngine"""

    @pytest.fixture
    def engine(self):
        return AuditTrailEngine()

    # ---- Initialization ----

    def test_engine_initializes(self, engine):
        assert engine.chain_integrity_enabled is True
        assert isinstance(engine.compliance_requirements, dict)

    def test_compliance_requirements_populated(self, engine):
        assert ComplianceCategory.GDPR in engine.compliance_requirements
        assert ComplianceCategory.AML in engine.compliance_requirements

    # ---- Enum values ----

    def test_event_types_exist(self):
        assert AuditEventType.USER_LOGIN.value == "user_login"
        assert AuditEventType.CASE_CREATED.value == "case_created"
        assert AuditEventType.SECURITY_BREACH.value == "security_breach"
        assert AuditEventType.COMPLIANCE_CHECK.value == "compliance_check"

    def test_severity_levels_exist(self):
        assert AuditSeverity.LOW.value == "low"
        assert AuditSeverity.MEDIUM.value == "medium"
        assert AuditSeverity.HIGH.value == "high"
        assert AuditSeverity.CRITICAL.value == "critical"

    def test_compliance_categories_exist(self):
        assert ComplianceCategory.GDPR.value == "gdpr"
        assert ComplianceCategory.AML.value == "aml"
        assert ComplianceCategory.SOX.value == "sox"

    # ---- log_event (mocked DB) ----

    @pytest.mark.asyncio
    async def test_log_event_returns_event_id(self, engine):
        with patch.object(engine, '_store_audit_event', new_callable=AsyncMock):
            with patch.object(engine, '_get_latest_event', new_callable=AsyncMock, return_value=None):
                with patch.object(engine, '_update_compliance_logs', new_callable=AsyncMock):
                    event_id = await engine.log_event(
                        event_type=AuditEventType.CASE_CREATED,
                        severity=AuditSeverity.MEDIUM,
                        user_id="user_001",
                        session_id="sess_abc",
                        ip_address="192.168.1.100",
                        user_agent="Mozilla/5.0",
                        action="case_created",
                        description="Created case",
                    )
                    assert event_id is not None
                    assert event_id.startswith("audit_")

    @pytest.mark.asyncio
    async def test_log_event_stores_event(self, engine):
        mock_store = AsyncMock()
        with patch.object(engine, '_store_audit_event', mock_store):
            with patch.object(engine, '_get_latest_event', new_callable=AsyncMock, return_value=None):
                with patch.object(engine, '_update_compliance_logs', new_callable=AsyncMock):
                    await engine.log_event(
                        event_type=AuditEventType.USER_LOGIN,
                        severity=AuditSeverity.LOW,
                        user_id="user_001",
                        session_id="sess_1",
                        ip_address="10.0.0.1",
                        user_agent="curl/7.0",
                    )
                    mock_store.assert_awaited_once()
                    stored_event = mock_store.call_args[0][0]
                    assert isinstance(stored_event, AuditEvent)
                    assert stored_event.event_type == AuditEventType.USER_LOGIN
                    assert stored_event.user_id == "user_001"

    @pytest.mark.asyncio
    async def test_log_event_with_compliance_categories(self, engine):
        mock_store = AsyncMock()
        with patch.object(engine, '_store_audit_event', mock_store):
            with patch.object(engine, '_get_latest_event', new_callable=AsyncMock, return_value=None):
                with patch.object(engine, '_update_compliance_logs', new_callable=AsyncMock) as mock_compliance:
                    await engine.log_event(
                        event_type=AuditEventType.COMPLIANCE_CHECK,
                        severity=AuditSeverity.MEDIUM,
                        user_id="officer_1",
                        session_id="sess_2",
                        ip_address="10.0.0.2",
                        user_agent="Chrome",
                        compliance_categories=[ComplianceCategory.GDPR],
                    )
                    mock_compliance.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_log_event_hash_chain_first_event(self, engine):
        """First event has no previous_hash"""
        mock_store = AsyncMock()
        with patch.object(engine, '_store_audit_event', mock_store):
            with patch.object(engine, '_get_latest_event', new_callable=AsyncMock, return_value=None):
                with patch.object(engine, '_update_compliance_logs', new_callable=AsyncMock):
                    await engine.log_event(
                        event_type=AuditEventType.USER_LOGIN,
                        severity=AuditSeverity.LOW,
                        user_id="u1",
                        session_id="s1",
                        ip_address="1.2.3.4",
                        user_agent="ua",
                    )
                    stored = mock_store.call_args[0][0]
                    assert stored.previous_hash is None
                    assert stored.event_hash != ""

    @pytest.mark.asyncio
    async def test_log_event_hash_chain_second_event(self, engine):
        """Second event references first event's hash"""
        first_event = AuditEvent(
            event_id="audit_1",
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.LOW,
            user_id="u1",
            session_id="s1",
            ip_address="1.2.3.4",
            user_agent="ua",
            event_hash="abc123",
        )
        mock_store = AsyncMock()
        with patch.object(engine, '_store_audit_event', mock_store):
            with patch.object(engine, '_get_latest_event', new_callable=AsyncMock, return_value=first_event):
                with patch.object(engine, '_update_compliance_logs', new_callable=AsyncMock):
                    await engine.log_event(
                        event_type=AuditEventType.USER_LOGOUT,
                        severity=AuditSeverity.LOW,
                        user_id="u1",
                        session_id="s1",
                        ip_address="1.2.3.4",
                        user_agent="ua",
                    )
                    stored = mock_store.call_args[0][0]
                    assert stored.previous_hash == "abc123"

    # ---- AuditEvent dataclass ----

    def test_audit_event_calculate_hash(self):
        event = AuditEvent(
            event_id="e1",
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.LOW,
            user_id="u1",
            session_id="s1",
            ip_address="1.1.1.1",
            user_agent="ua",
        )
        h1 = event.calculate_hash()
        h2 = event.calculate_hash()
        assert h1 == h2  # deterministic
        assert len(h1) == 64  # sha256 hex

    def test_audit_event_hash_changes_with_previous(self):
        event = AuditEvent(
            event_id="e1",
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.LOW,
            user_id="u1",
            session_id="s1",
            ip_address="1.1.1.1",
            user_agent="ua",
        )
        h_none = event.calculate_hash(None)
        h_prev = event.calculate_hash("prev_hash_abc")
        assert h_none != h_prev

    # ---- verify_chain_integrity (mocked DB) ----

    @pytest.mark.asyncio
    async def test_verify_chain_integrity_disabled(self, engine):
        engine.chain_integrity_enabled = False
        result = await engine.verify_chain_integrity()
        assert result.get("verified") is True
        assert "not enabled" in result.get("message", "").lower() or result.get("events_verified") == 0

    @pytest.mark.asyncio
    async def test_verify_chain_integrity_no_events(self, engine):
        with patch.object(engine, '_get_events_for_verification', new_callable=AsyncMock, return_value=[]):
            result = await engine.verify_chain_integrity()
            assert isinstance(result, dict)

    # ---- generate_audit_report (mocked DB) ----

    @pytest.mark.asyncio
    async def test_generate_audit_report_returns_report(self, engine):
        mock_events = [
            AuditEvent(
                event_id="e1", event_type=AuditEventType.USER_LOGIN,
                severity=AuditSeverity.LOW, user_id="u1",
                session_id="s1", ip_address="1.1.1.1", user_agent="ua",
                event_hash="h1",
            )
        ]
        with patch.object(engine, '_get_events_by_period', new_callable=AsyncMock, return_value=mock_events):
            with patch.object(engine, 'verify_chain_integrity', new_callable=AsyncMock, return_value={"valid": True}):
                with patch.object(engine, '_store_audit_report', new_callable=AsyncMock):
                    now = datetime.now(timezone.utc)
                    report = await engine.generate_audit_report(
                        report_type="general",
                        period_start=now - timedelta(hours=1),
                        period_end=now,
                        generated_by="admin",
                    )
                    assert isinstance(report, AuditReport)
                    assert report.total_events == 1

    # ---- search_audit_events (mocked DB) ----

    @pytest.mark.asyncio
    async def test_search_audit_events_by_type(self, engine):
        mock_events = [
            AuditEvent(
                event_id="e1", event_type=AuditEventType.SECURITY_BREACH,
                severity=AuditSeverity.HIGH, user_id="u1",
                session_id="s1", ip_address="1.1.1.1", user_agent="ua",
            )
        ]
        with patch.object(engine, '_get_all_events', new_callable=AsyncMock, return_value=mock_events):
            results = await engine.search_audit_events(
                event_types=[AuditEventType.SECURITY_BREACH]
            )
            assert len(results) == 1

    # ---- get_compliance_status (mocked DB) ----

    @pytest.mark.asyncio
    async def test_get_compliance_status_single_category(self, engine):
        with patch.object(engine, '_get_category_compliance_status', new_callable=AsyncMock, return_value={"status": "ok"}):
            result = await engine.get_compliance_status(ComplianceCategory.GDPR)
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_compliance_status_all(self, engine):
        with patch.object(engine, '_get_all_compliance_status', new_callable=AsyncMock, return_value={"gdpr": {}}):
            result = await engine.get_compliance_status()
            assert isinstance(result, dict)
