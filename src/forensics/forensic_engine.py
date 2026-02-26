"""
Jackdaw Sentry - Advanced Forensics Engine
Professional forensic analysis tools and evidence management
"""

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set

logger = logging.getLogger(__name__)


class ForensicCaseStatus(Enum):
    """Forensic case lifecycle status"""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    EVIDENCE_COLLECTION = "evidence_collection"
    ANALYSIS = "analysis"
    REVIEW = "review"
    CLOSED = "closed"
    ARCHIVED = "archived"


class EvidenceType(Enum):
    """Types of forensic evidence"""

    TRANSACTION_DATA = "transaction_data"
    BLOCKCHAIN_DATA = "blockchain_data"
    ADDRESS_ANALYSIS = "address_analysis"
    NETWORK_TRAFFIC = "network_traffic"
    COMMUNICATION_LOGS = "communication_logs"
    DOCUMENTS = "documents"
    IMAGES = "images"
    VIDEOS = "videos"
    AUDIO = "audio"
    METADATA = "metadata"
    TESTIMONY = "testimony"
    EXPERT_REPORT = "expert_report"
    OTHER = "other"


class EvidenceIntegrity(Enum):
    """Evidence integrity verification status"""

    VERIFIED = "verified"
    TAMPERED = "tampered"
    SUSPICIOUS = "suspicious"
    UNKNOWN = "unknown"


class LegalStandard(Enum):
    """Legal standards for evidence admissibility"""

    PREPONDERANCE = "preponderance"  # 50%+ likelihood
    CLEAR_AND_CONVINCING = "clear_and_convincing"  # 75%+ likelihood
    BEYOND_REASONABLE_DOUBT = "beyond_reasonable_doubt"  # 95%+ likelihood


@dataclass
class ForensicEvidence:
    """Individual piece of forensic evidence"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str = ""
    evidence_type: EvidenceType = EvidenceType.OTHER
    title: str = ""
    description: str = ""
    source: str = ""
    collection_date: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    collector: str = ""
    hash_value: str = ""
    integrity_status: EvidenceIntegrity = EvidenceIntegrity.UNKNOWN
    chain_of_custody: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None
    size_bytes: Optional[int] = None
    is_admissible: bool = False
    legal_weight: float = 0.0
    verified_by: Optional[str] = None
    verification_date: Optional[datetime] = None

    def calculate_hash(self, data: bytes) -> str:
        """Calculate SHA-256 hash of evidence data"""
        self.hash_value = hashlib.sha256(data).hexdigest()
        return self.hash_value

    def add_custody_entry(self, person: str, action: str, notes: str = "") -> None:
        """Add entry to chain of custody"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "person": person,
            "action": action,
            "notes": notes,
        }
        self.chain_of_custody.append(entry)

    def verify_integrity(self, data: bytes) -> bool:
        """Verify evidence integrity using hash"""
        if not self.hash_value:
            return False

        current_hash = hashlib.sha256(data).hexdigest()
        is_valid = current_hash == self.hash_value

        self.integrity_status = (
            EvidenceIntegrity.VERIFIED if is_valid else EvidenceIntegrity.TAMPERED
        )
        return is_valid


