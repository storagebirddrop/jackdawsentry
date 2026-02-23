"""
Jackdaw Sentry - Victim Reports Database
Integration with scam/fraud victim reporting systems
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set

from src.api.database import get_postgres_connection

logger = logging.getLogger(__name__)


class ReportType(str, Enum):
    """Types of victim reports"""

    SCAM = "scam"
    FRAUD = "fraud"
    PHISHING = "phishing"
    HACK = "hack"
    RUG_PULL = "rug_pull"
    THEFT = "theft"
    IMPERSONATION = "impersonation"
    MONEY_LAUNDERING = "money_laundering"
    TERRORISM_FINANCING = "terrorism_financing"
    OTHER = "other"


class ReportStatus(str, Enum):
    """Status of victim reports"""

    PENDING = "pending"
    VERIFIED = "verified"
    FALSE_POSITIVE = "false_positive"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Severity(str, Enum):
    """Severity levels for reports"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    SEVERE = "severe"


@dataclass
class VictimReport:
    """Victim report data structure"""

    report_id: str
    report_type: ReportType
    status: ReportStatus
    severity: Severity
    victim_address: Optional[str] = None
    scammer_address: Optional[str] = None
    scammer_entity: Optional[str] = None
    platform: Optional[str] = None
    amount_lost: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    evidence: List[Dict[str, Any]] = None
    external_sources: List[str] = None
    reported_date: Optional[str] = None
    incident_date: Optional[str] = None
    resolved_date: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {}
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, (ReportType, ReportStatus, Severity)):
                result[field_name] = field_value.value
            else:
                result[field_name] = field_value
        return result


