"""
Compliance Mobile Service Module

This module provides mobile-optimized data and services for compliance operations including:
- Lightweight dashboard summaries for mobile clients
- Push notification management
- Mobile-specific alert feeds
- Offline data packaging for field use
- Data synchronization between mobile and server
- User preference and settings management
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import uuid
import hashlib

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(Enum):
    """Notification type enumeration"""
    ALERT = "alert"
    DEADLINE = "deadline"
    CASE_UPDATE = "case_update"
    RISK_CHANGE = "risk_change"
    SYSTEM = "system"
    SYNC = "sync"


class SyncStatus(Enum):
    """Data sync status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


@dataclass
class MobileNotification:
    """Mobile push notification"""
    notification_id: str
    user_id: str
    title: str
    body: str
    notification_type: NotificationType
    priority: NotificationPriority
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    read: bool = False
    read_at: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


@dataclass
class MobileSettings:
    """Mobile user settings"""
    user_id: str
    push_enabled: bool = True
    alert_notifications: bool = True
    deadline_notifications: bool = True
    case_update_notifications: bool = True
    risk_change_notifications: bool = True
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None
    dashboard_widgets: List[str] = field(default_factory=lambda: [
        "risk_summary", "active_cases", "upcoming_deadlines", "recent_alerts"
    ])
    offline_data_categories: List[str] = field(default_factory=lambda: [
        "cases", "risk_assessments", "deadlines"
    ])
    sync_interval_minutes: int = 15
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    _QUIET_HOURS_RE = re.compile(r'^(?:[01]\d|2[0-3]):[0-5]\d$')
    _MIN_SYNC_INTERVAL: int = 1

    def __post_init__(self):
        for attr in ('quiet_hours_start', 'quiet_hours_end'):
            value = getattr(self, attr)
            if value is not None and not self._QUIET_HOURS_RE.match(value):
                raise ValueError(f"{attr} must be in HH:MM format (00:00–23:59), got '{value}'")
        if not isinstance(self.sync_interval_minutes, int) or self.sync_interval_minutes < self._MIN_SYNC_INTERVAL:
            raise ValueError(
                f"sync_interval_minutes must be an int >= {self._MIN_SYNC_INTERVAL}, "
                f"got {self.sync_interval_minutes!r}"
            )


@dataclass
class SyncRecord:
    """Data synchronization record"""
    sync_id: str
    user_id: str
    device_id: str
    status: SyncStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_uploaded: int = 0
    records_downloaded: int = 0
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None


