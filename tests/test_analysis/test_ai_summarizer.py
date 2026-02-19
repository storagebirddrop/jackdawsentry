"""
Unit tests for src/analysis/ai_summarizer.py (M14)
"""
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Template helpers (pure functions — no I/O)
# ---------------------------------------------------------------------------


class TestTemplateFunctions:
    def test_address_summary_contains_address_prefix(self):
        from src.analysis.ai_summarizer import _template_address_summary
        result = _template_address_summary(
            address="0xdeadbeefcafe1234",
            risk_level="high",
            score=0.65,
            feature_vector={"mixer_usage": 0.0},
        )
        assert "0xdeadbeef" in result

    def test_address_summary_mentions_risk_level(self):
        from src.analysis.ai_summarizer import _template_address_summary
        result = _template_address_summary(
            address="0x1234",
            risk_level="critical",
            score=0.90,
            feature_vector={},
        )
        assert "critical" in result.lower()

    def test_address_summary_lists_active_flags(self):
        from src.analysis.ai_summarizer import _template_address_summary
        result = _template_address_summary(
            address="0xabc",
            risk_level="high",
            score=0.7,
            feature_vector={"mixer_usage": 1.0, "privacy_tool_usage": 0.0},
        )
        assert "mixer" in result.lower()

    def test_address_summary_no_flags_fallback_text(self):
        from src.analysis.ai_summarizer import _template_address_summary
        result = _template_address_summary(
            address="0xabc",
            risk_level="low",
            score=0.1,
            feature_vector={"mixer_usage": 0.0},
        )
        assert "threshold" in result.lower() or "signal" in result.lower()

    def test_address_summary_includes_entity_name(self):
        from src.analysis.ai_summarizer import _template_address_summary
        result = _template_address_summary(
            address="0xabc",
            risk_level="critical",
            score=0.9,
            feature_vector={},
            entity_info={"entity_name": "Lazarus Group"},
        )
        assert "Lazarus Group" in result

    def test_transaction_summary_contains_hash_prefix(self):
        from src.analysis.ai_summarizer import _template_transaction_summary
        result = _template_transaction_summary(
            tx_hash="0xabcdef1234567890",
            interaction_type="mixer_deposit",
            protocol_name="Tornado Cash",
            risk_level="critical",
        )
        assert "0xabcdef12" in result

    def test_transaction_summary_mentions_protocol(self):
        from src.analysis.ai_summarizer import _template_transaction_summary
        result = _template_transaction_summary(
            tx_hash="0x1234",
            interaction_type="dex_swap",
            protocol_name="Uniswap V3",
            risk_level="low",
        )
        assert "Uniswap" in result

    def test_transaction_summary_no_protocol(self):
        from src.analysis.ai_summarizer import _template_transaction_summary
        result = _template_transaction_summary(
            tx_hash="0x1234",
            interaction_type="transfer",
            protocol_name=None,
            risk_level="low",
        )
        assert "transfer" in result.lower()

    def test_cluster_summary_contains_id_and_count(self):
        from src.analysis.ai_summarizer import _template_cluster_summary
        result = _template_cluster_summary("cluster-42", "mixer", 7, "mixer_usage")
        assert "cluster-42" in result
        assert "7" in result

    def test_cluster_summary_includes_dominant_feature(self):
        from src.analysis.ai_summarizer import _template_cluster_summary
        result = _template_cluster_summary("c1", "darknet", 3, "darknet_entity")
        assert "darknet" in result.lower()

    def test_cluster_summary_unknown_feature_graceful(self):
        from src.analysis.ai_summarizer import _template_cluster_summary
        # Should not raise even if dominant_feature is not in the dict
        result = _template_cluster_summary("c1", "mixer", 2, "nonexistent_feature")
        assert "c1" in result


# ---------------------------------------------------------------------------
# _call_claude (async, mock anthropic)
# ---------------------------------------------------------------------------


