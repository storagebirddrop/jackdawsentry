"""
Tests for pattern detection algorithms
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from src.patterns.algorithms.peeling_chain import PeelingChainDetector, Transaction
from src.patterns.algorithms.remaining_patterns import (
    CustodyChangeDetector, SynchronizedTransferDetector, 
    OffPeakActivityDetector, RoundAmountDetector
)
from src.patterns.models import PatternResult, PatternSeverity


class TestPeelingChainDetector:
    """Test cases for PeelingChainDetector"""
    
    @pytest.fixture
    def detector(self):
        """Create peeling chain detector instance"""
        return PeelingChainDetector()
    
    @pytest.fixture
    def sample_transactions(self):
        """Create sample transactions for peeling chain"""
        base_time = datetime.now(timezone.utc)
        
        return [
            Transaction(
                hash="0x1",
                address="0x1234567890123456789012345678901234567890",
                amount=1.0,
                timestamp=base_time,
                recipient="0x1111111111111111111111111111111111111111",
                sender="0x1234567890123456789012345678901234567890",
                blockchain="ethereum"
            ),
            Transaction(
                hash="0x2",
                address="0x1234567890123456789012345678901234567890",
                amount=0.5,
                timestamp=base_time + timedelta(hours=1),
                recipient="0x2222222222222222222222222222222222222222",
                sender="0x1234567890123456789012345678901234567890",
                blockchain="ethereum"
            ),
            Transaction(
                hash="0x3",
                address="0x1234567890123456789012345678901234567890",
                amount=0.25,
                timestamp=base_time + timedelta(hours=2),
                recipient="0x3333333333333333333333333333333333333333",
                sender="0x1234567890123456789012345678901234567890",
                blockchain="ethereum"
            ),
            Transaction(
                hash="0x4",
                address="0x1234567890123456789012345678901234567890",
                amount=0.125,
                timestamp=base_time + timedelta(hours=3),
                recipient="0x4444444444444444444444444444444444444444",
                sender="0x1234567890123456789012345678901234567890",
                blockchain="ethereum"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_detect_peeling_chain_success(self, detector, sample_transactions):
        """Test successful peeling chain detection"""
        
        result = await detector.detect_peeling_chain(
            transactions=sample_transactions,
            address="0x1234567890123456789012345678901234567890"
        )
        
        assert result.detected is True
        assert result.pattern_id == "peeling_chain"
        assert result.confidence_score > 0.5
        assert result.severity in [PatternSeverity.HIGH, PatternSeverity.CRITICAL]
        assert len(result.indicators_met) > 0
        assert result.transaction_count >= 3
    
    @pytest.mark.asyncio
    async def test_detect_peeling_chain_insufficient_transactions(self, detector):
        """Test peeling chain detection with insufficient transactions"""
        
        transactions = [
            Transaction(
                hash="0x1",
                address="0x1234567890123456789012345678901234567890",
                amount=1.0,
                timestamp=datetime.now(timezone.utc),
                recipient="0x1111111111111111111111111111111111111111",
                sender="0x1234567890123456789012345678901234567890",
                blockchain="ethereum"
            )
        ]
        
        result = await detector.detect_peeling_chain(
            transactions=transactions,
            address="0x1234567890123456789012345678901234567890"
        )
        
        assert result.detected is False
        assert result.confidence_score == 0.0
        assert "Insufficient transactions" in result.metadata.get("detection_reason", "")
    
    @pytest.mark.asyncio
    async def test_detect_peeling_chain_no_pattern(self, detector):
        """Test peeling chain detection with no pattern"""
        
        # Create transactions that don't form a peeling chain
        base_time = datetime.now(timezone.utc)
        transactions = [
            Transaction(
                hash="0x1",
                address="0x1234567890123456789012345678901234567890",
                amount=1.0,
                timestamp=base_time,
                recipient="0x1111111111111111111111111111111111111111",
                sender="0x1234567890123456789012345678901234567890",
                blockchain="ethereum"
            ),
            Transaction(
                hash="0x2",
                address="0x1234567890123456789012345678901234567890",
                amount=1.5,  # Increasing amount, not peeling
                timestamp=base_time + timedelta(hours=1),
                recipient="0x2222222222222222222222222222222222222222",
                sender="0x1234567890123456789012345678901234567890",
                blockchain="ethereum"
            )
        ]
        
        result = await detector.detect_peeling_chain(
            transactions=transactions,
            address="0x1234567890123456789012345678901234567890"
        )
        
        assert result.detected is False
        assert result.confidence_score == 0.0
    
    def test_is_peeling_step(self, detector):
        """Test peeling step detection logic"""
        
        base_time = datetime.now(timezone.utc)
        
        prev_tx = Transaction(
            hash="0x1",
            address="0x1234567890123456789012345678901234567890",
            amount=1.0,
            timestamp=base_time,
            recipient="0x1111111111111111111111111111111111111111",
            sender="0x1234567890123456789012345678901234567890",
            blockchain="ethereum"
        )
        
        # Valid peeling step
        curr_tx = Transaction(
            hash="0x2",
            address="0x1234567890123456789012345678901234567890",
            amount=0.5,  # 50% decrease
            timestamp=base_time + timedelta(hours=1),
            recipient="0x2222222222222222222222222222222222222222",
            sender="0x1234567890123456789012345678901234567890",
            blockchain="ethereum"
        )
        
        assert detector._is_peeling_step(prev_tx, curr_tx) is True
        
        # Invalid peeling step (same recipient)
        curr_tx_same_recipient = Transaction(
            hash="0x3",
            address="0x1234567890123456789012345678901234567890",
            amount=0.5,
            timestamp=base_time + timedelta(hours=1),
            recipient="0x1111111111111111111111111111111111111111",  # Same recipient
            sender="0x1234567890123456789012345678901234567890",
            blockchain="ethereum"
        )
        
        assert detector._is_peeling_step(prev_tx, curr_tx_same_recipient) is False


class TestCustodyChangeDetector:
    """Test cases for CustodyChangeDetector"""
    
    @pytest.fixture
    def detector(self):
        """Create custody change detector instance"""
        return CustodyChangeDetector()
    
    @pytest.mark.asyncio
    async def test_detect_custody_change_insufficient_transactions(self, detector):
        """Test custody change detection with insufficient transactions"""
        
        transactions = []  # Empty list
        
        result = await detector.detect_custody_change(
            transactions=transactions,
            address="0x1234567890123456789012345678901234567890"
        )
        
        assert result.detected is False
        assert result.confidence_score == 0.0
        assert "Insufficient transactions" in result.metadata.get("detection_reason", "")


class TestSynchronizedTransferDetector:
    """Test cases for SynchronizedTransferDetector"""
    
    @pytest.fixture
    def detector(self):
        """Create synchronized transfer detector instance"""
        return SynchronizedTransferDetector()
    
    @pytest.mark.asyncio
    async def test_detect_synchronized_transfers_insufficient_transactions(self, detector):
        """Test synchronized transfer detection with insufficient transactions"""
        
        transactions = []  # Empty list
        
        result = await detector.detect_synchronized_transfers(
            transactions=transactions,
            address="0x1234567890123456789012345678901234567890"
        )
        
        assert result.detected is False
        assert result.confidence_score == 0.0
        assert "Insufficient transactions" in result.metadata.get("detection_reason", "")


class TestOffPeakActivityDetector:
    """Test cases for OffPeakActivityDetector"""
    
    @pytest.fixture
    def detector(self):
        """Create off-peak activity detector instance"""
        return OffPeakActivityDetector()
    
    @pytest.mark.asyncio
    async def test_detect_off_peak_activity_insufficient_transactions(self, detector):
        """Test off-peak activity detection with insufficient transactions"""
        
        transactions = []  # Empty list
        
        result = await detector.detect_off_peak_activity(
            transactions=transactions,
            address="0x1234567890123456789012345678901234567890"
        )
        
        assert result.detected is False
        assert result.confidence_score == 0.0
        assert "Insufficient transactions" in result.metadata.get("detection_reason", "")


class TestRoundAmountDetector:
    """Test cases for RoundAmountDetector"""
    
    @pytest.fixture
    def detector(self):
        """Create round amount detector instance"""
        return RoundAmountDetector()
    
    @pytest.mark.asyncio
    async def test_detect_round_amounts_insufficient_transactions(self, detector):
        """Test round amount detection with insufficient transactions"""
        
        transactions = []  # Empty list
        
        result = await detector.detect_round_amounts(
            transactions=transactions,
            address="0x1234567890123456789012345678901234567890"
        )
        
        assert result.detected is False
        assert result.confidence_score == 0.0
        assert "Insufficient transactions" in result.metadata.get("detection_reason", "")
    
    def test_is_round_amount(self, detector):
        """Test round amount detection logic"""
        
        # Test exact round amounts
        assert detector._is_round_amount(1.0) is True
        assert detector._is_round_amount(10.0) is True
        assert detector._is_round_amount(100.0) is True
        
        # Test amounts within tolerance
        assert detector._is_round_amount(1.02) is True  # Within 5% of 1.0
        assert detector._is_round_amount(0.98) is True  # Within 5% of 1.0
        
        # Test amounts outside tolerance
        assert detector._is_round_amount(1.1) is False   # Outside 5% of 1.0
        assert detector._is_round_amount(0.9) is False   # Outside 5% of 1.0
        
        # Test non-round amounts
        assert detector._is_round_amount(1.37) is False
        assert detector._is_round_amount(7.23) is False


@pytest.mark.asyncio
async def test_algorithms_integration():
    """Integration test for all pattern algorithms"""
    
    # Mapping of detector classes to their detection methods
    detector_methods = {
        PeelingChainDetector: 'detect_peeling_chain',
        CustodyChangeDetector: 'detect_custody_change',
        SynchronizedTransferDetector: 'detect_synchronized_transfers',
        OffPeakActivityDetector: 'detect_off_peak_activity',
        RoundAmountDetector: 'detect_round_amounts'
    }
    
    base_time = datetime.now(timezone.utc)
    sample_transactions = [
        Transaction(
            hash="0x1",
            address="0x1234567890123456789012345678901234567890",
            amount=1.0,
            timestamp=base_time,
            recipient="0x1111111111111111111111111111111111111111",
            sender="0x1234567890123456789012345678901234567890",
            blockchain="ethereum"
        )
    ]
    
    for detector_class, method_name in detector_methods.items():
        detector = detector_class()
        # Test with insufficient transactions (should return empty result)
        method = getattr(detector, method_name)
        result = await method(
            transactions=sample_transactions[:1],  # Only 1 transaction
            address="0x1234567890123456789012345678901234567890"
        )
        
        assert isinstance(result, PatternResult)
        assert result.pattern_id is not None
        assert result.pattern_name is not None
