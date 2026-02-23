"""
Jackdaw Sentry - Threat Feeds API Router
REST endpoints for threat intelligence feed management and synchronization
"""

import json as _json
import logging
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from pydantic import BaseModel
from pydantic import field_validator

from src.api.auth import PERMISSIONS
from src.api.auth import User
from src.api.auth import check_permissions
from src.api.database import get_postgres_connection
from src.api.exceptions import JackdawException
from src.intelligence.threat_feeds import get_threat_intelligence_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed filter values
VALID_FEED_TYPES = {
    "sanctions",
    "scam",
    "hack",
    "phishing",
    "malware",
    "ransomware",
    "terrorism",
    "money_laundering",
    "dark_web",
    "mixer",
    "exchange_hack",
    "defi_exploit",
    "nft_fraud",
    "social_engineering",
}
VALID_FEED_STATUSES = {"active", "inactive", "error", "syncing", "disabled"}
VALID_THREAT_LEVELS = {"low", "medium", "high", "critical", "severe"}


# Pydantic models
class ThreatFeedCreate(BaseModel):
    name: str
    feed_type: str
    source_url: str
    api_key: Optional[str] = None
    sync_interval_minutes: int = 60
    enabled: bool = True
    config: Dict[str, Any] = {}
    description: Optional[str] = None

    @field_validator("feed_type")
    @classmethod
    def validate_feed_type(cls, v):
        if v not in VALID_FEED_TYPES:
            raise ValueError(f"Invalid feed type: {v}")
        return v

    @field_validator("sync_interval_minutes")
    @classmethod
    def validate_sync_interval(cls, v):
        if v < 5 or v > 1440:  # 5 minutes to 24 hours
            raise ValueError("Sync interval must be between 5 and 1440 minutes")
        return v


class ThreatFeedUpdate(BaseModel):
    name: Optional[str] = None
    feed_type: Optional[str] = None
    source_url: Optional[str] = None
    api_key: Optional[str] = None
    sync_interval_minutes: Optional[int] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    description: Optional[str] = None

    @field_validator("feed_type")
    @classmethod
    def validate_feed_type(cls, v):
        if v is not None and v not in VALID_FEED_TYPES:
            raise ValueError(f"Invalid feed type: {v}")
        return v

    @field_validator("sync_interval_minutes")
    @classmethod
    def validate_sync_interval(cls, v):
        if v is not None and (v < 5 or v > 1440):
            raise ValueError("Sync interval must be between 5 and 1440 minutes")
        return v


class ThreatFeedResponse(BaseModel):
    id: str
    name: str
    feed_type: str
    source_url: str
    enabled: bool
    status: str
    sync_interval_minutes: int
    last_sync: Optional[datetime]
    next_sync: Optional[datetime]
    total_items: int
    error_count: int
    config: Dict[str, Any]
    description: Optional[str]
    created_date: datetime
    last_updated: datetime


class ThreatIntelligenceQuery(BaseModel):
    query_type: str  # address, entity, pattern, threat
    query_value: str
    threat_types: List[str] = []
    time_range_days: int = 30
    include_inactive: bool = False

    @field_validator("query_type")
    @classmethod
    def validate_query_type(cls, v):
        valid_types = ["address", "entity", "pattern", "threat"]
        if v not in valid_types:
            raise ValueError(f"Invalid query type: {v}")
        return v

    @field_validator("threat_types")
    @classmethod
    def validate_threat_types(cls, v):
        for threat_type in v:
            if threat_type not in VALID_FEED_TYPES:
                raise ValueError(f"Invalid threat type: {threat_type}")
        return v


class ThreatIntelligenceItem(BaseModel):
    id: str
    feed_id: str
    feed_name: str
    threat_type: str
    threat_level: str
    title: str
    description: str
    indicators: List[str]  # addresses, domains, etc.
    first_seen: datetime
    last_seen: datetime
    confidence_score: float
    source_url: Optional[str]
    tags: List[str]
    metadata: Dict[str, Any]


class FeedHealthStatus(BaseModel):
    feed_id: str
    feed_name: str
    status: str
    last_sync: Optional[datetime]
    sync_duration_seconds: Optional[float]
    error_message: Optional[str]
    consecutive_errors: int
    items_last_sync: int
    uptime_percentage: float


