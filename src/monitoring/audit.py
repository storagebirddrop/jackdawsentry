"""
Jackdaw Sentry - Audit Logging Utilities

General audit logging utilities for comprehensive security event tracking.
"""

import json
import logging
import uuid
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from src.utils.encryption import create_data_checksum
from src.utils.encryption import encrypt_data
from src.utils.encryption import hash_data


class AuditSeverity(Enum):
    """Audit event severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditCategory(Enum):
    """Audit event categories"""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_CONFIG = "system_config"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    ERROR = "error"
    BUSINESS = "business"


class AuditEvent:
    """Audit event data structure"""

    def __init__(
        self,
        event_type: str,
        category: AuditCategory,
        severity: AuditSeverity,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.id = str(uuid.uuid4())
        self.event_type = event_type
        self.category = category
        self.severity = severity
        self.user_id = user_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.action = action
        self.details = details or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.session_id = session_id
        self.request_id = request_id
        self.timestamp = timestamp or datetime.now(timezone.utc)

        # Create checksum for integrity verification
        self.checksum = self._create_checksum()

    def _create_checksum(self) -> str:
        """Create checksum for audit event integrity"""
        event_data = {
            "id": self.id,
            "event_type": self.event_type,
            "category": self.category.value,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }
        return create_data_checksum(event_data)

    def verify_integrity(self) -> bool:
        """Verify audit event integrity"""
        current_checksum = self._create_checksum()
        return current_checksum == self.checksum

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary"""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "category": self.category.value,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "checksum": self.checksum,
        }

    def to_json(self) -> str:
        """Convert audit event to JSON"""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """Centralized audit logging system"""

    def __init__(self, logger_name: str = "audit"):
        """Initialize audit logger

        Args:
            logger_name: Name for the audit logger
        """
        self.logger = logging.getLogger(logger_name)
        self._setup_logger()

    def _setup_logger(self):
        """Setup audit logger with appropriate configuration"""
        # Create handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_event(self, event: AuditEvent) -> bool:
        """Log audit event

        Args:
            event: Audit event to log

        Returns:
            True if logging successful
        """
        try:
            # Log with appropriate level based on severity
            log_level = {
                AuditSeverity.LOW: logging.INFO,
                AuditSeverity.MEDIUM: logging.WARNING,
                AuditSeverity.HIGH: logging.ERROR,
                AuditSeverity.CRITICAL: logging.CRITICAL,
            }.get(event.severity, logging.INFO)

            self.logger.log(log_level, f"AUDIT: {event.to_json()}")

            return True
        except Exception as e:
            # Log error but don't raise to avoid breaking application
            self.logger.error(f"Failed to log audit event: {str(e)}")
            return False

    def create_event(
        self,
        event_type: str,
        category: Union[AuditCategory, str],
        severity: Union[AuditSeverity, str],
        **kwargs,
    ) -> AuditEvent:
        """Create and log audit event

        Args:
            event_type: Type of event
            category: Event category
            severity: Event severity
            **kwargs: Additional event parameters

        Returns:
            Created audit event
        """
        # Convert string enums to enum values
        if isinstance(category, str):
            try:
                category = AuditCategory(category.lower())
            except ValueError:
                category = AuditCategory.BUSINESS

        if isinstance(severity, str):
            try:
                severity = AuditSeverity(severity.lower())
            except ValueError:
                severity = AuditSeverity.MEDIUM

        event = AuditEvent(
            event_type=event_type, category=category, severity=severity, **kwargs
        )

        self.log_event(event)
        return event