class ComplianceMobileEngine:
    """Mobile-optimized compliance data engine"""

    def __init__(self):
        self.notifications: Dict[str, List[MobileNotification]] = {}  # user_id -> notifications
        self.settings: Dict[str, MobileSettings] = {}  # user_id -> settings
        self.sync_history: Dict[str, List[SyncRecord]] = {}  # user_id -> sync records
        self.offline_data_versions: Dict[str, str] = {}  # category -> version hash

    async def get_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Get mobile-optimised dashboard summary"""
        try:
            now = datetime.now(timezone.utc)

            # Compact risk summary
            risk_summary = {
                "overall_score": 0.42,
                "trend": "improving",
                "high_risk_entities": 3,
                "assessments_due": 2,
                "last_updated": now.isoformat(),
            }

            # Active cases snapshot
            active_cases = {
                "total": 12,
                "by_priority": {"critical": 1, "high": 3, "medium": 5, "low": 3},
                "assigned_to_me": 4,
                "updated_today": 2,
            }

            # Upcoming deadlines (next 7 days)
            upcoming_deadlines = [
                {
                    "deadline_id": "dl_001",
                    "title": "Q4 SAR Filing",
                    "due_date": (now + timedelta(days=2)).isoformat(),
                    "priority": "high",
                    "status": "pending",
                },
                {
                    "deadline_id": "dl_002",
                    "title": "Annual DORA Report",
                    "due_date": (now + timedelta(days=5)).isoformat(),
                    "priority": "medium",
                    "status": "in_progress",
                },
            ]

            # Recent alerts (last 24h)
            recent_alerts = {
                "total": 5,
                "critical": 0,
                "high": 1,
                "unread": 3,
            }

            # Quick stats
            quick_stats = {
                "compliance_score": 87.5,
                "sar_filed_this_month": 8,
                "cases_closed_this_week": 3,
                "pending_reviews": 6,
            }

            return {
                "user_id": user_id,
                "timestamp": now.isoformat(),
                "risk_summary": risk_summary,
                "active_cases": active_cases,
                "upcoming_deadlines": upcoming_deadlines,
                "recent_alerts": recent_alerts,
                "quick_stats": quick_stats,
            }

        except Exception as e:
            logger.error(f"Failed to get mobile dashboard for {user_id}: {e}")
            raise

    async def get_alerts(
        self,
        user_id: str,
        limit: int = 50,
        unread_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get mobile alert feed"""
        try:
            notifications = self.notifications.get(user_id, [])

            if unread_only:
                notifications = [n for n in notifications if not n.read]

            # Sort newest first
            notifications.sort(key=lambda n: n.created_at, reverse=True)
            notifications = notifications[:limit]

            return [
                {
                    "notification_id": n.notification_id,
                    "title": n.title,
                    "body": n.body,
                    "type": n.notification_type.value,
                    "priority": n.priority.value,
                    "created_at": n.created_at.isoformat(),
                    "read": n.read,
                    "data": n.data,
                }
                for n in notifications
            ]

        except Exception as e:
            logger.error(f"Failed to get alerts for {user_id}: {e}")
            raise

    async def send_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        notification_type: NotificationType = NotificationType.SYSTEM,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        data: Optional[Dict[str, Any]] = None,
    ) -> MobileNotification:
        """Send a push notification to a user"""
        try:
            notification = MobileNotification(
                notification_id=f"notif_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                title=title,
                body=body,
                notification_type=notification_type,
                priority=priority,
                data=data,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )

            if user_id not in self.notifications:
                self.notifications[user_id] = []
            self.notifications[user_id].append(notification)

            # Check user settings before "sending"
            settings = self.settings.get(user_id, MobileSettings(user_id=user_id))
            if not settings.push_enabled:
                logger.info(f"Push disabled for {user_id}, notification stored only")
            else:
                logger.info(f"Notification sent to {user_id}: {title}")

            return notification

        except Exception as e:
            logger.error(f"Failed to send notification to {user_id}: {e}")
            raise

    async def get_settings(self, user_id: str) -> MobileSettings:
        """Get mobile settings for a user"""
        try:
            if user_id not in self.settings:
                self.settings[user_id] = MobileSettings(user_id=user_id)
            return self.settings[user_id]
        except Exception as e:
            logger.error(f"Failed to get settings for {user_id}: {e}")
            raise

    async def update_settings(self, user_id: str, updates: Dict[str, Any]) -> MobileSettings:
        """Update mobile settings for a user"""
        try:
            settings = await self.get_settings(user_id)

            allowed_fields = {
                "push_enabled", "alert_notifications", "deadline_notifications",
                "case_update_notifications", "risk_change_notifications",
                "quiet_hours_start", "quiet_hours_end", "dashboard_widgets",
                "offline_data_categories", "sync_interval_minutes",
            }

            for key, value in updates.items():
                if key in allowed_fields and hasattr(settings, key):
                    setattr(settings, key, value)

            settings.updated_at = datetime.now(timezone.utc)
            self.settings[user_id] = settings
            logger.info(f"Updated mobile settings for {user_id}")
            return settings

        except Exception as e:
            logger.error(f"Failed to update settings for {user_id}: {e}")
            raise

    async def get_offline_data(
        self,
        user_id: str,
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Package data for offline mobile use"""
        try:
            settings = await self.get_settings(user_id)
            requested = categories or settings.offline_data_categories
            now = datetime.now(timezone.utc)

            offline_package = {
                "user_id": user_id,
                "generated_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=24)).isoformat(),
                "categories": {},
                "versions": {},
            }

            for category in requested:
                if category == "cases":
                    offline_package["categories"]["cases"] = {
                        "items": [
                            {
                                "case_id": "case_001",
                                "title": "High-risk transaction cluster",
                                "status": "open",
                                "priority": "high",
                                "assigned_to": user_id,
                                "updated_at": now.isoformat(),
                            },
                            {
                                "case_id": "case_002",
                                "title": "Sanctions screening match",
                                "status": "in_progress",
                                "priority": "critical",
                                "assigned_to": user_id,
                                "updated_at": (now - timedelta(hours=3)).isoformat(),
                            },
                        ],
                        "total": 2,
                    }
                elif category == "risk_assessments":
                    offline_package["categories"]["risk_assessments"] = {
                        "items": [
                            {
                                "assessment_id": "ra_001",
                                "entity_id": "ent_100",
                                "risk_level": "high",
                                "score": 78,
                                "updated_at": now.isoformat(),
                            },
                        ],
                        "total": 1,
                    }
                elif category == "deadlines":
                    offline_package["categories"]["deadlines"] = {
                        "items": [
                            {
                                "deadline_id": "dl_001",
                                "title": "Q4 SAR Filing",
                                "due_date": (now + timedelta(days=2)).isoformat(),
                                "status": "pending",
                            },
                        ],
                        "total": 1,
                    }
                elif category == "regulations":
                    offline_package["categories"]["regulations"] = {
                        "items": [
                            {"code": "AMLR", "title": "Anti-Money Laundering Regulation", "version": "2024.1"},
                            {"code": "DORA", "title": "Digital Operational Resilience Act", "version": "2024.1"},
                            {"code": "MiCA", "title": "Markets in Crypto-Assets", "version": "2024.1"},
                        ],
                        "total": 3,
                    }

            # Compute per-category version hashes and track them
            for category, cat_data in offline_package["categories"].items():
                version_hash = hashlib.sha256(
                    json.dumps(cat_data, sort_keys=True, default=str).encode()
                ).hexdigest()[:16]
                offline_package["versions"][category] = version_hash
                self.offline_data_versions[category] = version_hash

            offline_package["size_bytes"] = len(json.dumps(offline_package).encode())
            return offline_package

        except Exception as e:
            logger.error(f"Failed to get offline data for {user_id}: {e}")
            raise

    async def sync_data(
        self,
        user_id: str,
        device_id: str,
        client_data: Optional[Dict[str, Any]] = None,
    ) -> SyncRecord:
        """Synchronize data between mobile client and server"""
        try:
            sync_id = f"sync_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)

            record = SyncRecord(
                sync_id=sync_id,
                user_id=user_id,
                device_id=device_id,
                status=SyncStatus.IN_PROGRESS,
                started_at=now,
            )

            # Process uploaded data from client
            if client_data:
                uploaded = client_data.get("records", [])
                record.records_uploaded = len(uploaded)

                for item in uploaded:
                    # Detect conflicts (simplified)
                    if item.get("modified_at") and item.get("server_modified_at"):
                        client_mod = item["modified_at"]
                        server_mod = item["server_modified_at"]
                        if client_mod != server_mod:
                            record.conflicts.append({
                                "record_id": item.get("id"),
                                "type": item.get("type"),
                                "client_modified": client_mod,
                                "server_modified": server_mod,
                                "resolution": "server_wins",
                            })

            # Server-side changes to push to client
            record.records_downloaded = 5  # Mock count

            # Finalise
            record.completed_at = datetime.now(timezone.utc)
            if record.conflicts:
                record.status = SyncStatus.CONFLICT
            else:
                record.status = SyncStatus.COMPLETED

            # Store sync record
            if user_id not in self.sync_history:
                self.sync_history[user_id] = []
            self.sync_history[user_id].append(record)

            logger.info(
                f"Sync {sync_id} for {user_id}: uploaded={record.records_uploaded}, "
                f"downloaded={record.records_downloaded}, conflicts={len(record.conflicts)}"
            )
            return record

        except Exception as e:
            logger.error(f"Sync failed for {user_id}: {e}")
            raise

    async def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read"""
        try:
            notifications = self.notifications.get(user_id, [])
            for n in notifications:
                if n.notification_id == notification_id:
                    n.read = True
                    n.read_at = datetime.now(timezone.utc)
                    return True
            return False
        except Exception as e:
            logger.error(
                f"Failed to mark notification {notification_id} read for {user_id}: {e}"
            )
            return False
