"""
Jackdaw Sentry - Professional Services Framework
Expert support and training framework
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


class ServiceType(str, Enum):
    """Types of professional services"""

    CONSULTATION = "consultation"
    TRAINING = "training"
    INVESTIGATION = "investigation"
    EXPERT_REVIEW = "expert_review"
    COMPLIANCE_AUDIT = "compliance_audit"
    CUSTOM_INTEGRATION = "custom_integration"
    TECHNICAL_SUPPORT = "technical_support"
    LEGAL_SUPPORT = "legal_support"


class ServiceStatus(str, Enum):
    """Status of professional services"""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class ExpertiseLevel(str, Enum):
    """Expertise levels for professionals"""

    JUNIOR = "junior"
    INTERMEDIATE = "intermediate"
    SENIOR = "senior"
    EXPERT = "expert"
    MASTER = "master"


@dataclass
class ProfessionalService:
    """Professional service data structure"""

    id: str
    service_type: ServiceType
    status: ServiceStatus
    client_id: str
    client_name: str
    client_email: str
    title: str
    description: str
    assigned_expert_id: Optional[str] = None
    assigned_expert_name: Optional[str] = None
    expertise_level: ExpertiseLevel = ExpertiseLevel.SENIOR
    requirements: List[str] = None
    deliverables: List[str] = None
    timeline_days: int = 7
    hourly_rate: Optional[float] = None
    estimated_hours: Optional[float] = None
    total_cost: Optional[float] = None
    currency: str = "USD"
    priority: str = "normal"  # low, normal, high, urgent
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None


@dataclass
class Expert:
    """Expert professional data structure"""

    id: str
    name: str
    email: str
    expertise_level: ExpertiseLevel
    specializations: List[str] = None
    service_types: List[ServiceType] = None
    hourly_rate: float = 0.0
    currency: str = "USD"
    availability: Dict[str, Any] = None
    bio: str = None
    certifications: List[str] = None
    years_experience: int = 0
    rating: float = 0.0
    review_count: int = 0
    is_active: bool = True
    timezone: str = "UTC"
    languages: List[str] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class TrainingProgram:
    """Training program data structure"""

    id: str
    title: str
    description: str
    program_type: str  # basic, advanced, specialized
    duration_hours: int
    max_participants: int
    price_per_participant: float
    instructor_id: str
    instructor_name: str
    difficulty_level: str  # beginner, intermediate, advanced
    currency: str = "USD"
    prerequisites: List[str] = None
    learning_objectives: List[str] = None
    modules: List[Dict[str, Any]] = None
    tags: List[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None


class ProfessionalServicesManager:
    """Manager for professional services and expert support"""

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        self._initialized = False

    async def initialize(self):
        """Initialize the professional services manager"""
        if self._initialized:
            return

        logger.info("Initializing Professional Services Manager...")
        await self._create_professional_services_tables()
        await self._load_default_experts()
        await self._load_default_training_programs()
        self._initialized = True
        logger.info("Professional Services Manager initialized successfully")

    async def _create_professional_services_tables(self):
        """Create professional services tables"""

        create_services_table = """
        CREATE TABLE IF NOT EXISTS professional_services (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            service_id VARCHAR(255) NOT NULL UNIQUE,
            service_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            client_id VARCHAR(255) NOT NULL,
            client_name VARCHAR(255) NOT NULL,
            client_email VARCHAR(255) NOT NULL,
            assigned_expert_id VARCHAR(255),
            assigned_expert_name VARCHAR(255),
            expertise_level VARCHAR(20) NOT NULL DEFAULT 'senior',
            title VARCHAR(500) NOT NULL,
            description TEXT,
            requirements TEXT[] DEFAULT '{}',
            deliverables TEXT[] DEFAULT '{}',
            timeline_days INTEGER NOT NULL DEFAULT 7,
            hourly_rate DECIMAL(10,2),
            estimated_hours DECIMAL(10,2),
            total_cost DECIMAL(15,2),
            currency VARCHAR(10) NOT NULL DEFAULT 'USD',
            priority VARCHAR(20) NOT NULL DEFAULT 'normal',
            tags TEXT[] DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            scheduled_start TIMESTAMP WITH TIME ZONE,
            scheduled_end TIMESTAMP WITH TIME ZONE,
            actual_start TIMESTAMP WITH TIME ZONE,
            actual_end TIMESTAMP WITH TIME ZONE
        );
        
        CREATE INDEX IF NOT EXISTS idx_prof_services_type ON professional_services(service_type);
        CREATE INDEX IF NOT EXISTS idx_prof_services_status ON professional_services(status);
        CREATE INDEX IF NOT EXISTS idx_prof_services_client ON professional_services(client_id);
        CREATE INDEX IF NOT EXISTS idx_prof_services_expert ON professional_services(assigned_expert_id);
        CREATE INDEX IF NOT EXISTS idx_prof_services_priority ON professional_services(priority);
        CREATE INDEX IF NOT EXISTS idx_prof_services_created ON professional_services(created_at);
        """

        create_experts_table = """
        CREATE TABLE IF NOT EXISTS professional_experts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            expert_id VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            expertise_level VARCHAR(20) NOT NULL DEFAULT 'senior',
            specializations TEXT[] DEFAULT '{}',
            service_types TEXT[] DEFAULT '{}',
            hourly_rate DECIMAL(10,2) NOT NULL DEFAULT 0.0,
            currency VARCHAR(10) NOT NULL DEFAULT 'USD',
            availability JSONB DEFAULT '{}',
            bio TEXT,
            certifications TEXT[] DEFAULT '{}',
            years_experience INTEGER NOT NULL DEFAULT 0,
            rating DECIMAL(3,2) NOT NULL DEFAULT 0.0,
            review_count INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
            languages TEXT[] DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_experts_level ON professional_experts(expertise_level);
        CREATE INDEX IF NOT EXISTS idx_experts_active ON professional_experts(is_active);
        CREATE INDEX IF NOT EXISTS idx_experts_rating ON professional_experts(rating);
        CREATE INDEX IF NOT EXISTS idx_experts_specializations ON professional_experts USING GIN(specializations);
        """

        create_training_table = """
        CREATE TABLE IF NOT EXISTS training_programs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            program_id VARCHAR(255) NOT NULL UNIQUE,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            program_type VARCHAR(50) NOT NULL,
            duration_hours INTEGER NOT NULL,
            max_participants INTEGER NOT NULL DEFAULT 20,
            price_per_participant DECIMAL(10,2) NOT NULL,
            currency VARCHAR(10) NOT NULL DEFAULT 'USD',
            prerequisites TEXT[] DEFAULT '{}',
            learning_objectives TEXT[] DEFAULT '{}',
            modules JSONB DEFAULT '[]',
            instructor_id VARCHAR(255) NOT NULL,
            instructor_name VARCHAR(255) NOT NULL,
            difficulty_level VARCHAR(20) NOT NULL DEFAULT 'intermediate',
            tags TEXT[] DEFAULT '{}',
            is_active BOOLEAN DEFAULT TRUE,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_training_type ON training_programs(program_type);
        CREATE INDEX IF NOT EXISTS idx_training_instructor ON training_programs(instructor_id);
        CREATE INDEX IF NOT EXISTS idx_training_difficulty ON training_programs(difficulty_level);
        CREATE INDEX IF NOT EXISTS idx_training_active ON training_programs(is_active);
        """

        create_sessions_table = """
        CREATE TABLE IF NOT EXISTS training_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id VARCHAR(255) NOT NULL UNIQUE,
            program_id VARCHAR(255) NOT NULL,
            title VARCHAR(500) NOT NULL,
            scheduled_start TIMESTAMP WITH TIME ZONE NOT NULL,
            scheduled_end TIMESTAMP WITH TIME ZONE NOT NULL,
            instructor_id VARCHAR(255) NOT NULL,
            instructor_name VARCHAR(255) NOT NULL,
            max_participants INTEGER NOT NULL DEFAULT 20,
            current_participants INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(50) NOT NULL DEFAULT 'scheduled',
            location VARCHAR(255),
            meeting_url VARCHAR(500),
            materials JSONB DEFAULT '{}',
            notes TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_training_sessions_program ON training_sessions(program_id);
        CREATE INDEX IF NOT EXISTS idx_training_sessions_instructor ON training_sessions(instructor_id);
        CREATE INDEX IF NOT EXISTS idx_training_sessions_status ON training_sessions(status);
        CREATE INDEX IF NOT EXISTS idx_training_sessions_start ON training_sessions(scheduled_start);
        """

        conn = await get_postgres_connection()
        try:
            await conn.execute(create_services_table)
            await conn.execute(create_experts_table)
            await conn.execute(create_training_table)
            await conn.execute(create_sessions_table)
            await conn.commit()
            logger.info("Professional services tables created/verified")
        except Exception as e:
            logger.error(f"Error creating professional services tables: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def _load_default_experts(self):
        """Load default expert professionals"""

        default_experts = [
            Expert(
                id="expert_001",
                name="Dr. Sarah Chen",
                email="sarah.chen@jackdawsentry.com",
                expertise_level=ExpertiseLevel.MASTER,
                specializations=[
                    "blockchain_forensics",
                    "crypto_investigations",
                    "compliance",
                ],
                service_types=[
                    ServiceType.INVESTIGATION,
                    ServiceType.EXPERT_REVIEW,
                    ServiceType.CONSULTATION,
                ],
                hourly_rate=250.0,
                currency="USD",
                years_experience=12,
                rating=4.9,
                review_count=127,
                bio="Leading blockchain forensics expert with 12+ years experience in cryptocurrency investigations and compliance.",
                certifications=["CFE", "CCE", "CISSP", "CAM"],
                languages=["English", "Mandarin"],
                availability={
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                },
            ),
            Expert(
                id="expert_002",
                name="Michael Rodriguez",
                email="michael.rodriguez@jackdawsentry.com",
                expertise_level=ExpertiseLevel.EXPERT,
                specializations=[
                    "aml_compliance",
                    "regulatory_framework",
                    "risk_assessment",
                ],
                service_types=[
                    ServiceType.COMPLIANCE_AUDIT,
                    ServiceType.CONSULTATION,
                    ServiceType.TRAINING,
                ],
                hourly_rate=180.0,
                currency="USD",
                years_experience=8,
                rating=4.7,
                review_count=89,
                bio="AML compliance specialist with extensive experience in FATF regulations and crypto compliance frameworks.",
                certifications=["CAMS", "CAMS-AML", "CAMS-Audit"],
                languages=["English", "Spanish"],
                availability={
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                },
            ),
            Expert(
                id="expert_003",
                name="Emily Thompson",
                email="emily.thompson@jackdawsentry.com",
                expertise_level=ExpertiseLevel.SENIOR,
                specializations=[
                    "technical_analysis",
                    "blockchain_architecture",
                    "smart_contracts",
                ],
                service_types=[
                    ServiceType.TECHNICAL_SUPPORT,
                    ServiceType.CUSTOM_INTEGRATION,
                    ServiceType.TRAINING,
                ],
                hourly_rate=150.0,
                currency="USD",
                years_experience=6,
                rating=4.8,
                review_count=64,
                bio="Blockchain technical expert specializing in smart contract security and blockchain architecture analysis.",
                certifications=["CEH", "OSCP", "AWS", "Azure"],
                languages=["English", "French"],
                availability={
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                },
            ),
            Expert(
                id="expert_004",
                name="David Kim",
                email="david.kim@jackdawsentry.com",
                expertise_level=ExpertiseLevel.SENIOR,
                specializations=[
                    "legal_compliance",
                    "regulatory_law",
                    "international_standards",
                ],
                service_types=[
                    ServiceType.LEGAL_SUPPORT,
                    ServiceType.COMPLIANCE_AUDIT,
                    ServiceType.CONSULTATION,
                ],
                hourly_rate=200.0,
                currency="USD",
                years_experience=7,
                rating=4.6,
                review_count=52,
                bio="Legal compliance expert with focus on international crypto regulations and compliance frameworks.",
                certifications=["JD", "LLM", "CAMS", "CAMS-AML"],
                languages=["English", "Korean"],
                availability={
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                },
            ),
            Expert(
                id="expert_005",
                name="Lisa Anderson",
                email="lisa.anderson@jackdawsentry.com",
                expertise_level=ExpertiseLevel.INTERMEDIATE,
                specializations=[
                    "data_analysis",
                    "pattern_recognition",
                    "machine_learning",
                ],
                service_types=[
                    ServiceType.TECHNICAL_SUPPORT,
                    ServiceType.EXPERT_REVIEW,
                    ServiceType.TRAINING,
                ],
                hourly_rate=120.0,
                currency="USD",
                years_experience=4,
                rating=4.5,
                review_count=38,
                bio="Data analysis specialist with expertise in pattern recognition and machine learning for crypto investigations.",
                certifications=["MSc", "Python", "R", "SQL"],
                languages=["English", "German"],
                availability={
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                },
            ),
        ]

        for expert in default_experts:
            await self.add_expert(expert)

    async def _load_default_training_programs(self):
        """Load default training programs"""

        default_programs = [
            TrainingProgram(
                id="program_001",
                title="Blockchain Fundamentals for Investigators",
                description="Comprehensive introduction to blockchain technology for law enforcement and compliance professionals.",
                program_type="basic",
                duration_hours=16,
                max_participants=25,
                price_per_participant=500.0,
                currency="USD",
                prerequisites=[
                    "Basic computer skills",
                    "Understanding of financial crimes",
                ],
                learning_objectives=[
                    "Understand blockchain fundamentals",
                    "Identify different blockchain types",
                    "Basic cryptocurrency transaction analysis",
                    "Introduction to crypto compliance",
                ],
                modules=[
                    {
                        "title": "Introduction to Blockchain",
                        "duration": 4,
                        "topics": [
                            "What is blockchain",
                            "How it works",
                            "Key concepts",
                        ],
                    },
                    {
                        "title": "Cryptocurrency Basics",
                        "duration": 4,
                        "topics": ["Bitcoin", "Ethereum", "Altcoins", "Stablecoins"],
                    },
                    {
                        "title": "Transaction Analysis",
                        "duration": 4,
                        "topics": [
                            "Reading transactions",
                            "Address analysis",
                            "Basic tools",
                        ],
                    },
                    {
                        "title": "Compliance Introduction",
                        "duration": 4,
                        "topics": ["AML basics", "KYC", "Regulatory overview"],
                    },
                ],
                instructor_id="expert_001",
                instructor_name="Dr. Sarah Chen",
                difficulty_level="beginner",
                tags=["blockchain", "basics", "investigation", "compliance"],
            ),
            TrainingProgram(
                id="program_002",
                title="Advanced Crypto Investigation Techniques",
                description="Advanced techniques for cryptocurrency investigation and forensic analysis.",
                program_type="advanced",
                duration_hours=24,
                max_participants=15,
                price_per_participant=1200.0,
                currency="USD",
                prerequisites=[
                    "Blockchain Fundamentals",
                    "Basic investigation experience",
                ],
                learning_objectives=[
                    "Advanced transaction tracing",
                    "Cross-chain analysis",
                    "Mixing service identification",
                    "Evidence collection and preservation",
                ],
                modules=[
                    {
                        "title": "Advanced Transaction Analysis",
                        "duration": 6,
                        "topics": [
                            "Multi-hop tracing",
                            "Pattern analysis",
                            "Anomaly detection",
                        ],
                    },
                    {
                        "title": "Cross-Chain Investigation",
                        "duration": 6,
                        "topics": [
                            "Bridge analysis",
                            "Cross-chain transfers",
                            "Multi-chain tracking",
                        ],
                    },
                    {
                        "title": "Mixing Services Analysis",
                        "duration": 6,
                        "topics": [
                            "Tornado Cash",
                            "Other mixers",
                            "De-obfuscation techniques",
                        ],
                    },
                    {
                        "title": "Evidence Collection",
                        "duration": 6,
                        "topics": [
                            "Legal evidence",
                            "Chain analysis",
                            "Report writing",
                        ],
                    },
                ],
                instructor_id="expert_001",
                instructor_name="Dr. Sarah Chen",
                difficulty_level="advanced",
                tags=["investigation", "forensics", "advanced", "cross-chain"],
            ),
            TrainingProgram(
                id="program_003",
                title="Crypto AML Compliance Certification",
                description="Complete AML compliance training for cryptocurrency businesses and financial institutions.",
                program_type="specialized",
                duration_hours=32,
                max_participants=20,
                price_per_participant=2000.0,
                currency="USD",
                prerequisites=[
                    "Financial compliance experience",
                    "Blockchain knowledge",
                ],
                learning_objectives=[
                    "FATF Travel Rule compliance",
                    "Crypto-specific AML procedures",
                    "Risk assessment frameworks",
                    "Regulatory reporting requirements",
                ],
                modules=[
                    {
                        "title": "Regulatory Framework",
                        "duration": 8,
                        "topics": ["FATF guidelines", "Travel Rule", "MiCA", "5AMLD"],
                    },
                    {
                        "title": "Risk Assessment",
                        "duration": 8,
                        "topics": [
                            "Risk scoring",
                            "Customer due diligence",
                            "Transaction monitoring",
                        ],
                    },
                    {
                        "title": "Compliance Procedures",
                        "duration": 8,
                        "topics": ["KYC/CDD", "SAR filing", "Record keeping"],
                    },
                    {
                        "title": "Reporting Systems",
                        "duration": 8,
                        "topics": [
                            "Automated monitoring",
                            "Manual reviews",
                            "Audit trails",
                        ],
                    },
                ],
                instructor_id="expert_002",
                instructor_name="Michael Rodriguez",
                difficulty_level="advanced",
                tags=["aml", "compliance", "certification", "regulation"],
            ),
            TrainingProgram(
                id="program_004",
                title="Smart Contract Security Analysis",
                description="Technical training for smart contract security assessment and vulnerability analysis.",
                program_type="specialized",
                duration_hours=20,
                max_participants=12,
                price_per_participant=800.0,
                currency="USD",
                prerequisites=["Programming experience", "Blockchain basics"],
                learning_objectives=[
                    "Smart contract architecture",
                    "Common vulnerabilities",
                    "Security assessment tools",
                    "Audit methodologies",
                ],
                modules=[
                    {
                        "title": "Smart Contract Basics",
                        "duration": 4,
                        "topics": [
                            "Solidity basics",
                            "Contract structure",
                            "Gas optimization",
                        ],
                    },
                    {
                        "title": "Common Vulnerabilities",
                        "duration": 6,
                        "topics": ["Reentrancy", "Integer overflow", "Access control"],
                    },
                    {
                        "title": "Security Tools",
                        "duration": 6,
                        "topics": ["Slither", "Mythril", "Manual review"],
                    },
                    {
                        "title": "Audit Methodology",
                        "duration": 4,
                        "topics": ["Audit process", "Reporting", "Best practices"],
                    },
                ],
                instructor_id="expert_003",
                instructor_name="Emily Thompson",
                difficulty_level="intermediate",
                tags=["smart-contracts", "security", "audit", "technical"],
            ),
        ]

        for program in default_programs:
            await self.add_training_program(program)

    async def add_expert(self, expert: Expert) -> str:
        """Add a new expert professional"""

        insert_query = """
        INSERT INTO professional_experts (
            expert_id, name, email, expertise_level, specializations, service_types,
            hourly_rate, currency, availability, bio, certifications, years_experience,
            rating, review_count, is_active, timezone, languages, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
        RETURNING id
        """

        conn = await get_postgres_connection()
        try:
            result = await conn.fetchrow(
                insert_query,
                expert.id,
                expert.name,
                expert.email,
                expert.expertise_level.value,
                expert.specializations or [],
                (
                    [st.value for st in expert.service_types]
                    if expert.service_types
                    else []
                ),
                expert.hourly_rate,
                expert.currency,
                json.dumps(expert.availability or {}),
                expert.bio,
                expert.certifications or [],
                expert.years_experience,
                expert.rating,
                expert.review_count,
                expert.is_active,
                expert.timezone,
                expert.languages or [],
                json.dumps(expert.metadata or {}),
            )

            await conn.commit()
            logger.info(f"Added expert: {expert.name}")
            return str(result["id"])

        except Exception as e:
            logger.error(f"Error adding expert {expert.id}: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def get_expert(self, expert_id: str) -> Optional[Expert]:
        """Get expert by ID"""

        select_query = """
        SELECT id, expert_id, name, email, expertise_level, specializations, service_types,
               hourly_rate, currency, availability, bio, certifications, years_experience,
               rating, review_count, is_active, timezone, languages, metadata, created_at, updated_at
        FROM professional_experts
        WHERE expert_id = $1
        """

        conn = await get_postgres_connection()
        try:
            result = await conn.fetchrow(select_query, expert_id)

            if result:
                return Expert(
                    id=result["expert_id"],
                    name=result["name"],
                    email=result["email"],
                    expertise_level=ExpertiseLevel(result["expertise_level"]),
                    specializations=result["specializations"],
                    service_types=[ServiceType(st) for st in result["service_types"]],
                    hourly_rate=float(result["hourly_rate"]),
                    currency=result["currency"],
                    availability=result["availability"],
                    bio=result["bio"],
                    certifications=result["certifications"],
                    years_experience=result["years_experience"],
                    rating=float(result["rating"]),
                    review_count=result["review_count"],
                    is_active=result["is_active"],
                    timezone=result["timezone"],
                    languages=result["languages"],
                    metadata=result["metadata"],
                    created_at=result["created_at"],
                    updated_at=result["updated_at"],
                )

            return None

        except Exception as e:
            logger.error(f"Error getting expert {expert_id}: {e}")
            return None
        finally:
            await conn.close()

    async def search_experts(
        self,
        service_type: Optional[ServiceType] = None,
        expertise_level: Optional[ExpertiseLevel] = None,
        specializations: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        is_active: Optional[bool] = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Expert]:
        """Search experts with filters"""

        conditions = []
        params = []
        param_count = 0

        if service_type:
            conditions.append(f"$1 = ANY(service_types)")
            params.append(service_type.value)
            param_count += 1

        if expertise_level:
            conditions.append(f"expertise_level = ${param_count + 1}")
            params.append(expertise_level.value)
            param_count += 1

        if specializations:
            placeholders = ",".join(
                [f"${i + param_count + 1}" for i in range(len(specializations))]
            )
            conditions.append(f"${param_count + 1} = ANY(specializations)")
            params.extend(specializations)
            param_count += 1

        if min_rating is not None:
            conditions.append(f"rating >= ${param_count + 1}")
            params.append(min_rating)
            param_count += 1

        if is_active is not None:
            conditions.append(f"is_active = ${param_count + 1}")
            params.append(is_active)
            param_count += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        select_query = f"""
        SELECT id, expert_id, name, email, expertise_level, specializations, service_types,
               hourly_rate, currency, availability, bio, certifications, years_experience,
               rating, review_count, is_active, timezone, languages, metadata, created_at, updated_at
        FROM professional_experts
        {where_clause}
        ORDER BY rating DESC, years_experience DESC
        LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """

        params.extend([limit, offset])

        conn = await get_postgres_connection()
        try:
            results = await conn.fetch(select_query, *params)

            experts = []
            for result in results:
                expert = Expert(
                    id=result["expert_id"],
                    name=result["name"],
                    email=result["email"],
                    expertise_level=ExpertiseLevel(result["expertise_level"]),
                    specializations=result["specializations"],
                    service_types=[ServiceType(st) for st in result["service_types"]],
                    hourly_rate=float(result["hourly_rate"]),
                    currency=result["currency"],
                    availability=result["availability"],
                    bio=result["bio"],
                    certifications=result["certifications"],
                    years_experience=result["years_experience"],
                    rating=float(result["rating"]),
                    review_count=result["review_count"],
                    is_active=result["is_active"],
                    timezone=result["timezone"],
                    languages=result["languages"],
                    metadata=result["metadata"],
                    created_at=result["created_at"],
                    updated_at=result["updated_at"],
                )
                experts.append(expert)

            return experts

        except Exception as e:
            logger.error(f"Error searching experts: {e}")
            return []
        finally:
            await conn.close()

    async def add_training_program(self, program: TrainingProgram) -> str:
        """Add a new training program"""

        insert_query = """
        INSERT INTO training_programs (
            program_id, title, description, program_type, duration_hours, max_participants,
            price_per_participant, currency, prerequisites, learning_objectives, modules,
            instructor_id, instructor_name, difficulty_level, tags, is_active, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
        RETURNING id
        """

        conn = await get_postgres_connection()
        try:
            result = await conn.fetchrow(
                insert_query,
                program.id,
                program.title,
                program.description,
                program.program_type,
                program.duration_hours,
                program.max_participants,
                program.price_per_participant,
                program.currency,
                program.prerequisites or [],
                program.learning_objectives or [],
                json.dumps(program.modules or []),
                program.instructor_id,
                program.instructor_name,
                program.difficulty_level,
                program.tags or [],
                program.is_active,
                json.dumps(program.metadata or {}),
            )

            await conn.commit()
            logger.info(f"Added training program: {program.title}")
            return str(result["id"])

        except Exception as e:
            logger.error(f"Error adding training program {program.id}: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def get_training_program(self, program_id: str) -> Optional[TrainingProgram]:
        """Get training program by ID"""

        select_query = """
        SELECT id, program_id, title, description, program_type, duration_hours, max_participants,
               price_per_participant, currency, prerequisites, learning_objectives, modules,
               instructor_id, instructor_name, difficulty_level, tags, is_active, metadata,
               created_at, updated_at
        FROM training_programs
        WHERE program_id = $1
        """

        conn = await get_postgres_connection()
        try:
            result = await conn.fetchrow(select_query, program_id)

            if result:
                return TrainingProgram(
                    id=result["program_id"],
                    title=result["title"],
                    description=result["description"],
                    program_type=result["program_type"],
                    duration_hours=result["duration_hours"],
                    max_participants=result["max_participants"],
                    price_per_participant=float(result["price_per_participant"]),
                    currency=result["currency"],
                    prerequisites=result["prerequisites"],
                    learning_objectives=result["learning_objectives"],
                    modules=result["modules"],
                    instructor_id=result["instructor_id"],
                    instructor_name=result["instructor_name"],
                    difficulty_level=result["difficulty_level"],
                    tags=result["tags"],
                    is_active=result["is_active"],
                    metadata=result["metadata"],
                    created_at=result["created_at"],
                    updated_at=result["updated_at"],
                )

            return None

        except Exception as e:
            logger.error(f"Error getting training program {program_id}: {e}")
            return None
        finally:
            await conn.close()

    async def search_training_programs(
        self,
        program_type: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        instructor_id: Optional[str] = None,
        max_price: Optional[float] = None,
        is_active: Optional[bool] = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[TrainingProgram]:
        """Search training programs with filters"""

        conditions = []
        params = []
        param_count = 0

        if program_type:
            conditions.append(f"program_type = ${param_count + 1}")
            params.append(program_type)
            param_count += 1

        if difficulty_level:
            conditions.append(f"difficulty_level = ${param_count + 1}")
            params.append(difficulty_level)
            param_count += 1

        if instructor_id:
            conditions.append(f"instructor_id = ${param_count + 1}")
            params.append(instructor_id)
            param_count += 1

        if max_price is not None:
            conditions.append(f"price_per_participant <= ${param_count + 1}")
            params.append(max_price)
            param_count += 1

        if is_active is not None:
            conditions.append(f"is_active = ${param_count + 1}")
            params.append(is_active)
            param_count += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        select_query = f"""
        SELECT id, program_id, title, description, program_type, duration_hours, max_participants,
               price_per_participant, currency, prerequisites, learning_objectives, modules,
               instructor_id, instructor_name, difficulty_level, tags, is_active, metadata,
               created_at, updated_at
        FROM training_programs
        {where_clause}
        ORDER BY price_per_participant ASC, title ASC
        LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """

        params.extend([limit, offset])

        conn = await get_postgres_connection()
        try:
            results = await conn.fetch(select_query, *params)

            programs = []
            for result in results:
                program = TrainingProgram(
                    id=result["program_id"],
                    title=result["title"],
                    description=result["description"],
                    program_type=result["program_type"],
                    duration_hours=result["duration_hours"],
                    max_participants=result["max_participants"],
                    price_per_participant=float(result["price_per_participant"]),
                    currency=result["currency"],
                    prerequisites=result["prerequisites"],
                    learning_objectives=result["learning_objectives"],
                    modules=result["modules"],
                    instructor_id=result["instructor_id"],
                    instructor_name=result["instructor_name"],
                    difficulty_level=result["difficulty_level"],
                    tags=result["tags"],
                    is_active=result["is_active"],
                    metadata=result["metadata"],
                    created_at=result["created_at"],
                    updated_at=result["updated_at"],
                )
                programs.append(program)

            return programs

        except Exception as e:
            logger.error(f"Error searching training programs: {e}")
            return []
        finally:
            await conn.close()

    async def get_statistics(self) -> Dict[str, Any]:
        """Get professional services statistics"""

        try:
            conn = await get_postgres_connection()

            # Get expert statistics
            expert_stats_query = """
            SELECT 
                COUNT(*) as total_experts,
                COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_experts,
                AVG(rating) as avg_rating,
                AVG(years_experience) as avg_experience,
                expertise_level,
                COUNT(*) as count
            FROM professional_experts
            GROUP BY expertise_level
            """

            expert_results = await conn.fetch(expert_stats_query)

            total_experts = sum(row["count"] for row in expert_results)
            active_experts = sum(row["active_experts"] for row in expert_results)
            avg_rating = (
                float(expert_results[0]["avg_rating"])
                if expert_results and expert_results[0]["avg_rating"]
                else 0.0
            )
            avg_experience = (
                float(expert_results[0]["avg_experience"])
                if expert_results and expert_results[0]["avg_experience"]
                else 0.0
            )

            # Get training program statistics
            training_stats_query = """
            SELECT 
                COUNT(*) as total_programs,
                COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_programs,
                AVG(price_per_participant) as avg_price,
                AVG(duration_hours) as avg_duration,
                program_type,
                difficulty_level,
                COUNT(*) as count
            FROM training_programs
            GROUP BY program_type, difficulty_level
            """

            training_results = await conn.fetch(training_stats_query)

            total_programs = sum(row["count"] for row in training_results)
            active_programs = sum(row["active_programs"] for row in training_results)
            avg_price = (
                float(training_results[0]["avg_price"])
                if training_results and training_results[0]["avg_price"]
                else 0.0
            )
            avg_duration = (
                float(training_results[0]["avg_duration"])
                if training_results and training_results[0]["avg_duration"]
                else 0.0
            )

            return {
                "experts": {
                    "total_experts": total_experts,
                    "active_experts": active_experts,
                    "avg_rating": avg_rating,
                    "avg_experience": avg_experience,
                    "by_level": [
                        {
                            "expertise_level": row["expertise_level"],
                            "count": row["count"],
                            "active_count": row["active_experts"],
                        }
                        for row in expert_results
                    ],
                },
                "training_programs": {
                    "total_programs": total_programs,
                    "active_programs": active_programs,
                    "avg_price": avg_price,
                    "avg_duration": avg_duration,
                    "by_type": [
                        {
                            "program_type": row["program_type"],
                            "difficulty_level": row["difficulty_level"],
                            "count": row["count"],
                            "active_count": row["active_programs"],
                        }
                        for row in training_results
                    ],
                },
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting professional services statistics: {e}")
            return {}
        finally:
            await conn.close()

    def clear_cache(self):
        """Clear the professional services cache"""
        self.cache.clear()
        logger.info("Professional services cache cleared")


# Global professional services manager instance
_professional_services_manager = None


def get_professional_services_manager() -> ProfessionalServicesManager:
    """Get the global professional services manager instance"""
    global _professional_services_manager
    if _professional_services_manager is None:
        _professional_services_manager = ProfessionalServicesManager()
    return _professional_services_manager