class FeedStatistics(BaseModel):
    total_feeds: int
    active_feeds: int
    total_intelligence_items: int
    items_by_threat_type: Dict[str, int]
    items_by_threat_level: Dict[str, int]
    sync_success_rate: float
    average_sync_time: float
    last_24h_items: int


# API Endpoints
@router.get("/", response_model=List[ThreatFeedResponse])
async def list_threat_feeds(
    feed_type: Optional[str] = Query(None, description="Filter by feed type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """List threat intelligence feeds with optional filters"""
    try:
        threat_manager = await get_threat_intelligence_manager()

        # Build filters
        filters = {}
        if feed_type:
            if feed_type not in VALID_FEED_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid feed type: {feed_type}",
                )
            filters["feed_type"] = feed_type

        if status:
            if status not in VALID_FEED_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}",
                )
            filters["status"] = status

        if enabled is not None:
            filters["enabled"] = enabled

        feeds = await threat_manager.get_feeds(filters)

        return [ThreatFeedResponse(**feed.__dict__) for feed in feeds]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list threat feeds: {e}")
        raise JackdawException(message="Failed to list threat feeds", details=str(e))


@router.post(
    "/", response_model=ThreatFeedResponse, status_code=status.HTTP_201_CREATED
)
async def create_threat_feed(
    feed: ThreatFeedCreate,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Create a new threat intelligence feed"""
    try:
        threat_manager = await get_threat_intelligence_manager()

        feed_data = feed.model_dump()
        feed_data["id"] = str(uuid.uuid4())
        feed_data["status"] = "inactive"
        feed_data["created_date"] = datetime.now(timezone.utc)
        feed_data["last_updated"] = datetime.now(timezone.utc)
        feed_data["total_items"] = 0
        feed_data["error_count"] = 0

        created_feed = await threat_manager.create_feed(feed_data)

        logger.info(f"Created threat feed {created_feed.id} by user {current_user.id}")
        return ThreatFeedResponse(**created_feed.__dict__)

    except Exception as e:
        logger.error(f"Failed to create threat feed: {e}")
        raise JackdawException(message="Failed to create threat feed", details=str(e))


@router.get("/{feed_id}", response_model=ThreatFeedResponse)
async def get_threat_feed(
    feed_id: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get a specific threat feed by ID"""
    try:
        threat_manager = await get_threat_intelligence_manager()

        feed = await threat_manager.get_feed(feed_id)
        if not feed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Threat feed {feed_id} not found",
            )

        return ThreatFeedResponse(**feed.__dict__)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get threat feed {feed_id}: {e}")
        raise JackdawException(message="Failed to get threat feed", details=str(e))


@router.put("/{feed_id}", response_model=ThreatFeedResponse)
async def update_threat_feed(
    feed_id: str,
    feed_update: ThreatFeedUpdate,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Update a threat feed"""
    try:
        threat_manager = await get_threat_intelligence_manager()

        # Check if feed exists
        existing_feed = await threat_manager.get_feed(feed_id)
        if not existing_feed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Threat feed {feed_id} not found",
            )

        # Update feed
        update_data = feed_update.model_dump(exclude_unset=True)
        update_data["last_updated"] = datetime.now(timezone.utc)

        updated_feed = await threat_manager.update_feed(feed_id, update_data)

        logger.info(f"Updated threat feed {feed_id} by user {current_user.id}")
        return ThreatFeedResponse(**updated_feed.__dict__)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update threat feed {feed_id}: {e}")
        raise JackdawException(message="Failed to update threat feed", details=str(e))


@router.delete("/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_threat_feed(
    feed_id: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Delete a threat feed"""
    try:
        threat_manager = await get_threat_intelligence_manager()

        # Check if feed exists
        existing_feed = await threat_manager.get_feed(feed_id)
        if not existing_feed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Threat feed {feed_id} not found",
            )

        await threat_manager.delete_feed(feed_id)

        logger.info(f"Deleted threat feed {feed_id} by user {current_user.id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete threat feed {feed_id}: {e}")
        raise JackdawException(message="Failed to delete threat feed", details=str(e))


@router.post("/{feed_id}/sync", response_model=ThreatFeedResponse)
async def sync_threat_feed(
    feed_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Manually trigger synchronization of a threat feed"""
    try:
        threat_manager = await get_threat_intelligence_manager()

        # Check if feed exists
        existing_feed = await threat_manager.get_feed(feed_id)
        if not existing_feed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Threat feed {feed_id} not found",
            )

        # Trigger sync in background
        background_tasks.add_task(threat_manager.sync_feed, feed_id)

        logger.info(
            f"Triggered manual sync for threat feed {feed_id} by user {current_user.id}"
        )

        # Return current feed status
        return ThreatFeedResponse(**existing_feed.__dict__)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync threat feed {feed_id}: {e}")
        raise JackdawException(message="Failed to sync threat feed", details=str(e))


@router.get("/{feed_id}/health", response_model=FeedHealthStatus)
async def get_feed_health(
    feed_id: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get health status of a threat feed"""
    try:
        threat_manager = await get_threat_intelligence_manager()

        # Check if feed exists
        existing_feed = await threat_manager.get_feed(feed_id)
        if not existing_feed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Threat feed {feed_id} not found",
            )

        health = await threat_manager.get_feed_health(feed_id)

        return FeedHealthStatus(**health)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feed health {feed_id}: {e}")
        raise JackdawException(message="Failed to get feed health", details=str(e))


@router.post("/query/intelligence", response_model=List[ThreatIntelligenceItem])
async def query_threat_intelligence(
    query: ThreatIntelligenceQuery,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Query threat intelligence data"""
    try:
        threat_manager = await get_threat_intelligence_manager()

        # Validate query
        if query.time_range_days < 1 or query.time_range_days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Time range must be between 1 and 365 days",
            )

        results = await threat_manager.query_intelligence(
            query.query_type,
            query.query_value,
            query.threat_types,
            query.time_range_days,
            query.include_inactive,
        )

        return [ThreatIntelligenceItem(**item.__dict__) for item in results]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query threat intelligence: {e}")
        raise JackdawException(
            message="Failed to query threat intelligence", details=str(e)
        )


@router.get("/statistics/overview", response_model=FeedStatistics)
async def get_feed_statistics(
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get threat feed statistics"""
    try:
        threat_manager = await get_threat_intelligence_manager()

        stats = await threat_manager.get_statistics()

        return FeedStatistics(**stats)

    except Exception as e:
        logger.error(f"Failed to get threat feed statistics: {e}")
        raise JackdawException(
            message="Failed to get threat feed statistics", details=str(e)
        )


@router.post("/sync/all", response_model=Dict[str, str])
async def sync_all_feeds(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Trigger synchronization of all active threat feeds"""
    try:
        threat_manager = await get_threat_intelligence_manager()

        # Get all active feeds
        feeds = await threat_manager.get_feeds({"enabled": True, "status": "active"})

        sync_results = {}
        for feed in feeds:
            try:
                background_tasks.add_task(threat_manager.sync_feed, feed.id)
                sync_results[feed.id] = "sync_triggered"
            except Exception as e:
                sync_results[feed.id] = f"sync_failed: {str(e)}"

        logger.info(f"Triggered sync for {len(feeds)} feeds by user {current_user.id}")

        return sync_results

    except Exception as e:
        logger.error(f"Failed to sync all feeds: {e}")
        raise JackdawException(message="Failed to sync all feeds", details=str(e))


@router.get("/threat-types", response_model=List[str])
async def get_threat_types(
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get available threat types"""
    try:
        return list(VALID_FEED_TYPES)

    except Exception as e:
        logger.error(f"Failed to get threat types: {e}")
        raise JackdawException(message="Failed to get threat types", details=str(e))


@router.get("/items/recent", response_model=List[ThreatIntelligenceItem])
async def get_recent_intelligence(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    threat_type: Optional[str] = Query(None, description="Filter by threat type"),
    threat_level: Optional[str] = Query(None, description="Filter by threat level"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]])),
):
    """Get recent threat intelligence items"""
    try:
        threat_manager = await get_threat_intelligence_manager()

        # Validate filters
        if threat_type and threat_type not in VALID_FEED_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid threat type: {threat_type}",
            )

        if threat_level and threat_level not in VALID_THREAT_LEVELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid threat level: {threat_level}",
            )

        items = await threat_manager.get_recent_items(
            hours, threat_type, threat_level, limit
        )

        return [ThreatIntelligenceItem(**item.__dict__) for item in items]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recent intelligence: {e}")
        raise JackdawException(
            message="Failed to get recent intelligence", details=str(e)
        )
