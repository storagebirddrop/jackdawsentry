"""
Unit tests for src/analysis/investigation_narrative.py (M15)
"""
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

_INVESTIGATION = {
    "investigation_id": "INV-20240101-ABCDEF",
    "title": "Mixer Probe",
    "description": "Investigating suspected Tornado Cash usage.",
    "status": "in_progress",
    "priority": "high",
    "blockchain": "ethereum",
    "created_by": "analyst",
    "created_at": "2024-01-01T00:00:00",
    "risk_score": 0.72,
    "addresses": ["0xabc", "0xdef", "0x123"],
}

_EVIDENCE = [
    {
        "evidence_id": "EVD-001",
        "evidence_type": "transaction",
        "description": "Deposit to Tornado Cash 1 ETH pool",
        "confidence": 0.92,
        "added_by": "analyst",
        "added_at": "2024-01-02T10:00:00",
    },
    {
        "evidence_id": "EVD-002",
        "evidence_type": "pattern",
        "description": "Layering pattern detected across 5 hops",
        "confidence": 0.75,
        "added_by": "analyst",
        "added_at": "2024-01-03T11:00:00",
    },
]


# ---------------------------------------------------------------------------
# _risk_level_from_score
# ---------------------------------------------------------------------------


class TestRiskLevelFromScore:
    def test_critical(self):
        from src.analysis.investigation_narrative import _risk_level_from_score
        assert _risk_level_from_score(0.80) == "critical"

    def test_high(self):
        from src.analysis.investigation_narrative import _risk_level_from_score
        assert _risk_level_from_score(0.60) == "high"

    def test_medium(self):
        from src.analysis.investigation_narrative import _risk_level_from_score
        assert _risk_level_from_score(0.40) == "medium"

    def test_low(self):
        from src.analysis.investigation_narrative import _risk_level_from_score
        assert _risk_level_from_score(0.10) == "low"

    def test_boundary_critical(self):
        from src.analysis.investigation_narrative import _risk_level_from_score
        assert _risk_level_from_score(0.75) == "critical"

    def test_boundary_high(self):
        from src.analysis.investigation_narrative import _risk_level_from_score
        assert _risk_level_from_score(0.55) == "high"


# ---------------------------------------------------------------------------
# extract_key_findings
# ---------------------------------------------------------------------------


class TestExtractKeyFindings:
    def test_includes_address_count(self):
        from src.analysis.investigation_narrative import extract_key_findings
        findings = extract_key_findings(_INVESTIGATION, _EVIDENCE)
        assert any("3 address" in f for f in findings)

    def test_includes_risk_score(self):
        from src.analysis.investigation_narrative import extract_key_findings
        findings = extract_key_findings(_INVESTIGATION, _EVIDENCE)
        assert any("0.72" in f for f in findings)

    def test_includes_high_confidence_count(self):
        from src.analysis.investigation_narrative import extract_key_findings
        findings = extract_key_findings(_INVESTIGATION, _EVIDENCE)
        assert any("high-confidence" in f for f in findings)

    def test_includes_blockchain(self):
        from src.analysis.investigation_narrative import extract_key_findings
        findings = extract_key_findings(_INVESTIGATION, _EVIDENCE)
        assert any("ethereum" in f.lower() for f in findings)

    def test_no_evidence_still_returns_findings(self):
        from src.analysis.investigation_narrative import extract_key_findings
        findings = extract_key_findings(_INVESTIGATION, [])
        assert len(findings) >= 1

    def test_empty_investigation_returns_fallback(self):
        from src.analysis.investigation_narrative import extract_key_findings
        findings = extract_key_findings({}, [])
        assert len(findings) >= 1
        assert any("No significant" in f for f in findings)


# ---------------------------------------------------------------------------
# _template_narrative
# ---------------------------------------------------------------------------


