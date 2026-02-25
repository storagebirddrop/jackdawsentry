"""
Jackdaw Sentry - Court Defensible Evidence Unit Tests
Tests for legal compliance and court-ready evidence preparation
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import json

from src.forensics.court_defensible import (
    CourtDefensibleEvidence,
    LegalStandard,
    ComplianceCategory,
    EvidenceRequirement,
    LegalCompliance,
    CourtReadinessAssessment,
    FoundationRequirement,
    TestimonyPreparation,
    ExhibitPreparation,
)


class TestCourtDefensibleEvidence:
    """Test suite for CourtDefensibleEvidence"""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock PostgreSQL connection pool"""
        return AsyncMock()

    @pytest.fixture
    def court_defensible(self, mock_db_pool):
        """Create CourtDefensibleEvidence instance with mocked dependencies"""
        with patch("src.forensics.court_defensible.get_postgres_connection", return_value=mock_db_pool):
            return CourtDefensibleEvidence(mock_db_pool)

    # ---- Initialization Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_system_initializes(self, court_defensible, mock_db_pool):
        """Test system initialization creates required schema"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        await court_defensible.initialize()
        
        # Verify schema creation queries were executed
        assert mock_conn.execute.call_count >= 1
        mock_pool.acquire.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_system_shutdown(self, court_defensible):
        """Test system shutdown"""
        court_defensible.running = True
        await court_defensible.shutdown()
        assert court_defensible.running is False

    # ---- Legal Compliance Assessment Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_assess_evidence_compliance_success(self, court_defensible, mock_db_pool):
        """Test successful evidence compliance assessment"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        evidence_data = {
            "case_relevance": True,
            "material": True,
            "chain_complete": True
        }
        
        jurisdiction = "federal_us"
        court_type = "criminal"
        legal_standard = "beyond_reasonable_doubt"
        
        # Mock compliance requirements
        mock_requirements = [
            {
                "category": "authentication",
                "description": "Evidence authentication requirements",
                "required": True,
                "met": True,
                "details": "Digital signatures verified"
            },
            {
                "category": "chain_of_custody",
                "description": "Chain of custody requirements",
                "required": True,
                "met": True,
                "details": "Complete custody chain documented"
            },
            {
                "category": "original_format",
                "description": "Original format preservation",
                "required": True,
                "met": True,
                "details": "Original files preserved"
            }
        ]
        mock_conn.fetch.return_value = mock_requirements
        
        compliance = await court_defensible.assess_evidence(
            case_id, evidence_data, jurisdiction, court_type, legal_standard
        )
        
        assert isinstance(compliance, LegalCompliance)
        assert compliance.case_id == case_id
        assert compliance.jurisdiction == jurisdiction
        assert compliance.court_type == court_type
        assert compliance.legal_standard == legal_standard
        assert compliance.overall_score >= 0.9  # High compliance
        assert compliance.is_admissible is True
        assert len(compliance.requirements) == 3
        assert all(req.met for req in compliance.requirements)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_assess_evidence_compliance_failures(self, court_defensible, mock_db_pool):
        """Test evidence compliance assessment with failures"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        evidence_data = {
            "case_relevance": True,
            "material": False,  # Not material
            "chain_complete": False  # Incomplete chain
        }
        
        jurisdiction = "state_california"
        court_type = "civil"
        legal_standard = "preponderance"
        
        # Mock compliance requirements with failures
        mock_requirements = [
            {
                "category": "authentication",
                "description": "Evidence authentication requirements",
                "required": True,
                "met": False,  # Not met
                "details": "Missing digital signatures"
            },
            {
                "category": "chain_of_custody",
                "description": "Chain of custody requirements",
                "required": True,
                "met": False,  # Not met
                "details": "Custody chain gaps identified"
            },
            {
                "category": "original_format",
                "description": "Original format preservation",
                "required": True,
                "met": True,
                "details": "Original files preserved"
            }
        ]
        mock_conn.fetch.return_value = mock_requirements
        
        compliance = await court_defensible.assess_evidence(
            case_id, evidence_data, jurisdiction, court_type, legal_standard
        )
        
        assert compliance.overall_score < 0.7  # Low compliance
        assert compliance.is_admissible is False
        assert len([req for req in compliance.requirements if not req.met]) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_assess_evidence_irrelevant(self, court_defensible, mock_db_pool):
        """Test evidence assessment for irrelevant evidence"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        evidence_data = {
            "case_relevance": False,  # Not relevant
            "material": True,
            "chain_complete": True
        }
        
        jurisdiction = "federal_us"
        court_type = "criminal"
        legal_standard = "beyond_reasonable_doubt"
        
        compliance = await court_defensible.assess_evidence(
            case_id, evidence_data, jurisdiction, court_type, legal_standard
        )
        
        assert compliance.is_admissible is False
        assert compliance.overall_score == 0.0  # Not relevant
        assert "not relevant to case" in compliance.notes.lower()

    # ---- Court Submission Preparation Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prepare_court_submission(self, court_defensible, mock_db_pool):
        """Test successful court submission preparation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        jurisdiction = "federal_us"
        court_type = "criminal"
        legal_standard = "beyond_reasonable_doubt"
        
        # Mock case data
        mock_case = MagicMock(
            id=case_id,
            title="Major Cryptocurrency Case",
            description="Investigation of cryptocurrency fraud scheme",
            status="closed",
            jurisdiction="federal_us",
            legal_standard="beyond_reasonable_doubt"
        )
        
        # Mock evidence with compliance
        mock_evidence = [
            MagicMock(
                id=str(uuid4()),
                title="Verified Transaction Data",
                evidence_type="transaction_data",
                compliance_score=0.95,
                is_admissible=True
            ),
            MagicMock(
                id=str(uuid4()),
                title="Blockchain Analysis",
                evidence_type="address_analysis",
                compliance_score=0.88,
                is_admissible=True
            ),
            MagicMock(
                id=str(uuid4()),
                title="Expert Report",
                evidence_type="expert_report",
                compliance_score=0.92,
                is_admissible=True
            )
        ]
        
        # Mock compliance assessment
        mock_compliance = MagicMock(
            overall_score=0.92,
            is_admissible=True,
            requirements_met=8,
            total_requirements=10
        )
        
        mock_conn.fetchrow.side_effect = [mock_case, mock_compliance]
        mock_conn.fetch.return_value = mock_evidence
        
        submission = await court_defensible.prepare_court_submission(case_id)
        
        assert isinstance(submission, CourtReadinessAssessment)
        assert submission.case_id == case_id
        assert submission.jurisdiction == jurisdiction
        assert submission.court_type == court_type
        assert submission.legal_standard == legal_standard
        assert submission.overall_readiness_score >= 0.9
        assert submission.is_court_ready is True
        assert len(submission.admissible_evidence) == 3
        assert submission.total_evidence == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prepare_court_submission_insufficient_evidence(self, court_defensible, mock_db_pool):
        """Test court submission preparation with insufficient evidence"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        
        # Mock case with insufficient evidence
        mock_case = MagicMock(
            id=case_id,
            title="Minor Case",
            description="Small investigation case",
            status="closed"
        )
        
        # Mock limited evidence
        mock_evidence = [
            MagicMock(
                id=str(uuid4()),
                title="Limited Evidence",
                evidence_type="documents",
                compliance_score=0.6,
                is_admissible=False
            )
        ]
        
        # Mock low compliance assessment
        mock_compliance = MagicMock(
            overall_score=0.45,
            is_admissible=False,
            requirements_met=3,
            total_requirements=10
        )
        
        mock_conn.fetchrow.side_effect = [mock_case, mock_compliance]
        mock_conn.fetch.return_value = mock_evidence
        
        submission = await court_defensible.prepare_court_submission(case_id)
        
        assert submission.overall_readiness_score < 0.7
        assert submission.is_court_ready is False
        assert len(submission.admissible_evidence) == 0
        assert submission.total_evidence == 1

    # ---- Foundation Requirement Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_foundation_requirements(self, court_defensible, mock_db_pool):
        """Test getting foundation requirements for jurisdiction"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        jurisdiction = "federal_us"
        court_type = "criminal"
        legal_standard = "beyond_reasonable_doubt"
        
        # Mock foundation requirements
        mock_requirements = [
            {
                "category": "authentication",
                "description": "Evidence must be authenticated",
                "legal_basis": "Federal Rules of Evidence 901",
                "priority": "critical",
                "requirements": [
                    "Digital signatures or hash verification",
                    "Chain of custody documentation",
                    "Original format preservation"
                ]
            },
            {
                "category": "hearsay",
                "description": "Hearsay evidence exceptions",
                "legal_basis": "Federal Rules of Evidence 803",
                "priority": "high",
                "requirements": [
                    "Present sense impression",
                    "Reliability assessment",
                    "Availability for cross-examination"
                ]
            },
            {
                "category": "expert_testimony",
                "description": "Expert witness requirements",
                "legal_basis": "Federal Rules of Evidence 702",
                "priority": "medium",
                "requirements": [
                    "Qualified expert status",
                    "Reliable methodology",
                    "Peer recognition"
                ]
            }
        ]
        mock_conn.fetch.return_value = mock_requirements
        
        requirements = await court_defensible.get_foundation_requirements(
            jurisdiction, court_type, legal_standard
        )
        
        assert len(requirements) == 3
        assert requirements[0].category == "authentication"
        assert requirements[0].priority == "critical"
        assert requirements[1].category == "hearsay"
        assert requirements[1].priority == "high"
        assert requirements[2].category == "expert_testimony"
        assert requirements[2].priority == "medium"

    # ---- Testimony Preparation Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prepare_testimony(self, court_defensible, mock_db_pool):
        """Test testimony preparation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        evidence_id = str(uuid4())
        witness_type = "expert"
        court_type = "criminal"
        
        # Mock evidence
        mock_evidence = MagicMock(
            id=evidence_id,
            title="Blockchain Expert Analysis",
            evidence_type="expert_report",
            metadata={
                "expert_qualifications": ["PhD in Computer Science", "15 years experience"],
                "expertise_areas": ["blockchain", "cryptocurrency", "digital forensics"],
                "previous_testimony": 5
            }
        )
        
        mock_conn.fetchrow.return_value = mock_evidence
        
        testimony = await court_defensible.prepare_testimony(
            evidence_id, witness_type, court_type
        )
        
        assert isinstance(testimony, TestimonyPreparation)
        assert testimony.evidence_id == evidence_id
        assert testimony.witness_type == witness_type
        assert testimony.court_type == court_type
        assert testimony.prepared_direct_examination is not None
        assert testimony.prepared_cross_examination is not None
        assert testimony.visual_aids is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prepare_lay_testimony(self, court_defensible, mock_db_pool):
        """Test lay witness testimony preparation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        evidence_id = str(uuid4())
        witness_type = "lay"
        court_type = "civil"
        
        # Mock evidence
        mock_evidence = MagicMock(
            id=evidence_id,
            title="Victim Statement",
            evidence_type="testimony",
            metadata={
                "witness_name": "John Doe",
                "observation_date": datetime.now(timezone.utc) - timedelta(days=30),
                "statement_summary": "Observed suspicious transaction"
            }
        )
        
        mock_conn.fetchrow.return_value = mock_evidence
        
        testimony = await court_defensible.prepare_testimony(
            evidence_id, witness_type, court_type
        )
        
        assert testimony.witness_type == "lay"
        assert testimony.prepared_direct_examination is not None
        assert testimony.prepared_cross_examination is not None
        assert testimony.visual_aids is not None

    # ---- Exhibit Preparation Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prepare_exhibits(self, court_defensible, mock_db_pool):
        """Test exhibit preparation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        
        # Mock evidence for exhibits
        mock_evidence = [
            MagicMock(
                id=str(uuid4()),
                title="Transaction Ledger",
                evidence_type="documents",
                file_path="/evidence/ledger.pdf",
                metadata={"page_count": 50, "file_size": 1048576}
            ),
            MagicMock(
                id=str(uuid4()),
                title="Blockchain Screenshot",
                evidence_type="images",
                file_path="/evidence/screenshot.png",
                metadata={"resolution": "1920x1080", "file_size": 524288}
            ),
            MagicMock(
                id=str(uuid4()),
                title="Audio Recording",
                evidence_type="audio",
                file_path="/evidence/interview.mp3",
                metadata={"duration": 1800, "file_size": 8640000}
            )
        ]
        
        mock_conn.fetch.return_value = mock_evidence
        
        exhibits = await court_defensible.prepare_exhibits(case_id)
        
        assert isinstance(exhibits, ExhibitPreparation)
        assert len(exhibits.exhibits) == 3
        assert exhibits.total_exhibits == 3
        
        # Verify exhibit details
        for exhibit in exhibits.exhibits:
            assert exhibit.exhibit_number is not None
            assert exhibit.description is not None
            assert exhibit.markings is not None
            assert exhibit.authentication_verified is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prepare_exhibit_markings(self, court_defensible, temp_dir):
        """Test exhibit marking preparation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        evidence_id = str(uuid4())
        
        # Mock evidence
        mock_evidence = MagicMock(
            id=evidence_id,
            title="Evidence Document",
            file_path=os.path.join(temp_dir, "evidence.pdf"),
            metadata={"page_count": 10}
        )
        
        mock_conn.fetchrow.return_value = mock_evidence
        
        # Mock PDF marking
        with patch("PyPDF2.PdfReader") as mock_pdf_reader, \
             patch("PyPDF2.PdfWriter") as mock_pdf_writer:
            
            mock_reader = MagicMock()
            mock_writer = MagicMock()
            mock_pdf_reader.return_value = mock_reader
            mock_pdf_writer.return_value = mock_writer
            
            # Mock PDF pages
            mock_reader.pages = [MagicMock() for _ in range(10)]
            
            exhibits = await court_defensible.prepare_exhibit_markings(evidence_id)
        
        assert exhibits.success is True
        assert exhibits.marked_pages == 10
        assert exhibits.exhibit_id == evidence_id

    # ---- Legal Standards Tests ----

    @pytest.mark.unit
    def test_legal_standards_comparison(self):
        """Test legal standards comparison logic"""
        standards = [
            LegalStandard.PREPONDERANCE,
            LegalStandard.CLEAR_AND_CONVINCING,
            LegalStandard.BEYOND_REASONABLE_DOUBT,
            LegalStandard.REASONABLE_CERTAINTY
        ]
        
        # Test standard hierarchy
        assert LegalStandard.BEYOND_REASONABLE_DOUBT > LegalStandard.CLEAR_AND_CONVINCING
        assert LegalStandard.CLEAR_AND_CONVINCING > LegalStandard.PREPONDERANCE
        assert LegalStandard.REASONABLE_CERTAINTY < LegalStandard.PREPONDERANCE

    @pytest.mark.unit
    def test_compliance_category_requirements(self):
        """Test compliance category requirements"""
        categories = [
            ComplianceCategory.AUTHENTICATION,
            ComplianceCategory.CHAIN_OF_CUSTODY,
            ComplianceCategory.ORIGINAL_FORMAT,
            ComplianceCategory.HEARSAY,
            ComplianceCategory.EXPERT_TESTIMONY,
            ComplianceCategory.BEST_EVIDENCE_RULE
        ]
        
        for category in categories:
            assert hasattr(category, 'value')
            assert isinstance(category.value, str)

    # ---- Error Handling Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_connection_error(self, court_defensible, mock_db_pool):
        """Test handling of database connection errors"""
        mock_pool.acquire.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await court_defensible.assess_evidence(
                str(uuid4()), {}, "federal_us", "criminal", "beyond_reasonable_doubt"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_jurisdiction_error(self, court_defensible):
        """Test handling of invalid jurisdiction"""
        with pytest.raises(ValueError, match="Invalid jurisdiction"):
            await court_defensible.assess_evidence(
                str(uuid4()), {}, "invalid_jurisdiction", "criminal", "beyond_reasonable_doubt"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_legal_standard_error(self, court_defensible):
        """Test handling of invalid legal standard"""
        with pytest.raises(ValueError, match="Invalid legal standard"):
            await court_defensible.assess_evidence(
                str(uuid4()), {}, "federal_us", "criminal", "invalid_standard"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_evidence_not_found_error(self, court_defensible, mock_db_pool):
        """Test handling of evidence not found error"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        with pytest.raises(ValueError, match="Evidence not found"):
            await court_defensible.prepare_testimony(
                "nonexistent_id", "expert", "criminal"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_case_not_found_error(self, court_defensible, mock_db_pool):
        """Test handling of case not found error"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        with pytest.raises(ValueError, match="Case not found"):
            await court_defensible.prepare_court_submission("nonexistent_id")


class TestLegalComplianceModel:
    """Test suite for LegalCompliance data model"""

    @pytest.mark.unit
    def test_legal_compliance_creation(self):
        """Test LegalCompliance model creation"""
        compliance_data = {
            "id": str(uuid4()),
            "case_id": str(uuid4()),
            "jurisdiction": "federal_us",
            "court_type": "criminal",
            "legal_standard": "beyond_reasonable_doubt",
            "overall_score": 0.92,
            "is_admissible": True,
            "requirements_met": 8,
            "total_requirements": 10,
            "assessment_date": datetime.now(timezone.utc),
            "assessed_by": "legal_analyst_123",
            "notes": "High compliance score achieved",
            "requirements": [
                {
                    "category": "authentication",
                    "description": "Evidence authentication requirements",
                    "required": True,
                    "met": True,
                    "details": "Digital signatures verified"
                },
                {
                    "category": "chain_of_custody",
                    "description": "Chain of custody requirements",
                    "required": True,
                    "met": True,
                    "details": "Complete custody chain documented"
                }
            ],
            "gaps": [],
            "recommendations": []
        }
        
        compliance = LegalCompliance(**compliance_data)
        
        assert compliance.id == compliance_data["id"]
        assert compliance.jurisdiction == "federal_us"
        assert compliance.court_type == "criminal"
        assert compliance.legal_standard == LegalStandard.BEYOND_REASONABLE_DOUBT
        assert compliance.overall_score == 0.92
        assert compliance.is_admissible is True
        assert compliance.requirements_met == 8
        assert compliance.total_requirements == 10
        assert len(compliance.requirements) == 2

    @pytest.mark.unit
    def test_legal_compliance_low_score(self):
        """Test LegalCompliance with low compliance score"""
        compliance_data = {
            "id": str(uuid4()),
            "case_id": str(uuid4()),
            "jurisdiction": "state_california",
            "court_type": "civil",
            "legal_standard": "preponderance",
            "overall_score": 0.45,
            "is_admissible": False,
            "requirements_met": 3,
            "total_requirements": 10,
            "requirements": [
                {
                    "category": "authentication",
                    "description": "Evidence authentication requirements",
                    "required": True,
                    "met": False,
                    "details": "Missing digital signatures"
                },
                {
                    "category": "chain_of_custody",
                    "description": "Chain of custody requirements",
                    "required": True,
                    "met": False,
                    "details": "Custody chain gaps identified"
                }
            ],
            "gaps": ["Authentication failures", "Chain of custody gaps"],
            "recommendations": ["Obtain proper authentication", "Complete custody documentation"]
        }
        
        compliance = LegalCompliance(**compliance_data)
        
        assert compliance.overall_score == 0.45
        assert compliance.is_admissible is False
        assert compliance.requirements_met == 3
        assert len(compliance.gaps) == 2
        assert len(compliance.recommendations) == 2


class TestCourtReadinessAssessmentModel:
    """Test suite for CourtReadinessAssessment data model"""

    @pytest.mark.unit
    def test_court_readiness_assessment_creation(self):
        """Test CourtReadinessAssessment model creation"""
        assessment_data = {
            "case_id": str(uuid4()),
            "jurisdiction": "federal_us",
            "court_type": "criminal",
            "legal_standard": "beyond_reasonable_dubt",
            "overall_readiness_score": 0.88,
            "is_court_ready": True,
            "total_evidence": 15,
            "admissible_evidence": 12,
            "foundation_requirements_met": 8,
            "total_foundation_requirements": 10,
            "testimony_prepared": True,
            "exhibits_prepared": True,
            "requirements_met": [
                "Evidence authentication verified",
                "Chain of custody complete",
                "Original format preserved",
                "Expert testimony qualified"
            ],
            "gaps": ["Minor documentation gaps"],
            "recommendations": ["Complete missing documentation"],
            "assessment_date": datetime.now(timezone.utc),
            "assessed_by": "court_specialist_456"
        }
        
        assessment = CourtReadinessAssessment(**assessment_data)
        
        assert assessment.case_id == assessment_data["case_id"]
        assert assessment.jurisdiction == "federal_us"
        assert assessment.court_type == "criminal"
        assert assessment.legal_standard == LegalStandard.BEYOND_REASONABLE_DOUBT
        assert assessment.overall_readiness_score == 0.88
        assert assessment.is_court_ready is True
        assert assessment.total_evidence == 15
        assert assessment.admissible_evidence == 12
        assert assessment.foundation_requirements_met == 8
        assert assessment.testimony_prepared is True
        assert assessment.exhibits_prepared is True

    @pytest.mark.unit
    def test_court_readiness_insufficient(self):
        """Test CourtReadinessAssessment with insufficient readiness"""
        assessment_data = {
            "case_id": str(uuid4()),
            "jurisdiction": "state_california",
            "court_type": "civil",
            "legal_standard": "preponderance",
            "overall_readiness_score": 0.65,
            "is_court_ready": False,
            "total_evidence": 5,
            "admissible_evidence": 2,
            "foundation_requirements_met": 5,
            "total_foundation_requirements": 10,
            "testimony_prepared": False,
            "exhibits_prepared": False,
            "requirements_met": ["Authentication verified"],
            "gaps": ["Insufficient evidence", "No testimony prepared", "No exhibits prepared"],
            "recommendations": [
                "Collect additional evidence",
                "Prepare witness testimony",
                "Prepare court exhibits"
            ]
        }
        
        assessment = CourtReadinessAssessment(**assessment_data)
        
        assert assessment.overall_readiness_score == 0.65
        assert assessment.is_court_ready is False
        assert assessment.admissible_evidence == 2
        assert assessment.testimony_prepared is False
        assert assessment.exhibits_prepared is False


class TestFoundationRequirementModel:
    """Test suite for FoundationRequirement data model"""

    @pytest.mark.unit
    def test_foundation_requirement_creation(self):
        """Test FoundationRequirement model creation"""
        requirement_data = {
            "category": "authentication",
            "description": "Evidence must be authenticated",
            "legal_basis": "Federal Rules of Evidence 901",
            "priority": "critical",
            "requirements": [
                "Digital signatures or hash verification",
                "Chain of custody documentation",
                "Original format preservation",
                "Expert verification when applicable"
            ],
            "examples": [
                "Digitally signed documents",
                "Hash-verified files",
                "Original file formats preserved"
            ]
        }
        
        requirement = FoundationRequirement(**requirement_data)
        
        assert requirement.category == ComplianceCategory.AUTHENTICATION
        assert requirement.description == "Evidence must be authenticated"
        assert requirement.legal_basis == "Federal Rules of Evidence 901"
        assert requirement.priority == "critical"
        assert len(requirement.requirements) == 4
        assert len(requirement.examples) == 3

    @pytest.mark.unit
    def test_foundation_requirement_priority_levels(self):
        """Test foundation requirement priority levels"""
        priorities = ["critical", "high", "medium", "low"]
        
        for priority in priorities:
            requirement = FoundationRequirement(
                category="test",
                description="Test requirement",
                legal_basis="Test basis",
                priority=priority,
                requirements=["test"],
                examples=[]
            )
            assert requirement.priority == priority


class TestTestimonyPreparationModel:
    """Test suite for TestimonyPreparation data model"""

    @pytest.mark.unit
    def test_testimony_preparation_creation(self):
        """Test TestimonyPreparation model creation"""
        preparation_data = {
            "evidence_id": str(uuid4()),
            "witness_type": "expert",
            "court_type": "criminal",
            "witness_name": "Dr. Jane Smith",
            "witness_qualifications": ["PhD in Computer Science", "15 years experience"],
            "expertise_areas": ["blockchain", "cryptocurrency", "digital forensics"],
            "prepared_direct_examination": {
                "introduction": "Dr. Smith is a qualified expert...",
                "qualifications": "Dr. Smith holds a PhD...",
                "methodology": "The analysis was conducted using...",
                "findings": "Based on the analysis...",
                "conclusions": "The evidence supports..."
            },
            "prepared_cross_examination": {
                "potential_challenges": ["Methodology questions", "Bias allegations"],
                "responses": [
                    "Methodology is industry standard...",
                    "Multiple analysts verified results...",
                    "No bias in analysis..."
                ]
            },
            "visual_aids": [
                {
                    "type": "chart",
                    "title": "Transaction Flow Chart",
                    "description": "Visual representation of transactions"
                },
                {
                    "type": "diagram",
                    "title": "Network Analysis Diagram",
                    "description": "Network relationships"
                }
            ],
            "estimated_duration": 120,
            "preparation_date": datetime.now(timezone.utc)
        }
        
        preparation = TestimonyPreparation(**preparation_data)
        
        assert preparation.evidence_id == preparation_data["evidence_id"]
        assert preparation.witness_type == "expert"
        assert preparation.court_type == "criminal"
        assert preparation.witness_name == "Dr. Jane Smith"
        assert len(preparation.witness_qualifications) == 2
        assert len(preparation.expertise_areas) == 3
        assert preparation.prepared_direct_examination is not None
        assert preparation.prepared_cross_examination is not None
        assert len(preparation.visual_aids) == 2
        assert preparation.estimated_duration == 120


class TestExhibitPreparationModel:
    """Test suite for ExhibitPreparation data model"""

    @pytest.mark.unit
    def test_exhibit_preparation_creation(self):
        """Test ExhibitPreparation model creation"""
        preparation_data = {
            "case_id": str(uuid4()),
            "total_exhibits": 5,
            "exhibits": [
                {
                    "exhibit_number": "EX-001",
                    "title": "Transaction Ledger",
                    "description": "Complete transaction ledger",
                    "evidence_id": str(uuid4()),
                    "file_path": "/evidence/ledger.pdf",
                    "file_size": 1048576,
                    "pages": 50,
                    "markings": [
                        {
                            "page": 1,
                            "marking": "Exhibit 001 - Page 1",
                            "description": "First page of ledger"
                        },
                        {
                            "page": 25,
                            "marking": "Exhibit 001 - Page 25",
                            "description": "Highlighted transaction"
                        }
                    ],
                    "authentication_verified": True,
                    "original_preserved": True,
                    "court_accepted": False
                },
                {
                    "exhibit_number": "EX-002",
                    "title": "Blockchain Screenshot",
                    "description": "Screenshot of blockchain explorer",
                    "evidence_id": str(uuid4()),
                    "file_path": "/evidence/screenshot.png",
                    "file_size": 524288,
                    "markings": [
                        {
                            "page": 1,
                            "marking": "Exhibit 002 - Screenshot",
                            "description": "Blockchain explorer screenshot"
                        }
                    ],
                    "authentication_verified": True,
                    "original_preserved": True,
                    "court_accepted": False
                }
            ],
            "exhibit_list": [
                "EX-001: Transaction Ledger",
                "EX-002: Blockchain Screenshot"
            ],
            "preparation_date": datetime.now(timezone.utc),
            "prepared_by": "evidence_specialist_789"
        }
        
        preparation = ExhibitPreparation(**preparation_data)
        
        assert preparation.case_id == preparation_data["case_id"]
        assert preparation.total_exhibits == 5
        assert len(preparation.exhibits) == 2
        assert preparation.exhibit_list == ["EX-001: Transaction Ledger", "EX-002: Blockchain Screenshot"]
        assert preparation.preparation_date is not None
        assert len(preparation.exhibits[0].markings) == 2
        assert preparation.exhibits[0].authentication_verified is True
