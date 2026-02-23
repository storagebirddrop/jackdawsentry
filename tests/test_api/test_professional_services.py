"""
Jackdaw Sentry - Professional Services API Tests
Tests for professional services framework API endpoints
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import json
from fastapi.testclient import TestClient
from fastapi import status

from src.api.main import app
from src.intelligence.professional_services import (
    ProfessionalService,
    ProfessionalProfile,
    TrainingProgram,
    ServiceType,
    ServiceStatus,
    TrainingStatus
)


class TestProfessionalServicesAPI:
    """Test suite for Professional Services API endpoints"""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_services_manager(self):
        """Mock ProfessionalServicesManager"""
        return AsyncMock()

    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers"""
        return {"Authorization": "Bearer test_token"}

    # ---- Service Management Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_service_success(self, client, mock_services_manager, auth_headers):
        """Test successful service creation"""
        service_data = {
            "name": "Blockchain Forensics Service",
            "description": "Professional blockchain forensics and investigation services",
            "service_type": "forensics",
            "provider": "CryptoForensics Inc",
            "contact_email": "contact@cryptoforensics.com",
            "contact_phone": "+1-555-0123",
            "pricing_model": "hourly",
            "hourly_rate": 250.00,
            "currency": "USD",
            "specializations": ["bitcoin", "ethereum", "privacy_coins"],
            "certifications": ["CFE", "CEH"],
            "jurisdictions": ["US", "EU", "UK"],
            "response_time_hours": 24,
            "available": True
        }
        
        mock_service = ProfessionalService(
            id=str(uuid4()),
            name=service_data["name"],
            description=service_data["description"],
            service_type=ServiceType.FORENSICS,
            provider=service_data["provider"],
            contact_email=service_data["contact_email"],
            contact_phone=service_data["contact_phone"],
            pricing_model=service_data["pricing_model"],
            hourly_rate=service_data["hourly_rate"],
            currency=service_data["currency"],
            specializations=service_data["specializations"],
            certifications=service_data["certifications"],
            jurisdictions=service_data["jurisdictions"],
            response_time_hours=service_data["response_time_hours"],
            available=service_data["available"],
            status=ServiceStatus.ACTIVE,
            created_date=datetime.now(timezone.utc),
            updated_date=datetime.now(timezone.utc)
        )
        mock_services_manager.create_service.return_value = mock_service
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.post("/api/v1/intelligence/professional-services/services", json=service_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == service_data["name"]
        assert data["service_type"] == "forensics"
        assert data["status"] == "active"
        assert data["hourly_rate"] == 250.00

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_service_invalid_data(self, client, mock_services_manager, auth_headers):
        """Test service creation with invalid data"""
        invalid_data = {
            "name": "",  # Empty required field
            "service_type": "invalid_type",  # Invalid enum
            "hourly_rate": -50.00,  # Negative rate
            "contact_email": "invalid_email"  # Invalid email
        }
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.post("/api/v1/intelligence/professional-services/services", json=invalid_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_service_success(self, client, mock_services_manager, auth_headers):
        """Test successful service retrieval"""
        service_id = str(uuid4())
        
        mock_service = ProfessionalService(
            id=service_id,
            name="Legal Consultation Service",
            description="Expert legal consultation for cryptocurrency cases",
            service_type=ServiceType.LEGAL,
            provider="LawTech Legal",
            contact_email="legal@lawtech.com",
            status=ServiceStatus.ACTIVE,
            created_date=datetime.now(timezone.utc)
        )
        mock_services_manager.get_service.return_value = mock_service
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get(f"/api/v1/intelligence/professional-services/services/{service_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == service_id
        assert data["name"] == "Legal Consultation Service"
        assert data["service_type"] == "legal"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_service_not_found(self, client, mock_services_manager, auth_headers):
        """Test service retrieval when service doesn't exist"""
        service_id = str(uuid4())
        mock_services_manager.get_service.return_value = None
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get(f"/api/v1/intelligence/professional-services/services/{service_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_services_success(self, client, mock_services_manager, auth_headers):
        """Test successful services listing"""
        mock_services = [
            ProfessionalService(
                id=str(uuid4()),
                name="Forensics Service",
                service_type=ServiceType.FORENSICS,
                provider="Forensics Inc",
                status=ServiceStatus.ACTIVE,
                created_date=datetime.now(timezone.utc)
            ),
            ProfessionalService(
                id=str(uuid4()),
                name="Legal Service",
                service_type=ServiceType.LEGAL,
                provider="Legal Corp",
                status=ServiceStatus.ACTIVE,
                created_date=datetime.now(timezone.utc)
            )
        ]
        mock_services_manager.list_services.return_value = mock_services
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get("/api/v1/intelligence/professional-services/services", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Forensics Service"
        assert data[1]["name"] == "Legal Service"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_services_with_filters(self, client, mock_services_manager, auth_headers):
        """Test services listing with filters"""
        filters = {
            "service_type": "forensics",
            "status": "active",
            "available": True,
            "jurisdiction": "US"
        }
        
        mock_services = [
            ProfessionalService(
                id=str(uuid4()),
                name="US Forensics Service",
                service_type=ServiceType.FORENSICS,
                status=ServiceStatus.ACTIVE,
                available=True,
                jurisdictions=["US", "CA"],
                created_date=datetime.now(timezone.utc)
            )
        ]
        mock_services_manager.list_services.return_value = mock_services
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get("/api/v1/intelligence/professional-services/services", params=filters, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["service_type"] == "forensics"
        assert "US" in data[0]["jurisdictions"]

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_update_service_success(self, client, mock_services_manager, auth_headers):
        """Test successful service update"""
        service_id = str(uuid4())
        update_data = {
            "name": "Updated Service Name",
            "description": "Updated description",
            "hourly_rate": 300.00,
            "available": False,
            "response_time_hours": 48
        }
        
        mock_service = ProfessionalService(
            id=service_id,
            name=update_data["name"],
            description=update_data["description"],
            hourly_rate=update_data["hourly_rate"],
            available=update_data["available"],
            response_time_hours=update_data["response_time_hours"],
            status=ServiceStatus.INACTIVE,
            updated_date=datetime.now(timezone.utc)
        )
        mock_services_manager.update_service.return_value = mock_service
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.put(f"/api/v1/intelligence/professional-services/services/{service_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Service Name"
        assert data["hourly_rate"] == 300.00
        assert data["available"] is False

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_delete_service_success(self, client, mock_services_manager, auth_headers):
        """Test successful service deletion"""
        service_id = str(uuid4())
        mock_services_manager.delete_service.return_value = True
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.delete(f"/api/v1/intelligence/professional-services/services/{service_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    # ---- Professional Profile Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_profile_success(self, client, mock_services_manager, auth_headers):
        """Test successful professional profile creation"""
        profile_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1-555-0123",
            "title": "Senior Blockchain Forensics Expert",
            "company": "CryptoForensics Inc",
            "specializations": ["bitcoin", "ethereum", "privacy_coins"],
            "certifications": ["CFE", "CEH", "CAM"],
            "years_experience": 8,
            "education": ["MS Computer Science", "BS Digital Forensics"],
            "languages": ["English", "Spanish"],
            "jurisdictions": ["US", "EU"],
            "hourly_rate": 350.00,
            "currency": "USD",
            "available_for_hire": True,
            "bio": "Expert in blockchain forensics with 8+ years experience"
        }
        
        mock_profile = ProfessionalProfile(
            id=str(uuid4()),
            name=profile_data["name"],
            email=profile_data["email"],
            phone=profile_data["phone"],
            title=profile_data["title"],
            company=profile_data["company"],
            specializations=profile_data["specializations"],
            certifications=profile_data["certifications"],
            years_experience=profile_data["years_experience"],
            education=profile_data["education"],
            languages=profile_data["languages"],
            jurisdictions=profile_data["jurisdictions"],
            hourly_rate=profile_data["hourly_rate"],
            currency=profile_data["currency"],
            available_for_hire=profile_data["available_for_hire"],
            bio=profile_data["bio"],
            created_date=datetime.now(timezone.utc),
            updated_date=datetime.now(timezone.utc)
        )
        mock_services_manager.create_profile.return_value = mock_profile
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.post("/api/v1/intelligence/professional-services/profiles", json=profile_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == profile_data["name"]
        assert data["title"] == profile_data["title"]
        assert data["years_experience"] == 8
        assert data["hourly_rate"] == 350.00

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_profile_success(self, client, mock_services_manager, auth_headers):
        """Test successful profile retrieval"""
        profile_id = str(uuid4())
        
        mock_profile = ProfessionalProfile(
            id=profile_id,
            name="Jane Smith",
            email="jane.smith@example.com",
            title="Cryptocurrency Legal Expert",
            company="LawTech Legal",
            specializations=["cryptocurrency_law", "compliance"],
            certifications=["JD", "LLM"],
            years_experience=12,
            created_date=datetime.now(timezone.utc)
        )
        mock_services_manager.get_profile.return_value = mock_profile
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get(f"/api/v1/intelligence/professional-services/profiles/{profile_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == profile_id
        assert data["name"] == "Jane Smith"
        assert data["title"] == "Cryptocurrency Legal Expert"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_search_profiles_success(self, client, mock_services_manager, auth_headers):
        """Test successful profile search"""
        search_params = {
            "specialization": "bitcoin",
            "jurisdiction": "US",
            "min_experience": 5,
            "available_for_hire": True,
            "limit": 20
        }
        
        mock_profiles = [
            ProfessionalProfile(
                id=str(uuid4()),
                name="Bitcoin Expert 1",
                specializations=["bitcoin", "ethereum"],
                jurisdictions=["US", "CA"],
                years_experience=8,
                available_for_hire=True,
                created_date=datetime.now(timezone.utc)
            ),
            ProfessionalProfile(
                id=str(uuid4()),
                name="Bitcoin Expert 2",
                specializations=["bitcoin", "privacy_coins"],
                jurisdictions=["US", "EU"],
                years_experience=10,
                available_for_hire=True,
                created_date=datetime.now(timezone.utc)
            )
        ]
        mock_services_manager.search_profiles.return_value = mock_profiles
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get("/api/v1/intelligence/professional-services/profiles/search", params=search_params, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        for profile in data:
            assert "bitcoin" in profile["specializations"]
            assert "US" in profile["jurisdictions"]
            assert profile["available_for_hire"] is True

    # ---- Training Program Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_training_program_success(self, client, mock_services_manager, auth_headers):
        """Test successful training program creation"""
        program_data = {
            "title": "Advanced Blockchain Forensics Certification",
            "description": "Comprehensive training in blockchain forensics techniques",
            "provider": "CryptoForensics Academy",
            "duration_hours": 40,
            "difficulty_level": "advanced",
            "prerequisites": ["Basic blockchain knowledge", "Digital forensics experience"],
            "topics": ["Bitcoin analysis", "Ethereum tracing", "Privacy coins investigation"],
            "certification_offered": True,
            "price": 2500.00,
            "currency": "USD",
            "format": "online",
            "language": "English",
            "max_participants": 30,
            "start_date": "2024-02-01T09:00:00Z",
            "end_date": "2024-02-29T17:00:00Z"
        }
        
        mock_program = TrainingProgram(
            id=str(uuid4()),
            title=program_data["title"],
            description=program_data["description"],
            provider=program_data["provider"],
            duration_hours=program_data["duration_hours"],
            difficulty_level=program_data["difficulty_level"],
            prerequisites=program_data["prerequisites"],
            topics=program_data["topics"],
            certification_offered=program_data["certification_offered"],
            price=program_data["price"],
            currency=program_data["currency"],
            format=program_data["format"],
            language=program_data["language"],
            max_participants=program_data["max_participants"],
            start_date=datetime.fromisoformat("2024-02-01T09:00:00+00:00"),
            end_date=datetime.fromisoformat("2024-02-29T17:00:00+00:00"),
            status=TrainingStatus.SCHEDULED,
            created_date=datetime.now(timezone.utc)
        )
        mock_services_manager.create_training_program.return_value = mock_program
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.post("/api/v1/intelligence/professional-services/training", json=program_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == program_data["title"]
        assert data["difficulty_level"] == "advanced"
        assert data["price"] == 2500.00
        assert data["certification_offered"] is True

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_enroll_in_training_success(self, client, mock_services_manager, auth_headers):
        """Test successful training enrollment"""
        program_id = str(uuid4())
        enrollment_data = {
            "participant_name": "John Doe",
            "participant_email": "john.doe@example.com",
            "participant_phone": "+1-555-0123",
            "company": "CryptoForensics Inc",
            "experience_level": "intermediate",
            "special_interests": ["bitcoin", "ethereum"],
            "payment_method": "credit_card"
        }
        
        enrollment_result = {
            "success": True,
            "enrollment_id": str(uuid4()),
            "program_id": program_id,
            "status": "enrolled",
            "payment_status": "paid",
            "enrollment_date": datetime.now(timezone.utc)
        }
        mock_services_manager.enroll_in_training.return_value = enrollment_result
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.post(
                f"/api/v1/intelligence/professional-services/training/{program_id}/enroll",
                json=enrollment_data,
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "enrolled"
        assert data["payment_status"] == "paid"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_training_programs_success(self, client, mock_services_manager, auth_headers):
        """Test successful training programs listing"""
        mock_programs = [
            TrainingProgram(
                id=str(uuid4()),
                title="Basic Blockchain Analysis",
                provider="Crypto Academy",
                difficulty_level="beginner",
                status=TrainingStatus.ENROLLING,
                start_date=datetime.now(timezone.utc) + timedelta(days=30),
                created_date=datetime.now(timezone.utc)
            ),
            TrainingProgram(
                id=str(uuid4()),
                title="Advanced Cryptocurrency Law",
                provider="LegalTech Institute",
                difficulty_level="advanced",
                status=TrainingStatus.SCHEDULED,
                start_date=datetime.now(timezone.utc) + timedelta(days=60),
                created_date=datetime.now(timezone.utc)
            )
        ]
        mock_services_manager.list_training_programs.return_value = mock_programs
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get("/api/v1/intelligence/professional-services/training", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Basic Blockchain Analysis"
        assert data[1]["title"] == "Advanced Cryptocurrency Law"

    # ---- Service Assignment Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_assign_service_success(self, client, mock_services_manager, auth_headers):
        """Test successful service assignment"""
        assignment_data = {
            "service_id": str(uuid4()),
            "case_id": str(uuid4()),
            "client_name": "ABC Corporation",
            "client_email": "contact@abc.com",
            "urgency_level": "high",
            "description": "Need blockchain forensics for stolen cryptocurrency investigation",
            "budget_range": "10000-20000",
            "timeline": "2-3 weeks",
            "required_skills": ["bitcoin_analysis", "transaction_tracing"],
            "jurisdiction": "US"
        }
        
        assignment_result = {
            "success": True,
            "assignment_id": str(uuid4()),
            "matched_professionals": [
                {
                    "profile_id": str(uuid4()),
                    "name": "Expert Forensics Specialist",
                    "match_score": 0.95,
                    "availability": "immediate"
                }
            ],
            "assignment_date": datetime.now(timezone.utc)
        }
        mock_services_manager.assign_service.return_value = assignment_result
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.post(
                "/api/v1/intelligence/professional-services/assign",
                json=assignment_data,
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert len(data["matched_professionals"]) == 1
        assert data["matched_professionals"][0]["match_score"] == 0.95

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_assignments_success(self, client, mock_services_manager, auth_headers):
        """Test successful assignments retrieval"""
        mock_assignments = [
            {
                "id": str(uuid4()),
                "service_name": "Blockchain Forensics",
                "client_name": "Client A",
                "status": "assigned",
                "assigned_professional": "Expert 1",
                "created_date": datetime.now(timezone.utc) - timedelta(days=1)
            },
            {
                "id": str(uuid4()),
                "service_name": "Legal Consultation",
                "client_name": "Client B",
                "status": "in_progress",
                "assigned_professional": "Expert 2",
                "created_date": datetime.now(timezone.utc) - timedelta(days=3)
            }
        ]
        mock_services_manager.get_assignments.return_value = mock_assignments
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get("/api/v1/intelligence/professional-services/assignments", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["status"] == "assigned"
        assert data[1]["status"] == "in_progress"

    # ---- Statistics and Analytics Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_service_statistics_success(self, client, mock_services_manager, auth_headers):
        """Test successful service statistics retrieval"""
        stats = {
            "total_services": 45,
            "active_services": 38,
            "inactive_services": 7,
            "services_by_type": {
                "forensics": 15,
                "legal": 12,
                "consulting": 10,
                "training": 8
            },
            "services_by_jurisdiction": {
                "US": 25,
                "EU": 18,
                "UK": 12,
                "Global": 8
            },
            "average_hourly_rate": 275.50,
            "rate_range": {"min": 150.00, "max": 500.00},
            "total_profiles": 120,
            "available_profiles": 85,
            "average_response_time_hours": 18.5
        }
        mock_services_manager.get_service_statistics.return_value = stats
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get("/api/v1/intelligence/professional-services/statistics", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_services"] == 45
        assert data["active_services"] == 38
        assert data["services_by_type"]["forensics"] == 15
        assert data["average_hourly_rate"] == 275.50

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_training_statistics_success(self, client, mock_services_manager, auth_headers):
        """Test successful training statistics retrieval"""
        stats = {
            "total_programs": 25,
            "active_programs": 18,
            "completed_programs": 120,
            "total_enrollments": 850,
            "active_enrollments": 45,
            "completion_rate": 0.85,
            "programs_by_difficulty": {
                "beginner": 8,
                "intermediate": 10,
                "advanced": 7
            },
            "average_program_price": 1850.00,
            "total_revenue": 1572500.00,
            "top_providers": [
                {"name": "CryptoForensics Academy", "programs": 8},
                {"name": "LegalTech Institute", "programs": 6}
            ]
        }
        mock_services_manager.get_training_statistics.return_value = stats
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get("/api/v1/intelligence/professional-services/training/statistics", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_programs"] == 25
        assert data["completion_rate"] == 0.85
        assert data["average_program_price"] == 1850.00

    # ---- Authentication and Authorization Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client, mock_services_manager):
        """Test API access without authentication"""
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get("/api/v1/intelligence/professional-services/services")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_invalid_token(self, client, mock_services_manager):
        """Test API access with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get("/api/v1/intelligence/professional-services/services", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ---- Error Handling Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_database_connection_error(self, client, mock_services_manager, auth_headers):
        """Test handling of database connection errors"""
        mock_services_manager.list_services.side_effect = Exception("Database connection failed")
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get("/api/v1/intelligence/professional-services/services", headers=auth_headers)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_service_not_found_error(self, client, mock_services_manager, auth_headers):
        """Test handling of service not found errors"""
        service_id = str(uuid4())
        mock_services_manager.get_service.return_value = None
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.get(f"/api/v1/intelligence/professional-services/services/{service_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_enrollment_capacity_error(self, client, mock_services_manager, auth_headers):
        """Test handling of enrollment capacity errors"""
        program_id = str(uuid4())
        mock_services_manager.enroll_in_training.side_effect = ValueError("Program is at full capacity")
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            response = client.post(
                f"/api/v1/intelligence/professional-services/training/{program_id}/enroll",
                json={"participant_name": "John Doe"},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Program is at full capacity" in data["detail"]

    # ---- Data Validation Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_email_validation(self, client, mock_services_manager, auth_headers):
        """Test email validation in service and profile creation"""
        invalid_emails = [
            "invalid_email",
            "@domain.com",
            "user@",
            "user..name@domain.com",
            "user@domain..com"
        ]
        
        for email in invalid_emails:
            service_data = {
                "name": "Test Service",
                "service_type": "forensics",
                "provider": "Test Provider",
                "contact_email": email
            }
            
            with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
                response = client.post("/api/v1/intelligence/professional-services/services", json=service_data, headers=auth_headers)
            
            # Should fail validation
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_price_validation(self, client, mock_services_manager, auth_headers):
        """Test price validation in services and training"""
        invalid_prices = [-100.00, 0.00, 999999.99]  # Negative, zero, too high
        
        for price in invalid_prices:
            service_data = {
                "name": "Test Service",
                "service_type": "forensics",
                "provider": "Test Provider",
                "contact_email": "test@example.com",
                "hourly_rate": price
            }
            
            with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
                response = client.post("/api/v1/intelligence/professional-services/services", json=service_data, headers=auth_headers)
            
            # Should fail validation
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ---- Integration Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_complete_service_workflow(self, client, mock_services_manager, auth_headers):
        """Test complete professional services workflow"""
        # 1. Create service
        service_data = {
            "name": "Complete Workflow Service",
            "service_type": "forensics",
            "provider": "Test Provider",
            "contact_email": "test@example.com",
            "hourly_rate": 250.00,
            "available": True
        }
        
        mock_service = ProfessionalService(
            id=str(uuid4()),
            **service_data,
            status=ServiceStatus.ACTIVE,
            created_date=datetime.now(timezone.utc)
        )
        mock_services_manager.create_service.return_value = mock_service
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            create_response = client.post("/api/v1/intelligence/professional-services/services", json=service_data, headers=auth_headers)
        
        assert create_response.status_code == status.HTTP_201_CREATED
        service_id = create_response.json()["id"]
        
        # 2. Create professional profile
        profile_data = {
            "name": "Test Professional",
            "email": "professional@example.com",
            "title": "Forensics Expert",
            "specializations": ["bitcoin", "ethereum"],
            "years_experience": 5,
            "hourly_rate": 300.00,
            "available_for_hire": True
        }
        
        mock_profile = ProfessionalProfile(
            id=str(uuid4()),
            **profile_data,
            created_date=datetime.now(timezone.utc)
        )
        mock_services_manager.create_profile.return_value = mock_profile
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            profile_response = client.post("/api/v1/intelligence/professional-services/profiles", json=profile_data, headers=auth_headers)
        
        assert profile_response.status_code == status.HTTP_201_CREATED
        profile_id = profile_response.json()["id"]
        
        # 3. Assign service to client
        assignment_data = {
            "service_id": service_id,
            "case_id": str(uuid4()),
            "client_name": "Test Client",
            "client_email": "client@example.com",
            "urgency_level": "medium",
            "description": "Test case assignment"
        }
        
        assignment_result = {
            "success": True,
            "assignment_id": str(uuid4()),
            "matched_professionals": [
                {
                    "profile_id": profile_id,
                    "name": "Test Professional",
                    "match_score": 0.90
                }
            ]
        }
        mock_services_manager.assign_service.return_value = assignment_result
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            assignment_response = client.post("/api/v1/intelligence/professional-services/assign", json=assignment_data, headers=auth_headers)
        
        assert assignment_response.status_code == status.HTTP_201_CREATED
        assignment_data = assignment_response.json()
        assert assignment_data["success"] is True
        assert len(assignment_data["matched_professionals"]) == 1
        
        # 4. Get statistics
        stats = {
            "total_services": 1,
            "active_services": 1,
            "total_profiles": 1,
            "available_profiles": 1,
            "total_assignments": 1
        }
        mock_services_manager.get_service_statistics.return_value = stats
        
        with patch("src.api.routers.professional_services.get_professional_services_manager", return_value=mock_services_manager):
            stats_response = client.get("/api/v1/intelligence/professional-services/statistics", headers=auth_headers)
        
        assert stats_response.status_code == status.HTTP_200_OK
        stats_data = stats_response.json()
        assert stats_data["total_services"] == 1
        assert stats_data["total_assignments"] == 1
