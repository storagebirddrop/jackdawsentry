"""
Jackdaw Sentry - Analysis Router
Blockchain transaction analysis endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, field_validator
import asyncio
import logging
import time as _time

from src.api.auth import User, check_permissions, PERMISSIONS
from src.api.database import get_neo4j_session, get_postgres_connection
from src.api.exceptions import JackdawException
from src.analysis.pattern_detection import MLPatternDetector
from src.analysis.mixer_detection import MixerDetector
from src.analysis.cross_chain import CrossChainAnalyzer
from src.analysis.risk_scoring import compute_risk_score

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy singletons for analysis engines
_pattern_detector: Optional[MLPatternDetector] = None
_mixer_detector: Optional[MixerDetector] = None
_cross_chain_analyzer: Optional[CrossChainAnalyzer] = None


def _get_pattern_detector() -> MLPatternDetector:
    global _pattern_detector
    if _pattern_detector is None:
        _pattern_detector = MLPatternDetector()
    return _pattern_detector


def _get_mixer_detector() -> MixerDetector:
    global _mixer_detector
    if _mixer_detector is None:
        _mixer_detector = MixerDetector()
    return _mixer_detector


def _get_cross_chain_analyzer() -> CrossChainAnalyzer:
    global _cross_chain_analyzer
    if _cross_chain_analyzer is None:
        _cross_chain_analyzer = CrossChainAnalyzer()
    return _cross_chain_analyzer


# Pydantic models
class AddressAnalysisRequest(BaseModel):
    address: str
    blockchain: str
    depth: int = 3
    include_tokens: bool = True
    time_range: Optional[int] = None  # days
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Address cannot be empty')
        return v.strip()

    @field_validator('blockchain')
    @classmethod
    def validate_blockchain(cls, v):
        supported = ['bitcoin', 'ethereum', 'bsc', 'polygon', 'arbitrum', 'base',
                    'avalanche', 'solana', 'tron', 'xrpl', 'stellar']
        if v.lower() not in supported:
            raise ValueError(f'Unsupported blockchain: {v}')
        return v.lower()

    @field_validator('depth')
    @classmethod
    def validate_depth(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Depth must be between 1 and 10')
        return v


class TransactionAnalysisRequest(BaseModel):
    transaction_hash: str
    blockchain: str
    include_detailed_trace: bool = False
    
    @field_validator('transaction_hash')
    @classmethod
    def validate_hash(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Transaction hash cannot be empty')
        return v.strip()


class RiskScoreRequest(BaseModel):
    addresses: List[str]
    blockchain: str
    analysis_type: str = "standard"  # standard, enhanced, forensic
    
    @field_validator('addresses')
    @classmethod
    def validate_addresses(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one address must be provided')
        if len(v) > 100:
            raise ValueError('Maximum 100 addresses allowed per request')
        return [addr.strip() for addr in v if addr.strip()]


class AnalysisResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime


# Endpoints
@router.post("/address", response_model=AnalysisResponse)
async def analyze_address(
    request: AddressAnalysisRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]]))
):
    """Analyze blockchain address for transaction patterns and risk assessment"""
    try:
        start = _time.monotonic()
        logger.info(f"Starting address analysis for {request.address} on {request.blockchain}")

        analysis_data = {
            "address": request.address,
            "blockchain": request.blockchain,
        }

        async with get_neo4j_session() as session:
            # Get address node and basic stats
            addr_result = await session.run(
                """
                OPTIONAL MATCH (a:Address {address: $address, blockchain: $blockchain})
                OPTIONAL MATCH (a)-[t:SENT|RECEIVED]-()
                RETURN a,
                       count(t) AS tx_count,
                       min(t.timestamp) AS first_seen,
                       max(t.timestamp) AS last_seen,
                       sum(CASE WHEN t.value IS NOT NULL THEN t.value ELSE 0 END) AS total_value,
                       collect(DISTINCT labels(a)) AS addr_labels
                """,
                address=request.address,
                blockchain=request.blockchain,
            )
            record = await addr_result.single()

            if record and record["a"]:
                analysis_data["transaction_count"] = record["tx_count"]
                analysis_data["total_value"] = float(record["total_value"] or 0)
                analysis_data["first_seen"] = record["first_seen"]
                analysis_data["last_seen"] = record["last_seen"]
                node_props = dict(record["a"])
                analysis_data["labels"] = node_props.get("labels", [])
                analysis_data["risk_score"] = node_props.get("risk_score", 0.0)
            else:
                # Address not in Neo4j yet — query RPC directly for live data
                analysis_data["transaction_count"] = 0
                analysis_data["total_value"] = 0.0
                analysis_data["first_seen"] = None
                analysis_data["last_seen"] = None
                analysis_data["labels"] = []
                analysis_data["risk_score"] = 0.0
                try:
                    from src.collectors.rpc.factory import get_rpc_client
                    rpc = get_rpc_client(request.blockchain)
                    if rpc:
                        addr_info = await rpc.get_address_info(request.address)
                        if addr_info:
                            analysis_data["transaction_count"] = addr_info.transaction_count or 0
                            analysis_data["total_value"] = float(addr_info.balance or 0)
                            analysis_data["labels"] = [addr_info.type] if addr_info.type else []
                            analysis_data["source"] = "live_rpc"
                except Exception as _rpc_err:
                    logger.warning(f"Live RPC fallback failed for {request.address}: {_rpc_err}")

            # Connected addresses (up to depth)
            # Neo4j 5 does not allow parameter substitution in relationship depth bounds,
            # so the depth literal is interpolated directly (it's an integer, safe to inline).
            _depth = max(1, min(int(request.depth), 10))
            conn_result = await session.run(
                f"""
                MATCH (a:Address {{address: $address, blockchain: $blockchain}})
                      -[:SENT|RECEIVED*1..{_depth}]-(connected:Address)
                RETURN DISTINCT connected.address AS addr LIMIT 50
                """,
                address=request.address,
                blockchain=request.blockchain,
            )
            conn_records = await conn_result.data()
            analysis_data["connected_addresses"] = [r["addr"] for r in conn_records]

        # Engine enrichment (graceful degradation on any failure)
        pattern_results: List[Dict[str, Any]] = []
        mixer_detected = False
        mixer_risk = 0.0
        try:
            patterns = await _get_pattern_detector().detect_patterns(
                request.address, request.blockchain
            )
            pattern_results = [
                {
                    "pattern_type": p.pattern_type.value,
                    "confidence": p.confidence,
                    "risk_score": p.risk_score,
                    "severity": p.severity,
                    "description": p.description,
                }
                for p in patterns
            ]
        except Exception as exc:
            logger.debug(f"Pattern detection skipped: {exc}")

        try:
            mixer_analysis = await _get_mixer_detector().detect_mixer_usage(
                request.address, request.blockchain
            )
            mixer_detected = mixer_analysis.is_mixer_user
            mixer_risk = mixer_analysis.risk_score
        except Exception as exc:
            logger.debug(f"Mixer detection skipped: {exc}")

        base_score = float(analysis_data.get("risk_score") or 0.0)
        computed_risk = compute_risk_score(
            pattern_matches=pattern_results,
            mixer_detected=mixer_detected,
            mixer_risk=mixer_risk,
            base_score=base_score,
        )
        analysis_data["risk_score"] = computed_risk
        analysis_data["detected_patterns"] = pattern_results
        analysis_data["mixer_detected"] = mixer_detected

        elapsed_ms = int((_time.monotonic() - start) * 1000)
        metadata = {
            "analysis_depth": request.depth,
            "include_tokens": request.include_tokens,
            "processing_time_ms": elapsed_ms,
            "data_sources": ["neo4j", "pattern_engine", "mixer_engine"],
        }

        return AnalysisResponse(
            success=True,
            data=analysis_data,
            metadata=metadata,
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Address analysis failed: {e}")
        raise JackdawException(
            message=f"Address analysis failed: {str(e)}",
            error_code="ANALYSIS_FAILED",
        )


@router.post("/transaction", response_model=AnalysisResponse)
async def analyze_transaction(
    request: TransactionAnalysisRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]]))
):
    """Analyze individual transaction for compliance risks"""
    try:
        start = _time.monotonic()
        logger.info(f"Analyzing transaction {request.transaction_hash} on {request.blockchain}")

        analysis_data = {
            "transaction_hash": request.transaction_hash,
            "blockchain": request.blockchain,
        }

        async with get_neo4j_session() as session:
            tx_result = await session.run(
                """
                OPTIONAL MATCH (t:Transaction {hash: $hash, blockchain: $blockchain})
                OPTIONAL MATCH (from_addr:Address)-[:SENT]->(t)
                OPTIONAL MATCH (t)-[:RECEIVED]->(to_addr:Address)
                RETURN t, from_addr.address AS from_address, to_addr.address AS to_address
                """,
                hash=request.transaction_hash,
                blockchain=request.blockchain,
            )
            record = await tx_result.single()

            if record and record["t"]:
                tx_props = dict(record["t"])
                analysis_data["from_address"] = record["from_address"]
                analysis_data["to_address"] = record["to_address"]
                analysis_data["value"] = tx_props.get("value", 0)
                analysis_data["gas_used"] = tx_props.get("gas_used")
                analysis_data["gas_price"] = tx_props.get("gas_price")
                analysis_data["timestamp"] = tx_props.get("timestamp")
                analysis_data["risk_indicators"] = tx_props.get("risk_indicators", [])
                analysis_data["compliance_flags"] = tx_props.get("compliance_flags", [])
                analysis_data["sanctions_check"] = tx_props.get("sanctions_check", "clear")
            else:
                analysis_data["from_address"] = None
                analysis_data["to_address"] = None
                analysis_data["value"] = 0
                analysis_data["risk_indicators"] = []
                analysis_data["compliance_flags"] = []
                analysis_data["sanctions_check"] = "unknown"
                analysis_data["note"] = "Transaction not found in database"

            if request.include_detailed_trace and record and record["t"]:
                trace_result = await session.run(
                    """
                    MATCH path = (src:Address)-[:SENT|RECEIVED*1..5]->(dst:Address)
                    WHERE any(r IN relationships(path) WHERE r.hash = $hash)
                    RETURN [n IN nodes(path) WHERE n:Address | n.address] AS addresses,
                           length(path) AS path_length
                    LIMIT 1
                    """,
                    hash=request.transaction_hash,
                )
                trace_record = await trace_result.single()
                if trace_record:
                    analysis_data["trace"] = {
                        "path_length": trace_record["path_length"],
                        "intermediate_addresses": trace_record["addresses"],
                    }

        # Cross-chain analysis enrichment (graceful degradation)
        cross_chain_flags: List[str] = []
        try:
            cc_result = await _get_cross_chain_analyzer().analyze_transaction(
                request.transaction_hash, request.blockchain
            )
            if cc_result and cc_result.patterns:
                cross_chain_flags = [p.value for p in cc_result.patterns]
                if not analysis_data.get("value"):
                    analysis_data["value"] = cc_result.amount
        except Exception as exc:
            logger.debug(f"Cross-chain analysis skipped: {exc}")

        analysis_data["cross_chain_flags"] = cross_chain_flags

        elapsed_ms = int((_time.monotonic() - start) * 1000)
        metadata = {
            "include_detailed_trace": request.include_detailed_trace,
            "processing_time_ms": elapsed_ms,
            "data_sources": ["neo4j", "cross_chain_engine"],
        }

        return AnalysisResponse(
            success=True,
            data=analysis_data,
            metadata=metadata,
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Transaction analysis failed: {e}")
        raise JackdawException(
            message=f"Transaction analysis failed: {str(e)}",
            error_code="TRANSACTION_ANALYSIS_FAILED",
        )


@router.post("/risk-score", response_model=AnalysisResponse)
async def calculate_risk_scores(
    request: RiskScoreRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]]))
):
    """Calculate risk scores for multiple addresses from Neo4j"""
    try:
        start = _time.monotonic()
        logger.info(f"Calculating risk scores for {len(request.addresses)} addresses")

        risk_scores = {}
        high = medium = low = 0
        total_score = 0.0

        async with get_neo4j_session() as session:
            result = await session.run(
                """
                UNWIND $addresses AS addr
                OPTIONAL MATCH (a:Address {address: addr, blockchain: $blockchain})
                OPTIONAL MATCH (a)-[t:SENT|RECEIVED]-()
                OPTIONAL MATCH (s:SanctionEntry {address: addr})
                RETURN addr AS address,
                       a.risk_score AS risk_score,
                       count(DISTINCT t) AS tx_count,
                       count(DISTINCT s) AS sanctions_hits
                """,
                addresses=request.addresses,
                blockchain=request.blockchain,
            )
            records = await result.data()

            for record in records:
                addr = record["address"]
                score = float(record["risk_score"] or 0.0) if record["risk_score"] is not None else 0.0
                tx_count = record["tx_count"]
                sanctions_hits = record["sanctions_hits"]

                # Adjust score if sanctions hits
                if sanctions_hits > 0:
                    score = min(1.0, score + 0.5)

                if score >= 0.7:
                    rec = "block"
                    high += 1
                elif score >= 0.4:
                    rec = "enhanced_review"
                    medium += 1
                else:
                    rec = "monitor"
                    low += 1

                total_score += score
                risk_scores[addr] = {
                    "overall_score": round(score, 4),
                    "transaction_count": tx_count,
                    "sanctions_hits": sanctions_hits,
                    "recommendation": rec,
                }

        avg_score = round(total_score / max(len(request.addresses), 1), 4)
        elapsed_ms = int((_time.monotonic() - start) * 1000)

        analysis_data = {
            "addresses": risk_scores,
            "summary": {
                "high_risk_count": high,
                "medium_risk_count": medium,
                "low_risk_count": low,
                "average_risk_score": avg_score,
            },
            "analysis_type": request.analysis_type,
        }

        metadata = {
            "total_addresses": len(request.addresses),
            "analysis_type": request.analysis_type,
            "processing_time_ms": elapsed_ms,
            "data_sources": ["neo4j"],
        }

        return AnalysisResponse(
            success=True,
            data=analysis_data,
            metadata=metadata,
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Risk scoring failed: {e}")
        raise JackdawException(
            message=f"Risk scoring failed: {str(e)}",
            error_code="RISK_SCORING_FAILED",
        )


@router.get("/patterns/{blockchain}")
async def get_transaction_patterns(
    blockchain: str,
    time_range: int = 30,  # days
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]]))
):
    """Get common transaction patterns for a blockchain from Neo4j"""
    try:
        logger.info(f"Getting transaction patterns for {blockchain}")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=time_range)).isoformat()

        patterns = {}
        async with get_neo4j_session() as session:
            # Amount statistics
            amt_result = await session.run(
                """
                MATCH (t:Transaction {blockchain: $blockchain})
                WHERE t.timestamp >= $cutoff
                RETURN avg(t.value) AS avg_amount,
                       percentileDisc(t.value, 0.5) AS median_amount,
                       count(t) AS tx_count
                """,
                blockchain=blockchain,
                cutoff=cutoff,
            )
            amt_record = await amt_result.single()
            patterns["amount_patterns"] = {
                "average_amount": float(amt_record["avg_amount"] or 0) if amt_record else 0,
                "median_amount": float(amt_record["median_amount"] or 0) if amt_record else 0,
                "transaction_count": amt_record["tx_count"] if amt_record else 0,
            }

            # Hub addresses (most connected, within time range)
            hub_result = await session.run(
                """
                MATCH (a:Address {blockchain: $blockchain})-[r:SENT|RECEIVED]-()
                WHERE r.timestamp >= $cutoff
                RETURN a.address AS addr, count(r) AS degree
                ORDER BY degree DESC LIMIT 10
                """,
                blockchain=blockchain,
                cutoff=cutoff,
            )
            hub_records = await hub_result.data()
            patterns["network_patterns"] = {
                "hub_addresses": [{"address": r["addr"], "connections": r["degree"]} for r in hub_records],
            }

        return {
            "success": True,
            "blockchain": blockchain,
            "time_range_days": time_range,
            "patterns": patterns,
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Pattern analysis failed: {e}")
        raise JackdawException(
            message=f"Pattern analysis failed: {str(e)}",
            error_code="PATTERN_ANALYSIS_FAILED",
        )


@router.get("/statistics")
async def get_analysis_statistics(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]]))
):
    """Get analysis system statistics aggregated from Neo4j"""
    try:
        start = _time.perf_counter()
        stats = {}
        async with get_neo4j_session() as session:
            # Total addresses and transactions
            count_result = await session.run(
                """
                OPTIONAL MATCH (a:Address)
                WITH count(a) AS addr_count
                OPTIONAL MATCH (t:Transaction)
                RETURN addr_count, count(t) AS tx_count
                """
            )
            count_record = await count_result.single()
            stats["total_addresses"] = count_record["addr_count"] if count_record else 0
            stats["total_transactions"] = count_record["tx_count"] if count_record else 0

            # Blockchain distribution
            dist_result = await session.run(
                """
                MATCH (a:Address)
                RETURN a.blockchain AS blockchain, count(a) AS count
                ORDER BY count DESC
                """
            )
            dist_records = await dist_result.data()
            stats["blockchain_distribution"] = {r["blockchain"]: r["count"] for r in dist_records if r["blockchain"]}

            # Risk distribution
            risk_result = await session.run(
                """
                MATCH (a:RiskAssessment)
                RETURN a.risk_level AS level, count(a) AS count
                """
            )
            risk_records = await risk_result.data()
            stats["risk_distribution"] = {r["level"]: r["count"] for r in risk_records if r["level"]}

        processing_time_ms = int((_time.perf_counter() - start) * 1000)

        return {
            "success": True,
            "statistics": stats,
            "processing_time_ms": processing_time_ms,
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Statistics retrieval failed: {e}")
        raise JackdawException(
            message=f"Statistics retrieval failed: {str(e)}",
            error_code="STATISTICS_FAILED",
        )


@router.post("/address/full", response_model=AnalysisResponse)
async def analyze_address_full(
    request: AddressAnalysisRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]]))
):
    """Full combined analysis: patterns, mixer, cross-chain, and risk score via asyncio.gather()."""
    try:
        start = _time.monotonic()

        async def _get_patterns():
            try:
                return await _get_pattern_detector().detect_patterns(request.address, request.blockchain)
            except Exception:
                return []

        async def _get_mixer():
            try:
                return await _get_mixer_detector().detect_mixer_usage(request.address, request.blockchain)
            except Exception:
                return None

        patterns_raw, mixer_analysis = await asyncio.gather(_get_patterns(), _get_mixer())

        pattern_results = [
            {
                "pattern_type": p.pattern_type.value,
                "confidence": p.confidence,
                "risk_score": p.risk_score,
                "severity": p.severity,
                "description": p.description,
            }
            for p in (patterns_raw or [])
        ]
        mixer_detected = bool(mixer_analysis and mixer_analysis.is_mixer_user)
        mixer_risk = float(mixer_analysis.risk_score) if mixer_analysis else 0.0

        computed_risk = compute_risk_score(
            pattern_matches=pattern_results,
            mixer_detected=mixer_detected,
            mixer_risk=mixer_risk,
        )

        elapsed_ms = int((_time.monotonic() - start) * 1000)
        data = {
            "address": request.address,
            "blockchain": request.blockchain,
            "risk_score": computed_risk,
            "detected_patterns": pattern_results,
            "mixer_detected": mixer_detected,
            "mixer_risk": mixer_risk,
        }
        metadata = {
            "processing_time_ms": elapsed_ms,
            "data_sources": ["pattern_engine", "mixer_engine"],
        }
        return AnalysisResponse(
            success=True,
            data=data,
            metadata=metadata,
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Full address analysis failed: {e}")
        raise JackdawException(
            message=f"Full address analysis failed: {str(e)}",
            error_code="FULL_ANALYSIS_FAILED",
        )
