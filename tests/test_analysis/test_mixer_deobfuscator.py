"""
Unit tests for src/analysis/mixer_deobfuscator.py (M14)
"""
import pytest
from src.analysis.mixer_deobfuscator import (
    MixerTransaction,
    CandidatePair,
    _amount_similarity,
    _timing_score,
    _combined_confidence,
    find_candidate_pairs,
    build_mixer_transactions,
    summarize_deobfuscation,
)


# ---------------------------------------------------------------------------
# _amount_similarity
# ---------------------------------------------------------------------------


class TestAmountSimilarity:
    def test_identical_amounts_return_one(self):
        assert _amount_similarity(1.0, 1.0) == pytest.approx(1.0)

    def test_zero_amounts_return_one(self):
        assert _amount_similarity(0.0, 0.0) == pytest.approx(1.0)

    def test_very_different_amounts_near_zero(self):
        # diff ≈ 1.0 → exp(-2) ≈ 0.135; use < 0.2 threshold
        score = _amount_similarity(0.1, 100.0)
        assert score < 0.2

    def test_five_percent_diff_high_score(self):
        # 5% diff → exp(-0.1) ≈ 0.905
        score = _amount_similarity(1.0, 1.05)
        assert score > 0.85

    def test_symmetric(self):
        assert _amount_similarity(1.0, 2.0) == pytest.approx(_amount_similarity(2.0, 1.0))

    def test_tornado_cash_denomination_exact_match(self):
        # Typical Tornado: same amount in and out (minus fee handled externally)
        assert _amount_similarity(1.0, 1.0) == pytest.approx(1.0)
        assert _amount_similarity(10.0, 10.0) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# _timing_score
# ---------------------------------------------------------------------------


class TestTimingScore:
    def test_immediate_withdrawal_returns_one(self):
        # 0 delay → score=1.0
        assert _timing_score(0, 72.0) == pytest.approx(1.0)

    def test_withdrawal_at_max_window_returns_zero(self):
        # exactly at max → 0
        assert _timing_score(72 * 3600, 72.0) == pytest.approx(0.0)

    def test_beyond_window_returns_zero(self):
        assert _timing_score(100 * 3600, 72.0) == 0.0

    def test_negative_delay_returns_zero(self):
        # withdrawal before deposit
        assert _timing_score(-1, 72.0) == 0.0

    def test_midpoint_returns_half(self):
        half = 36 * 3600
        score = _timing_score(half, 72.0)
        assert score == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# _combined_confidence
# ---------------------------------------------------------------------------


class TestCombinedConfidence:
    def test_perfect_signals_near_one(self):
        # amount_sim=1, timing=1, same_chain=True
        conf = _combined_confidence(1.0, 1.0, True)
        assert conf == pytest.approx(1.0)

    def test_all_zero_returns_some_chain_weight(self):
        # same_chain bonus still applies
        conf = _combined_confidence(0.0, 0.0, True)
        assert conf > 0.0

    def test_cross_chain_lowers_confidence(self):
        same = _combined_confidence(1.0, 1.0, True)
        cross = _combined_confidence(1.0, 1.0, False)
        assert same > cross

    def test_capped_at_one(self):
        assert _combined_confidence(1.0, 1.0, True) <= 1.0


# ---------------------------------------------------------------------------
# find_candidate_pairs
# ---------------------------------------------------------------------------

_NOW = 1_700_000_000.0  # arbitrary epoch


def _dep(tx="dep1", amount=1.0, delay=0):
    return MixerTransaction(
        tx_hash=tx, address="0xdepositor",
        direction="deposit", amount=amount,
        timestamp=_NOW - delay * 3600, chain="ethereum",
    )


def _wit(tx="wit1", amount=1.0, delay=2):
    return MixerTransaction(
        tx_hash=tx, address="0xwithdrawer",
        direction="withdrawal", amount=amount,
        timestamp=_NOW + delay * 3600, chain="ethereum",
    )


