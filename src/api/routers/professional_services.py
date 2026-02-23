"""
Jackdaw Sentry - Professional Services API Router
REST endpoints for expert support, training, and professional services management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, field_validator
import logging
import uuid
import json as _json

from src.api.auth import User, check_permissions, PERMISSIONS
from src.api.database import get_postgres_connection
from src.api.exceptions import JackdawException
from src.intelligence.professional_services import get_professional_services_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed filter values
VALID_SERVICE_TYPES = {"consultation", "training", "investigation", "expert_review", "compliance_audit", "custom_integration", "technical_support", "legal_support"}
VALID_SERVICE_STATUSES = {"pending", "scheduled", "in_progress", "completed", "cancelled", "on_hold"}
VALID_EXPERTISE_LEVELS = {"junior", "intermediate", "senior", "expert", "master"}
VALID_TRAINING_LEVELS = {"beginner", "intermediate", "advanced", "expert"}

# Pydantic models
class ProfessionalServiceRequest(BaseModel):
    service_type: str
    title: str
    description: str
    priority: str = "medium"  # low, medium, high, urgent
    requested_date: Optional[datetime] = None
    duration_hours: Optional[int] = None
    budget_range: Optional[str] = None
    required_expertise: List[str] = []
    specific_requirements: List[str] = []
    contact_info: Dict[str, str]
    
    @field_validator('service_type')
    @classmethod
    def validate_service_type(cls, v):
        if v not in VALID_SERVICE_TYPES:
            raise ValueError(f'Invalid service type: {v}')
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        valid_priorities = {"low", "medium", "high", "urgent"}
        if v not in valid_priorities:
            raise ValueError(f'Invalid priority: {v}')
        return v

class ProfessionalServiceUpdate(BaseModel):
    service_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_professional: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    cost: Optional[float] = None
    notes: Optional[str] = None
    deliverables: List[str] = []
    
    @field_validator('service_type')
    @classmethod
    def validate_service_type(cls, v):
        if v is not None and v not in VALID_SERVICE_TYPES:
            raise ValueError(f'Invalid service type: {v}')
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v is not None:
            valid_priorities = {"low", "medium", "high", "urgent"}
            if v not in valid_priorities:
                raise ValueError(f'Invalid priority: {v}')
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in VALID_SERVICE_STATUSES:
            raise ValueError(f'Invalid status: {v}')
        return v

class ProfessionalProfile(BaseModel):
    name: str
    email: str
    expertise_level: str
    specializations: List[str]
    experience_years: int
    certifications: List[str]
    education: List[Dict[str, str]]
    languages: List[str]
    hourly_rate: Optional[float] = None
    availability: Dict[str, Any]  # Schedule, timezone, etc.
    bio: Optional[str] = None
    linkedin_profile: Optional[str] = None
    certifications_verified: bool = False
    
    @field_validator('expertise_level')
    @classmethod
    def validate_expertise_level(cls, v):
        if v not in VALID_EXPERTISE_LEVELS:
            raise ValueError(f'Invalid expertise level: {v}')
        return v

class TrainingProgram(BaseModel):
    title: str
    description: str
    level: str
    duration_hours: int
    max_participants: int
    price_per_participant: float
    topics: List[str]
    prerequisites: List[str]
    learning_objectives: List[str]
    instructor_id: str
    schedule: Dict[str, Any]
    materials: List[str]
    certification_offered: bool
    
    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        if v not in VALID_TRAINING_LEVELS:
            raise ValueError(f'Invalid training level: {v}')
        return v

class TrainingEnrollment(BaseModel):
    training_program_id: str
    participant_name: str
    participant_email: str
    participant_company: Optional[str] = None
    participant_role: Optional[str] = None
    experience_level: str = "intermediate"
    special_requirements: Optional[str] = None
    billing_info: Optional[Dict[str, str]] = None
    
    @field_validator('experience_level')
    @classmethod
    def validate_experience_level(cls, v):
        if v not in VALID_EXPERTISE_LEVELS:
            raise ValueError(f'Invalid experience level: {v}')
        return v

class ProfessionalServiceResponse(BaseModel):
    id: str
    service_type: str
    title: str
    description: str
    priority: str
    status: str
    client_id: str
    assigned_professional: Optional[str]
    requested_date: datetime
    scheduled_date: Optional[datetime]
    completion_date: Optional[datetime]
    estimated_duration: Optional[int]
    actual_duration: Optional[int]
    cost: Optional[float]
    deliverables: List[str]
    notes: Optional[str]
    created_date: datetime
    last_updated: datetime

class ProfessionalProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    expertise_level: str
    specializations: List[str]
    experience_years: int
    certifications: List[str]
    education: List[Dict[str, str]]
    languages: List[str]
    hourly_rate: Optional[float]
    availability: Dict[str, Any]
    bio: Optional[str]
    linkedin_profile: Optional[str]
    certifications_verified: bool
    rating: Optional[float]
    completed_services: int
    created_date: datetime
    last_updated: datetime

class TrainingProgramResponse(BaseModel):
    id: str
    title: str
    description: str
    level: str
    duration_hours: int
    max_participants: int
    current_enrollments: int
    price_per_participant: float
    topics: List[str]
    prerequisites: List[str]
    learning_objectives: List[str]
    instructor_id: str
    instructor_name: str
    schedule: Dict[str, Any]
    materials: List[str]
    certification_offered: bool
    status: str
    created_date: datetime
    last_updated: datetime

class ServiceStatistics(BaseModel):
    total_services: int
    services_by_type: Dict[str, int]
    services_by_status: Dict[str, int]
    services_by_priority: Dict[str, int]
    average_completion_time_hours: float
    total_revenue: float
    client_satisfaction_score: Optional[float]
    professional_utilization: Dict[str, float]

# API Endpoints
@router.get("/services", response_model=List[ProfessionalServiceResponse])
async def list_professional_services(
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """List professional services with optional filters"""
    try:
        services_manager = await get_professional_services_manager()
        
        # Build filters
        filters = {}
        if service_type:
            if service_type not in VALID_SERVICE_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid service type: {service_type}"
                )
            filters["service_type"] = service_type
        
        if status:
            if status not in VALID_SERVICE_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}"
                )
            filters["status"] = status
        
        if priority:
            valid_priorities = {"low", "medium", "high", "urgent"}
            if priority not in valid_priorities:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid priority: {priority}"
                )
            filters["priority"] = priority
        
        if client_id:
            filters["client_id"] = client_id
        
        services = await services_manager.get_services(filters, limit, offset)
        
        return [ProfessionalServiceResponse(**service.__dict__) for service in services]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list professional services: {e}")
        raise JackdawException(
            message="Failed to list professional services",
            details=str(e)
        )

@router.post("/services", response_model=ProfessionalServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_professional_service(
    service_request: ProfessionalServiceRequest,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"]))
):
    """Create a new professional service request"""
    try:
        services_manager = await get_professional_services_manager()
        
        service_data = service_request.model_dump()
        service_data["id"] = str(uuid.uuid4())
        service_data["client_id"] = current_user.id
        service_data["status"] = "pending"
        service_data["created_date"] = datetime.now(timezone.utc)
        service_data["last_updated"] = datetime.now(timezone.utc)
        
        created_service = await services_manager.create_service(service_data)
        
        logger.info(f"Created professional service request {created_service.id} by user {current_user.id}")
        return ProfessionalServiceResponse(**created_service.__dict__)
        
    except Exception as e:
        logger.error(f"Failed to create professional service: {e}")
        raise JackdawException(
            message="Failed to create professional service",
            details=str(e)
        )

@router.get("/services/{service_id}", response_model=ProfessionalServiceResponse)
async def get_professional_service(
    service_id: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Get a specific professional service by ID"""
    try:
        services_manager = await get_professional_services_manager()
        
        service = await services_manager.get_service(service_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Professional service {service_id} not found"
            )
        
        return ProfessionalServiceResponse(**service.__dict__)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get professional service {service_id}: {e}")
        raise JackdawException(
            message="Failed to get professional service",
            details=str(e)
        )

