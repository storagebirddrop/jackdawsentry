"""
Jackdaw Sentry - Audit Trail and Compliance Logging
Comprehensive audit trail system with immutable logging
Regulatory compliance logging and audit reporting
"""

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from src.api.config import settings
from src.api.database import get_neo4j_session
from src.api.database import get_redis_connection

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Audit event types"""

    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    CASE_CREATED = "case_created"
    CASE_UPDATED = "case_updated"
    CASE_CLOSED = "case_closed"
    EVIDENCE_ADDED = "evidence_added"
    EVIDENCE_MODIFIED = "evidence_modified"
    REPORT_GENERATED = "report_generated"
    REPORT_SUBMITTED = "report_submitted"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    API_ACCESS = "api_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SECURITY_BREACH = "security_breach"
    COMPLIANCE_CHECK = "compliance_check"
    REGULATORY_FILING = "regulatory_filing"


class AuditSeverity(Enum):
    """Audit event severity"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceCategory(Enum):
    """Compliance categories"""

    GDPR = "gdpr"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"
    AML = "aml"
    KYC = "kyc"
    ISO_27001 = "iso_27001"
    NIST = "nist"
    FINRA = "finra"
    SEC = "sec"


@dataclass
class AuditEvent:
    """Audit event"""

    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: str
    session_id: str
    ip_address: str
    user_agent: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    action: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    compliance_categories: List[ComplianceCategory] = field(default_factory=list)
    retention_period: timedelta = field(
        default_factory=lambda: timedelta(days=2555)
    )  # 7 years default
    event_hash: str = ""
    previous_hash: Optional[str] = None  # For chain integrity

    def calculate_hash(self, previous_hash: str = None) -> str:
        """Calculate event hash for integrity"""
        event_str = json.dumps(
            {
                "event_id": self.event_id,
                "event_type": self.event_type.value,
                "severity": self.severity.value,
                "user_id": self.user_id,
                "session_id": self.session_id,
                "ip_address": self.ip_address,
                "timestamp": self.timestamp.isoformat(),
                "resource_id": self.resource_id,
                "resource_type": self.resource_type,
                "action": self.action,
                "description": self.description,
                "details": self.details,
                "previous_hash": previous_hash,
            },
            sort_keys=True,
        )
        return hashlib.sha256(event_str.encode()).hexdigest()


@dataclass
class ComplianceLog:
    """Compliance log entry"""

    log_id: str
    compliance_category: ComplianceCategory
    requirement_id: str
    status: str  # compliant, non_compliant, partial
    timestamp: datetime = field(default_factory=datetime.utcnow)
    assessed_by: str = ""
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    evidence_references: List[str] = field(default_factory=list)
    next_review_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    """Audit report"""

    report_id: str
    report_type: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime = field(default_factory=datetime.utcnow)
    generated_by: str = ""
    summary: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    compliance_status: Dict[str, str] = field(default_factory=dict)
    total_events: int = 0
    critical_events: int = 0
    high_events: int = 0
    medium_events: int = 0
    low_events: int = 0