class AuditTrail:
    """Audit trail management and analysis"""

    def __init__(self, storage_backend: Optional[str] = None):
        """Initialize audit trail

        Args:
            storage_backend: Backend for storing audit logs
        """
        self.storage_backend = storage_backend
        self.events: List[AuditEvent] = []

    def add_event(self, event: AuditEvent) -> bool:
        """Add event to audit trail

        Args:
            event: Audit event to add

        Returns:
            True if event added successfully
        """
        try:
            # Verify event integrity before adding
            if not event.verify_integrity():
                raise ValueError("Event integrity verification failed")

            self.events.append(event)
            return True
        except Exception as e:
            logging.error(f"Failed to add event to audit trail: {str(e)}")
            return False

    def get_events(
        self,
        limit: int = 100,
        category: Optional[AuditCategory] = None,
        severity: Optional[AuditSeverity] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditEvent]:
        """Get filtered audit events

        Args:
            limit: Maximum number of events to return
            category: Filter by category
            severity: Filter by severity
            user_id: Filter by user ID
            start_time: Filter events after this time
            end_time: Filter events before this time

        Returns:
            Filtered list of audit events
        """
        filtered_events = self.events

        # Apply filters
        if category:
            filtered_events = [e for e in filtered_events if e.category == category]

        if severity:
            filtered_events = [e for e in filtered_events if e.severity == severity]

        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]

        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]

        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]

        # Sort by timestamp (newest first) and limit
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_events[:limit]

    def generate_report(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate audit trail report

        Args:
            start_time: Report start time
            end_time: Report end time

        Returns:
            Audit trail report
        """
        events = self.get_events(limit=10000, start_time=start_time, end_time=end_time)

        # Calculate statistics
        total_events = len(events)
        events_by_category = {}
        events_by_severity = {}
        events_by_user = {}

        for event in events:
            # Category statistics
            cat_key = event.category.value
            events_by_category[cat_key] = events_by_category.get(cat_key, 0) + 1

            # Severity statistics
            sev_key = event.severity.value
            events_by_severity[sev_key] = events_by_severity.get(sev_key, 0) + 1

            # User statistics
            if event.user_id:
                events_by_user[event.user_id] = events_by_user.get(event.user_id, 0) + 1

        return {
            "report_period": {
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
            },
            "summary": {
                "total_events": total_events,
                "events_by_category": events_by_category,
                "events_by_severity": events_by_severity,
                "events_by_user": events_by_user,
            },
            "integrity_issues": [
                event.id for event in events if not event.verify_integrity()
            ],
        }

    def verify_integrity(self) -> Dict[str, Any]:
        """Verify integrity of all audit events

        Returns:
            Integrity verification report
        """
        total_events = len(self.events)
        verified_events = 0
        failed_events = []

        for event in self.events:
            if event.verify_integrity():
                verified_events += 1
            else:
                failed_events.append(event.id)

        return {
            "total_events": total_events,
            "verified_events": verified_events,
            "failed_events": len(failed_events),
            "failed_event_ids": failed_events,
            "integrity_percentage": (
                (verified_events / total_events * 100) if total_events > 0 else 100
            ),
        }


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None
_audit_trail: Optional[AuditTrail] = None


def get_audit_logger() -> AuditLogger:
    """Get or create global audit logger

    Returns:
        AuditLogger instance
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def get_audit_trail() -> AuditTrail:
    """Get or create global audit trail

    Returns:
        AuditTrail instance
    """
    global _audit_trail
    if _audit_trail is None:
        _audit_trail = AuditTrail()
    return _audit_trail


def log_audit_event(
    event_type: str,
    category: Union[AuditCategory, str],
    severity: Union[AuditSeverity, str],
    **kwargs,
) -> AuditEvent:
    """Log audit event using global logger and trail

    Args:
        event_type: Type of event
        category: Event category
        severity: Event severity
        **kwargs: Additional event parameters

    Returns:
        Created audit event
    """
    logger = get_audit_logger()
    trail = get_audit_trail()

    event = logger.create_event(
        event_type=event_type, category=category, severity=severity, **kwargs
    )

    trail.add_event(event)
    return event


# Convenience functions for common audit events
def log_authentication_event(
    event_type: str,
    user_id: str,
    success: bool = True,
    ip_address: Optional[str] = None,
    **kwargs,
) -> AuditEvent:
    """Log authentication event

    Args:
        event_type: Authentication event type
        user_id: User ID
        success: Whether authentication was successful
        ip_address: IP address
        **kwargs: Additional parameters

    Returns:
        Created audit event
    """
    return log_audit_event(
        event_type=event_type,
        category=AuditCategory.AUTHENTICATION,
        severity=AuditSeverity.MEDIUM if success else AuditSeverity.HIGH,
        user_id=user_id,
        ip_address=ip_address,
        details={"success": success, **kwargs},
    )


def log_data_access_event(
    resource_type: str, resource_id: str, user_id: str, action: str, **kwargs
) -> AuditEvent:
    """Log data access event

    Args:
        resource_type: Type of resource accessed
        resource_id: ID of resource accessed
        user_id: User ID
        action: Action performed
        **kwargs: Additional parameters

    Returns:
        Created audit event
    """
    return log_audit_event(
        event_type="data_access",
        category=AuditCategory.DATA_ACCESS,
        severity=AuditSeverity.LOW,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        action=action,
        **kwargs,
    )


def log_security_event(
    event_type: str, severity: Union[AuditSeverity, str] = AuditSeverity.HIGH, **kwargs
) -> AuditEvent:
    """Log security event

    Args:
        event_type: Security event type
        severity: Event severity
        **kwargs: Additional parameters

    Returns:
        Created audit event
    """
    return log_audit_event(
        event_type=event_type,
        category=AuditCategory.SECURITY,
        severity=severity,
        **kwargs,
    )


def log_compliance_event(event_type: str, **kwargs) -> AuditEvent:
    """Log compliance event

    Args:
        event_type: Compliance event type
        **kwargs: Additional parameters

    Returns:
        Created audit event
    """
    return log_audit_event(
        event_type=event_type,
        category=AuditCategory.COMPLIANCE,
        severity=AuditSeverity.MEDIUM,
        **kwargs,
    )