@router.put("/services/{service_id}", response_model=ProfessionalServiceResponse)
async def update_professional_service(
    service_id: str,
    service_update: ProfessionalServiceUpdate,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"]))
):
    """Update a professional service"""
    try:
        services_manager = await get_professional_services_manager()
        
        # Check if service exists
        existing_service = await services_manager.get_service(service_id)
        if not existing_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Professional service {service_id} not found"
            )
        
        # Update service
        update_data = service_update.model_dump(exclude_unset=True)
        update_data["last_updated"] = datetime.now(timezone.utc)
        
        updated_service = await services_manager.update_service(service_id, update_data)
        
        logger.info(f"Updated professional service {service_id} by user {current_user.id}")
        return ProfessionalServiceResponse(**updated_service.__dict__)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update professional service {service_id}: {e}")
        raise JackdawException(
            message="Failed to update professional service",
            details=str(e)
        )

@router.get("/professionals", response_model=List[ProfessionalProfileResponse])
async def list_professionals(
    expertise_level: Optional[str] = Query(None, description="Filter by expertise level"),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    available: Optional[bool] = Query(None, description="Filter by availability"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """List available professionals"""
    try:
        services_manager = await get_professional_services_manager()
        
        # Build filters
        filters = {}
        if expertise_level:
            if expertise_level not in VALID_EXPERTISE_LEVELS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid expertise level: {expertise_level}"
                )
            filters["expertise_level"] = expertise_level
        
        if specialization:
            filters["specialization"] = specialization
        
        if available is not None:
            filters["available"] = available
        
        professionals = await services_manager.get_professionals(filters, limit)
        
        return [ProfessionalProfileResponse(**prof.__dict__) for prof in professionals]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list professionals: {e}")
        raise JackdawException(
            message="Failed to list professionals",
            details=str(e)
        )

@router.post("/professionals", response_model=ProfessionalProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_professional_profile(
    profile: ProfessionalProfile,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"]))
):
    """Create a new professional profile"""
    try:
        services_manager = await get_professional_services_manager()
        
        profile_data = profile.model_dump()
        profile_data["id"] = str(uuid.uuid4())
        profile_data["created_date"] = datetime.now(timezone.utc)
        profile_data["last_updated"] = datetime.now(timezone.utc)
        profile_data["rating"] = None
        profile_data["completed_services"] = 0
        
        created_profile = await services_manager.create_professional(profile_data)
        
        logger.info(f"Created professional profile {created_profile.id} by user {current_user.id}")
        return ProfessionalProfileResponse(**created_profile.__dict__)
        
    except Exception as e:
        logger.error(f"Failed to create professional profile: {e}")
        raise JackdawException(
            message="Failed to create professional profile",
            details=str(e)
        )

@router.get("/professionals/{professional_id}", response_model=ProfessionalProfileResponse)
async def get_professional_profile(
    professional_id: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Get a specific professional profile by ID"""
    try:
        services_manager = await get_professional_services_manager()
        
        profile = await services_manager.get_professional(professional_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Professional profile {professional_id} not found"
            )
        
        return ProfessionalProfileResponse(**profile.__dict__)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get professional profile {professional_id}: {e}")
        raise JackdawException(
            message="Failed to get professional profile",
            details=str(e)
        )

@router.get("/training", response_model=List[TrainingProgramResponse])
async def list_training_programs(
    level: Optional[str] = Query(None, description="Filter by training level"),
    status: Optional[str] = Query(None, description="Filter by status"),
    instructor_id: Optional[str] = Query(None, description="Filter by instructor ID"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """List available training programs"""
    try:
        services_manager = await get_professional_services_manager()
        
        # Build filters
        filters = {}
        if level:
            if level not in VALID_TRAINING_LEVELS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid training level: {level}"
                )
            filters["level"] = level
        
        if status:
            filters["status"] = status
        
        if instructor_id:
            filters["instructor_id"] = instructor_id
        
        programs = await services_manager.get_training_programs(filters)
        
        return [TrainingProgramResponse(**program.__dict__) for program in programs]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list training programs: {e}")
        raise JackdawException(
            message="Failed to list training programs",
            details=str(e)
        )

@router.post("/training", response_model=TrainingProgramResponse, status_code=status.HTTP_201_CREATED)
async def create_training_program(
    program: TrainingProgram,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"]))
):
    """Create a new training program"""
    try:
        services_manager = await get_professional_services_manager()
        
        program_data = program.model_dump()
        program_data["id"] = str(uuid.uuid4())
        program_data["current_enrollments"] = 0
        program_data["status"] = "draft"
        program_data["created_date"] = datetime.now(timezone.utc)
        program_data["last_updated"] = datetime.now(timezone.utc)
        
        created_program = await services_manager.create_training_program(program_data)
        
        logger.info(f"Created training program {created_program.id} by user {current_user.id}")
        return TrainingProgramResponse(**created_program.__dict__)
        
    except Exception as e:
        logger.error(f"Failed to create training program: {e}")
        raise JackdawException(
            message="Failed to create training program",
            details=str(e)
        )

@router.post("/training/enroll", response_model=Dict[str, str])
async def enroll_in_training(
    enrollment: TrainingEnrollment,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"]))
):
    """Enroll in a training program"""
    try:
        services_manager = await get_professional_services_manager()
        
        # Check if training program exists and has space
        program = await services_manager.get_training_program(enrollment.training_program_id)
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training program {enrollment.training_program_id} not found"
            )
        
        if program.current_enrollments >= program.max_participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Training program is full"
            )
        
        enrollment_data = enrollment.model_dump()
        enrollment_data["id"] = str(uuid.uuid4())
        enrollment_data["enrollment_date"] = datetime.now(timezone.utc)
        enrollment_data["status"] = "enrolled"
        enrollment_data["client_id"] = current_user.id
        
        enrollment_id = await services_manager.enroll_in_training(enrollment_data)
        
        logger.info(f"Enrolled user {current_user.id} in training program {enrollment.training_program_id}")
        
        return {"enrollment_id": enrollment_id, "status": "enrolled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enroll in training: {e}")
        raise JackdawException(
            message="Failed to enroll in training",
            details=str(e)
        )

@router.get("/services/statistics", response_model=ServiceStatistics)
async def get_service_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Get professional services statistics"""
    try:
        services_manager = await get_professional_services_manager()
        
        stats = await services_manager.get_statistics(days)
        
        return ServiceStatistics(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get service statistics: {e}")
        raise JackdawException(
            message="Failed to get service statistics",
            details=str(e)
        )

@router.post("/services/{service_id}/assign", response_model=ProfessionalServiceResponse)
async def assign_professional(
    service_id: str,
    professional_id: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"]))
):
    """Assign a professional to a service"""
    try:
        services_manager = await get_professional_services_manager()
        
        # Check if service exists
        existing_service = await services_manager.get_service(service_id)
        if not existing_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Professional service {service_id} not found"
            )
        
        # Check if professional exists
        professional = await services_manager.get_professional(professional_id)
        if not professional:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Professional {professional_id} not found"
            )
        
        update_data = {
            "assigned_professional": professional_id,
            "status": "scheduled",
            "last_updated": datetime.now(timezone.utc)
        }
        
        updated_service = await services_manager.update_service(service_id, update_data)
        
        logger.info(f"Assigned professional {professional_id} to service {service_id} by user {current_user.id}")
        return ProfessionalServiceResponse(**updated_service.__dict__)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign professional to service {service_id}: {e}")
        raise JackdawException(
            message="Failed to assign professional",
            details=str(e)
        )

@router.get("/services/my", response_model=List[ProfessionalServiceResponse])
async def get_my_services(
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Get services for the current user"""
    try:
        services_manager = await get_professional_services_manager()
        
        filters = {"client_id": current_user.id}
        if status:
            if status not in VALID_SERVICE_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}"
                )
            filters["status"] = status
        
        services = await services_manager.get_services(filters, 100, 0)
        
        return [ProfessionalServiceResponse(**service.__dict__) for service in services]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user services: {e}")
        raise JackdawException(
            message="Failed to get user services",
            details=str(e)
        )