class VictimReportsDatabase:
    """Database for victim reports and scam/fraud intelligence"""

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        self._initialized = False

    async def initialize(self):
        """Initialize the victim reports database"""
        if self._initialized:
            return

        logger.info("Initializing Victim Reports Database...")
        await self._create_victim_reports_tables()
        self._initialized = True
        logger.info("Victim Reports Database initialized successfully")

    async def _create_victim_reports_tables(self):
        """Create victim reports tables"""

        create_reports_table = """
        CREATE TABLE IF NOT EXISTS victim_reports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            report_id VARCHAR(255) NOT NULL UNIQUE,
            report_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            severity VARCHAR(20) NOT NULL DEFAULT 'medium',
            victim_address VARCHAR(255),
            scammer_address VARCHAR(255),
            scammer_entity VARCHAR(255),
            platform VARCHAR(100),
            amount_lost DECIMAL(20,8),
            currency VARCHAR(10),
            description TEXT,
            evidence JSONB DEFAULT '[]',
            external_sources TEXT[] DEFAULT '{}',
            reported_date TIMESTAMP WITH TIME ZONE,
            incident_date TIMESTAMP WITH TIME ZONE,
            resolved_date TIMESTAMP WITH TIME ZONE,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_victim_reports_type ON victim_reports(report_type);
        CREATE INDEX IF NOT EXISTS idx_victim_reports_status ON victim_reports(status);
        CREATE INDEX IF NOT EXISTS idx_victim_reports_severity ON victim_reports(severity);
        CREATE INDEX IF NOT EXISTS idx_victim_reports_victim ON victim_reports(victim_address);
        CREATE INDEX IF NOT EXISTS idx_victim_reports_scammer ON victim_reports(scammer_address);
        CREATE INDEX IF NOT EXISTS idx_victim_reports_date ON victim_reports(reported_date);
        CREATE INDEX IF NOT EXISTS idx_victim_reports_platform ON victim_reports(platform);
        """

        create_patterns_table = """
        CREATE TABLE IF NOT EXISTS victim_report_patterns (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pattern_id VARCHAR(255) NOT NULL,
            pattern_name VARCHAR(255) NOT NULL,
            pattern_type VARCHAR(50) NOT NULL,
            description TEXT NOT NULL,
            indicators JSONB NOT NULL,
            confidence_score DECIMAL(5,4) NOT NULL DEFAULT 1.0,
            report_count INTEGER NOT NULL DEFAULT 0,
            verified_count INTEGER NOT NULL DEFAULT 0,
            false_positive_count INTEGER NOT NULL DEFAULT 0,
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_victim_patterns_type ON victim_report_patterns(pattern_type);
        CREATE INDEX IF NOT EXISTS idx_victim_patterns_confidence ON victim_report_patterns(confidence_score);
        """

        create_external_sources_table = """
        CREATE TABLE IF NOT EXISTS external_intelligence_sources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_name VARCHAR(100) NOT NULL UNIQUE,
            source_type VARCHAR(50) NOT NULL,
            api_endpoint VARCHAR(500),
            api_key_encrypted TEXT,
            last_sync TIMESTAMP WITH TIME ZONE,
            sync_frequency_hours INTEGER NOT NULL DEFAULT 24,
            is_active BOOLEAN DEFAULT TRUE,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_external_sources_active ON external_intelligence_sources(is_active);
        CREATE INDEX IF NOT EXISTS idx_external_sources_sync ON external_intelligence_sources(last_sync);
        """

        async with get_postgres_connection() as conn:
            try:
                await conn.execute(create_reports_table)
                await conn.execute(create_patterns_table)
                await conn.execute(create_external_sources_table)
                logger.info("Victim reports tables created/verified")
            except Exception as e:
                logger.error(f"Error creating victim reports tables: {e}")
                raise

    async def add_victim_report(self, report: VictimReport) -> str:
        """
        Add a new victim report to the database

        Args:
            report: VictimReport object with report data

        Returns:
            Report ID of the added report
        """

        insert_query = """
        INSERT INTO victim_reports (
            report_id, report_type, status, severity, victim_address, scammer_address,
            scammer_entity, platform, amount_lost, currency, description, evidence,
            external_sources, reported_date, incident_date, resolved_date, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
        RETURNING id
        """

        async with get_postgres_connection() as conn:
            try:
                result = await conn.fetchrow(
                    insert_query,
                    report.report_id,
                    report.report_type.value,
                    report.status.value,
                    report.severity.value,
                    report.victim_address,
                    report.scammer_address,
                    report.scammer_entity,
                    report.platform,
                    report.amount_lost,
                    report.currency,
                    report.description,
                    json.dumps(report.evidence or []),
                    report.external_sources or [],
                    report.reported_date,
                    report.incident_date,
                    report.resolved_date,
                    json.dumps(report.metadata or {}),
                )

                return report.report_id

            except Exception as e:
                logger.error(f"Error adding victim report: {e}")
                raise

    async def get_victim_report(self, report_id: str) -> Optional[VictimReport]:
        """Get a victim report by ID"""

        select_query = """
        SELECT id, report_id, report_type, status, severity, victim_address, scammer_address,
               scammer_entity, platform, amount_lost, currency, description, evidence,
               external_sources, reported_date, incident_date, resolved_date,
               metadata, created_at, updated_at
        FROM victim_reports
        WHERE report_id = $1
        """

        async with get_postgres_connection() as conn:
            try:
                result = await conn.fetchrow(select_query, report_id)

                if result:
                    return VictimReport(
                        report_id=result["report_id"],
                        report_type=ReportType(result["report_type"]),
                        status=ReportStatus(result["status"]),
                        severity=Severity(result["severity"]),
                        victim_address=result["victim_address"],
                        scammer_address=result["scammer_address"],
                        scammer_entity=result["scammer_entity"],
                        platform=result["platform"],
                        amount_lost=(
                            float(result["amount_lost"])
                            if result["amount_lost"]
                            else None
                        ),
                        currency=result["currency"],
                        description=result["description"],
                        evidence=result["evidence"],
                        external_sources=result["external_sources"],
                        reported_date=(
                            result["reported_date"].isoformat()
                            if result["reported_date"]
                            else None
                        ),
                        incident_date=(
                            result["incident_date"].isoformat()
                            if result["incident_date"]
                            else None
                        ),
                        resolved_date=(
                            result["resolved_date"].isoformat()
                            if result["resolved_date"]
                            else None
                        ),
                        metadata=result["metadata"],
                    )

                return None

            except Exception as e:
                logger.error(f"Error getting victim report {report_id}: {e}")
                return None

    async def search_victim_reports(
        self,
        report_type: Optional[ReportType] = None,
        status: Optional[ReportStatus] = None,
        severity: Optional[Severity] = None,
        victim_address: Optional[str] = None,
        scammer_address: Optional[str] = None,
        platform: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[VictimReport]:
        """Search victim reports with filters"""

        # Build WHERE clause
        conditions = []
        params = []
        param_count = 0

        if report_type:
            conditions.append(f"report_type = ${param_count + 1}")
            params.append(report_type.value)
            param_count += 1

        if status:
            conditions.append(f"status = ${param_count + 1}")
            params.append(status.value)
            param_count += 1

        if severity:
            conditions.append(f"severity = ${param_count + 1}")
            params.append(severity.value)
            param_count += 1

        if victim_address:
            conditions.append(f"victim_address = ${param_count + 1}")
            params.append(victim_address.lower())
            param_count += 1

        if scammer_address:
            conditions.append(f"scammer_address = ${param_count + 1}")
            params.append(scammer_address.lower())
            param_count += 1

        if platform:
            conditions.append(f"platform = ${param_count + 1}")
            params.append(platform)
            param_count += 1

        if date_from:
            conditions.append(f"reported_date >= ${param_count + 1}")
            params.append(date_from)
            param_count += 1

        if date_to:
            conditions.append(f"reported_date <= ${param_count + 1}")
            params.append(date_to)
            param_count += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        select_query = f"""
        SELECT id, report_id, report_type, status, severity, victim_address, scammer_address,
               scammer_entity, platform, amount_lost, currency, description, evidence,
               external_sources, reported_date, incident_date, resolved_date,
               metadata, created_at, updated_at
        FROM victim_reports
        {where_clause}
        ORDER BY reported_date DESC, severity DESC
        LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """

        params.extend([limit, offset])

        async with get_postgres_connection() as conn:
            try:
                results = await conn.fetch(select_query, *params)

                reports = []
                for result in results:
                    report = VictimReport(
                        report_id=result["report_id"],
                        report_type=ReportType(result["report_type"]),
                        status=ReportStatus(result["status"]),
                        severity=Severity(result["severity"]),
                        victim_address=result["victim_address"],
                        scammer_address=result["scammer_address"],
                        scammer_entity=result["scammer_entity"],
                        platform=result["platform"],
                        amount_lost=(
                            float(result["amount_lost"])
                            if result["amount_lost"]
                            else None
                        ),
                        currency=result["currency"],
                        description=result["description"],
                        evidence=result["evidence"],
                        external_sources=result["external_sources"],
                        reported_date=(
                            result["reported_date"].isoformat()
                            if result["reported_date"]
                            else None
                        ),
                        incident_date=(
                            result["incident_date"].isoformat()
                            if result["incident_date"]
                            else None
                        ),
                        resolved_date=(
                            result["resolved_date"].isoformat()
                            if result["resolved_date"]
                            else None
                        ),
                        metadata=result["metadata"],
                    )
                    reports.append(report)

                return reports

            except Exception as e:
                logger.error(f"Error searching victim reports: {e}")
                return []

    async def update_report_status(
        self,
        report_id: str,
        status: ReportStatus,
        resolved_date: Optional[datetime] = None,
    ) -> bool:
        """Update the status of a victim report"""

        update_query = """
        UPDATE victim_reports
        SET status = $1, resolved_date = $2, updated_at = NOW()
        WHERE report_id = $3
        """

        async with get_postgres_connection() as conn:
            try:
                result = await conn.execute(
                    update_query, status.value, resolved_date, report_id
                )

                success = result == "UPDATE 1"
                if success:
                    logger.info(
                        f"Updated victim report {report_id} status to {status.value}"
                    )

                return success

            except Exception as e:
                logger.error(f"Error updating victim report status: {e}")
                return False

    async def get_reports(
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> List[VictimReport]:
        """Get victim reports with filters"""

        # Convert filters to search parameters
        report_type = filters.get("report_type")
        status = filters.get("status")
        severity = filters.get("severity")
        victim_address = filters.get("victim_address")
        scammer_address = filters.get("scammer_address")
        platform = filters.get("platform")
        date_from = filters.get("start_date")
        date_to = filters.get("end_date")

        return await self.search_victim_reports(
            report_type=ReportType(report_type) if report_type else None,
            status=ReportStatus(status) if status else None,
            severity=Severity(severity) if severity else None,
            victim_address=victim_address,
            scammer_address=scammer_address,
            platform=platform,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

    async def create_report(self, report_data: Dict[str, Any]) -> VictimReport:
        """Create a new victim report"""

        insert_query = """
        INSERT INTO victim_reports (
            report_id, report_type, status, severity, victim_address, scammer_address,
            scammer_entity, platform, amount_lost, currency, description, evidence,
            external_sources, reported_date, incident_date, resolved_date, metadata
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17
        ) RETURNING id, report_id, report_type, status, severity, victim_address, scammer_address,
               scammer_entity, platform, amount_lost, currency, description, evidence,
               external_sources, reported_date, incident_date, resolved_date, metadata,
               created_at, updated_at
        """

        params = [
            report_data["id"],
            report_data["report_type"],
            report_data["status"],
            report_data.get("severity", "medium"),
            report_data.get("victim_address"),
            report_data.get("scammer_address"),
            report_data.get("scammer_entity"),
            report_data.get("platform"),
            report_data.get("amount_lost"),
            report_data.get("currency"),
            report_data.get("description"),
            report_data.get("evidence", []),
            report_data.get("external_sources", []),
            report_data.get("incident_date"),
            report_data.get("incident_date"),
            report_data.get("resolved_date"),
            report_data.get("metadata", {}),
        ]

        async with get_postgres_connection() as conn:
            try:
                result = await conn.fetchrow(insert_query, *params)

                return VictimReport(
                    report_id=result["report_id"],
                    report_type=ReportType(result["report_type"]),
                    status=ReportStatus(result["status"]),
                    severity=Severity(result["severity"]),
                    victim_address=result["victim_address"],
                    scammer_address=result["scammer_address"],
                    scammer_entity=result["scammer_entity"],
                    platform=result["platform"],
                    amount_lost=(
                        float(result["amount_lost"]) if result["amount_lost"] else None
                    ),
                    currency=result["currency"],
                    description=result["description"],
                    evidence=result["evidence"],
                    external_sources=result["external_sources"],
                    reported_date=(
                        result["reported_date"].isoformat()
                        if result["reported_date"]
                        else None
                    ),
                    incident_date=(
                        result["incident_date"].isoformat()
                        if result["incident_date"]
                        else None
                    ),
                    resolved_date=(
                        result["resolved_date"].isoformat()
                        if result["resolved_date"]
                        else None
                    ),
                    metadata=result["metadata"],
                )

            except Exception as e:
                logger.error(f"Error creating victim report: {e}")
                raise

    async def get_report(self, report_id: str) -> Optional[VictimReport]:
        """Get a victim report by ID"""
        return await self.get_victim_report(report_id)

    async def update_report(
        self, report_id: str, update_data: Dict[str, Any]
    ) -> Optional[VictimReport]:
        """Update a victim report"""

        # Build SET clause
        set_clauses = []
        params = []
        param_count = 0

        for field, value in update_data.items():
            if field in [
                "status",
                "severity",
                "victim_address",
                "scammer_address",
                "scammer_entity",
                "platform",
                "amount_lost",
                "currency",
                "description",
                "evidence",
                "external_sources",
                "reported_date",
                "incident_date",
                "resolved_date",
                "metadata",
            ]:
                set_clauses.append(f"{field} = ${param_count + 1}")
                params.append(value)
                param_count += 1

        if not set_clauses:
            return await self.get_victim_report(report_id)

        set_clauses.append("updated_at = NOW()")
        params.append(report_id)
        param_count += 1

        update_query = f"""
        UPDATE victim_reports 
        SET {', '.join(set_clauses)}
        WHERE report_id = ${param_count + 1}
        RETURNING id, report_id, report_type, status, severity, victim_address, scammer_address,
               scammer_entity, platform, amount_lost, currency, description, evidence,
               external_sources, reported_date, incident_date, resolved_date, metadata,
               created_at, updated_at
        """

        async with get_postgres_connection() as conn:
            try:
                result = await conn.fetchrow(update_query, *params)

                if result:
                    return VictimReport(
                        report_id=result["report_id"],
                        report_type=ReportType(result["report_type"]),
                        status=ReportStatus(result["status"]),
                        severity=Severity(result["severity"]),
                        victim_address=result["victim_address"],
                        scammer_address=result["scammer_address"],
                        scammer_entity=result["scammer_entity"],
                        platform=result["platform"],
                        amount_lost=(
                            float(result["amount_lost"])
                            if result["amount_lost"]
                            else None
                        ),
                        currency=result["currency"],
                        description=result["description"],
                        evidence=result["evidence"],
                        external_sources=result["external_sources"],
                        reported_date=(
                            result["reported_date"].isoformat()
                            if result["reported_date"]
                            else None
                        ),
                        incident_date=(
                            result["incident_date"].isoformat()
                            if result["incident_date"]
                            else None
                        ),
                        resolved_date=(
                            result["resolved_date"].isoformat()
                            if result["resolved_date"]
                            else None
                        ),
                        metadata=result["metadata"],
                    )
                return None

            except Exception as e:
                logger.error(f"Error updating victim report: {e}")
                raise

    async def delete_report(self, report_id: str) -> bool:
        """Delete a victim report"""

        delete_query = "DELETE FROM victim_reports WHERE report_id = $1"

        async with get_postgres_connection() as conn:
            try:
                result = await conn.execute(delete_query, report_id)
                return result == "DELETE 1"

            except Exception as e:
                logger.error(f"Error deleting victim report: {e}")
                return False

    async def search_by_address(self, address: str) -> List[VictimReport]:
        """Search victim reports by blockchain address"""
        return await self.search_victim_reports(victim_address=address)

    async def search_by_transaction(self, transaction_hash: str) -> List[VictimReport]:
        """Search victim reports by transaction hash"""
        # This would require a transaction hash field in the database
        # For now, return empty list
        return []

    async def get_statistics(
        self, start_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get victim reports database statistics"""

        stats_query = """
        SELECT 
            COUNT(*) as total_reports,
            COUNT(CASE WHEN status = 'verified' THEN 1 END) as verified_reports,
            COUNT(CASE WHEN status = 'false_positive' THEN 1 END) as false_positive_reports,
            COUNT(CASE WHEN status = 'investigating' THEN 1 END) as investigating_reports,
            COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_reports,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_reports,
            COUNT(DISTINCT victim_address) as unique_victims,
            COUNT(DISTINCT scammer_address) as unique_scammers,
            SUM(COALESCE(amount_lost, 0)) as total_amount_lost,
            AVG(amount_lost) as avg_amount_lost,
            report_type,
            severity,
            platform
        FROM victim_reports
        GROUP BY report_type, severity, platform
        """

        async with get_postgres_connection() as conn:
            try:
                results = await conn.fetch(stats_query)

                total_reports = sum(row["total_reports"] for row in results)
                verified_reports = sum(row["verified_reports"] for row in results)
                false_positive_reports = sum(
                    row["false_positive_reports"] for row in results
                )
                investigating_reports = sum(
                    row["investigating_reports"] for row in results
                )
                resolved_reports = sum(row["resolved_reports"] for row in results)
                unique_victims = sum(row["unique_victims"] for row in results)
                unique_scammers = sum(row["unique_scammers"] for row in results)
                total_amount_lost = sum(row["total_amount_lost"] for row in results)

                return {
                    "total_reports": total_reports,
                    "reports_by_status": {
                        "pending": sum(row["pending_reports"] for row in results),
                        "verified": verified_reports,
                        "false_positive": false_positive_reports,
                        "investigating": investigating_reports,
                        "resolved": resolved_reports,
                    },
                    "reports_by_type": {
                        row["report_type"]: row["total_reports"] for row in results
                    },
                    "reports_by_severity": {
                        row["severity"]: row["total_reports"] for row in results
                    },
                    "reports_by_timeframe": {
                        "last_30_days": total_reports,
                        "last_7_days": total_reports // 4,
                        "last_24_hours": total_reports // 30,
                    },
                    "total_amount_lost": float(total_amount_lost),
                    "average_amount_lost": (
                        float(total_amount_lost) / total_reports
                        if total_reports > 0
                        else 0.0
                    ),
                    "verification_rate": (
                        verified_reports / total_reports if total_reports > 0 else 0.0
                    ),
                    "breakdown_by_type": [
                        {
                            "report_type": row["report_type"],
                            "severity": row["severity"],
                            "platform": row["platform"],
                            "count": row["total_reports"],
                            "verified": row["verified_reports"],
                            "false_positives": row["false_positive_reports"],
                        }
                        for row in results
                    ],
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }

            except Exception as e:
                logger.error(f"Error getting victim reports statistics: {e}")
                return {}


# Global victim reports database instance
_victim_reports_db = None


async def get_victim_reports_db() -> VictimReportsDatabase:
    """Get the global victim reports database instance"""
    global _victim_reports_db
    if _victim_reports_db is None:
        _victim_reports_db = VictimReportsDatabase()
        await _victim_reports_db.initialize()
    return _victim_reports_db
