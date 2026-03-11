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


class LegalStandard(str, Enum):
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


# Defensive parsing helpers for enum conversions
def _parse_priority(value: str) -> "CasePriority":
    """Parse case priority with defensive error handling"""
    try:
        return CasePriority(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid priority value '{value}', defaulting to MEDIUM")
        return CasePriority.MEDIUM


def _parse_status(value: str) -> ForensicCaseStatus:
    """Parse case status with defensive error handling"""
    try:
        return ForensicCaseStatus(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid status value '{value}', defaulting to OPEN")
        return ForensicCaseStatus.OPEN


def _parse_legal_standard(value: str) -> LegalStandard:
    """Parse legal standard with defensive error handling"""
    try:
        return LegalStandard(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid legal standard value '{value}', defaulting to PREPONDERANCE")
        return LegalStandard.PREPONDERANCE


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
    cases_by_type: Dict[str, int] = field(default_factory=dict)
    average_case_duration_days: float = 0.0
    average_resolution_days: float = 0.0
    total_evidence_items: int = 0
    total_reports: int = 0
    cases_with_court_preparation: int = 0
    completion_rate: float = 0.0
    completed_cases: int = 0
    total_case_duration_days: float = 0.0

    def __post_init__(self) -> None:
        if (
            self.total_cases
            and self.completed_cases
            and not self.completion_rate
        ):
            self.completion_rate = self.completed_cases / self.total_cases
        if (
            self.total_cases
            and self.total_case_duration_days
            and not self.average_case_duration_days
        ):
            self.average_case_duration_days = (
                self.total_case_duration_days / self.total_cases
            )
        if not self.average_resolution_days:
            self.average_resolution_days = self.average_case_duration_days


@dataclass
class ForensicCase:
    """Forensic investigation case"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    case_number: str = ""
    title: str = ""
    description: str = ""
    case_type: str = "other"
    status: ForensicCaseStatus = ForensicCaseStatus.OPEN
    priority: CasePriority = CasePriority.MEDIUM
    assigned_investigator: Optional[str] = None
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None
    evidence_ids: List[str] = field(default_factory=list)
    evidence_count: int = 0
    client_id: Optional[str] = None
    jurisdiction: str = ""
    legal_standard: LegalStandard = LegalStandard.PREPONDERANCE
    related_cases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.status, ForensicCaseStatus):
            self.status = _parse_status(self.status)
        if not isinstance(self.priority, CasePriority):
            self.priority = _parse_priority(self.priority)
        if not isinstance(self.legal_standard, LegalStandard):
            self.legal_standard = _parse_legal_standard(self.legal_standard)
        if self.evidence_count == 0 and self.evidence_ids:
            self.evidence_count = len(self.evidence_ids)

    def add_evidence(self, evidence_id: str) -> None:
        """Add evidence to case"""
        if evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)
            self.evidence_count += 1
            self.last_updated = datetime.now(timezone.utc)

    def remove_evidence(self, evidence_id: str) -> None:
        """Remove evidence from case"""
        if evidence_id in self.evidence_ids:
            self.evidence_ids.remove(evidence_id)
            self.evidence_count = max(0, self.evidence_count - 1)
            self.last_updated = datetime.now(timezone.utc)

    def update_status(self, new_status: ForensicCaseStatus) -> None:
        """Update case status"""
        self.status = new_status
        self.last_updated = datetime.now(timezone.utc)
        if new_status in [ForensicCaseStatus.CLOSED, ForensicCaseStatus.ARCHIVED]:
            self.actual_completion_date = datetime.now(timezone.utc)

    @property
    def updated_date(self) -> datetime:
        """Backward-compatible alias for older callers."""
        return self.last_updated

    @updated_date.setter
    def updated_date(self, value: datetime) -> None:
        self.last_updated = value

    @property
    def closed_date(self) -> Optional[datetime]:
        """Backward-compatible alias for older callers."""
        return self.actual_completion_date

    @closed_date.setter
    def closed_date(self, value: Optional[datetime]) -> None:
        self.actual_completion_date = value

    @property
    def completion_date(self) -> Optional[datetime]:
        """Alias used by report-generation code paths."""
        return self.actual_completion_date


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

    @staticmethod
    def _row_value(row: Any, key: str, default: Any = None) -> Any:
        """Read columns from dict-like rows, asyncpg rows, or mocked objects."""
        if row is None:
            return default
        if isinstance(row, dict):
            return row.get(key, default)
        if hasattr(row, "__dict__") and key in row.__dict__:
            return row.__dict__[key]
        try:
            return row[key]
        except Exception:
            return default

    def _case_defaults(self, case_id: Optional[str] = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        return {
            "id": case_id or str(uuid.uuid4()),
            "case_number": "",
            "title": "",
            "description": "",
            "case_type": "other",
            "status": ForensicCaseStatus.OPEN.value,
            "priority": CasePriority.MEDIUM.value,
            "assigned_investigator": None,
            "created_date": now,
            "last_updated": now,
            "estimated_completion_date": None,
            "actual_completion_date": None,
            "evidence_ids": [],
            "evidence_count": 0,
            "client_id": None,
            "jurisdiction": "",
            "legal_standard": LegalStandard.PREPONDERANCE.value,
            "related_cases": [],
            "tags": [],
            "notes": None,
            "metadata": {},
        }

    def _case_to_dict(self, case: ForensicCase) -> Dict[str, Any]:
        return {
            "id": case.id,
            "case_number": case.case_number,
            "title": case.title,
            "description": case.description,
            "case_type": case.case_type,
            "status": case.status.value,
            "priority": case.priority.value,
            "assigned_investigator": case.assigned_investigator,
            "created_date": case.created_date,
            "last_updated": case.last_updated,
            "estimated_completion_date": case.estimated_completion_date,
            "actual_completion_date": case.actual_completion_date,
            "evidence_ids": list(case.evidence_ids),
            "evidence_count": case.evidence_count,
            "client_id": case.client_id,
            "jurisdiction": case.jurisdiction,
            "legal_standard": case.legal_standard.value,
            "related_cases": list(case.related_cases),
            "tags": list(case.tags),
            "notes": case.notes,
            "metadata": dict(case.metadata),
        }

    def _build_case(
        self, row: Any, fallback: Optional[Dict[str, Any]] = None
    ) -> ForensicCase:
        data = self._case_defaults()
        if fallback:
            data.update(fallback)

        created_date = self._row_value(row, "created_date", data["created_date"])
        last_updated = self._row_value(
            row,
            "last_updated",
            self._row_value(row, "updated_date", data["last_updated"]),
        )
        actual_completion_date = self._row_value(
            row,
            "actual_completion_date",
            self._row_value(row, "closed_date", data["actual_completion_date"]),
        )

        tags = self._row_value(row, "tags", data["tags"])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = [tags]

        related_cases = self._row_value(row, "related_cases", data["related_cases"])
        if isinstance(related_cases, str):
            try:
                related_cases = json.loads(related_cases)
            except Exception:
                related_cases = [related_cases]

        evidence_ids = self._row_value(row, "evidence_ids", data["evidence_ids"])
        if isinstance(evidence_ids, str):
            try:
                evidence_ids = json.loads(evidence_ids)
            except Exception:
                evidence_ids = [evidence_ids]

        metadata = self._row_value(row, "metadata", data["metadata"])
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = data["metadata"]

        return ForensicCase(
            id=str(self._row_value(row, "id", data["id"])),
            case_number=str(self._row_value(row, "case_number", data["case_number"])),
            title=self._row_value(row, "title", data["title"]),
            description=self._row_value(row, "description", data["description"]),
            case_type=self._row_value(row, "case_type", data["case_type"]),
            status=self._row_value(row, "status", data["status"]),
            priority=self._row_value(row, "priority", data["priority"]),
            assigned_investigator=self._row_value(
                row, "assigned_investigator", data["assigned_investigator"]
            ),
            created_date=created_date,
            last_updated=last_updated,
            estimated_completion_date=self._row_value(
                row,
                "estimated_completion_date",
                data["estimated_completion_date"],
            ),
            actual_completion_date=actual_completion_date,
            evidence_ids=evidence_ids or [],
            evidence_count=int(
                self._row_value(
                    row,
                    "evidence_count",
                    data["evidence_count"] or len(evidence_ids or []),
                )
            ),
            client_id=self._row_value(row, "client_id", data["client_id"]),
            jurisdiction=self._row_value(row, "jurisdiction", data["jurisdiction"]),
            legal_standard=self._row_value(
                row, "legal_standard", data["legal_standard"]
            ),
            related_cases=related_cases or [],
            tags=tags or [],
            notes=self._row_value(row, "notes", data["notes"]),
            metadata=metadata or {},
        )

    async def _create_database_schema(self) -> None:
        """Create forensic database tables"""
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS forensic_cases (
                id UUID PRIMARY KEY,
                case_number TEXT UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                case_type TEXT NOT NULL DEFAULT 'other',
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                assigned_investigator TEXT,
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                closed_date TIMESTAMP WITH TIME ZONE,
                estimated_completion_date TIMESTAMP WITH TIME ZONE,
                evidence_count INTEGER DEFAULT 0,
                client_id UUID,
                jurisdiction TEXT,
                legal_standard TEXT NOT NULL,
                related_cases JSONB DEFAULT '[]',
                tags JSONB DEFAULT '[]',
                notes TEXT,
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
        if not str(case_data.get("title", "")).strip():
            raise ValueError("Title is required")

        priority_value = case_data.get("priority", CasePriority.MEDIUM.value)
        legal_standard_value = case_data.get(
            "legal_standard", LegalStandard.PREPONDERANCE.value
        )

        try:
            priority = CasePriority(str(priority_value).lower())
        except ValueError as exc:
            raise ValueError("Invalid priority") from exc

        try:
            legal_standard = LegalStandard(str(legal_standard_value).lower())
        except ValueError as exc:
            raise ValueError("Invalid legal standard") from exc

        now = datetime.now(timezone.utc)
        case_number = case_data.get("case_number") or f"CASE-{uuid.uuid4().hex[:8].upper()}"

        case = ForensicCase(
            id=str(case_data.get("id", uuid.uuid4())),
            case_number=case_number,
            title=case_data["title"],
            description=case_data.get("description", ""),
            case_type=case_data.get("case_type", "other"),
            status=ForensicCaseStatus.OPEN,
            priority=priority,
            assigned_investigator=case_data.get("assigned_investigator"),
            created_date=case_data.get("created_date", now),
            last_updated=case_data.get("last_updated", now),
            estimated_completion_date=case_data.get("estimated_completion_date"),
            actual_completion_date=case_data.get("actual_completion_date"),
            evidence_ids=case_data.get("evidence_ids", []),
            evidence_count=case_data.get("evidence_count", 0),
            client_id=case_data.get("client_id"),
            jurisdiction=case_data.get("jurisdiction", ""),
            legal_standard=legal_standard,
            related_cases=case_data.get("related_cases", []),
            tags=case_data.get("tags", []),
            notes=case_data.get("notes"),
            metadata=case_data.get("metadata", {}),
        )

        if self.db_pool:
            query = """
            INSERT INTO forensic_cases (
                id, case_number, title, description, case_type, status, priority,
                assigned_investigator, created_date, updated_date, closed_date,
                estimated_completion_date, evidence_count, client_id,
                jurisdiction, legal_standard, related_cases, tags, notes, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                $16, $17, $18, $19, $20
            )
            RETURNING id
            """
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    case.id,
                    case.case_number,
                    case.title,
                    case.description,
                    case.case_type,
                    case.status.value,
                    case.priority.value,
                    case.assigned_investigator,
                    case.created_date,
                    case.last_updated,
                    case.actual_completion_date,
                    case.estimated_completion_date,
                    case.evidence_count,
                    case.client_id,
                    case.jurisdiction,
                    case.legal_standard.value,
                    json.dumps(case.related_cases),
                    json.dumps(case.tags),
                    case.notes,
                    json.dumps(case.metadata),
                )
            if row:
                case.id = str(self._row_value(row, "id", case.id))

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
            query = "SELECT * FROM forensic_cases WHERE id = $1"
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, case_id)
            if row:
                case = self._build_case(row, self._case_defaults(case_id))
                self.cases[case.id] = case
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

    async def get_cases(
        self, filters: Optional[Dict[str, Any]] = None, limit: int = 100, offset: int = 0
    ) -> List[ForensicCase]:
        """Return cases matching filter criteria."""
        filters = filters or {}
        if self.db_pool:
            return await self._search_cases_db(filters, limit=limit, offset=offset)

        results: List[ForensicCase] = []
        for case in self.cases.values():
            if "status" in filters and case.status.value != filters["status"]:
                continue
            if "priority" in filters and case.priority.value != filters["priority"]:
                continue
            if (
                "assigned_investigator" in filters
                and case.assigned_investigator != filters["assigned_investigator"]
            ):
                continue
            if "jurisdiction" in filters and case.jurisdiction != filters["jurisdiction"]:
                continue
            if "client_id" in filters and case.client_id != filters["client_id"]:
                continue
            if "tags" in filters:
                required_tags = set(filters["tags"])
                if not required_tags.issubset(set(case.tags)):
                    continue
            results.append(case)
        return results[offset : offset + limit]

    async def search_cases(
        self, field_or_filters: Any, search_term: Optional[str] = None, limit: int = 100
    ) -> List[ForensicCase]:
        """Search cases by filter dict or by a specific searchable field."""
        if isinstance(field_or_filters, dict):
            return await self.get_cases(field_or_filters, limit=limit, offset=0)

        field_name = str(field_or_filters)
        if search_term is None:
            return []

        if field_name not in {"title", "tags", "description"}:
            raise ValueError("Unsupported search field")

        if self.db_pool:
            if field_name == "tags":
                query = (
                    "SELECT * FROM forensic_cases "
                    "WHERE tags::text ILIKE $1 "
                    "ORDER BY created_date DESC LIMIT $2"
                )
            else:
                query = (
                    f"SELECT * FROM forensic_cases "
                    f"WHERE COALESCE({field_name}, '') ILIKE $1 "
                    "ORDER BY created_date DESC LIMIT $2"
                )
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, f"%{search_term}%", limit)
            return [
                self._build_case(row, self._case_defaults(str(self._row_value(row, "id", uuid.uuid4()))))
                for row in rows
            ]

        lowered = search_term.lower()
        matched = []
        for case in self.cases.values():
            if field_name == "title" and lowered in case.title.lower():
                matched.append(case)
            elif field_name == "tags" and any(lowered in tag.lower() for tag in case.tags):
                matched.append(case)
        return matched[:limit]

    async def update_case(
        self, case_id: str, update_data: Dict[str, Any]
    ) -> ForensicCase:
        """Update a case and return the merged record."""
        normalized = dict(update_data)

        if "status" in normalized:
            try:
                normalized["status"] = ForensicCaseStatus(normalized["status"])
            except ValueError as exc:
                raise ValueError("Invalid status") from exc

        if "priority" in normalized:
            try:
                normalized["priority"] = CasePriority(normalized["priority"])
            except ValueError as exc:
                raise ValueError("Invalid priority") from exc

        if "legal_standard" in normalized:
            try:
                normalized["legal_standard"] = LegalStandard(normalized["legal_standard"])
            except ValueError as exc:
                raise ValueError("Invalid legal standard") from exc

        existing_case = self.cases.get(case_id)

        if not self.db_pool:
            if existing_case is None:
                raise ValueError("Case not found")
            merged = self._case_to_dict(existing_case)
            for key, value in normalized.items():
                merged[key] = value.value if isinstance(value, Enum) else value
            merged["last_updated"] = datetime.now(timezone.utc)
            updated_case = self._build_case(merged, self._case_defaults(case_id))
            self.cases[case_id] = updated_case
            return updated_case

        db_updates = {}
        for key, value in normalized.items():
            mapped_key = key
            if key == "actual_completion_date":
                mapped_key = "closed_date"
            db_updates[mapped_key] = value.value if isinstance(value, Enum) else value
        if (
            db_updates.get("status") == ForensicCaseStatus.CLOSED.value
            and "closed_date" not in db_updates
        ):
            db_updates["closed_date"] = datetime.now(timezone.utc)
        db_updates["updated_date"] = datetime.now(timezone.utc)

        assignments = []
        values = []
        for column, value in db_updates.items():
            assignments.append(f"{column} = ${len(values) + 1}")
            values.append(value)

        query = (
            f"UPDATE forensic_cases SET {', '.join(assignments)} "
            f"WHERE id = ${len(values) + 1} RETURNING *"
        )
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *values, case_id)

        if not row:
            raise ValueError("Case not found")

        fallback = self._case_defaults(case_id)
        if existing_case is not None:
            fallback.update(self._case_to_dict(existing_case))
        fallback.update({k: v for k, v in db_updates.items() if k != "updated_date"})
        if "closed_date" in db_updates:
            fallback["actual_completion_date"] = db_updates["closed_date"]
        fallback["last_updated"] = db_updates["updated_date"]
        updated_case = self._build_case(row, fallback)
        self.cases[updated_case.id] = updated_case
        return updated_case

    async def increment_evidence_count(self, case_id: str) -> bool:
        """Increment the evidence count for a case."""
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id, evidence_count FROM forensic_cases WHERE id = $1",
                    case_id,
                )
                if not row:
                    return False
                await conn.execute(
                    "UPDATE forensic_cases SET evidence_count = $1 WHERE id = $2",
                    int(self._row_value(row, "evidence_count", 0)) + 1,
                    case_id,
                )
        case = self.cases.get(case_id)
        if case is not None:
            case.evidence_count += 1
            case.last_updated = datetime.now(timezone.utc)
        return True

    async def decrement_evidence_count(self, case_id: str) -> bool:
        """Decrement the evidence count for a case."""
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id, evidence_count FROM forensic_cases WHERE id = $1",
                    case_id,
                )
                if not row:
                    return False
                await conn.execute(
                    "UPDATE forensic_cases SET evidence_count = $1 WHERE id = $2",
                    max(0, int(self._row_value(row, "evidence_count", 0)) - 1),
                    case_id,
                )
        case = self.cases.get(case_id)
        if case is not None:
            case.evidence_count = max(0, case.evidence_count - 1)
            case.last_updated = datetime.now(timezone.utc)
        return True

    async def get_statistics(self, days: int = 30) -> CaseStatistics:
        """Return forensic case statistics."""
        if self.db_pool:
            query = "SELECT * FROM forensic_case_statistics($1)"
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, days)
            if row:
                payload = dict(row) if isinstance(row, dict) else row
                return CaseStatistics(**payload)
            return CaseStatistics()

        status_counts: Dict[str, int] = {}
        priority_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}
        completed_cases = 0
        total_case_duration_days = 0.0

        for case in self.cases.values():
            status_counts[case.status.value] = status_counts.get(case.status.value, 0) + 1
            priority_counts[case.priority.value] = (
                priority_counts.get(case.priority.value, 0) + 1
            )
            type_counts[case.case_type] = type_counts.get(case.case_type, 0) + 1
            if case.actual_completion_date:
                completed_cases += 1
                total_case_duration_days += (
                    case.actual_completion_date - case.created_date
                ).days

        return CaseStatistics(
            total_cases=len(self.cases),
            cases_by_status=status_counts,
            cases_by_priority=priority_counts,
            cases_by_type=type_counts,
            total_evidence_items=sum(case.evidence_count for case in self.cases.values()),
            total_reports=len(self.reports),
            completed_cases=completed_cases,
            total_case_duration_days=total_case_duration_days,
        )

    async def get_case_statistics(self) -> CaseStatistics:
        """Backward-compatible statistics entrypoint."""
        return await self.get_statistics()

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
                case.priority.value,
                case.assigned_investigator,
                case.created_date,
                case.last_updated,
                case.client_id,
                case.jurisdiction,
                case.legal_standard.value,
                json.dumps(case.tags),
                case.notes,
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
                return self._build_case(row, self._case_defaults(case_id))
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

    async def _search_cases_db(
        self, filters: Dict[str, Any], limit: int = 100, offset: int = 0
    ) -> List[ForensicCase]:
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

        if "jurisdiction" in filters:
            conditions.append(f"jurisdiction = ${param_idx}")
            params.append(filters["jurisdiction"])
            param_idx += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        query = (
            f"SELECT * FROM forensic_cases {where_clause} "
            f"ORDER BY created_date DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        )
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            cases = []
            for row in rows:
                case = self._build_case(
                    row,
                    self._case_defaults(
                        str(self._row_value(row, "id", uuid.uuid4()))
                    ),
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


async def get_forensic_engine() -> ForensicEngine:
    """Get and lazily initialize the global forensic engine instance."""
    global _forensic_engine
    if _forensic_engine is None:
        _forensic_engine = ForensicEngine()
    if not _forensic_engine.running:
        await _forensic_engine.initialize()
    return _forensic_engine


# Aliases and additional types for API compatibility
CaseStatus = ForensicCaseStatus
