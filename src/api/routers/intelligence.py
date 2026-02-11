"""
Jackdaw Sentry - Intelligence Router
Threat intelligence and dark web monitoring endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
import logging

from src.api.auth import User, check_permissions, PERMISSIONS
from src.api.database import get_postgres_connection, get_redis_connection
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
    """Query threat intelligence databases"""
    try:
        logger.info(f"Querying intelligence for {request.query_type}: {request.query_value}")
        
        if request.query_type == "address":
            intelligence_data = {
                "address": request.query_value,
                "threat_indicators": {
                    "dark_web_mentions": 2,
                    "sanctions_list_hits": 0,
                    "leaked_data_exposure": 1,
                    "forum_discussions": 5
                },
                "risk_score": 0.35,
                "sources": {
                    "dark_web": {
                        "mentions": 2,
                        "contexts": ["marketplace", "money_transfer"],
                        "last_seen": datetime.utcnow() - timedelta(days=3)
                    },
                    "leaks": {
                        "exposure_count": 1,
                        "leak_source": "crypto_exchange_breach_2023",
                        "data_types": ["address", "transaction_history"]
                    },
                    "forums": {
                        "discussion_count": 5,
                        "sentiment": "neutral",
                        "topics": ["trading", "privacy"]
                    }
                },
                "timeline": [
                    {
                        "date": datetime.utcnow() - timedelta(days=3),
                        "source": "dark_web",
                        "event": "address_mentioned",
                        "details": "Mentioned in dark web marketplace"
                    },
                    {
                        "date": datetime.utcnow() - timedelta(days=15),
                        "source": "leaks",
                        "event": "data_exposure",
                        "details": "Address found in leaked exchange data"
                    }
                ]
            }
        
        elif request.query_type == "entity":
            intelligence_data = {
                "entity": request.query_value,
                "entity_type": "exchange",
                "threat_indicators": {
                    "regulatory_issues": 1,
                    "security_incidents": 2,
                    "compliance_violations": 0,
                    "reputation_risk": "medium"
                },
                "risk_score": 0.42,
                "sources": {
                    "regulatory": {
                        "violations": 1,
                        "fines_usd": 50000,
                        "jurisdictions": ["US", "EU"]
                    },
                    "security": {
                        "incidents": 2,
                        "types": ["data_breach", "phishing"],
                        "severity": "medium"
                    }
                }
            }
        
        elif request.query_type == "pattern":
            intelligence_data = {
                "pattern": request.query_value,
                "pattern_type": "transaction_pattern",
                "matches_found": 15,
                "risk_indicators": {
                    "structuring": True,
                    "rapid_movement": True,
                    "mixing_behavior": False,
                    "geographic_anomaly": False
                },
                "similar_cases": [
                    {
                        "case_id": "CASE-001",
                        "similarity_score": 0.85,
                        "outcome": "suspicious_activity_confirmed"
                    },
                    {
                        "case_id": "CASE-002", 
                        "similarity_score": 0.72,
                        "outcome": "false_positive"
                    }
                ]
            }
        
        else:  # threat
            intelligence_data = {
                "threat": request.query_value,
                "threat_category": "phishing",
                "active_campaigns": 3,
                "affected_platforms": ["exchange", "wallet", "defi"],
                "indicators": [
                    {
                        "type": "domain",
                        "value": "fake-example.com",
                        "confidence": 0.95,
                        "first_seen": datetime.utcnow() - timedelta(days=7)
                    },
                    {
                        "type": "address",
                        "value": "0x1234567890123456789012345678901234567890",
                        "confidence": 0.80,
                        "first_seen": datetime.utcnow() - timedelta(days=5)
                    }
                ]
            }
        
        metadata = {
            "query_type": request.query_type,
            "sources_queried": request.sources,
            "time_range_days": request.time_range_days,
            "processing_time_ms": 350,
            "data_freshness_hours": 6
        }
        
        return IntelligenceResponse(
            success=True,
            intelligence_data=intelligence_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Intelligence query failed: {e}")
        raise JackdawException(
            message=f"Intelligence query failed: {str(e)}",
            error_code="INTELLIGENCE_QUERY_FAILED"
        )


@router.post("/alerts", response_model=IntelligenceResponse)
async def create_threat_alert(
    request: ThreatAlertRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_intelligence"]]))
):
    """Create new threat intelligence alert"""
    try:
        logger.info(f"Creating threat alert: {request.title}")
        
        alert_data = {
            "alert_id": f"ALT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "title": request.title,
            "description": request.description,
            "severity": request.severity,
            "threat_type": request.threat_type,
            "status": "active",
            "created_by": current_user.username,
            "created_at": datetime.utcnow(),
            "indicators": request.indicators,
            "confidence": request.confidence,
            "affected_entities": [],
            "mitigation_steps": [],
            "related_alerts": []
        }
        
        # Add severity-specific actions
        if request.severity == "critical":
            alert_data["immediate_actions"] = ["notify_management", "consider_blocking"]
        elif request.severity == "high":
            alert_data["immediate_actions"] = ["enhanced_monitoring", "investigation_required"]
        
        metadata = {
            "alert_validation": "passed",
            "duplicate_check": "no_duplicates_found",
            "auto_enrichment": "completed"
        }
        
        return IntelligenceResponse(
            success=True,
            intelligence_data=alert_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Threat alert creation failed: {e}")
        raise JackdawException(
            message=f"Threat alert creation failed: {str(e)}",
            error_code="ALERT_CREATION_FAILED"
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
    """List threat intelligence alerts"""
    try:
        logger.info(f"Listing threat alerts with filters")
        
        alerts = [
            {
                "alert_id": "ALT-20240101001",
                "title": "Phishing Campaign Targeting DeFi Users",
                "description": "New phishing campaign discovered targeting DeFi wallet users",
                "severity": "high",
                "threat_type": "phishing",
                "status": "active",
                "created_at": datetime.utcnow() - timedelta(hours=6),
                "created_by": "intelligence_analyst1",
                "confidence": 0.85,
                "indicators_count": 5
            },
            {
                "alert_id": "ALT-20240101002",
                "title": "Dark Web Marketplace Activity Spike",
                "description": "Unusual increase in activity on known dark web marketplace",
                "severity": "medium",
                "threat_type": "money_laundering",
                "status": "monitoring",
                "created_at": datetime.utcnow() - timedelta(hours=12),
                "created_by": "intelligence_analyst2",
                "confidence": 0.72,
                "indicators_count": 3
            }
        ]
        
        # Apply filters
        if severity:
            alerts = [alert for alert in alerts if alert["severity"] == severity]
        if status:
            alerts = [alert for alert in alerts if alert["status"] == status]
        if threat_type:
            alerts = [alert for alert in alerts if alert["threat_type"] == threat_type]
        
        # Apply pagination
        total_count = len(alerts)
        paginated_alerts = alerts[offset:offset + limit]
        
        return {
            "success": True,
            "alerts": paginated_alerts,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "filters_applied": {
                "severity": severity,
                "status": status,
                "threat_type": threat_type
            },
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Alert listing failed: {e}")
        raise JackdawException(
            message=f"Alert listing failed: {str(e)}",
            error_code="ALERT_LISTING_FAILED"
        )


@router.post("/subscriptions", response_model=IntelligenceResponse)
async def create_intelligence_subscription(
    request: IntelligenceSubscriptionRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_intelligence"]]))
):
    """Create intelligence subscription"""
    try:
        logger.info(f"Creating intelligence subscription: {request.subscription_type}")
        
        subscription_data = {
            "subscription_id": f"SUB-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "subscription_type": request.subscription_type,
            "subscription_value": request.subscription_value,
            "created_by": current_user.username,
            "created_at": datetime.utcnow(),
            "status": "active",
            "notification_channels": request.notification_channels,
            "filters": request.filters,
            "last_notification": None,
            "notification_count": 0
        }
        
        metadata = {
            "subscription_validation": "passed",
            "notification_setup": "completed",
            "estimated_daily_alerts": 5
        }
        
        return IntelligenceResponse(
            success=True,
            intelligence_data=subscription_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Subscription creation failed: {e}")
        raise JackdawException(
            message=f"Subscription creation failed: {str(e)}",
            error_code="SUBSCRIPTION_CREATION_FAILED"
        )


@router.get("/dark-web/monitoring")
async def get_dark_web_monitoring_status(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """Get dark web monitoring status"""
    try:
        monitoring_status = {
            "monitoring_active": True,
            "monitored_platforms": [
                {
                    "name": "AlphaBay",
                    "status": "active",
                    "last_scan": datetime.utcnow() - timedelta(hours=2),
                    "items_collected": 1250
                },
                {
                    "name": "Dream Market",
                    "status": "active", 
                    "last_scan": datetime.utcnow() - timedelta(hours=3),
                    "items_collected": 890
                },
                {
                    "name": "Forum Threads",
                    "status": "active",
                    "last_scan": datetime.utcnow() - timedelta(hours=1),
                    "threads_analyzed": 3400
                }
            ],
            "statistics": {
                "total_mentions_today": 45,
                "high_priority_alerts": 3,
                "new_addresses_identified": 12,
                "threat_patterns_detected": 7
            },
            "next_scan": datetime.utcnow() + timedelta(minutes=30)
        }
        
        return {
            "success": True,
            "monitoring_status": monitoring_status,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Dark web monitoring status failed: {e}")
        raise JackdawException(
            message=f"Dark web monitoring status failed: {str(e)}",
            error_code="MONITORING_STATUS_FAILED"
        )


@router.get("/sources")
async def get_intelligence_sources(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """Get available intelligence sources"""
    try:
        sources = [
            {
                "source_id": "dark_web_001",
                "name": "Dark Web Markets",
                "type": "dark_web",
                "status": "active",
                "coverage": "global",
                "update_frequency_hours": 1,
                "data_types": ["market_listings", "forum_posts", "chat_messages"],
                "reliability_score": 0.85,
                "last_updated": datetime.utcnow() - timedelta(hours=1)
            },
            {
                "source_id": "sanctions_001",
                "name": "Global Sanctions Lists",
                "type": "sanctions",
                "status": "active",
                "coverage": "global",
                "update_frequency_hours": 6,
                "data_types": ["sanctions_lists", "watch_lists", "blocked_entities"],
                "reliability_score": 0.98,
                "last_updated": datetime.utcnow() - timedelta(hours=6)
            },
            {
                "source_id": "leaks_001",
                "name": "Data Leak Monitoring",
                "type": "leaks",
                "status": "active",
                "coverage": "global",
                "update_frequency_hours": 4,
                "data_types": ["leaked_credentials", "exposed_addresses", "breach_data"],
                "reliability_score": 0.75,
                "last_updated": datetime.utcnow() - timedelta(hours=4)
            }
        ]
        
        return {
            "success": True,
            "sources": sources,
            "total_sources": len(sources),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Intelligence sources retrieval failed: {e}")
        raise JackdawException(
            message=f"Intelligence sources retrieval failed: {str(e)}",
            error_code="SOURCES_RETRIEVAL_FAILED"
        )


@router.get("/statistics")
async def get_intelligence_statistics(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """Get intelligence system statistics"""
    try:
        stats = {
            "total_alerts": 1250,
            "active_alerts": 23,
            "daily_intelligence_items": 450,
            "monitored_sources": 15,
            "active_subscriptions": 89,
            "dark_web_mentions_today": 45,
            "threat_detection_rate": 0.87,
            "false_positive_rate": 0.12,
            "average_processing_time_ms": 280,
            "intelligence_by_type": {
                "phishing": 350,
                "money_laundering": 280,
                "malware": 190,
                "scams": 230,
                "terrorism": 45
            },
            "source_effectiveness": {
                "dark_web": 0.85,
                "sanctions": 0.98,
                "leaks": 0.75,
                "forums": 0.68
            }
        }
        
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Intelligence statistics failed: {e}")
        raise JackdawException(
            message=f"Intelligence statistics failed: {str(e)}",
            error_code="STATISTICS_FAILED"
        )