class TestCallClaude:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_api_key(self):
        from src.analysis import ai_summarizer
        with patch.object(ai_summarizer, "_API_KEY", ""):
            result = await ai_summarizer._call_claude("test prompt")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        from src.analysis import ai_summarizer
        # Inject a fake anthropic module that raises on instantiation
        fake_anthropic = MagicMock()
        fake_anthropic.AsyncAnthropic.side_effect = Exception("API error")
        with patch.object(ai_summarizer, "_API_KEY", "sk-test"), \
             patch.dict(sys.modules, {"anthropic": fake_anthropic}):
            result = await ai_summarizer._call_claude("prompt")
        assert result is None


# ---------------------------------------------------------------------------
# Public API: summarize_address_risk
# ---------------------------------------------------------------------------


class TestSummarizeAddressRisk:
    @pytest.mark.asyncio
    async def test_uses_template_when_no_api_key(self):
        from src.analysis import ai_summarizer
        with patch.object(ai_summarizer, "_API_KEY", ""):
            result = await ai_summarizer.summarize_address_risk(
                address="0x1234abcd",
                risk_level="high",
                score=0.65,
                feature_vector={"mixer_usage": 1.0},
            )
        assert result["source"] == "template"
        assert result["model"] is None
        assert len(result["summary"]) > 10

    @pytest.mark.asyncio
    async def test_uses_claude_api_when_key_present(self):
        from src.analysis import ai_summarizer
        with patch.object(ai_summarizer, "_API_KEY", "sk-ant-test"), \
             patch.object(ai_summarizer, "_call_claude", new_callable=AsyncMock,
                          return_value="This is an AI summary."):
            result = await ai_summarizer.summarize_address_risk(
                address="0xabc",
                risk_level="critical",
                score=0.9,
                feature_vector={},
            )
        assert result["source"] == "claude_api"
        assert result["summary"] == "This is an AI summary."

    @pytest.mark.asyncio
    async def test_falls_back_to_template_when_api_fails(self):
        from src.analysis import ai_summarizer
        with patch.object(ai_summarizer, "_API_KEY", "sk-ant-test"), \
             patch.object(ai_summarizer, "_call_claude", new_callable=AsyncMock,
                          return_value=None):
            result = await ai_summarizer.summarize_address_risk(
                address="0xabc",
                risk_level="low",
                score=0.1,
                feature_vector={},
            )
        assert result["source"] == "template"
        assert len(result["summary"]) > 0

    @pytest.mark.asyncio
    async def test_returns_required_keys(self):
        from src.analysis import ai_summarizer
        with patch.object(ai_summarizer, "_API_KEY", ""):
            result = await ai_summarizer.summarize_address_risk(
                address="0xabc",
                risk_level="low",
                score=0.1,
                feature_vector={},
            )
        assert {"summary", "source", "model"} == set(result.keys())


# ---------------------------------------------------------------------------
# Public API: summarize_transaction
# ---------------------------------------------------------------------------


class TestSummarizeTransaction:
    @pytest.mark.asyncio
    async def test_template_fallback(self):
        from src.analysis import ai_summarizer
        with patch.object(ai_summarizer, "_API_KEY", ""):
            result = await ai_summarizer.summarize_transaction(
                tx_hash="0xdeadbeef",
                interaction_type="dex_swap",
                protocol_name="Uniswap",
                risk_level="low",
            )
        assert result["source"] == "template"
        assert "0xdeadbeef" in result["summary"]

    @pytest.mark.asyncio
    async def test_returns_required_keys(self):
        from src.analysis import ai_summarizer
        with patch.object(ai_summarizer, "_API_KEY", ""):
            result = await ai_summarizer.summarize_transaction(
                tx_hash="0xabc",
                interaction_type="transfer",
            )
        assert {"summary", "source", "model"} == set(result.keys())


# ---------------------------------------------------------------------------
# Public API: summarize_cluster
# ---------------------------------------------------------------------------


class TestSummarizeCluster:
    @pytest.mark.asyncio
    async def test_always_template(self):
        from src.analysis.ai_summarizer import summarize_cluster
        result = await summarize_cluster("c1", "mixer", 5, "mixer_usage")
        assert result["source"] == "template"
        assert "c1" in result["summary"]

    @pytest.mark.asyncio
    async def test_none_dominant_feature(self):
        from src.analysis.ai_summarizer import summarize_cluster
        result = await summarize_cluster("c2", "exchange", 10)
        assert len(result["summary"]) > 0
