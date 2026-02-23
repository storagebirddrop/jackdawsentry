"""
Jackdaw Sentry - Computed Risk Scoring
Weighted multi-signal risk score combining sanctions, patterns, mixer, and volume.
"""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional


def compute_risk_score(
    sanctions_hits: int = 0,
    pattern_matches: Optional[List[Dict[str, Any]]] = None,
    mixer_detected: bool = False,
    mixer_risk: float = 0.0,
    volume_anomaly: float = 0.0,
    base_score: float = 0.0,
) -> float:
    """Return a weighted risk score in [0.0, 1.0].

    Weights:
      - Sanctions hit:       0.50 (binary, any hit → full weight)
      - Pattern detection:   0.30 (average pattern risk_score × weight)
      - Mixer usage:         0.20 (mixer_risk capped to weight)
      - Volume anomaly:      additive bonus up to 0.10
    """
    # Sanctions component (weight 0.50)
    sanctions_component = 0.5 if sanctions_hits > 0 else 0.0

    # Pattern component (weight 0.30)
    pattern_component = 0.0
    if pattern_matches:
        pattern_risks = [
            p.get("risk_score", 0.0) for p in pattern_matches if isinstance(p, dict)
        ]
        if pattern_risks:
            avg_pattern_risk = sum(pattern_risks) / len(pattern_risks)
            pattern_component = min(avg_pattern_risk * 0.30, 0.30)

    # Mixer component (weight 0.20)
    mixer_component = 0.0
    if mixer_detected:
        mixer_component = min(mixer_risk * 0.20, 0.20)

    # Volume anomaly bonus (additive, up to 0.10)
    volume_component = min(volume_anomaly * 0.10, 0.10)

    score = sanctions_component + pattern_component + mixer_component + volume_component

    # Blend with base_score (from Neo4j node property) — take the max
    score = max(score, base_score)

    return round(min(score, 1.0), 4)
