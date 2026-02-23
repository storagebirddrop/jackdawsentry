"""
Jackdaw Sentry - Court Defensible Evidence System
Legal standards compliance and court-ready evidence preparation
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


class LegalJurisdiction(Enum):
    """Legal jurisdictions"""

    FEDERAL_US = "federal_us"
    STATE_US = "state_us"
    UK = "uk"
    EU = "eu"
    INTERNATIONAL = "international"
    OTHER = "other"


class EvidenceAdmissibility(Enum):
    """Evidence admissibility status"""

    ADMISSIBLE = "admissible"
    INADMISSIBLE = "inadmissible"
    CONDITIONAL = "conditional"
    UNDER_REVIEW = "under_review"
    CHALLENGED = "challenged"


class LegalStandard(Enum):
    """Legal standards of proof"""

    PREPONDERANCE = "preponderance"  # 50%+ likelihood
    CLEAR_AND_CONVINCING = "clear_and_convincing"  # 75%+ likelihood
    BEYOND_REASONABLE_DOUBT = "beyond_reasonable_doubt"  # 95%+ likelihood
    REASONABLE_CERTAINTY = "reasonable_certainty"  # High probability


class CourtType(Enum):
    """Types of courts"""

    CRIMINAL = "criminal"
    CIVIL = "civil"
    ADMINISTRATIVE = "administrative"
    ARBITRATION = "arbitration"
    MILITARY = "military"
    INTERNATIONAL = "international"


@dataclass
class LegalRequirement:
    """Legal requirement for evidence admissibility"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    jurisdiction: LegalJurisdiction = LegalJurisdiction.FEDERAL_US
    court_type: CourtType = CourtType.CRIMINAL
    requirement_type: str = ""
    description: str = ""
    is_mandatory: bool = True
    verification_method: str = ""
    precedence_level: int = 1  # Higher = more important
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def check_compliance(self, evidence_data: Dict[str, Any]) -> bool:
        """Check if evidence meets this requirement"""
        # This would be implemented based on specific requirement types
        # For now, return True as placeholder
        return True


@dataclass
class CourtDefensibleEvidence:
    """Court-defensible evidence with legal compliance"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    evidence_id: str = ""
    jurisdiction: LegalJurisdiction = LegalJurisdiction.FEDERAL_US
    court_type: CourtType = CourtType.CRIMINAL
    legal_standard: LegalStandard = LegalStandard.PREPONDERANCE
    admissibility_status: EvidenceAdmissibility = EvidenceAdmissibility.UNDER_REVIEW
    compliance_score: float = 0.0  # 0-100
    legal_requirements_met: List[str] = field(default_factory=list)
    legal_requirements_missing: List[str] = field(default_factory=list)
    challenges: List[Dict[str, Any]] = field(default_factory=list)
    precedents: List[Dict[str, Any]] = field(default_factory=list)
    expert_testimony: Optional[Dict[str, Any]] = None
    foundation_laid: bool = False
    authentication_method: str = ""
    chain_of_custody_verified: bool = False
    hearsay_exception: Optional[str] = None
    relevance_score: float = 0.0
    reliability_score: float = 0.0
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_reviewed: Optional[datetime] = None
    reviewed_by: Optional[str] = None

    def calculate_compliance_score(self) -> float:
        """Calculate overall compliance score"""
        total_requirements = len(self.legal_requirements_met) + len(
            self.legal_requirements_missing
        )
        if total_requirements == 0:
            return 0.0

        met_ratio = len(self.legal_requirements_met) / total_requirements
        base_score = met_ratio * 70  # 70% weight for requirements

        # Add scores for other factors
        relevance_weight = 15  # 15% weight for relevance
        reliability_weight = 15  # 15% weight for reliability

        total_score = (
            base_score
            + (self.relevance_score * relevance_weight)
            + (self.reliability_score * reliability_weight)
        )
        return min(100.0, total_score)

    def check_admissibility(self) -> EvidenceAdmissibility:
        """Determine evidence admissibility status"""
        compliance_score = self.calculate_compliance_score()

        if compliance_score >= 90:
            return EvidenceAdmissibility.ADMISSIBLE
        elif compliance_score >= 70:
            return EvidenceAdmissibility.CONDITIONAL
        elif compliance_score >= 50:
            return EvidenceAdmissibility.UNDER_REVIEW
        else:
            return EvidenceAdmissibility.INADMISSIBLE


@dataclass
class LegalChallenge:
    """Potential legal challenge to evidence"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    evidence_id: str = ""
    challenge_type: str = ""
    description: str = ""
    legal_basis: str = ""
    severity: str = "low"  # low, medium, high, critical
    likelihood: float = 0.0  # 0-1 probability of challenge succeeding
    mitigation_strategy: str = ""
    precedent_cases: List[str] = field(default_factory=list)
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_resolved: bool = False
    resolution_method: Optional[str] = None
    resolution_date: Optional[datetime] = None


