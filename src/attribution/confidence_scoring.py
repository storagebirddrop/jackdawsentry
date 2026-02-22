"""
Jackdaw Sentry - Confidence Scoring
Advanced confidence scoring algorithms for entity attribution
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import math

from .models import AttributionSource, AddressAttribution, ConfidenceFactors

logger = logging.getLogger(__name__)


class EvidenceType(str, Enum):
    """Types of evidence that support attribution"""
    TRANSACTION_PATTERN = "transaction_pattern"
    PUBLIC_DISCLOSURE = "public_disclosure"
    REGULATORY_FILING = "regulatory_filing"
    EXCHANGE_API = "exchange_api"
    BLOCKCHAIN_ANALYSIS = "blockchain_analysis"
    CLUSTER_ANALYSIS = "cluster_analysis"
    OFF_CHAIN_INTELLIGENCE = "off_chain_intelligence"
    CROWDSOURCED = "crowdsourced"


@dataclass
class Evidence:
    """Evidence supporting attribution"""
    evidence_type: EvidenceType
    description: str
    confidence_contribution: float
    source_reference: Optional[str] = None
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}


class ConfidenceScorer:
    """Advanced confidence scoring for entity attribution"""
    
    def __init__(self):
        self.weights = {
            'source_reliability': 0.30,
            'evidence_strength': 0.25,
            'corroboration_count': 0.20,
            'recency': 0.15,
            'blockchain_analysis': 0.10
        }
        
        self.evidence_weights = {
            EvidenceType.PUBLIC_DISCLOSURE: 0.95,
            EvidenceType.REGULATORY_FILING: 0.90,
            EvidenceType.EXCHANGE_API: 0.85,
            EvidenceType.BLOCKCHAIN_ANALYSIS: 0.80,
            EvidenceType.CLUSTER_ANALYSIS: 0.75,
            EvidenceType.TRANSACTION_PATTERN: 0.70,
            EvidenceType.OFF_CHAIN_INTELLIGENCE: 0.65,
            EvidenceType.CROWDSOURCED: 0.40
        }
    
    async def calculate_confidence_score(
        self, 
        attribution: AddressAttribution,
        source: AttributionSource,
        evidence: List[Evidence],
        corroborating_attributions: List[AddressAttribution] = None
    ) -> float:
        """Calculate comprehensive confidence score for attribution"""
        
        # Calculate individual factors
        factors = await self._calculate_confidence_factors(
            attribution, source, evidence, corroborating_attributions or []
        )
        
        # Apply weighted scoring
        confidence = (
            factors.source_reliability * self.weights['source_reliability'] +
            factors.evidence_strength * self.weights['evidence_strength'] +
            factors.corroboration_count * self.weights['corroboration_count'] +
            factors.recency_score * self.weights['recency'] +
            factors.blockchain_analysis * self.weights['blockchain_analysis']
        )
        
        # Apply diminishing returns for very high scores
        confidence = self._apply_diminishing_returns(confidence)
        
        # Ensure score is within bounds
        confidence = max(0.0, min(1.0, confidence))
        
        return confidence
    
    async def _calculate_confidence_factors(
        self,
        attribution: AddressAttribution,
        source: AttributionSource,
        evidence: List[Evidence],
        corroborating_attributions: List[AddressAttribution]
    ) -> ConfidenceFactors:
        """Calculate individual confidence factors"""
        
        # Source reliability factor
        source_reliability = source.reliability_score
        
        # Evidence strength factor
        evidence_strength = await self._calculate_evidence_strength(evidence)
        
        # Corroboration factor
        corroboration_count = len(corroborating_attributions)
        corroboration_score = self._calculate_corroboration_score(corroboration_count)
        
        # Recency factor
        recency_score = self._calculate_recency_score(attribution.last_verified)
        
        # Blockchain analysis factor
        blockchain_analysis = await self._calculate_blockchain_confidence(attribution)
        
        # Historical accuracy factor (if available)
        historical_accuracy = await self._calculate_historical_accuracy(source)
        
        return ConfidenceFactors(
            source_reliability=source_reliability,
            evidence_strength=evidence_strength,
            corroboration_count=corroboration_count,
            recency_score=recency_score,
            blockchain_analysis=blockchain_analysis,
            historical_accuracy=historical_accuracy
        )
    
    async def _calculate_evidence_strength(self, evidence: List[Evidence]) -> float:
        """Calculate evidence strength factor"""
        if not evidence:
            return 0.0
        
        weighted_scores = []
        total_weight = 0.0
        
        for ev in evidence:
            weight = self.evidence_weights.get(ev.evidence_type, 0.5)
            score = ev.confidence_contribution * weight
            
            weighted_scores.append(score)
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        # Weighted average
        evidence_strength = sum(weighted_scores) / total_weight
        
        # Boost for multiple evidence types
        diversity_boost = min(0.1, len(set(ev.evidence_type for ev in evidence)) * 0.02)
        
        return min(1.0, evidence_strength + diversity_boost)
    
    def _calculate_corroboration_score(self, corroboration_count: int) -> float:
        """Calculate corroboration score based on number of corroborating sources"""
        if corroboration_count == 0:
            return 0.0
        elif corroboration_count == 1:
            return 0.3
        elif corroboration_count == 2:
            return 0.6
        elif corroboration_count == 3:
            return 0.8
        elif corroboration_count >= 4:
            return 0.95
        else:
            return 0.0
    
    def _calculate_recency_score(self, last_verified: Optional[datetime]) -> float:
        """Calculate recency score based on last verification time"""
        if last_verified is None:
            return 0.5  # Neutral score for unverified attributions
        
        now = datetime.now(timezone.utc)
        age_days = (now - last_verified).days
        
        if age_days <= 7:
            return 1.0
        elif age_days <= 30:
            return 0.9
        elif age_days <= 90:
            return 0.8
        elif age_days <= 180:
            return 0.6
        elif age_days <= 365:
            return 0.4
        else:
            return 0.2
    
    async def _calculate_blockchain_confidence(self, attribution: AddressAttribution) -> float:
        """Calculate blockchain analysis confidence"""
        # This would integrate with actual blockchain analysis
        # For now, return a default based on attribution evidence
        
        if attribution.evidence:
            # Look for blockchain-specific evidence
            blockchain_evidence = [
                ev for ev in attribution.evidence.values() if isinstance(ev, dict)
                and ev.get('type') in ['transaction_pattern', 'cluster_analysis']
            ]
            
            if blockchain_evidence:
                return 0.8
            else:
                return 0.6
        else:
            return 0.5
    
    async def _calculate_historical_accuracy(self, source: AttributionSource) -> float:
        """Calculate historical accuracy for attribution source"""
        # This would track historical accuracy of each source
        # For now, use reliability score as proxy
        return source.reliability_score
    
    def _apply_diminishing_returns(self, confidence: float) -> float:
        """Apply diminishing returns for very high confidence scores"""
        if confidence >= 0.9:
            # Apply logarithmic scaling for very high scores
            return 0.9 + 0.1 * math.log10(1 + (confidence - 0.9) * 10)
        else:
            return confidence
    
    async def batch_calculate_confidence(
        self,
        attributions: List[AddressAttribution],
        sources: Dict[int, AttributionSource],
        evidence_map: Dict[str, List[Evidence]]
    ) -> List[float]:
        """Calculate confidence scores for multiple attributions"""
        
        confidence_scores = []
        
        for attribution in attributions:
            source = sources.get(attribution.attribution_source_id)
            if not source:
                confidence_scores.append(0.0)
                continue
            
            evidence = evidence_map.get(attribution.address, [])
            
            score = await self.calculate_confidence_score(attribution, source, evidence)
            confidence_scores.append(score)
        
        return confidence_scores
    
    def update_weights(self, new_weights: Dict[str, float]):
        """Update confidence scoring weights"""
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError("Weights must sum to approximately 1.0")
        
        self.weights.update(new_weights)
        logger.info(f"Updated confidence scoring weights: {self.weights}")
    
    def get_confidence_explanation(self, factors: ConfidenceFactors) -> Dict[str, str]:
        """Get human-readable explanation of confidence factors"""
        
        explanations = {
            'source_reliability': f"Source reliability: {factors.source_reliability:.2%} (based on historical accuracy)",
            'evidence_strength': f"Evidence strength: {factors.evidence_strength:.2%} (quality and diversity of supporting evidence)",
            'corroboration_count': f"Corroboration: {factors.corroboration_count} corroborating sources",
            'recency_score': f"Recency: {factors.recency_score:.2%} (based on last verification)",
            'blockchain_analysis': f"Blockchain analysis: {factors.blockchain_analysis:.2%} (on-chain pattern confidence)",
            'historical_accuracy': f"Historical accuracy: {factors.historical_accuracy:.2%} (source track record)"
        }
        
        return explanations


# Global confidence scorer instance
_confidence_scorer = None

def get_confidence_scorer() -> ConfidenceScorer:
    """Get the global confidence scorer instance"""
    global _confidence_scorer
    if _confidence_scorer is None:
        _confidence_scorer = ConfidenceScorer()
    return _confidence_scorer