class CasePriority(str, Enum):
    """Case priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"


@dataclass
class CaseStatistics:
    """Statistics for forensic cases"""

    total_cases: int = 0
    open_cases: int = 0
    closed_cases: int = 0
    cases_by_status: Dict[str, int] = field(default_factory=dict)
    cases_by_priority: Dict[str, int] = field(default_factory=dict)
    average_resolution_days: float = 0.0
    total_evidence_items: int = 0
    total_reports: int = 0


@dataclass
class ForensicCase:
    """Forensic investigation case"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    case_number: str = ""
    title: str = ""
    description: str = ""
    status: ForensicCaseStatus = ForensicCaseStatus.OPEN
    priority: CasePriority = CasePriority.MEDIUM
    assigned_investigator: str = ""
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_date: Optional[datetime] = None
    evidence_ids: List[str] = field(default_factory=list)
    client_id: Optional[str] = None
    jurisdiction: str = ""
    legal_standard: LegalStandard = LegalStandard.PREPONDERANCE
    tags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_evidence(self, evidence_id: str) -> None:
        """Add evidence to case"""
        if evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)
            self.updated_date = datetime.now(timezone.utc)

    def remove_evidence(self, evidence_id: str) -> None:
        """Remove evidence from case"""
        if evidence_id in self.evidence_ids:
            self.evidence_ids.remove(evidence_id)
            self.updated_date = datetime.now(timezone.utc)

    def update_status(self, new_status: ForensicCaseStatus) -> None:
        """Update case status"""
        self.status = new_status
        self.updated_date = datetime.now(timezone.utc)
        if new_status in [ForensicCaseStatus.CLOSED, ForensicCaseStatus.ARCHIVED]:
            self.closed_date = datetime.now(timezone.utc)