class TestTemplateNarrative:
    def test_contains_investigation_id(self):
        from src.analysis.investigation_narrative import _template_narrative
        result = _template_narrative(_INVESTIGATION, _EVIDENCE)
        assert "INV-20240101-ABCDEF" in result

    def test_contains_title(self):
        from src.analysis.investigation_narrative import _template_narrative
        result = _template_narrative(_INVESTIGATION, _EVIDENCE)
        assert "Mixer Probe" in result

    def test_contains_status(self):
        from src.analysis.investigation_narrative import _template_narrative
        result = _template_narrative(_INVESTIGATION, _EVIDENCE)
        assert "in progress" in result.lower()

    def test_contains_description(self):
        from src.analysis.investigation_narrative import _template_narrative
        result = _template_narrative(_INVESTIGATION, _EVIDENCE)
        assert "Tornado Cash" in result

    def test_evidence_section_present(self):
        from src.analysis.investigation_narrative import _template_narrative
        result = _template_narrative(_INVESTIGATION, _EVIDENCE)
        assert "Evidence chain" in result

    def test_no_evidence_fallback_text(self):
        from src.analysis.investigation_narrative import _template_narrative
        result = _template_narrative(_INVESTIGATION, [])
        assert "No evidence" in result

    def test_risk_score_override(self):
        from src.analysis.investigation_narrative import _template_narrative
        # Override score to critical
        result = _template_narrative(_INVESTIGATION, [], risk_score=0.9)
        assert "critical" in result.lower()

    def test_auto_disclaimer_present(self):
        from src.analysis.investigation_narrative import _template_narrative
        result = _template_narrative(_INVESTIGATION, _EVIDENCE)
        assert "auto-generated" in result.lower()


# ---------------------------------------------------------------------------
# generate_investigation_narrative (public API)
# ---------------------------------------------------------------------------


class TestGenerateInvestigationNarrative:
    @pytest.mark.asyncio
    async def test_returns_required_keys(self):
        from src.analysis import investigation_narrative as mod
        with patch.object(mod, "_API_KEY", ""):
            result = await mod.generate_investigation_narrative(_INVESTIGATION, _EVIDENCE)
        assert {"narrative", "key_findings", "risk_assessment", "source", "model"} == set(result.keys())

    @pytest.mark.asyncio
    async def test_template_source_when_no_api_key(self):
        from src.analysis import investigation_narrative as mod
        with patch.object(mod, "_API_KEY", ""):
            result = await mod.generate_investigation_narrative(_INVESTIGATION, _EVIDENCE)
        assert result["source"] == "template"
        assert result["model"] is None

    @pytest.mark.asyncio
    async def test_claude_api_source_when_key_present(self):
        from src.analysis import investigation_narrative as mod
        with patch.object(mod, "_API_KEY", "sk-ant-test"), \
             patch.object(mod, "_call_claude_narrative", new_callable=AsyncMock,
                          return_value="A professional narrative."):
            result = await mod.generate_investigation_narrative(_INVESTIGATION, _EVIDENCE)
        assert result["source"] == "claude_api"
        assert result["narrative"] == "A professional narrative."

    @pytest.mark.asyncio
    async def test_falls_back_to_template_when_api_fails(self):
        from src.analysis import investigation_narrative as mod
        with patch.object(mod, "_API_KEY", "sk-ant-test"), \
             patch.object(mod, "_call_claude_narrative", new_callable=AsyncMock, return_value=None):
            result = await mod.generate_investigation_narrative(_INVESTIGATION, _EVIDENCE)
        assert result["source"] == "template"

    @pytest.mark.asyncio
    async def test_key_findings_is_list(self):
        from src.analysis import investigation_narrative as mod
        with patch.object(mod, "_API_KEY", ""):
            result = await mod.generate_investigation_narrative(_INVESTIGATION, _EVIDENCE)
        assert isinstance(result["key_findings"], list)
        assert len(result["key_findings"]) >= 1

    @pytest.mark.asyncio
    async def test_risk_assessment_is_string(self):
        from src.analysis import investigation_narrative as mod
        with patch.object(mod, "_API_KEY", ""):
            result = await mod.generate_investigation_narrative(_INVESTIGATION, _EVIDENCE)
        assert isinstance(result["risk_assessment"], str)
        assert len(result["risk_assessment"]) > 5

    @pytest.mark.asyncio
    async def test_returns_none_on_api_exception(self):
        from src.analysis import investigation_narrative as mod
        fake_anthropic = MagicMock()
        fake_anthropic.AsyncAnthropic.side_effect = Exception("API down")
        with patch.object(mod, "_API_KEY", "sk-ant-test"), \
             patch.dict(sys.modules, {"anthropic": fake_anthropic}):
            result = await mod._call_claude_narrative("some prompt")
        assert result is None