@dataclass
class ExpertQualification:
    """Expert witness qualification details"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    expert_name: str = ""
    credentials: List[str] = field(default_factory=list)
    experience_years: int = 0
    specializations: List[str] = field(default_factory=list)
    publications: List[str] = field(default_factory=list)
    testimony_history: List[Dict[str, Any]] = field(default_factory=list)
    education: List[Dict[str, Any]] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    professional_memberships: List[str] = field(default_factory=list)
    cvv_score: float = 0.0  # Court-validated expert score
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def calculate_cvv_score(self) -> float:
        """Calculate court-validated expert score"""
        education_score = min(20, len(self.education) * 5)
        experience_score = min(30, self.experience_years * 1.5)
        publication_score = min(20, len(self.publiclications) * 2)
        testimony_score = min(20, len(self.testimony_history) * 4)
        certification_score = min(10, len(self.certifications) * 2)

        total_score = (
            education_score
            + experience_score
            + publication_score
            + testimony_score
            + certification_score
        )
        return min(100.0, total_score)


class CourtDefensibleEvidence:
    """Court-defensible evidence management system"""

    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.evidence: Dict[str, CourtDefensibleEvidence] = {}
        self.requirements: Dict[str, LegalRequirement] = {}
        self.challenges: Dict[str, LegalChallenge] = {}
        self.experts: Dict[str, ExpertQualification] = {}
        self.running = False
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour

        logger.info("CourtDefensibleEvidence initialized")

    async def initialize(self) -> None:
        """Initialize court-defensible evidence system"""
        if self.db_pool:
            await self._create_database_schema()

        # Load default legal requirements
        await self._load_default_requirements()

        self.running = True
        logger.info("CourtDefensibleEvidence started")

    async def shutdown(self) -> None:
        """Shutdown court-defensible evidence system"""
        self.running = False
        logger.info("CourtDefensibleEvidence shutdown")

    async def _create_database_schema(self) -> None:
        """Create court-defensible evidence database tables"""
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS legal_requirements (
                id UUID PRIMARY KEY,
                jurisdiction TEXT NOT NULL,
                court_type TEXT NOT NULL,
                requirement_type TEXT NOT NULL,
                description TEXT,
                is_mandatory BOOLEAN DEFAULT TRUE,
                verification_method TEXT,
                precedence_level INTEGER DEFAULT 1,
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS court_defensible_evidence (
                id UUID PRIMARY KEY,
                evidence_id UUID NOT NULL,
                jurisdiction TEXT NOT NULL,
                court_type TEXT NOT NULL,
                legal_standard TEXT NOT NULL,
                admissibility_status TEXT NOT NULL,
                compliance_score FLOAT DEFAULT 0.0,
                legal_requirements_met JSONB DEFAULT '[]',
                legal_requirements_missing JSONB DEFAULT '[]',
                challenges JSONB DEFAULT '[]',
                precedents JSONB DEFAULT '[]',
                expert_testimony JSONB,
                foundation_laid BOOLEAN DEFAULT FALSE,
                authentication_method TEXT,
                chain_of_custody_verified BOOLEAN DEFAULT FALSE,
                hearsay_exception TEXT,
                relevance_score FLOAT DEFAULT 0.0,
                reliability_score FLOAT DEFAULT 0.0,
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_reviewed TIMESTAMP WITH TIME ZONE,
                reviewed_by TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS legal_challenges (
                id UUID PRIMARY KEY,
                evidence_id UUID NOT NULL,
                challenge_type TEXT NOT NULL,
                description TEXT,
                legal_basis TEXT,
                severity TEXT NOT NULL,
                likelihood FLOAT DEFAULT 0.0,
                mitigation_strategy TEXT,
                precedent_cases JSONB DEFAULT '[]',
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_resolved BOOLEAN DEFAULT FALSE,
                resolution_method TEXT,
                resolution_date TIMESTAMP WITH TIME ZONE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS expert_qualifications (
                id UUID PRIMARY KEY,
                expert_name TEXT NOT NULL,
                credentials JSONB DEFAULT '[]',
                experience_years INTEGER DEFAULT 0,
                specializations JSONB DEFAULT '[]',
                publications JSONB DEFAULT '[]',
                testimony_history JSONB DEFAULT '[]',
                education JSONB DEFAULT '[]',
                certifications JSONB DEFAULT '[]',
                professional_memberships JSONB DEFAULT '[]',
                cvv_score FLOAT DEFAULT 0.0,
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_legal_requirements_jurisdiction ON legal_requirements(jurisdiction);
            CREATE INDEX IF NOT EXISTS idx_court_defensible_evidence ON court_defensible_evidence(evidence_id);
            CREATE INDEX IF NOT EXISTS idx_legal_challenges_evidence ON legal_challenges(evidence_id);
            CREATE INDEX IF NOT EXISTS idx_expert_qualifications_name ON expert_qualifications(expert_name);
            """,
        ]

        async with self.db_pool.acquire() as conn:
            for query in schema_queries:
                await conn.execute(query)

        logger.info("Court-defensible evidence database schema created")

    async def _load_default_requirements(self) -> None:
        """Load default legal requirements"""
        default_requirements = [
            {
                "jurisdiction": LegalJurisdiction.FEDERAL_US,
                "court_type": CourtType.CRIMINAL,
                "requirement_type": "relevance",
                "description": "Evidence must be relevant to the case",
                "is_mandatory": True,
                "verification_method": "legal_analysis",
                "precedence_level": 1,
            },
            {
                "jurisdiction": LegalJurisdiction.FEDERAL_US,
                "court_type": CourtType.CRIMINAL,
                "requirement_type": "authentication",
                "description": "Evidence must be properly authenticated",
                "is_mandatory": True,
                "verification_method": "chain_of_custody",
                "precedence_level": 2,
            },
            {
                "jurisdiction": LegalJurisdiction.FEDERAL_US,
                "court_type": CourtType.CRIMINAL,
                "requirement_type": "hearsay",
                "description": "Hearsay evidence must fall under an exception",
                "is_mandatory": True,
                "verification_method": "legal_analysis",
                "precedence_level": 3,
            },
            {
                "jurisdiction": LegalJurisdiction.FEDERAL_US,
                "court_type": CourtType.CRIMINAL,
                "requirement_type": "best_evidence",
                "description": "Original evidence preferred over copies",
                "is_mandatory": False,
                "verification_method": "document_analysis",
                "precedence_level": 4,
            },
        ]

        for req_data in default_requirements:
            requirement = LegalRequirement(**req_data)
            self.requirements[requirement.id] = requirement

            if self.db_pool:
                await self._save_requirement_to_db(requirement)

        logger.info(f"Loaded {len(default_requirements)} default legal requirements")

    async def assess_evidence(
        self,
        evidence_id: str,
        evidence_data: Dict[str, Any],
        jurisdiction: LegalJurisdiction,
        court_type: CourtType,
        legal_standard: LegalStandard,
    ) -> CourtDefensibleEvidence:
        """Assess evidence for court admissibility"""
        # Get applicable requirements
        applicable_requirements = await self._get_applicable_requirements(
            jurisdiction, court_type
        )

        # Check compliance with each requirement
        requirements_met = []
        requirements_missing = []

        for requirement in applicable_requirements:
            if requirement.check_compliance(evidence_data):
                requirements_met.append(requirement.id)
            else:
                requirements_missing.append(requirement.id)

        # Calculate scores
        relevance_score = self._calculate_relevance_score(evidence_data)
        reliability_score = self._calculate_reliability_score(evidence_data)

        # Create court-defensible evidence record
        court_evidence = CourtDefensibleEvidence(
            evidence_id=evidence_id,
            jurisdiction=jurisdiction,
            court_type=court_type,
            legal_standard=legal_standard,
            legal_requirements_met=requirements_met,
            legal_requirements_missing=requirements_missing,
            relevance_score=relevance_score,
            reliability_score=reliability_score,
        )

        # Calculate compliance score and admissibility
        court_evidence.compliance_score = court_evidence.calculate_compliance_score()
        court_evidence.admissibility_status = court_evidence.check_admissibility()

        # Identify potential challenges
        challenges = await self._identify_potential_challenges(
            court_evidence, evidence_data
        )
        court_evidence.challenges = challenges

        if self.db_pool:
            await self._save_court_evidence_to_db(court_evidence)

        self.evidence[court_evidence.id] = court_evidence
        logger.info(
            f"Assessed evidence {evidence_id}: {court_evidence.admissibility_status.value}"
        )
        return court_evidence

    async def add_expert_qualification(
        self, expert_data: Dict[str, Any]
    ) -> ExpertQualification:
        """Add expert witness qualification"""
        expert = ExpertQualification(
            expert_name=expert_data["expert_name"],
            credentials=expert_data.get("credentials", []),
            experience_years=expert_data.get("experience_years", 0),
            specializations=expert_data.get("specializations", []),
            publications=expert_data.get("publications", []),
            testimony_history=expert_data.get("testimony_history", []),
            education=expert_data.get("education", []),
            certifications=expert_data.get("certifications", []),
            professional_memberships=expert_data.get("professional_memberships", []),
        )

        expert.cvv_score = expert.calculate_cvv_score()

        if self.db_pool:
            await self._save_expert_to_db(expert)

        self.experts[expert.id] = expert
        logger.info(f"Added expert qualification: {expert.expert_name}")
        return expert

    async def create_legal_challenge(
        self, evidence_id: str, challenge_data: Dict[str, Any]
    ) -> LegalChallenge:
        """Create legal challenge record"""
        challenge = LegalChallenge(
            evidence_id=evidence_id,
            challenge_type=challenge_data["challenge_type"],
            description=challenge_data["description"],
            legal_basis=challenge_data["legal_basis"],
            severity=challenge_data.get("severity", "medium"),
            likelihood=challenge_data.get("likelihood", 0.5),
            mitigation_strategy=challenge_data.get("mitigation_strategy", ""),
            precedent_cases=challenge_data.get("precedent_cases", []),
        )

        if self.db_pool:
            await self._save_challenge_to_db(challenge)

        self.challenges[challenge.id] = challenge
        logger.info(f"Created legal challenge: {challenge.challenge_type}")
        return challenge

    async def get_court_evidence(
        self, evidence_id: str
    ) -> Optional[CourtDefensibleEvidence]:
        """Get court-defensible evidence assessment"""
        for court_evidence in self.evidence.values():
            if court_evidence.evidence_id == evidence_id:
                return court_evidence

        if self.db_pool:
            court_evidence = await self._load_court_evidence_from_db(evidence_id)
            if court_evidence:
                self.evidence[court_evidence.id] = court_evidence
                return court_evidence

        return None

    async def get_expert_by_name(
        self, expert_name: str
    ) -> Optional[ExpertQualification]:
        """Get expert qualification by name"""
        for expert in self.experts.values():
            if expert.expert_name == expert_name:
                return expert

        if self.db_pool:
            expert = await self._load_expert_by_name_from_db(expert_name)
            if expert:
                self.experts[expert.id] = expert
                return expert

        return None

    async def get_challenges_for_evidence(
        self, evidence_id: str
    ) -> List[LegalChallenge]:
        """Get all challenges for evidence"""
        challenges = []
        for challenge in self.challenges.values():
            if challenge.evidence_id == evidence_id:
                challenges.append(challenge)

        if self.db_pool:
            db_challenges = await self._load_challenges_for_evidence(evidence_id)
            for challenge in db_challenges:
                if challenge.id not in [c.id for c in challenges]:
                    challenges.append(challenge)
                    self.challenges[challenge.id] = challenge

        return challenges

    async def prepare_court_submission(self, evidence_id: str) -> Dict[str, Any]:
        """Prepare evidence for court submission"""
        court_evidence = await self.get_court_evidence(evidence_id)
        if not court_evidence:
            raise ValueError(f"No court assessment found for evidence {evidence_id}")

        challenges = await self.get_challenges_for_evidence(evidence_id)

        submission_package = {
            "evidence_id": evidence_id,
            "assessment_id": court_evidence.id,
            "admissibility_status": court_evidence.admissibility_status.value,
            "compliance_score": court_evidence.compliance_score,
            "jurisdiction": court_evidence.jurisdiction.value,
            "court_type": court_evidence.court_type.value,
            "legal_standard": court_evidence.legal_standard.value,
            "requirements_met": court_evidence.legal_requirements_met,
            "requirements_missing": court_evidence.legal_requirements_missing,
            "challenges": [
                {
                    "type": c.challenge_type,
                    "description": c.description,
                    "severity": c.severity,
                    "likelihood": c.likelihood,
                    "mitigation": c.mitigation_strategy,
                }
                for c in challenges
            ],
            "foundation_requirements": self._get_foundation_requirements(
                court_evidence
            ),
            "testimony_preparation": self._prepare_testimony_guidance(court_evidence),
            "exhibit_preparation": self._prepare_exhibit_guidance(court_evidence),
        }

        return submission_package

    def _calculate_relevance_score(self, evidence_data: Dict[str, Any]) -> float:
        """Calculate evidence relevance score"""
        # Simple relevance calculation based on evidence data
        score = 50.0  # Base score

        # Boost for direct case relevance
        if evidence_data.get("case_relevance", False):
            score += 30.0

        # Boost for materiality
        if evidence_data.get("material", False):
            score += 20.0

        return min(100.0, score)

    def _calculate_reliability_score(self, evidence_data: Dict[str, Any]) -> float:
        """Calculate evidence reliability score"""
        score = 50.0  # Base score

        # Boost for verified sources
        if evidence_data.get("source_verified", False):
            score += 25.0

        # Boost for chain of custody
        if evidence_data.get("chain_complete", False):
            score += 25.0

        return min(100.0, score)

    async def _get_applicable_requirements(
        self, jurisdiction: LegalJurisdiction, court_type: CourtType
    ) -> List[LegalRequirement]:
        """Get applicable legal requirements"""
        requirements = []

        for requirement in self.requirements.values():
            if (
                requirement.jurisdiction == jurisdiction
                and requirement.court_type == court_type
            ):
                requirements.append(requirement)

        # Sort by precedence level
        requirements.sort(key=lambda r: r.precedence_level)

        return requirements

    async def _identify_potential_challenges(
        self, court_evidence: CourtDefensibleEvidence, evidence_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify potential legal challenges"""
        challenges = []

        # Check for hearsay issues
        if (
            evidence_data.get("is_hearsay", False)
            and not court_evidence.hearsay_exception
        ):
            challenges.append(
                {
                    "type": "hearsay",
                    "description": "Evidence may be considered hearsay",
                    "severity": "high",
                    "likelihood": 0.7,
                }
            )

        # Check for authentication issues
        if not court_evidence.chain_of_custody_verified:
            challenges.append(
                {
                    "type": "authentication",
                    "description": "Chain of custody not fully verified",
                    "severity": "medium",
                    "likelihood": 0.5,
                }
            )

        # Check for relevance issues
        if court_evidence.relevance_score < 50:
            challenges.append(
                {
                    "type": "relevance",
                    "description": "Evidence relevance may be questioned",
                    "severity": "medium",
                    "likelihood": 0.6,
                }
            )

        return challenges

    def _get_foundation_requirements(
        self, court_evidence: CourtDefensibleEvidence
    ) -> List[str]:
        """Get foundation laying requirements"""
        requirements = [
            "Establish witness competence",
            "Lay foundation for evidence authenticity",
            "Show chain of custody completeness",
            "Demonstrate relevance to case matters",
        ]

        if court_evidence.hearsay_exception:
            requirements.append("Establish hearsay exception applicability")

        return requirements

    def _prepare_testimony_guidance(
        self, court_evidence: CourtDefensibleEvidence
    ) -> Dict[str, Any]:
        """Prepare expert testimony guidance"""
        return {
            "key_points": [
                "Focus on facts within personal knowledge",
                "Use clear, non-technical language when possible",
                "Maintain professional demeanor",
                "Answer questions directly and concisely",
            ],
            "preparation_steps": [
                "Review all evidence thoroughly",
                "Prepare visual aids if appropriate",
                "Anticipate cross-examination questions",
                "Practice explaining complex concepts simply",
            ],
            "legal_considerations": [
                "Stay within scope of expertise",
                "Avoid speculation",
                "Be prepared for Daubert challenges",
                "Maintain objectivity",
            ],
        }

    def _prepare_exhibit_guidance(
        self, court_evidence: CourtDefensibleEvidence
    ) -> Dict[str, Any]:
        """Prepare exhibit submission guidance"""
        return {
            "exhibit_requirements": [
                "Proper authentication foundation",
                "Clear labeling and identification",
                "Relevance demonstration",
                "Chain of custody documentation",
            ],
            "submission_steps": [
                "Mark for identification",
                "Lay foundation",
                "Offer into evidence",
                "Address any objections",
            ],
            "best_practices": [
                "Use high-quality reproductions",
                "Prepare exhibit lists in advance",
                "Have backup copies available",
                "Ensure all exhibits are properly indexed",
            ],
        }

    # Database helper methods
    async def _save_requirement_to_db(self, requirement: LegalRequirement) -> None:
        """Save legal requirement to database"""
        query = """
        INSERT INTO legal_requirements 
        (id, jurisdiction, court_type, requirement_type, description, is_mandatory,
         verification_method, precedence_level, created_date)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (id) DO UPDATE SET
        description = EXCLUDED.description,
        is_mandatory = EXCLUDED.is_mandatory,
        verification_method = EXCLUDED.verification_method,
        precedence_level = EXCLUDED.precedence_level
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                requirement.id,
                requirement.jurisdiction.value,
                requirement.court_type.value,
                requirement.requirement_type,
                requirement.description,
                requirement.is_mandatory,
                requirement.verification_method,
                requirement.precedence_level,
                requirement.created_date,
            )

    async def _save_court_evidence_to_db(
        self, court_evidence: CourtDefensibleEvidence
    ) -> None:
        """Save court-defensible evidence to database"""
        query = """
        INSERT INTO court_defensible_evidence 
        (id, evidence_id, jurisdiction, court_type, legal_standard, admissibility_status,
         compliance_score, legal_requirements_met, legal_requirements_missing, challenges,
         precedents, expert_testimony, foundation_laid, authentication_method,
         chain_of_custody_verified, hearsay_exception, relevance_score, reliability_score,
         created_date, last_reviewed, reviewed_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
        ON CONFLICT (id) DO UPDATE SET
        admissibility_status = EXCLUDED.admissibility_status,
        compliance_score = EXCLUDED.compliance_score,
        legal_requirements_met = EXCLUDED.legal_requirements_met,
        legal_requirements_missing = EXCLUDED.legal_requirements_missing,
        challenges = EXCLUDED.challenges,
        precedents = EXCLUDED.precedents,
        expert_testimony = EXCLUDED.expert_testimony,
        foundation_laid = EXCLUDED.foundation_laid,
        authentication_method = EXCLUDED.authentication_method,
        chain_of_custody_verified = EXCLUDED.chain_of_custody_verified,
        hearsay_exception = EXCLUDED.hearsay_exception,
        relevance_score = EXCLUDED.relevance_score,
        reliability_score = EXCLUDED.reliability_score,
        last_reviewed = EXCLUDED.last_reviewed,
        reviewed_by = EXCLUDED.reviewed_by
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                court_evidence.id,
                court_evidence.evidence_id,
                court_evidence.jurisdiction.value,
                court_evidence.court_type.value,
                court_evidence.legal_standard.value,
                court_evidence.admissibility_status.value,
                court_evidence.compliance_score,
                json.dumps(court_evidence.legal_requirements_met),
                json.dumps(court_evidence.legal_requirements_missing),
                json.dumps(court_evidence.challenges),
                json.dumps(court_evidence.precedents),
                json.dumps(court_evidence.expert_testimony),
                court_evidence.foundation_laid,
                court_evidence.authentication_method,
                court_evidence.chain_of_custody_verified,
                court_evidence.hearsay_exception,
                court_evidence.relevance_score,
                court_evidence.reliability_score,
                court_evidence.created_date,
                court_evidence.last_reviewed,
                court_evidence.reviewed_by,
            )

    async def _save_expert_to_db(self, expert: ExpertQualification) -> None:
        """Save expert qualification to database"""
        query = """
        INSERT INTO expert_qualifications 
        (id, expert_name, credentials, experience_years, specializations, publications,
         testimony_history, education, certifications, professional_memberships, cvv_score, created_date)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (id) DO UPDATE SET
        credentials = EXCLUDED.credentials,
        experience_years = EXCLUDED.experience_years,
        specializations = EXCLUDED.specializations,
        publications = EXCLUDED.publications,
        testimony_history = EXCLUDED.testimony_history,
        education = EXCLUDED.education,
        certifications = EXCLUDED.certifications,
        professional_memberships = EXCLUDED.professional_memberships,
        cvv_score = EXCLUDED.cvv_score
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                expert.id,
                expert.expert_name,
                json.dumps(expert.credentials),
                expert.experience_years,
                json.dumps(expert.specializations),
                json.dumps(expert.publications),
                json.dumps(expert.testimony_history),
                json.dumps(expert.education),
                json.dumps(expert.certifications),
                json.dumps(expert.professional_memberships),
                expert.cvv_score,
                expert.created_date,
            )

    async def _save_challenge_to_db(self, challenge: LegalChallenge) -> None:
        """Save legal challenge to database"""
        query = """
        INSERT INTO legal_challenges 
        (id, evidence_id, challenge_type, description, legal_basis, severity, likelihood,
         mitigation_strategy, precedent_cases, created_date, is_resolved, resolution_method, resolution_date)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (id) DO UPDATE SET
        description = EXCLUDED.description,
        legal_basis = EXCLUDED.legal_basis,
        severity = EXCLUDED.severity,
        likelihood = EXCLUDED.likelihood,
        mitigation_strategy = EXCLUDED.mitigation_strategy,
        precedent_cases = EXCLUDED.precedent_cases,
        is_resolved = EXCLUDED.is_resolved,
        resolution_method = EXCLUDED.resolution_method,
        resolution_date = EXCLUDED.resolution_date
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                challenge.id,
                challenge.evidence_id,
                challenge.challenge_type,
                challenge.description,
                challenge.legal_basis,
                challenge.severity,
                challenge.likelihood,
                challenge.mitigation_strategy,
                json.dumps(challenge.precedent_cases),
                challenge.created_date,
                challenge.is_resolved,
                challenge.resolution_method,
                challenge.resolution_date,
            )

    async def _load_court_evidence_from_db(
        self, evidence_id: str
    ) -> Optional[CourtDefensibleEvidence]:
        """Load court-defensible evidence from database"""
        query = "SELECT * FROM court_defensible_evidence WHERE evidence_id = $1"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, evidence_id)
            if row:
                return CourtDefensibleEvidence(
                    id=row["id"],
                    evidence_id=row["evidence_id"],
                    jurisdiction=LegalJurisdiction(row["jurisdiction"]),
                    court_type=CourtType(row["court_type"]),
                    legal_standard=LegalStandard(row["legal_standard"]),
                    admissibility_status=EvidenceAdmissibility(
                        row["admissibility_status"]
                    ),
                    compliance_score=row["compliance_score"],
                    legal_requirements_met=(
                        json.loads(row["legal_requirements_met"])
                        if row["legal_requirements_met"]
                        else []
                    ),
                    legal_requirements_missing=(
                        json.loads(row["legal_requirements_missing"])
                        if row["legal_requirements_missing"]
                        else []
                    ),
                    challenges=(
                        json.loads(row["challenges"]) if row["challenges"] else []
                    ),
                    precedents=(
                        json.loads(row["precedents"]) if row["precedents"] else []
                    ),
                    expert_testimony=(
                        json.loads(row["expert_testimony"])
                        if row["expert_testimony"]
                        else None
                    ),
                    foundation_laid=row["foundation_laid"],
                    authentication_method=row["authentication_method"],
                    chain_of_custody_verified=row["chain_of_custody_verified"],
                    hearsay_exception=row["hearsay_exception"],
                    relevance_score=row["relevance_score"],
                    reliability_score=row["reliability_score"],
                    created_date=row["created_date"],
                    last_reviewed=row["last_reviewed"],
                    reviewed_by=row["reviewed_by"],
                )
        return None

    async def _load_expert_by_name_from_db(
        self, expert_name: str
    ) -> Optional[ExpertQualification]:
        """Load expert qualification from database by name"""
        query = "SELECT * FROM expert_qualifications WHERE expert_name = $1"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, expert_name)
            if row:
                return ExpertQualification(
                    id=row["id"],
                    expert_name=row["expert_name"],
                    credentials=(
                        json.loads(row["credentials"]) if row["credentials"] else []
                    ),
                    experience_years=row["experience_years"],
                    specializations=(
                        json.loads(row["specializations"])
                        if row["specializations"]
                        else []
                    ),
                    publications=(
                        json.loads(row["publications"]) if row["publications"] else []
                    ),
                    testimony_history=(
                        json.loads(row["testimony_history"])
                        if row["testimony_history"]
                        else []
                    ),
                    education=json.loads(row["education"]) if row["education"] else [],
                    certifications=(
                        json.loads(row["certifications"])
                        if row["certifications"]
                        else []
                    ),
                    professional_memberships=(
                        json.loads(row["professional_memberships"])
                        if row["professional_memberships"]
                        else []
                    ),
                    cvv_score=row["cvv_score"],
                    created_date=row["created_date"],
                )
        return None

    async def _load_challenges_for_evidence(
        self, evidence_id: str
    ) -> List[LegalChallenge]:
        """Load challenges for evidence from database"""
        query = "SELECT * FROM legal_challenges WHERE evidence_id = $1"

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, evidence_id)
            challenges = []
            for row in rows:
                challenge = LegalChallenge(
                    id=row["id"],
                    evidence_id=row["evidence_id"],
                    challenge_type=row["challenge_type"],
                    description=row["description"],
                    legal_basis=row["legal_basis"],
                    severity=row["severity"],
                    likelihood=row["likelihood"],
                    mitigation_strategy=row["mitigation_strategy"],
                    precedent_cases=(
                        json.loads(row["precedent_cases"])
                        if row["precedent_cases"]
                        else []
                    ),
                    created_date=row["created_date"],
                    is_resolved=row["is_resolved"],
                    resolution_method=row["resolution_method"],
                    resolution_date=row["resolution_date"],
                )
                challenges.append(challenge)

            return challenges


# Global court defensible evidence instance
_court_defensible = None


def get_court_defensible_evidence() -> CourtDefensibleEvidence:
    """Get the global court defensible evidence instance"""
    global _court_defensible
    if _court_defensible is None:
        _court_defensible = CourtDefensibleEvidence()
    return _court_defensible
