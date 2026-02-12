"""
Jackdaw Sentry - Intelligence Router
Threat intelligence and dark web monitoring endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, validator
import logging
import uuid
import json as _json

from src.api.auth import User, check_permissions, PERMISSIONS
from src.api.database import get_neo4j_session
from src.api.exceptions import JackdawException

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class IntelligenceQueryRequest(BaseModel):
    query_type: str  # address, entity, pattern, threat
    query_value: str
    sources: List[str] = ["all"]
    time_range_days: int = 30
    
    @validator('query_type')
    def validate_query_type(cls, v):
        valid_types = ["address", "entity", "pattern", "threat"]
        if v not in valid_types:
            raise ValueError(f'Invalid query type: {v}')
        return v
    
    @validator('sources')
    def validate_sources(cls, v):
        valid_sources = ["dark_web", "sanctions", "leaks", "forums", "social_media", "all"]
        for source in v:
            if source not in valid_sources:
                raise ValueError(f'Invalid source: {source}')
        return v


class ThreatAlertRequest(BaseModel):
    title: str
    description: str
    severity: str  # low, medium, high, critical
    threat_type: str  # malware, phishing, scam, money_laundering, terrorism
    indicators: List[Dict[str, Any]]
    confidence: float = 0.5
    
    @validator('severity')
    def validate_severity(cls, v):
        valid_severities = ["low", "medium", "high", "critical"]
        if v not in valid_severities:
            raise ValueError(f'Invalid severity: {v}')
        return v
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v


class IntelligenceSubscriptionRequest(BaseModel):
    subscription_type: str  # address, entity, keyword, pattern
    subscription_value: str
    notification_channels: List[str] = ["email"]
    filters: Dict[str, Any] = {}
    
    @validator('subscription_type')
    def validate_subscription_type(cls, v):
        valid_types = ["address", "entity", "keyword", "pattern"]
        if v not in valid_types:
            raise ValueError(f'Invalid subscription type: {v}')
        return v


class IntelligenceResponse(BaseModel):
    success: bool
    intelligence_data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime


# Endpoints
@router.post("/query", response_model=IntelligenceResponse)
async def query_intelligence(
    request: IntelligenceQueryRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """Query threat intelligence from Neo4j"""
    try:
        import time as _time
        start = _time.monotonic()
        logger.info(f"Querying intelligence for {request.query_type}: {request.query_value}")

        intelligence_data: Dict[str, Any] = {"query_type": request.query_type, "query_value": request.query_value}

        async with get_neo4j_session() as session:
            if request.query_type == "address":
                # Check sanctions, threat intel, and risk data for address
                result = await session.run(
                    """
                    OPTIONAL MATCH (a:Address {address: $val})
                    OPTIONAL MATCH (s:SanctionEntry {address: $val})
                    OPTIONAL MATCH (ti:ThreatIntel)-[:MENTIONS]->(a)
                    RETURN a.risk_score AS risk_score,
                           count(DISTINCT s) AS sanctions_hits,
                           count(DISTINCT ti) AS intel_mentions,
                           collect(DISTINCT ti.source) AS sources
                    """,
                    val=request.query_value,
                )
                rec = await result.single()
                intelligence_data["risk_score"] = float(rec["risk_score"] or 0) if rec else 0
                intelligence_data["sanctions_hits"] = rec["sanctions_hits"] if rec else 0
                intelligence_data["intel_mentions"] = rec["intel_mentions"] if rec else 0
                intelligence_data["sources"] = rec["sources"] if rec else []

            elif request.query_type == "entity":
                result = await session.run(
                    """
                    OPTIONAL MATCH (e:Entity {name: $val})
                    OPTIONAL MATCH (e)<-[:RELATED_TO]-(ti:ThreatIntel)
                    RETURN e, count(ti) AS threat_count,
                           collect(DISTINCT ti.threat_type) AS threat_types
                    """,
                    val=request.query_value,
                )
                rec = await result.single()
                if rec and rec["e"]:
                    intelligence_data.update(dict(rec["e"]))
                intelligence_data["threat_count"] = rec["threat_count"] if rec else 0
                intelligence_data["threat_types"] = rec["threat_types"] if rec else []

            elif request.query_type == "pattern":
                result = await session.run(
                    """
                    OPTIONAL MATCH (p:ThreatPattern {pattern: $val})
                    OPTIONAL MATCH (p)-[:MATCHED]->(c:Case)
                    RETURN p, count(c) AS matches_found,
                           collect({case_id: c.investigation_id, status: c.status}) AS matched_cases
                    """,
                    val=request.query_value,
                )
                rec = await result.single()
                if rec and rec["p"]:
                    intelligence_data.update(dict(rec["p"]))
                intelligence_data["matches_found"] = rec["matches_found"] if rec else 0
                intelligence_data["matched_cases"] = rec["matched_cases"] if rec else []

            else:  # threat
                result = await session.run(
                    """
                    OPTIONAL MATCH (t:ThreatAlert {threat_type: $val})
                    WHERE t.status = 'active'
                    RETURN count(t) AS active_count,
                           collect(DISTINCT t.severity) AS severities
                    """,
                    val=request.query_value,
                )
                rec = await result.single()
                intelligence_data["active_threats"] = rec["active_count"] if rec else 0
                intelligence_data["severities"] = rec["severities"] if rec else []

        elapsed_ms = int((_time.monotonic() - start) * 1000)
        metadata = {
            "query_type": request.query_type,
            "sources_queried": request.sources,
            "time_range_days": request.time_range_days,
            "processing_time_ms": elapsed_ms,
            "data_source": "neo4j",
        }

        return IntelligenceResponse(
            success=True, intelligence_data=intelligence_data,
            metadata=metadata, timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Intelligence query failed: {e}")
        raise JackdawException(
            message=f"Intelligence query failed: {str(e)}",
            error_code="INTELLIGENCE_QUERY_FAILED",
        )


@router.post("/alerts", response_model=IntelligenceResponse)
async def create_threat_alert(
    request: ThreatAlertRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_intelligence"]]))
):
    """Create new threat intelligence alert and persist to Neo4j"""
    try:
        logger.info(f"Creating threat alert: {request.title}")
        now = datetime.now(timezone.utc)
        alert_id = f"ALT-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        async with get_neo4j_session() as session:
            await session.run(
                """
                CREATE (a:ThreatAlert {
                    alert_id: $alert_id, title: $title,
                    description: $description, severity: $severity,
                    threat_type: $threat_type, status: 'active',
                    created_by: $created_by, created_at: $created_at,
                    indicators: $indicators, confidence: $confidence
                })
                """,
                alert_id=alert_id, title=request.title,
                description=request.description, severity=request.severity,
                threat_type=request.threat_type,
                created_by=current_user.username,
                created_at=now.isoformat(),
                indicators=_json.dumps(request.indicators),
                confidence=request.confidence,
            )

        alert_data = {
            "alert_id": alert_id, "title": request.title,
            "description": request.description, "severity": request.severity,
            "threat_type": request.threat_type, "status": "active",
            "created_by": current_user.username, "created_at": now.isoformat(),
            "confidence": request.confidence,
        }

        if request.severity == "critical":
            alert_data["immediate_actions"] = ["notify_management", "consider_blocking"]
        elif request.severity == "high":
            alert_data["immediate_actions"] = ["enhanced_monitoring", "investigation_required"]

        metadata = {"persisted_to": "neo4j", "alert_validation": "passed"}

        return IntelligenceResponse(
            success=True, intelligence_data=alert_data,
            metadata=metadata, timestamp=now,
        )

    except Exception as e:
        logger.error(f"Threat alert creation failed: {e}")
        raise JackdawException(
            message=f"Threat alert creation failed: {str(e)}",
            error_code="ALERT_CREATION_FAILED",
        )


@router.get("/alerts")
async def list_threat_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    threat_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """List threat intelligence alerts from Neo4j"""
    try:
        logger.info("Listing threat alerts with filters")

        where_clauses = []
        params: Dict[str, Any] = {"skip_val": offset, "limit_val": limit}
        if severity:
            where_clauses.append("a.severity = $severity")
            params["severity"] = severity
        if status:
            where_clauses.append("a.status = $status")
            params["status"] = status
        if threat_type:
            where_clauses.append("a.threat_type = $threat_type")
            params["threat_type"] = threat_type
        where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        async with get_neo4j_session() as session:
            count_result = await session.run(
                f"MATCH (a:ThreatAlert) {where_str} RETURN count(a) AS total", **params
            )
            count_rec = await count_result.single()
            total_count = count_rec["total"] if count_rec else 0

            result = await session.run(
                f"MATCH (a:ThreatAlert) {where_str} RETURN a "
                f"ORDER BY a.created_at DESC SKIP $skip_val LIMIT $limit_val",
                **params,
            )
            records = await result.data()

        alerts = [dict(r["a"]) for r in records]

        return {
            "success": True,
            "alerts": alerts,
            "pagination": {
                "total_count": total_count, "limit": limit,
                "offset": offset, "has_more": offset + limit < total_count,
            },
            "filters_applied": {"severity": severity, "status": status, "threat_type": threat_type},
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Alert listing failed: {e}")
        raise JackdawException(
            message=f"Alert listing failed: {str(e)}",
            error_code="ALERT_LISTING_FAILED",
        )


@router.post("/subscriptions", response_model=IntelligenceResponse)
async def create_intelligence_subscription(
    request: IntelligenceSubscriptionRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_intelligence"]]))
):
    """Create intelligence subscription and persist to Neo4j"""
    try:
        logger.info(f"Creating intelligence subscription: {request.subscription_type}")
        now = datetime.now(timezone.utc)
        sub_id = f"SUB-{uuid.uuid4().hex[:8].upper()}"

        async with get_neo4j_session() as session:
            await session.run(
                """
                CREATE (s:IntelSubscription {
                    subscription_id: $sub_id,
                    subscription_type: $sub_type,
                    subscription_value: $sub_value,
                    created_by: $created_by, created_at: $created_at,
                    status: 'active',
                    notification_channels: $channels,
                    filters: $filters,
                    notification_count: 0
                })
                """,
                sub_id=sub_id, sub_type=request.subscription_type,
                sub_value=request.subscription_value,
                created_by=current_user.username,
                created_at=now.isoformat(),
                channels=request.notification_channels,
                filters=_json.dumps(request.filters),
            )

        subscription_data = {
            "subscription_id": sub_id,
            "subscription_type": request.subscription_type,
            "subscription_value": request.subscription_value,
            "created_by": current_user.username,
            "created_at": now.isoformat(),
            "status": "active",
            "notification_channels": request.notification_channels,
        }
        metadata = {"persisted_to": "neo4j", "subscription_validation": "passed"}

        return IntelligenceResponse(
            success=True, intelligence_data=subscription_data,
            metadata=metadata, timestamp=now,
        )

    except Exception as e:
        logger.error(f"Subscription creation failed: {e}")
        raise JackdawException(
            message=f"Subscription creation failed: {str(e)}",
            error_code="SUBSCRIPTION_CREATION_FAILED",
        )


@router.get("/dark-web/monitoring")
async def get_dark_web_monitoring_status(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """Get dark web monitoring status from Neo4j"""
    try:
        monitoring_status: Dict[str, Any] = {"monitoring_active": True}

        async with get_neo4j_session() as session:
            # Get monitored sources
            src_result = await session.run(
                "MATCH (s:IntelSource {type: 'dark_web'}) RETURN s ORDER BY s.last_scan DESC"
            )
            src_records = await src_result.data()
            monitoring_status["monitored_platforms"] = [dict(r["s"]) for r in src_records]

            # Today's alert stats
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            stats_result = await session.run(
                """
                OPTIONAL MATCH (a:ThreatAlert)
                WHERE a.created_at >= $today
                RETURN count(a) AS total_today,
                       count(CASE WHEN a.severity IN ['high','critical'] THEN 1 END) AS high_priority
                """,
                today=today,
            )
            stats_rec = await stats_result.single()
            monitoring_status["statistics"] = {
                "alerts_today": stats_rec["total_today"] if stats_rec else 0,
                "high_priority_alerts": stats_rec["high_priority"] if stats_rec else 0,
            }

        return {
            "success": True,
            "monitoring_status": monitoring_status,
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Dark web monitoring status failed: {e}")
        raise JackdawException(
            message=f"Dark web monitoring status failed: {str(e)}",
            error_code="MONITORING_STATUS_FAILED",
        )


@router.get("/sources")
async def get_intelligence_sources(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """Get available intelligence sources from Neo4j"""
    try:
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH (s:IntelSource) RETURN s ORDER BY s.name"
            )
            records = await result.data()

        sources = [dict(r["s"]) for r in records]

        return {
            "success": True,
            "sources": sources,
            "total_sources": len(sources),
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Intelligence sources retrieval failed: {e}")
        raise JackdawException(
            message=f"Intelligence sources retrieval failed: {str(e)}",
            error_code="SOURCES_RETRIEVAL_FAILED",
        )


@router.get("/statistics")
async def get_intelligence_statistics(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """Get intelligence system statistics from Neo4j"""
    try:
        stats: Dict[str, Any] = {}
        async with get_neo4j_session() as session:
            alert_result = await session.run(
                """
                MATCH (a:ThreatAlert)
                RETURN count(a) AS total,
                       count(CASE WHEN a.status = 'active' THEN 1 END) AS active
                """
            )
            alert_rec = await alert_result.single()
            stats["total_alerts"] = alert_rec["total"] if alert_rec else 0
            stats["active_alerts"] = alert_rec["active"] if alert_rec else 0

            type_result = await session.run(
                "MATCH (a:ThreatAlert) RETURN a.threat_type AS ttype, count(a) AS c"
            )
            type_recs = await type_result.data()
            stats["alerts_by_type"] = {r["ttype"]: r["c"] for r in type_recs if r["ttype"]}

            sub_result = await session.run(
                "MATCH (s:IntelSubscription {status: 'active'}) RETURN count(s) AS total"
            )
            sub_rec = await sub_result.single()
            stats["active_subscriptions"] = sub_rec["total"] if sub_rec else 0

            src_result = await session.run(
                "MATCH (s:IntelSource) RETURN count(s) AS total"
            )
            src_rec = await src_result.single()
            stats["monitored_sources"] = src_rec["total"] if src_rec else 0

        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Intelligence statistics failed: {e}")
        raise JackdawException(
            message=f"Intelligence statistics failed: {str(e)}",
            error_code="STATISTICS_FAILED",
        )