class AuditTrailEngine:
    """Audit trail and compliance logging engine"""

    def __init__(self):
        self.cache_ttl = 3600  # 1 hour
        self.chain_integrity_enabled = True
        self.compliance_requirements = {}

        # Initialize compliance requirements
        self._initialize_compliance_requirements()

    def _initialize_compliance_requirements(self):
        """Initialize compliance requirements"""
        self.compliance_requirements = {
            ComplianceCategory.GDPR: [
                {
                    "requirement_id": "GDPR_ART_5",
                    "name": "Principles relating to processing of personal data",
                    "description": "Personal data shall be processed lawfully, fairly and in a transparent manner",
                    "audit_events": ["user_login", "data_export", "data_import"],
                    "retention_period": timedelta(days=2555),  # 7 years
                },
                {
                    "requirement_id": "GDPR_ART_32",
                    "name": "Security of processing",
                    "description": "Appropriate technical and organisational measures shall be implemented",
                    "audit_events": [
                        "security_breach",
                        "privilege_escalation",
                        "system_config_change",
                    ],
                    "retention_period": timedelta(days=2555),
                },
            ],
            ComplianceCategory.AML: [
                {
                    "requirement_id": "AML_RECORD_KEEPING",
                    "name": "Record keeping requirements",
                    "description": "Maintain records for at least 5 years",
                    "audit_events": [
                        "case_created",
                        "evidence_added",
                        "report_generated",
                    ],
                    "retention_period": timedelta(days=1825),  # 5 years
                },
                {
                    "requirement_id": "AML_MONITORING",
                    "name": "Transaction monitoring",
                    "description": "Monitor and report suspicious transactions",
                    "audit_events": [
                        "case_created",
                        "report_submitted",
                        "regulatory_filing",
                    ],
                    "retention_period": timedelta(days=1825),
                },
            ],
            ComplianceCategory.SOX: [
                {
                    "requirement_id": "SOX_404",
                    "name": "Internal control over financial reporting",
                    "description": "Maintain internal controls and audit trails",
                    "audit_events": [
                        "report_generated",
                        "system_config_change",
                        "data_export",
                    ],
                    "retention_period": timedelta(days=2555),
                }
            ],
        }

    async def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        user_id: str,
        session_id: str,
        ip_address: str,
        user_agent: str,
        action: str = "",
        description: str = "",
        resource_id: str = None,
        resource_type: str = None,
        details: Dict[str, Any] = None,
        compliance_categories: List[ComplianceCategory] = None,
    ) -> str:
        """Log audit event"""
        try:
            event_id = f"audit_{uuid.uuid4()}"

            # Create audit event
            event = AuditEvent(
                event_id=event_id,
                event_type=event_type,
                severity=severity,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                action=action,
                description=description,
                resource_id=resource_id,
                resource_type=resource_type,
                details=details or {},
                compliance_categories=compliance_categories or [],
            )

            # Get previous hash for chain integrity
            if self.chain_integrity_enabled:
                previous_event = await self._get_latest_event()
                event.previous_hash = (
                    previous_event.event_hash if previous_event else None
                )
                event.event_hash = event.calculate_hash(event.previous_hash)
            else:
                event.event_hash = event.calculate_hash()

            # Store event
            await self._store_audit_event(event)

            # Update compliance logs if needed
            await self._update_compliance_logs(event)

            logger.info(f"Logged audit event {event_id}: {event_type.value}")

            return event_id

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            raise

    async def verify_chain_integrity(
        self, start_date: datetime = None, end_date: datetime = None
    ) -> Dict[str, Any]:
        """Verify audit trail chain integrity"""
        try:
            if not self.chain_integrity_enabled:
                return {
                    "verified": True,
                    "message": "Chain integrity not enabled",
                    "events_verified": 0,
                }

            # Get events for verification
            events = await self._get_events_for_verification(start_date, end_date)

            if not events:
                return {
                    "verified": True,
                    "message": "No events to verify",
                    "events_verified": 0,
                }

            # Verify chain integrity
            violations = []
            previous_hash = None

            for event in events:
                # Recalculate hash
                calculated_hash = event.calculate_hash(previous_hash)

                if calculated_hash != event.event_hash:
                    violations.append(
                        {
                            "event_id": event.event_id,
                            "timestamp": event.timestamp.isoformat(),
                            "stored_hash": event.event_hash,
                            "calculated_hash": calculated_hash,
                            "violation": "Hash mismatch",
                        }
                    )

                previous_hash = event.event_hash

            return {
                "verified": len(violations) == 0,
                "events_verified": len(events),
                "violations": violations,
                "verification_timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to verify chain integrity: {e}")
            return {"verified": False, "error": str(e), "events_verified": 0}

    async def generate_audit_report(
        self,
        report_type: str,
        period_start: datetime,
        period_end: datetime,
        generated_by: str,
        filters: Dict[str, Any] = None,
    ) -> AuditReport:
        """Generate audit report"""
        try:
            report_id = f"audit_report_{uuid.uuid4()}"

            # Get events for the period
            events = await self._get_events_by_period(period_start, period_end, filters)

            # Analyze events
            severity_counts = {
                AuditSeverity.LOW: 0,
                AuditSeverity.MEDIUM: 0,
                AuditSeverity.HIGH: 0,
                AuditSeverity.CRITICAL: 0,
            }

            event_type_counts = {}
            user_activity = {}
            compliance_status = {}

            for event in events:
                # Count by severity
                severity_counts[event.severity] += 1

                # Count by event type
                event_type_counts[event.event_type.value] = (
                    event_type_counts.get(event.event_type.value, 0) + 1
                )

                # Track user activity
                user_activity[event.user_id] = user_activity.get(event.user_id, 0) + 1

                # Check compliance categories
                for category in event.compliance_categories:
                    if category.value not in compliance_status:
                        compliance_status[category.value] = {
                            "compliant": 0,
                            "non_compliant": 0,
                            "total": 0,
                        }
                    compliance_status[category.value]["total"] += 1
                    # Simplified compliance check - in production would be more sophisticated
                    compliance_status[category.value]["compliant"] += 1

            # Identify findings
            findings = []

            # Critical events
            critical_events = [
                e for e in events if e.severity == AuditSeverity.CRITICAL
            ]
            if critical_events:
                findings.append(
                    {
                        "type": "critical_events",
                        "count": len(critical_events),
                        "description": f"Found {len(critical_events)} critical events requiring immediate attention",
                        "events": [
                            {
                                "event_id": e.event_id,
                                "timestamp": e.timestamp.isoformat(),
                                "description": e.description,
                                "user_id": e.user_id,
                            }
                            for e in critical_events[:5]  # Limit to top 5
                        ],
                    }
                )

            # Security events
            security_events = [
                e
                for e in events
                if e.event_type
                in [AuditEventType.SECURITY_BREACH, AuditEventType.PRIVILEGE_ESCALATION]
            ]
            if security_events:
                findings.append(
                    {
                        "type": "security_events",
                        "count": len(security_events),
                        "description": f"Found {len(security_events)} security-related events",
                        "events": [
                            {
                                "event_id": e.event_id,
                                "timestamp": e.timestamp.isoformat(),
                                "event_type": e.event_type.value,
                                "description": e.description,
                            }
                            for e in security_events
                        ],
                    }
                )

            # Generate recommendations
            recommendations = []

            if severity_counts[AuditSeverity.CRITICAL] > 0:
                recommendations.append(
                    "Review and address all critical events immediately"
                )

            if severity_counts[AuditSeverity.HIGH] > 10:
                recommendations.append(
                    "Consider implementing additional security controls"
                )

            if len(user_activity) > 100:
                recommendations.append(
                    "Review user access patterns and implement principle of least privilege"
                )

            # Create report
            report = AuditReport(
                report_id=report_id,
                report_type=report_type,
                period_start=period_start,
                period_end=period_end,
                generated_by=generated_by,
                summary={
                    "total_events": len(events),
                    "severity_breakdown": {
                        k.value: v for k, v in severity_counts.items()
                    },
                    "event_type_breakdown": event_type_counts,
                    "unique_users": len(user_activity),
                    "compliance_categories": list(compliance_status.keys()),
                },
                findings=findings,
                recommendations=recommendations,
                compliance_status=compliance_status,
                total_events=len(events),
                critical_events=severity_counts[AuditSeverity.CRITICAL],
                high_events=severity_counts[AuditSeverity.HIGH],
                medium_events=severity_counts[AuditSeverity.MEDIUM],
                low_events=severity_counts[AuditSeverity.LOW],
            )

            # Store report
            await self._store_audit_report(report)

            logger.info(
                f"Generated audit report {report_id} for period {period_start} to {period_end}"
            )

            return report

        except Exception as e:
            logger.error(f"Failed to generate audit report: {e}")
            raise

    async def get_compliance_status(
        self, category: ComplianceCategory = None
    ) -> Dict[str, Any]:
        """Get compliance status"""
        try:
            if category:
                return await self._get_category_compliance_status(category)
            else:
                return await self._get_all_compliance_status()
        except Exception as e:
            logger.error(f"Failed to get compliance status: {e}")
            raise

    async def search_audit_events(
        self,
        event_types: List[AuditEventType] = None,
        severity: AuditSeverity = None,
        user_id: str = None,
        date_range: tuple = None,
        resource_id: str = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Search audit events"""
        try:
            # Get all events (in production, this would use proper database queries)
            all_events = await self._get_all_events()

            filtered_events = []
            for event in all_events:
                # Apply filters
                if event_types and event.event_type not in event_types:
                    continue
                if severity and event.severity != severity:
                    continue
                if user_id and event.user_id != user_id:
                    continue
                if date_range:
                    start_date, end_date = date_range
                    if event.timestamp < start_date or event.timestamp > end_date:
                        continue
                if resource_id and event.resource_id != resource_id:
                    continue

                filtered_events.append(event)

            # Sort by timestamp (most recent first)
            filtered_events.sort(key=lambda x: x.timestamp, reverse=True)

            return filtered_events[:limit]

        except Exception as e:
            logger.error(f"Failed to search audit events: {e}")
            return []

    async def _store_audit_event(self, event: AuditEvent):
        """Store audit event"""
        try:
            async with get_neo4j_session() as session:
                query = """
                CREATE (e:AuditEvent {
                    event_id: $event_id,
                    event_type: $event_type,
                    severity: $severity,
                    user_id: $user_id,
                    session_id: $session_id,
                    ip_address: $ip_address,
                    user_agent: $user_agent,
                    timestamp: $timestamp,
                    resource_id: $resource_id,
                    resource_type: $resource_type,
                    action: $action,
                    description: $description,
                    details: $details,
                    compliance_categories: $compliance_categories,
                    retention_period: $retention_period,
                    event_hash: $event_hash,
                    previous_hash: $previous_hash
                })
                """
                await session.run(
                    query,
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type.value,
                        "severity": event.severity.value,
                        "user_id": event.user_id,
                        "session_id": event.session_id,
                        "ip_address": event.ip_address,
                        "user_agent": event.user_agent,
                        "timestamp": event.timestamp.isoformat(),
                        "resource_id": event.resource_id,
                        "resource_type": event.resource_type,
                        "action": event.action,
                        "description": event.description,
                        "details": json.dumps(event.details),
                        "compliance_categories": [
                            cat.value for cat in event.compliance_categories
                        ],
                        "retention_period": event.retention_period.total_seconds(),
                        "event_hash": event.event_hash,
                        "previous_hash": event.previous_hash,
                    },
                )
        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")
            raise

    async def _get_latest_event(self) -> Optional[AuditEvent]:
        """Get latest audit event"""
        try:
            async with get_neo4j_session() as session:
                query = (
                    "MATCH (e:AuditEvent) RETURN e ORDER BY e.timestamp DESC LIMIT 1"
                )
                result = await session.run(query)
                record = await result.single()

                if record:
                    data = record["e"]
                    return AuditEvent(
                        event_id=data["event_id"],
                        event_type=AuditEventType(data["event_type"]),
                        severity=AuditSeverity(data["severity"]),
                        user_id=data["user_id"],
                        session_id=data["session_id"],
                        ip_address=data["ip_address"],
                        user_agent=data["user_agent"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        resource_id=data.get("resource_id"),
                        resource_type=data.get("resource_type"),
                        action=data.get("action", ""),
                        description=data.get("description", ""),
                        details=json.loads(data.get("details", "{}")),
                        compliance_categories=[
                            ComplianceCategory(cat)
                            for cat in data.get("compliance_categories", [])
                        ],
                        retention_period=timedelta(
                            seconds=data.get("retention_period", 0)
                        ),
                        event_hash=data.get("event_hash", ""),
                        previous_hash=data.get("previous_hash"),
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get latest event: {e}")
            return None

    async def _get_events_for_verification(
        self, start_date: datetime = None, end_date: datetime = None
    ) -> List[AuditEvent]:
        """Get events for chain verification"""
        try:
            async with get_neo4j_session() as session:
                if start_date and end_date:
                    query = """
                    MATCH (e:AuditEvent)
                    WHERE e.timestamp >= $start_date AND e.timestamp <= $end_date
                    RETURN e ORDER BY e.timestamp ASC
                    """
                    result = await session.run(
                        query,
                        {
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                        },
                    )
                else:
                    query = "MATCH (e:AuditEvent) RETURN e ORDER BY e.timestamp ASC"
                    result = await session.run(query)

                records = await result.data()
                events = []

                for record in records:
                    data = record["e"]
                    event = AuditEvent(
                        event_id=data["event_id"],
                        event_type=AuditEventType(data["event_type"]),
                        severity=AuditSeverity(data["severity"]),
                        user_id=data["user_id"],
                        session_id=data["session_id"],
                        ip_address=data["ip_address"],
                        user_agent=data["user_agent"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        resource_id=data.get("resource_id"),
                        resource_type=data.get("resource_type"),
                        action=data.get("action", ""),
                        description=data.get("description", ""),
                        details=json.loads(data.get("details", "{}")),
                        compliance_categories=[
                            ComplianceCategory(cat)
                            for cat in data.get("compliance_categories", [])
                        ],
                        retention_period=timedelta(
                            seconds=data.get("retention_period", 0)
                        ),
                        event_hash=data.get("event_hash", ""),
                        previous_hash=data.get("previous_hash"),
                    )
                    events.append(event)

                return events
        except Exception as e:
            logger.error(f"Failed to get events for verification: {e}")
            return []

    async def _get_events_by_period(
        self, start_date: datetime, end_date: datetime, filters: Dict[str, Any] = None
    ) -> List[AuditEvent]:
        """Get events by time period"""
        try:
            async with get_neo4j_session() as session:
                query = """
                MATCH (e:AuditEvent)
                WHERE e.timestamp >= $start_date AND e.timestamp <= $end_date
                RETURN e ORDER BY e.timestamp DESC
                """
                result = await session.run(
                    query,
                    {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                )

                records = await result.data()
                events = []

                for record in records:
                    data = record["e"]
                    event = AuditEvent(
                        event_id=data["event_id"],
                        event_type=AuditEventType(data["event_type"]),
                        severity=AuditSeverity(data["severity"]),
                        user_id=data["user_id"],
                        session_id=data["session_id"],
                        ip_address=data["ip_address"],
                        user_agent=data["user_agent"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        resource_id=data.get("resource_id"),
                        resource_type=data.get("resource_type"),
                        action=data.get("action", ""),
                        description=data.get("description", ""),
                        details=json.loads(data.get("details", "{}")),
                        compliance_categories=[
                            ComplianceCategory(cat)
                            for cat in data.get("compliance_categories", [])
                        ],
                        retention_period=timedelta(
                            seconds=data.get("retention_period", 0)
                        ),
                        event_hash=data.get("event_hash", ""),
                        previous_hash=data.get("previous_hash"),
                    )
                    events.append(event)

                return events
        except Exception as e:
            logger.error(f"Failed to get events by period: {e}")
            return []

    async def _get_all_events(self) -> List[AuditEvent]:
        """Get all audit events"""
        try:
            async with get_neo4j_session() as session:
                query = "MATCH (e:AuditEvent) RETURN e ORDER BY e.timestamp DESC"
                result = await session.run(query)
                records = await result.data()

                events = []
                for record in records:
                    data = record["e"]
                    event = AuditEvent(
                        event_id=data["event_id"],
                        event_type=AuditEventType(data["event_type"]),
                        severity=AuditSeverity(data["severity"]),
                        user_id=data["user_id"],
                        session_id=data["session_id"],
                        ip_address=data["ip_address"],
                        user_agent=data["user_agent"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        resource_id=data.get("resource_id"),
                        resource_type=data.get("resource_type"),
                        action=data.get("action", ""),
                        description=data.get("description", ""),
                        details=json.loads(data.get("details", "{}")),
                        compliance_categories=[
                            ComplianceCategory(cat)
                            for cat in data.get("compliance_categories", [])
                        ],
                        retention_period=timedelta(
                            seconds=data.get("retention_period", 0)
                        ),
                        event_hash=data.get("event_hash", ""),
                        previous_hash=data.get("previous_hash"),
                    )
                    events.append(event)

                return events
        except Exception as e:
            logger.error(f"Failed to get all events: {e}")
            return []

    async def _store_audit_report(self, report: AuditReport):
        """Store audit report"""
        try:
            async with get_neo4j_session() as session:
                query = """
                CREATE (r:AuditReport {
                    report_id: $report_id,
                    report_type: $report_type,
                    period_start: $period_start,
                    period_end: $period_end,
                    generated_at: $generated_at,
                    generated_by: $generated_by,
                    summary: $summary,
                    findings: $findings,
                    recommendations: $recommendations,
                    compliance_status: $compliance_status,
                    total_events: $total_events,
                    critical_events: $critical_events,
                    high_events: $high_events,
                    medium_events: $medium_events,
                    low_events: $low_events
                })
                """
                await session.run(
                    query,
                    {
                        "report_id": report.report_id,
                        "report_type": report.report_type,
                        "period_start": report.period_start.isoformat(),
                        "period_end": report.period_end.isoformat(),
                        "generated_at": report.generated_at.isoformat(),
                        "generated_by": report.generated_by,
                        "summary": json.dumps(report.summary),
                        "findings": json.dumps(report.findings),
                        "recommendations": json.dumps(report.recommendations),
                        "compliance_status": json.dumps(report.compliance_status),
                        "total_events": report.total_events,
                        "critical_events": report.critical_events,
                        "high_events": report.high_events,
                        "medium_events": report.medium_events,
                        "low_events": report.low_events,
                    },
                )
        except Exception as e:
            logger.error(f"Failed to store audit report: {e}")
            raise

    async def _update_compliance_logs(self, event: AuditEvent):
        """Update compliance logs based on event"""
        try:
            for category in event.compliance_categories:
                # Update compliance status for category
                # In production, this would be more sophisticated
                pass
        except Exception as e:
            logger.error(f"Failed to update compliance logs: {e}")

    async def _get_category_compliance_status(
        self, category: ComplianceCategory
    ) -> Dict[str, Any]:
        """Get compliance status for specific category"""
        try:
            requirements = self.compliance_requirements.get(category, [])

            status = {
                "category": category.value,
                "requirements": [],
                "overall_status": "compliant",
                "last_assessed": datetime.now(timezone.utc).isoformat(),
            }

            for req in requirements:
                # Check if events exist for this requirement
                events_count = len(
                    await self.search_audit_events(
                        event_types=[AuditEventType(ev) for ev in req["audit_events"]]
                    )
                )

                req_status = {
                    "requirement_id": req["requirement_id"],
                    "name": req["name"],
                    "status": "compliant" if events_count > 0 else "non_compliant",
                    "events_count": events_count,
                    "last_activity": None,
                }

                status["requirements"].append(req_status)

                if req_status["status"] == "non_compliant":
                    status["overall_status"] = "non_compliant"

            return status
        except Exception as e:
            logger.error(f"Failed to get category compliance status: {e}")
            return {}

    async def _get_all_compliance_status(self) -> Dict[str, Any]:
        """Get compliance status for all categories"""
        try:
            status = {
                "categories": {},
                "overall_status": "compliant",
                "last_assessed": datetime.now(timezone.utc).isoformat(),
            }

            for category in ComplianceCategory:
                category_status = await self._get_category_compliance_status(category)
                status["categories"][category.value] = category_status

                if category_status.get("overall_status") == "non_compliant":
                    status["overall_status"] = "non_compliant"

            return status
        except Exception as e:
            logger.error(f"Failed to get all compliance status: {e}")
            return {}


# Global audit trail engine instance
_audit_trail_engine: Optional[AuditTrailEngine] = None


def get_audit_trail_engine() -> AuditTrailEngine:
    """Get global audit trail engine instance"""
    global _audit_trail_engine
    if _audit_trail_engine is None:
        _audit_trail_engine = AuditTrailEngine()
    return _audit_trail_engine
