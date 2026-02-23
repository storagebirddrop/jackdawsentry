"""
Jackdaw Sentry - Professional Services Unit Tests
Tests for expert support, training, and professional services management
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.intelligence.professional_services import (
    ProfessionalServicesManager,
    ServiceType,
    ServiceStatus,
    ExpertiseLevel,
    ProfessionalService,
    ProfessionalProfile,
    TrainingProgram,
    TrainingEnrollment,
    ServiceStatistics,
)


class TestProfessionalServicesManager:
    """Test suite for ProfessionalServicesManager"""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock PostgreSQL connection pool"""
        return AsyncMock()

    @pytest.fixture
    def services_manager(self, mock_db_pool):
        """Create ProfessionalServicesManager instance with mocked dependencies"""
        with patch("src.intelligence.professional_services.get_postgres_connection", return_value=mock_db_pool):
            return ProfessionalServicesManager(mock_db_pool)

    # ---- Initialization Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_manager_initializes(self, services_manager, mock_db_pool):
        """Test manager initialization creates required schema"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        await services_manager.initialize()
        
        # Verify schema creation queries were executed
        assert mock_conn.execute.call_count >= 1
        mock_pool.acquire.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_manager_shutdown(self, services_manager):
        """Test manager shutdown"""
        services_manager.running = True
        await services_manager.shutdown()
        assert services_manager.running is False

    # ---- Service Creation Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_service_success(self, services_manager, mock_db_pool):
        """Test successful service creation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": str(uuid4())}
        
        service_data = {
            "service_type": "consultation",
            "title": "Blockchain Investigation Consultation",
            "description": "Expert consultation for blockchain investigation",
            "priority": "high",
            "requested_date": datetime.now(timezone.utc) + timedelta(days=7),
            "duration_hours": 8,
            "budget_range": "$5000-$10000",
            "required_expertise": ["blockchain_analysis", "forensics"],
            "specific_requirements": ["Experience with Bitcoin", "Court testimony experience"],
            "contact_info": {"email": "client@example.com", "phone": "+1234567890"}
        }
        
        service = await services_manager.create_service(service_data)
        
        assert isinstance(service, ProfessionalService)
        assert service.service_type == ServiceType.CONSULTATION
        assert service.title == "Blockchain Investigation Consultation"
        assert service.priority == "high"
        assert service.status == ServiceStatus.PENDING

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_service_invalid_data(self, services_manager):
        """Test service creation with invalid data"""
        invalid_data = {
            "service_type": "invalid_type",  # Invalid enum value
            "title": "",  # Empty required field
            "priority": "invalid_priority"  # Invalid priority
        }
        
        with pytest.raises(ValueError, match="Invalid service type"):
            await services_manager.create_service(invalid_data)

    # ---- Service Retrieval Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_service_success(self, services_manager, mock_db_pool):
        """Test successful service retrieval"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        service_id = str(uuid4())
        mock_row = {
            "id": service_id,
            "service_type": "investigation",
            "title": "Crypto Fraud Investigation",
            "description": "Comprehensive investigation of cryptocurrency fraud",
            "priority": "critical",
            "status": "in_progress",
            "client_id": "client_123",
            "assigned_professional": "professional_456",
            "requested_date": datetime.now(timezone.utc) - timedelta(days=5),
            "scheduled_date": datetime.now(timezone.utc) - timedelta(days=2),
            "estimated_duration": 40,
            "actual_duration": None,
            "cost": 15000.0,
            "deliverables": ["Investigation report", "Evidence analysis"],
            "notes": "Complex case requiring blockchain forensics",
            "created_date": datetime.now(timezone.utc) - timedelta(days=6),
            "last_updated": datetime.now(timezone.utc) - timedelta(days=1)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        service = await services_manager.get_service(service_id)
        
        assert service is not None
        assert service.id == service_id
        assert service.service_type == ServiceType.INVESTIGATION
        assert service.status == ServiceStatus.IN_PROGRESS
        assert service.assigned_professional == "professional_456"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_service_not_found(self, services_manager, mock_db_pool):
        """Test service retrieval when service doesn't exist"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        service = await services_manager.get_service("nonexistent_id")
        assert service is None

    # ---- Service Update Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_service_success(self, services_manager, mock_db_pool):
        """Test successful service update"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        service_id = str(uuid4())
        update_data = {
            "status": "completed",
            "actual_duration": 35,
            "cost": 14000.0,
            "notes": "Investigation completed successfully"
        }
        
        mock_row = {
            "id": service_id,
            "status": "completed",
            "actual_duration": 35,
            "cost": 14000.0,
            "notes": "Investigation completed successfully",
            "last_updated": datetime.now(timezone.utc)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        updated_service = await services_manager.update_service(service_id, update_data)
        
        assert updated_service.status == ServiceStatus.COMPLETED
        assert updated_service.actual_duration == 35
        assert updated_service.cost == 14000.0

    # ---- Professional Profile Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_professional_success(self, services_manager, mock_db_pool):
        """Test successful professional profile creation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": str(uuid4())}
        
        profile_data = {
            "name": "Dr. Jane Smith",
            "email": "jane.smith@example.com",
            "expertise_level": "expert",
            "specializations": ["blockchain_forensics", "cryptocurrency_analysis", "court_testimony"],
            "experience_years": 15,
            "certifications": ["CFE", "CCE", "CEH"],
            "education": [
                {"degree": "PhD", "field": "Computer Science", "institution": "MIT"},
                {"degree": "MS", "field": "Digital Forensics", "institution": "Stanford"}
            ],
            "languages": ["English", "Spanish"],
            "hourly_rate": 250.0,
            "availability": {
                "timezone": "UTC-5",
                "working_hours": "9:00-17:00",
                "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            },
            "bio": "Expert in blockchain forensics with 15 years of experience",
            "linkedin_profile": "https://linkedin.com/in/janesmith"
        }
        
        profile = await services_manager.create_professional(profile_data)
        
        assert isinstance(profile, ProfessionalProfile)
        assert profile.name == "Dr. Jane Smith"
        assert profile.email == "jane.smith@example.com"
        assert profile.expertise_level == ExpertiseLevel.EXPERT
        assert profile.experience_years == 15
        assert profile.hourly_rate == 250.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_professionals_with_filters(self, services_manager, mock_db_pool):
        """Test getting professionals with filters"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        filters = {
            "expertise_level": "expert",
            "specialization": "blockchain_forensics",
            "available": True
        }
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "name": "Dr. Jane Smith",
                "expertise_level": "expert",
                "specializations": ["blockchain_forensics", "cryptocurrency_analysis"],
                "experience_years": 15,
                "hourly_rate": 250.0,
                "availability": {"available": True}
            },
            {
                "id": str(uuid4()),
                "name": "John Doe",
                "expertise_level": "expert",
                "specializations": ["blockchain_forensics", "smart_contract_analysis"],
                "experience_years": 12,
                "hourly_rate": 200.0,
                "availability": {"available": True}
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        professionals = await services_manager.get_professionals(filters, 50)
        
        assert len(professionals) == 2
        for prof in professionals:
            assert prof.expertise_level == ExpertiseLevel.EXPERT
            assert "blockchain_forensics" in prof.specializations

    # ---- Training Program Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_training_program_success(self, services_manager, mock_db_pool):
        """Test successful training program creation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": str(uuid4())}
        
        program_data = {
            "title": "Advanced Blockchain Forensics",
            "description": "Comprehensive training on blockchain forensics techniques",
            "level": "advanced",
            "duration_hours": 40,
            "max_participants": 20,
            "price_per_participant": 2500.0,
            "topics": [
                "Bitcoin transaction analysis",
                "Ethereum smart contract forensics",
                "Chain analysis techniques",
                "Court presentation skills"
            ],
            "prerequisites": ["Basic blockchain knowledge", "Programming experience"],
            "learning_objectives": [
                "Master blockchain forensics tools",
                "Conduct comprehensive investigations",
                "Present findings in court"
            ],
            "instructor_id": "instructor_123",
            "schedule": {
                "start_date": datetime.now(timezone.utc) + timedelta(days=30),
                "end_date": datetime.now(timezone.utc) + timedelta(days=40),
                "session_times": "9:00-17:00"
            },
            "materials": ["Forensics toolkit", "Case studies", "Reference guides"],
            "certification_offered": True
        }
        
        program = await services_manager.create_training_program(program_data)
        
        assert isinstance(program, TrainingProgram)
        assert program.title == "Advanced Blockchain Forensics"
        assert program.level == "advanced"
        assert program.duration_hours == 40
        assert program.max_participants == 20
        assert program.price_per_participant == 2500.0
        assert program.certification_offered is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_training_programs_with_filters(self, services_manager, mock_db_pool):
        """Test getting training programs with filters"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        filters = {
            "level": "advanced",
            "status": "active"
        }
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "title": "Advanced Blockchain Forensics",
                "level": "advanced",
                "status": "active",
                "current_enrollments": 15,
                "max_participants": 20,
                "price_per_participant": 2500.0
            },
            {
                "id": str(uuid4()),
                "title": "Expert Cryptocurrency Analysis",
                "level": "advanced",
                "status": "active",
                "current_enrollments": 8,
                "max_participants": 15,
                "price_per_participant": 3000.0
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        programs = await services_manager.get_training_programs(filters)
        
        assert len(programs) == 2
        for program in programs:
            assert program.level == "advanced"
            assert program.status == "active"

    # ---- Training Enrollment Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enroll_in_training_success(self, services_manager, mock_db_pool):
        """Test successful training enrollment"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Mock training program with space
        program_row = {
            "id": str(uuid4()),
            "current_enrollments": 10,
            "max_participants": 20
        }
        mock_conn.fetchrow.return_value = program_row
        
        enrollment_data = {
            "training_program_id": str(uuid4()),
            "participant_name": "Alice Johnson",
            "participant_email": "alice@example.com",
            "participant_company": "Crypto Analytics Inc",
            "participant_role": "Security Analyst",
            "experience_level": "intermediate",
            "special_requirements": "Focus on Bitcoin forensics",
            "billing_info": {"method": "credit_card", "address": "123 Main St"}
        }
        
        enrollment_id = await services_manager.enroll_in_training(enrollment_data)
        
        assert enrollment_id is not None
        assert isinstance(enrollment_id, str)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enroll_in_training_full(self, services_manager, mock_db_pool):
        """Test training enrollment when program is full"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Mock full training program
        program_row = {
            "id": str(uuid4()),
            "current_enrollments": 20,
            "max_participants": 20
        }
        mock_conn.fetchrow.return_value = program_row
        
        enrollment_data = {
            "training_program_id": str(uuid4()),
            "participant_name": "Alice Johnson",
            "participant_email": "alice@example.com"
        }
        
        with pytest.raises(Exception, match="Training program is full"):
            await services_manager.enroll_in_training(enrollment_data)

    # ---- Statistics Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_statistics(self, services_manager, mock_db_pool):
        """Test statistics calculation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        days = 30
        
        # Mock statistics query results
        mock_stats = {
            "total_services": 150,
            "services_by_type": {
                ServiceType.CONSULTATION.value: 40,
                ServiceType.TRAINING.value: 35,
                ServiceType.INVESTIGATION.value: 30,
                ServiceType.EXPERT_REVIEW.value: 25,
                ServiceType.COMPLIANCE_AUDIT.value: 15,
                ServiceType.CUSTOM_INTEGRATION.value: 5
            },
            "services_by_status": {
                ServiceStatus.PENDING.value: 30,
                ServiceStatus.SCHEDULED.value: 40,
                ServiceStatus.IN_PROGRESS.value: 50,
                ServiceStatus.COMPLETED.value: 25,
                ServiceStatus.CANCELLED.value: 5
            },
            "services_by_priority": {
                "low": 20,
                "medium": 60,
                "high": 50,
                "urgent": 20
            },
            "average_completion_time_hours": 25.5,
            "total_revenue": 750000.0,
            "client_satisfaction_score": 4.7,
            "professional_utilization": {
                "expert": 0.85,
                "senior": 0.75,
                "intermediate": 0.60,
                "junior": 0.40
            }
        }
        mock_conn.fetchrow.return_value = mock_stats
        
        stats = await services_manager.get_statistics(days)
        
        assert isinstance(stats, ServiceStatistics)
        assert stats.total_services == 150
        assert stats.average_completion_time_hours == 25.5
        assert stats.total_revenue == 750000.0
        assert stats.client_satisfaction_score == 4.7

    # ---- Service Assignment Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_assign_professional_to_service(self, services_manager, mock_db_pool):
        """Test assigning a professional to a service"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        service_id = str(uuid4())
        professional_id = str(uuid4())
        
        # Mock service and professional existence
        mock_conn.fetchrow.side_effect = [
            {"id": service_id, "status": "pending"},  # Service exists
            {"id": professional_id, "name": "Dr. Jane Smith"}  # Professional exists
        ]
        
        update_data = {
            "assigned_professional": professional_id,
            "status": "scheduled",
            "last_updated": datetime.now(timezone.utc)
        }
        
        mock_conn.fetchrow.return_value = {
            "id": service_id,
            "assigned_professional": professional_id,
            "status": "scheduled",
            "last_updated": datetime.now(timezone.utc)
        }
        
        updated_service = await services_manager.update_service(service_id, update_data)
        
        assert updated_service.assigned_professional == professional_id
        assert updated_service.status == ServiceStatus.SCHEDULED

    # ---- Error Handling Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_connection_error(self, services_manager, mock_db_pool):
        """Test handling of database connection errors"""
        mock_pool.acquire.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await services_manager.create_service({
                "service_type": "consultation",
                "title": "Test Service",
                "description": "Test description"
            })

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_service_type_validation(self, services_manager):
        """Test validation of invalid service types"""
        invalid_service_data = {
            "service_type": "nonexistent_type",  # Invalid enum value
            "title": "Test Service",
            "description": "Test description"
        }
        
        with pytest.raises(ValueError, match="Invalid service type"):
            await services_manager.create_service(invalid_service_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_expertise_level_validation(self, services_manager):
        """Test validation of invalid expertise levels"""
        invalid_profile_data = {
            "name": "Test Professional",
            "email": "test@example.com",
            "expertise_level": "invalid_level",  # Invalid enum value
            "specializations": ["test"],
            "experience_years": 5
        }
        
        with pytest.raises(ValueError, match="Invalid expertise level"):
            await services_manager.create_professional(invalid_profile_data)


class TestProfessionalServiceModel:
    """Test suite for ProfessionalService data model"""

    @pytest.mark.unit
    def test_professional_service_creation(self):
        """Test ProfessionalService model creation"""
        service_data = {
            "id": str(uuid4()),
            "service_type": "investigation",
            "title": "Cryptocurrency Fraud Investigation",
            "description": "Comprehensive investigation of cryptocurrency fraud",
            "priority": "critical",
            "status": "in_progress",
            "client_id": "client_123",
            "assigned_professional": "professional_456",
            "requested_date": datetime.now(timezone.utc) - timedelta(days=5),
            "scheduled_date": datetime.now(timezone.utc) - timedelta(days=2),
            "completion_date": None,
            "estimated_duration": 40,
            "actual_duration": None,
            "cost": 15000.0,
            "deliverables": ["Investigation report", "Evidence analysis", "Court testimony preparation"],
            "notes": "Complex case requiring blockchain forensics",
            "created_date": datetime.now(timezone.utc) - timedelta(days=6),
            "last_updated": datetime.now(timezone.utc) - timedelta(days=1)
        }
        
        service = ProfessionalService(**service_data)
        
        assert service.id == service_data["id"]
        assert service.service_type == ServiceType.INVESTIGATION
        assert service.title == "Cryptocurrency Fraud Investigation"
        assert service.priority == "critical"
        assert service.status == ServiceStatus.IN_PROGRESS
        assert service.assigned_professional == "professional_456"
        assert service.estimated_duration == 40
        assert service.cost == 15000.0
        assert len(service.deliverables) == 3

    @pytest.mark.unit
    def test_professional_service_optional_fields(self):
        """Test ProfessionalService with optional fields"""
        service_data = {
            "id": str(uuid4()),
            "service_type": "consultation",
            "title": "Basic Consultation",
            "description": "Simple consultation service",
            "priority": "medium",
            "status": "pending",
            "client_id": "client_789",
            "estimated_duration": 2,
            "deliverables": [],
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        service = ProfessionalService(**service_data)
        
        assert service.assigned_professional is None
        assert service.scheduled_date is None
        assert service.completion_date is None
        assert service.actual_duration is None
        assert service.cost is None
        assert service.notes is None


class TestProfessionalProfileModel:
    """Test suite for ProfessionalProfile data model"""

    @pytest.mark.unit
    def test_professional_profile_creation(self):
        """Test ProfessionalProfile model creation"""
        profile_data = {
            "id": str(uuid4()),
            "name": "Dr. Jane Smith",
            "email": "jane.smith@example.com",
            "expertise_level": "expert",
            "specializations": ["blockchain_forensics", "cryptocurrency_analysis", "court_testimony"],
            "experience_years": 15,
            "certifications": ["CFE", "CCE", "CEH"],
            "education": [
                {"degree": "PhD", "field": "Computer Science", "institution": "MIT"},
                {"degree": "MS", "field": "Digital Forensics", "institution": "Stanford"}
            ],
            "languages": ["English", "Spanish"],
            "hourly_rate": 250.0,
            "availability": {
                "timezone": "UTC-5",
                "working_hours": "9:00-17:00",
                "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            },
            "bio": "Expert in blockchain forensics with 15 years of experience",
            "linkedin_profile": "https://linkedin.com/in/janesmith",
            "certifications_verified": True,
            "rating": 4.8,
            "completed_services": 125,
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        profile = ProfessionalProfile(**profile_data)
        
        assert profile.id == profile_data["id"]
        assert profile.name == "Dr. Jane Smith"
        assert profile.expertise_level == ExpertiseLevel.EXPERT
        assert profile.experience_years == 15
        assert profile.hourly_rate == 250.0
        assert profile.certifications_verified is True
        assert profile.rating == 4.8
        assert profile.completed_services == 125
        assert len(profile.specializations) == 3
        assert len(profile.certifications) == 3

    @pytest.mark.unit
    def test_professional_profile_optional_fields(self):
        """Test ProfessionalProfile with optional fields"""
        profile_data = {
            "id": str(uuid4()),
            "name": "John Doe",
            "email": "john@example.com",
            "expertise_level": "senior",
            "specializations": ["blockchain_analysis"],
            "experience_years": 8,
            "certifications": [],
            "education": [],
            "languages": ["English"],
            "availability": {"timezone": "UTC-5"},
            "certifications_verified": False,
            "rating": None,
            "completed_services": 0,
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        profile = ProfessionalProfile(**profile_data)
        
        assert profile.hourly_rate is None
        assert profile.bio is None
        assert profile.linkedin_profile is None
        assert profile.rating is None
        assert profile.completed_services == 0


class TestTrainingProgramModel:
    """Test suite for TrainingProgram data model"""

    @pytest.mark.unit
    def test_training_program_creation(self):
        """Test TrainingProgram model creation"""
        program_data = {
            "id": str(uuid4()),
            "title": "Advanced Blockchain Forensics",
            "description": "Comprehensive training on blockchain forensics techniques",
            "level": "advanced",
            "duration_hours": 40,
            "max_participants": 20,
            "current_enrollments": 15,
            "price_per_participant": 2500.0,
            "topics": [
                "Bitcoin transaction analysis",
                "Ethereum smart contract forensics",
                "Chain analysis techniques",
                "Court presentation skills"
            ],
            "prerequisites": ["Basic blockchain knowledge", "Programming experience"],
            "learning_objectives": [
                "Master blockchain forensics tools",
                "Conduct comprehensive investigations",
                "Present findings in court"
            ],
            "instructor_id": "instructor_123",
            "instructor_name": "Dr. Jane Smith",
            "schedule": {
                "start_date": datetime.now(timezone.utc) + timedelta(days=30),
                "end_date": datetime.now(timezone.utc) + timedelta(days=40),
                "session_times": "9:00-17:00"
            },
            "materials": ["Forensics toolkit", "Case studies", "Reference guides"],
            "certification_offered": True,
            "status": "active",
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        program = TrainingProgram(**program_data)
        
        assert program.id == program_data["id"]
        assert program.title == "Advanced Blockchain Forensics"
        assert program.level == "advanced"
        assert program.duration_hours == 40
        assert program.max_participants == 20
        assert program.current_enrollments == 15
        assert program.price_per_participant == 2500.0
        assert program.certification_offered is True
        assert program.status == "active"
        assert len(program.topics) == 4
        assert len(program.learning_objectives) == 3