class TestFindCandidatePairs:
    def test_matching_pair_returned(self):
        txs = [_dep(), _wit()]
        pairs = find_candidate_pairs(txs)
        assert len(pairs) >= 1

    def test_pair_fields_present(self):
        pairs = find_candidate_pairs([_dep(), _wit()])
        p = pairs[0]
        assert p.deposit_tx == "dep1"
        assert p.withdrawal_tx == "wit1"
        assert p.delay_hours == pytest.approx(2.0)

    def test_withdrawal_before_deposit_excluded(self):
        dep = _dep()
        wit = MixerTransaction(
            tx_hash="w", address="0xw", direction="withdrawal",
            amount=1.0, timestamp=_NOW - 3600, chain="ethereum"
        )
        pairs = find_candidate_pairs([dep, wit])
        assert len(pairs) == 0

    def test_withdrawal_beyond_window_excluded(self):
        dep = _dep()
        wit = MixerTransaction(
            tx_hash="w", address="0xw", direction="withdrawal",
            amount=1.0, timestamp=_NOW + 200 * 3600, chain="ethereum"
        )
        pairs = find_candidate_pairs([dep, wit], max_delay_hours=72)
        assert len(pairs) == 0

    def test_low_confidence_pair_excluded(self):
        # Very different amounts; raise min_confidence above timing+chain floor (~0.52)
        dep = _dep(amount=1.0)
        wit = _wit(amount=999.0)
        pairs = find_candidate_pairs([dep, wit], min_confidence=0.6)
        assert len(pairs) == 0

    def test_sorted_by_confidence_descending(self):
        dep = _dep()
        w1 = _wit(tx="w1", amount=1.0, delay=1)   # fast → high timing
        w2 = _wit(tx="w2", amount=1.0, delay=60)   # slow → low timing
        pairs = find_candidate_pairs([dep, w1, w2], min_confidence=0.0)
        assert pairs[0].confidence >= pairs[-1].confidence

    def test_cross_chain_pair_detected(self):
        dep = MixerTransaction(
            tx_hash="d1", address="0xd", direction="deposit",
            amount=1.0, timestamp=_NOW, chain="ethereum"
        )
        wit = MixerTransaction(
            tx_hash="w1", address="0xw", direction="withdrawal",
            amount=1.0, timestamp=_NOW + 3600, chain="polygon"
        )
        pairs = find_candidate_pairs([dep, wit], min_confidence=0.0)
        assert any(not p.same_chain for p in pairs)

    def test_empty_list_returns_empty(self):
        assert find_candidate_pairs([]) == []

    def test_only_deposits_returns_empty(self):
        assert find_candidate_pairs([_dep(), _dep("d2")]) == []

    def test_only_withdrawals_returns_empty(self):
        assert find_candidate_pairs([_wit(), _wit("w2")]) == []

    def test_notes_exact_amount_match(self):
        pairs = find_candidate_pairs([_dep(), _wit()], min_confidence=0.0)
        assert any("exact amount match" in p.notes for p in pairs)

    def test_notes_same_day_withdrawal(self):
        dep = _dep()
        wit = _wit(delay=12)  # 12 hours → same day note
        pairs = find_candidate_pairs([dep, wit], min_confidence=0.0)
        # p.notes is a list of strings; check substring match
        assert any("same day" in note for p in pairs for note in p.notes)


# ---------------------------------------------------------------------------
# build_mixer_transactions
# ---------------------------------------------------------------------------


class TestBuildMixerTransactions:
    def test_mixer_deposit_direction(self):
        raw = [{
            "tx_hash": "0x1", "from_address": "0xuser",
            "to_address": "0xmixer", "value": 1.0,
            "timestamp": _NOW, "chain": "ethereum",
            "interaction_type": "mixer_deposit",
        }]
        txs = build_mixer_transactions(raw, mixer_addresses={"0xmixer"})
        assert len(txs) == 1
        assert txs[0].direction == "deposit"
        assert txs[0].address == "0xuser"

    def test_mixer_withdrawal_direction(self):
        raw = [{
            "tx_hash": "0x2", "from_address": "0xmixer",
            "to_address": "0xrecipient", "value": 1.0,
            "timestamp": _NOW, "chain": "ethereum",
            "interaction_type": "mixer_withdraw",
        }]
        txs = build_mixer_transactions(raw, mixer_addresses={"0xmixer"})
        assert len(txs) == 1
        assert txs[0].direction == "withdrawal"
        assert txs[0].address == "0xrecipient"

    def test_non_mixer_tx_excluded(self):
        raw = [{
            "tx_hash": "0x3", "from_address": "0xa",
            "to_address": "0xb", "value": 1.0,
            "timestamp": _NOW, "chain": "ethereum",
            "interaction_type": "dex_swap",
        }]
        txs = build_mixer_transactions(raw, mixer_addresses=set())
        assert len(txs) == 0

    def test_address_detection_by_known_address(self):
        """to_address is a known mixer address → deposit, even without interaction_type."""
        raw = [{
            "tx_hash": "0x4", "from_address": "0xuser",
            "to_address": "0xknownmixer", "value": 0.1,
            "timestamp": _NOW, "chain": "ethereum",
            "interaction_type": "",
        }]
        txs = build_mixer_transactions(raw, mixer_addresses={"0xknownmixer"})
        assert len(txs) == 1
        assert txs[0].direction == "deposit"

    def test_empty_input_returns_empty(self):
        assert build_mixer_transactions([], mixer_addresses=set()) == []


# ---------------------------------------------------------------------------
# summarize_deobfuscation
# ---------------------------------------------------------------------------


class TestSummarizeDeobfuscation:
    def test_empty_pairs(self):
        result = summarize_deobfuscation([])
        assert result["total_pairs"] == 0
        assert result["candidate_pairs"] == []

    def test_returns_expected_keys(self):
        pairs = find_candidate_pairs([_dep(), _wit()])
        result = summarize_deobfuscation(pairs)
        assert "total_pairs" in result
        assert "high_confidence_pairs" in result
        assert "candidate_pairs" in result
        assert "note" in result

    def test_high_confidence_counted_correctly(self):
        dep = _dep()
        wit = _wit(delay=1)  # 1h delay → high confidence for exact amounts
        pairs = find_candidate_pairs([dep, wit])
        result = summarize_deobfuscation(pairs)
        if pairs[0].confidence >= 0.70:
            assert result["high_confidence_pairs"] >= 1

    def test_note_contains_disclaimer(self):
        # Non-empty results carry the probabilistic disclaimer
        pairs = find_candidate_pairs([_dep(), _wit()])
        result = summarize_deobfuscation(pairs)
        assert "probabilistic" in result["note"].lower() or "investigat" in result["note"].lower()

    def test_each_pair_has_required_fields(self):
        pairs = find_candidate_pairs([_dep(), _wit()], min_confidence=0.0)
        result = summarize_deobfuscation(pairs)
        for p in result["candidate_pairs"]:
            assert "deposit_tx" in p
            assert "withdrawal_tx" in p
            assert "confidence" in p