@dataclass
class ForensicReport:
    """Generated forensic analysis report"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str = ""
    title: str = ""
    summary: str = ""
    findings: List[str] = field(default_factory=list)
    evidence_analysis: Dict[str, Any] = field(default_factory=dict)
    conclusions: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    generated_by: str = ""
    legal_review: bool = False
    legal_reviewer: Optional[str] = None
    legal_review_date: Optional[datetime] = None
    template_used: str = ""
    format: str = "pdf"  # pdf, html, json
    file_path: Optional[str] = None
    is_court_ready: bool = False
    confidence_score: float = 0.0


class ForensicEngine:
    """Main forensic analysis and evidence management engine"""

    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.cases: Dict[str, ForensicCase] = {}
        self.evidence: Dict[str, ForensicEvidence] = {}
        self.reports: Dict[str, ForensicReport] = {}
        self.running = False
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour

        logger.info("ForensicEngine initialized")

    async def initialize(self) -> None:
        """Initialize forensic engine and database schema"""
        if self.db_pool:
            await self._create_database_schema()

        self.running = True
        logger.info("ForensicEngine started")

    async def shutdown(self) -> None:
        """Shutdown forensic engine"""
        self.running = False
        logger.info("ForensicEngine shutdown")

    async def _create_database_schema(self) -> None:
        """Create forensic database tables"""
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS forensic_cases (
                id UUID PRIMARY KEY,
                case_number TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                assigned_investigator TEXT,
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                closed_date TIMESTAMP WITH TIME ZONE,
                client_id UUID,
                jurisdiction TEXT,
                legal_standard TEXT NOT NULL,
                tags JSONB DEFAULT '[]',
                notes JSONB DEFAULT '[]',
                metadata JSONB DEFAULT '{}'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS forensic_evidence (
                id UUID PRIMARY KEY,
                case_id UUID REFERENCES forensic_cases(id),
                evidence_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                source TEXT,
                collection_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                collector TEXT,
                hash_value TEXT,
                integrity_status TEXT NOT NULL,
                chain_of_custody JSONB DEFAULT '[]',
                metadata JSONB DEFAULT '{}',
                file_path TEXT,
                size_bytes BIGINT,
                is_admissible BOOLEAN DEFAULT FALSE,
                legal_weight FLOAT DEFAULT 0.0,
                verified_by TEXT,
                verification_date TIMESTAMP WITH TIME ZONE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS forensic_reports (
                id UUID PRIMARY KEY,
                case_id UUID REFERENCES forensic_cases(id),
                title TEXT NOT NULL,
                summary TEXT,
                findings JSONB DEFAULT '[]',
                evidence_analysis JSONB DEFAULT '{}',
                conclusions JSONB DEFAULT '[]',
                recommendations JSONB DEFAULT '[]',
                generated_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                generated_by TEXT NOT NULL,
                legal_review BOOLEAN DEFAULT FALSE,
                legal_reviewer TEXT,
                legal_review_date TIMESTAMP WITH TIME ZONE,
                template_used TEXT,
                format TEXT NOT NULL,
                file_path TEXT,
                is_court_ready BOOLEAN DEFAULT FALSE,
                confidence_score FLOAT DEFAULT 0.0
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_forensic_cases_status ON forensic_cases(status);
            CREATE INDEX IF NOT EXISTS idx_forensic_cases_priority ON forensic_cases(priority);
            CREATE INDEX IF NOT EXISTS idx_forensic_cases_client ON forensic_cases(client_id);
            CREATE INDEX IF NOT EXISTS idx_forensic_evidence_case ON forensic_evidence(case_id);
            CREATE INDEX IF NOT EXISTS idx_forensic_evidence_type ON forensic_evidence(evidence_type);
            CREATE INDEX IF NOT EXISTS idx_forensic_reports_case ON forensic_reports(case_id);
            """,
        ]

        async with self.db_pool.acquire() as conn:
            for query in schema_queries:
                await conn.execute(query)

        logger.info("Forensic database schema created")

    async def create_case(self, case_data: Dict[str, Any]) -> ForensicCase:
        """Create new forensic case"""
        case = ForensicCase(
            case_number=case_data.get("case_number", ""),
            title=case_data["title"],
            description=case_data.get("description", ""),
            priority=CasePriority(case_data.get("priority", "medium").lower()),
            assigned_investigator=case_data.get("assigned_investigator", ""),
            client_id=case_data.get("client_id"),
            jurisdiction=case_data.get("jurisdiction", ""),
            legal_standard=LegalStandard(
                case_data.get("legal_standard", "preponderance")
            ),
            tags=case_data.get("tags", []),
            metadata=case_data.get("metadata", {}),
        )

        if self.db_pool:
            await self._save_case_to_db(case)

        self.cases[case.id] = case
        logger.info(f"Created forensic case: {case.id}")
        return case

    async def add_evidence(
        self, case_id: str, evidence_data: Dict[str, Any]
    ) -> ForensicEvidence:
        """Add evidence to case"""
        evidence = ForensicEvidence(
            case_id=case_id,
            evidence_type=EvidenceType(evidence_data.get("evidence_type", "other")),
            title=evidence_data["title"],
            description=evidence_data.get("description", ""),
            source=evidence_data.get("source", ""),
            collector=evidence_data.get("collector", ""),
            metadata=evidence_data.get("metadata", {}),
            file_path=evidence_data.get("file_path"),
            size_bytes=evidence_data.get("size_bytes"),
        )

        # Calculate hash if file path provided
        if evidence.file_path:
            try:
                with open(evidence.file_path, "rb") as f:
                    evidence.calculate_hash(f.read())
            except Exception as e:
                logger.error(
                    f"Failed to calculate hash for evidence {evidence.id}: {e}"
                )

        if self.db_pool:
            await self._save_evidence_to_db(evidence)

        self.evidence[evidence.id] = evidence

        # Add to case
        if case_id in self.cases:
            self.cases[case_id].add_evidence(evidence.id)

        logger.info(f"Added evidence {evidence.id} to case {case_id}")
        return evidence

    async def verify_evidence(self, evidence_id: str, data: bytes) -> bool:
        """Verify evidence integrity"""
        if evidence_id not in self.evidence:
            raise ValueError(f"Evidence {evidence_id} not found")

        evidence = self.evidence[evidence_id]
        is_valid = evidence.verify_integrity(data)

        if self.db_pool:
            await self._update_evidence_integrity(
                evidence_id, evidence.integrity_status
            )

        logger.info(f"Verified evidence {evidence_id}: {is_valid}")
        return is_valid

    async def generate_report(
        self, case_id: str, report_data: Dict[str, Any]
    ) -> ForensicReport:
        """Generate forensic analysis report"""
        report = ForensicReport(
            case_id=case_id,
            title=report_data["title"],
            summary=report_data.get("summary", ""),
            findings=report_data.get("findings", []),
            evidence_analysis=report_data.get("evidence_analysis", {}),
            conclusions=report_data.get("conclusions", []),
            recommendations=report_data.get("recommendations", []),
            generated_by=report_data["generated_by"],
            template_used=report_data.get("template_used", ""),
            format=report_data.get("format", "pdf"),
            confidence_score=report_data.get("confidence_score", 0.0),
        )

        if self.db_pool:
            await self._save_report_to_db(report)

        self.reports[report.id] = report
        logger.info(f"Generated forensic report: {report.id}")
        return report

    async def get_case(self, case_id: str) -> Optional[ForensicCase]:
        """Get forensic case by ID"""
        if case_id in self.cases:
            return self.cases[case_id]

        if self.db_pool:
            case = await self._load_case_from_db(case_id)
            if case:
                self.cases[case_id] = case
                return case

        return None

    async def get_evidence(self, evidence_id: str) -> Optional[ForensicEvidence]:
        """Get evidence by ID"""
        if evidence_id in self.evidence:
            return self.evidence[evidence_id]

        if self.db_pool:
            evidence = await self._load_evidence_from_db(evidence_id)
            if evidence:
                self.evidence[evidence_id] = evidence
                return evidence

        return None

    async def search_cases(self, filters: Dict[str, Any]) -> List[ForensicCase]:
        """Search forensic cases with filters"""
        if self.db_pool:
            return await self._search_cases_db(filters)

        # In-memory search
        results = []
        for case in self.cases.values():
            match = True

            if "status" in filters and case.status.value != filters["status"]:
                match = False
            if "priority" in filters and case.priority != filters["priority"]:
                match = False
            if (
                "assigned_investigator" in filters
                and case.assigned_investigator != filters["assigned_investigator"]
            ):
                match = False
            if "client_id" in filters and case.client_id != filters["client_id"]:
                match = False
            if "tags" in filters:
                required_tags = set(filters["tags"])
                if not required_tags.issubset(set(case.tags)):
                    match = False

            if match:
                results.append(case)

        return results

    async def get_case_statistics(self) -> CaseStatistics:
        """Get forensic case statistics"""
        total_cases = len(self.cases)
        if self.db_pool:
            total_cases = await self._get_case_count_db()

        status_counts = {}
        priority_counts = {}
        open_cases = 0
        closed_cases = 0
        resolution_days = []

        for case in self.cases.values():
            status_counts[case.status.value] = (
                status_counts.get(case.status.value, 0) + 1
            )
            priority_counts[case.priority.value] = priority_counts.get(case.priority.value, 0) + 1
            
            if case.status == ForensicCaseStatus.OPEN:
                open_cases += 1
            elif case.status == ForensicCaseStatus.CLOSED and case.closed_date:
                closed_cases += 1
                resolution_days.append((case.closed_date - case.created_date).days)

        # Calculate average resolution days (skip unresolved cases)
        avg_resolution_days = sum(resolution_days) / len(resolution_days) if resolution_days else 0.0

        return CaseStatistics(
            total_cases=total_cases,
            open_cases=open_cases,
            closed_cases=closed_cases,
            cases_by_status=status_counts,
            cases_by_priority=priority_counts,
            average_resolution_days=avg_resolution_days,
            total_evidence_items=len(self.evidence),
            total_reports=len(self.reports)
        )

    # Database helper methods
    async def _save_case_to_db(self, case: ForensicCase) -> None:
        """Save case to database"""
        query = """
        INSERT INTO forensic_cases 
        (id, case_number, title, description, status, priority, assigned_investigator,
         created_date, updated_date, client_id, jurisdiction, legal_standard, tags, notes, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        ON CONFLICT (id) DO UPDATE SET
        title = EXCLUDED.title,
        description = EXCLUDED.description,
        status = EXCLUDED.status,
        priority = EXCLUDED.priority,
        assigned_investigator = EXCLUDED.assigned_investigator,
        updated_date = EXCLUDED.updated_date,
        client_id = EXCLUDED.client_id,
        jurisdiction = EXCLUDED.jurisdiction,
        legal_standard = EXCLUDED.legal_standard,
        tags = EXCLUDED.tags,
        notes = EXCLUDED.notes,
        metadata = EXCLUDED.metadata
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                case.id,
                case.case_number,
                case.title,
                case.description,
                case.status.value,
                case.priority,
                case.assigned_investigator,
                case.created_date,
                case.updated_date,
                case.client_id,
                case.jurisdiction,
                case.legal_standard.value,
                json.dumps(case.tags),
                json.dumps(case.notes),
                json.dumps(case.metadata),
            )

    async def _save_evidence_to_db(self, evidence: ForensicEvidence) -> None:
        """Save evidence to database"""
        query = """
        INSERT INTO forensic_evidence 
        (id, case_id, evidence_type, title, description, source, collection_date, collector,
         hash_value, integrity_status, chain_of_custody, metadata, file_path, size_bytes,
         is_admissible, legal_weight, verified_by, verification_date)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
        ON CONFLICT (id) DO UPDATE SET
        title = EXCLUDED.title,
        description = EXCLUDED.description,
        integrity_status = EXCLUDED.integrity_status,
        chain_of_custody = EXCLUDED.chain_of_custody,
        metadata = EXCLUDED.metadata,
        is_admissible = EXCLUDED.is_admissible,
        legal_weight = EXCLUDED.legal_weight,
        verified_by = EXCLUDED.verified_by,
        verification_date = EXCLUDED.verification_date
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                evidence.id,
                evidence.case_id,
                evidence.evidence_type.value,
                evidence.title,
                evidence.description,
                evidence.source,
                evidence.collection_date,
                evidence.collector,
                evidence.hash_value,
                evidence.integrity_status.value,
                json.dumps(evidence.chain_of_custody),
                json.dumps(evidence.metadata),
                evidence.file_path,
                evidence.size_bytes,
                evidence.is_admissible,
                evidence.legal_weight,
                evidence.verified_by,
                evidence.verification_date,
            )

    async def _save_report_to_db(self, report: ForensicReport) -> None:
        """Save report to database"""
        query = """
        INSERT INTO forensic_reports 
        (id, case_id, title, summary, findings, evidence_analysis, conclusions, recommendations,
         generated_date, generated_by, legal_review, legal_reviewer, legal_review_date,
         template_used, format, file_path, is_court_ready, confidence_score)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
        ON CONFLICT (id) DO UPDATE SET
        title = EXCLUDED.title,
        summary = EXCLUDED.summary,
        findings = EXCLUDED.findings,
        evidence_analysis = EXCLUDED.evidence_analysis,
        conclusions = EXCLUDED.conclusions,
        recommendations = EXCLUDED.recommendations,
        legal_review = EXCLUDED.legal_review,
        legal_reviewer = EXCLUDED.legal_reviewer,
        legal_review_date = EXCLUDED.legal_review_date,
        file_path = EXCLUDED.file_path,
        is_court_ready = EXCLUDED.is_court_ready,
        confidence_score = EXCLUDED.confidence_score
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                report.id,
                report.case_id,
                report.title,
                report.summary,
                json.dumps(report.findings),
                json.dumps(report.evidence_analysis),
                json.dumps(report.conclusions),
                json.dumps(report.recommendations),
                report.generated_date,
                report.generated_by,
                report.legal_review,
                report.legal_reviewer,
                report.legal_review_date,
                report.template_used,
                report.format,
                report.file_path,
                report.is_court_ready,
                report.confidence_score,
            )

    async def _load_case_from_db(self, case_id: str) -> Optional[ForensicCase]:
        """Load case from database"""
        query = "SELECT * FROM forensic_cases WHERE id = $1"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, case_id)
            if row:
                return ForensicCase(
                    id=row["id"],
                    case_number=row["case_number"],
                    title=row["title"],
                    description=row["description"],
                    status=ForensicCaseStatus(row["status"]),
                    priority=CasePriority(row["priority"]),
                    assigned_investigator=row["assigned_investigator"],
                    created_date=row["created_date"],
                    updated_date=row["updated_date"],
                    closed_date=row["closed_date"],
                    client_id=row["client_id"],
                    jurisdiction=row["jurisdiction"],
                    legal_standard=LegalStandard(row["legal_standard"]),
                    tags=json.loads(row["tags"]) if row["tags"] else [],
                    notes=json.loads(row["notes"]) if row["notes"] else [],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
        return None

    async def _load_evidence_from_db(
        self, evidence_id: str
    ) -> Optional[ForensicEvidence]:
        """Load evidence from database"""
        query = "SELECT * FROM forensic_evidence WHERE id = $1"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, evidence_id)
            if row:
                return ForensicEvidence(
                    id=row["id"],
                    case_id=row["case_id"],
                    evidence_type=EvidenceType(row["evidence_type"]),
                    title=row["title"],
                    description=row["description"],
                    source=row["source"],
                    collection_date=row["collection_date"],
                    collector=row["collector"],
                    hash_value=row["hash_value"],
                    integrity_status=EvidenceIntegrity(row["integrity_status"]),
                    chain_of_custody=(
                        json.loads(row["chain_of_custody"])
                        if row["chain_of_custody"]
                        else []
                    ),
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    file_path=row["file_path"],
                    size_bytes=row["size_bytes"],
                    is_admissible=row["is_admissible"],
                    legal_weight=row["legal_weight"],
                    verified_by=row["verified_by"],
                    verification_date=row["verification_date"],
                )
        return None

    async def _search_cases_db(self, filters: Dict[str, Any]) -> List[ForensicCase]:
        """Search cases in database"""
        conditions = []
        params = []
        param_idx = 1

        if "status" in filters:
            conditions.append(f"status = ${param_idx}")
            params.append(filters["status"])
            param_idx += 1

        if "priority" in filters:
            conditions.append(f"priority = ${param_idx}")
            params.append(filters["priority"])
            param_idx += 1

        if "assigned_investigator" in filters:
            conditions.append(f"assigned_investigator = ${param_idx}")
            params.append(filters["assigned_investigator"])
            param_idx += 1

        if "client_id" in filters:
            conditions.append(f"client_id = ${param_idx}")
            params.append(filters["client_id"])
            param_idx += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        query = (
            f"SELECT * FROM forensic_cases {where_clause} ORDER BY created_date DESC"
        )

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            cases = []
            for row in rows:
                case = ForensicCase(
                    id=row["id"],
                    case_number=row["case_number"],
                    title=row["title"],
                    description=row["description"],
                    status=ForensicCaseStatus(row["status"]),
                    priority=CasePriority(row["priority"]),
                    assigned_investigator=row["assigned_investigator"],
                    created_date=row["created_date"],
                    updated_date=row["updated_date"],
                    closed_date=row["closed_date"],
                    client_id=row["client_id"],
                    jurisdiction=row["jurisdiction"],
                    legal_standard=LegalStandard(row["legal_standard"]),
                    tags=json.loads(row["tags"]) if row["tags"] else [],
                    notes=json.loads(row["notes"]) if row["notes"] else [],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )

                # Filter by tags if specified
                if "tags" in filters:
                    required_tags = set(filters["tags"])
                    if not required_tags.issubset(set(case.tags)):
                        continue

                cases.append(case)

            return cases

    async def _get_case_count_db(self) -> int:
        """Get total case count from database"""
        query = "SELECT COUNT(*) as count FROM forensic_cases"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query)
            return row["count"]

    async def _update_evidence_integrity(
        self, evidence_id: str, integrity_status: EvidenceIntegrity
    ) -> None:
        """Update evidence integrity status"""
        query = "UPDATE forensic_evidence SET integrity_status = $1 WHERE id = $2"

        async with self.db_pool.acquire() as conn:
            await conn.execute(query, integrity_status.value, evidence_id)


# Global forensic engine instance
_forensic_engine = None


def get_forensic_engine() -> ForensicEngine:
    """Get the global forensic engine instance"""
    global _forensic_engine
    if _forensic_engine is None:
        _forensic_engine = ForensicEngine()
    return _forensic_engine


# Aliases and additional types for API compatibility
CaseStatus = ForensicCaseStatus
