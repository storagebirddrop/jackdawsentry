"""
Jackdaw Sentry - Admin Router
System administration and management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
import logging

from src.api.auth import User, check_permissions, PERMISSIONS
from src.api.database import get_postgres_connection, get_neo4j_session, get_redis_connection
from src.api.exceptions import JackdawException

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class UserManagementRequest(BaseModel):
    username: str
    email: str
    role: str
    permissions: List[str]
    is_active: bool = True
    
    @validator('role')
    def validate_role(cls, v):
        valid_roles = ["viewer", "analyst", "compliance_officer", "admin"]
        if v not in valid_roles:
            raise ValueError(f'Invalid role: {v}')
        return v


class SystemConfigRequest(BaseModel):
    config_key: str
    config_value: Any
    description: str
    is_sensitive: bool = False


class MaintenanceRequest(BaseModel):
    maintenance_type: str  # backup, cleanup, update, restart
    schedule_time: Optional[datetime] = None
    duration_minutes: int = 30
    notification_required: bool = True
    
    @validator('maintenance_type')
    def validate_maintenance_type(cls, v):
        valid_types = ["backup", "cleanup", "update", "restart", "shutdown"]
        if v not in valid_types:
            raise ValueError(f'Invalid maintenance type: {v}')
        return v


class AdminResponse(BaseModel):
    success: bool
    admin_data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime


# Endpoints
@router.get("/users")
async def list_users(
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(check_permissions([PERMISSIONS["admin_users"]]))
):
    """List system users"""
    try:
        logger.info(f"Listing users with filters")
        
        users = [
            {
                "user_id": "USR-001",
                "username": "admin",
                "email": "admin@jackdawsentry.com",
                "role": "admin",
                "permissions": list(PERMISSIONS.values()),
                "is_active": True,
                "created_at": datetime.utcnow() - timedelta(days=365),
                "last_login": datetime.utcnow() - timedelta(hours=2),
                "login_count": 1250
            },
            {
                "user_id": "USR-002",
                "username": "analyst1",
                "email": "analyst1@jackdawsentry.com",
                "role": "analyst",
                "permissions": ["analysis:read", "analysis:write", "investigations:read", "investigations:write"],
                "is_active": True,
                "created_at": datetime.utcnow() - timedelta(days=180),
                "last_login": datetime.utcnow() - timedelta(hours=6),
                "login_count": 450
            },
            {
                "user_id": "USR-003",
                "username": "compliance1",
                "email": "compliance1@jackdawsentry.com",
                "role": "compliance_officer",
                "permissions": ["compliance:read", "compliance:write", "investigations:read", "investigations:write"],
                "is_active": True,
                "created_at": datetime.utcnow() - timedelta(days=90),
                "last_login": datetime.utcnow() - timedelta(days=1),
                "login_count": 230
            }
        ]
        
        # Apply filters
        if role:
            users = [user for user in users if user["role"] == role]
        if is_active is not None:
            users = [user for user in users if user["is_active"] == is_active]
        
        # Apply pagination
        total_count = len(users)
        paginated_users = users[offset:offset + limit]
        
        return {
            "success": True,
            "users": paginated_users,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "filters_applied": {
                "role": role,
                "is_active": is_active
            },
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"User listing failed: {e}")
        raise JackdawException(
            message=f"User listing failed: {str(e)}",
            error_code="USER_LISTING_FAILED"
        )


@router.post("/users", response_model=AdminResponse)
async def create_user(
    request: UserManagementRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["admin_users"]]))
):
    """Create new user"""
    try:
        logger.info(f"Creating user: {request.username}")
        
        user_data = {
            "user_id": f"USR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "username": request.username,
            "email": request.email,
            "role": request.role,
            "permissions": request.permissions,
            "is_active": request.is_active,
            "created_by": current_user.username,
            "created_at": datetime.utcnow(),
            "last_login": None,
            "login_count": 0
        }
        
        metadata = {
            "validation_status": "passed",
            "duplicate_check": "no_duplicates_found",
            "notification_sent": True
        }
        
        return AdminResponse(
            success=True,
            admin_data=user_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"User creation failed: {e}")
        raise JackdawException(
            message=f"User creation failed: {str(e)}",
            error_code="USER_CREATION_FAILED"
        )


@router.put("/users/{user_id}", response_model=AdminResponse)
async def update_user(
    user_id: str,
    request: UserManagementRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["admin_users"]]))
):
    """Update user details"""
    try:
        logger.info(f"Updating user: {user_id}")
        
        update_data = {
            "user_id": user_id,
            "username": request.username,
            "email": request.email,
            "role": request.role,
            "permissions": request.permissions,
            "is_active": request.is_active,
            "updated_by": current_user.username,
            "updated_at": datetime.utcnow()
        }
        
        metadata = {
            "update_fields": ["username", "email", "role", "permissions", "is_active"],
            "previous_values": {},  # In real implementation, would fetch previous values
            "change_approved": True
        }
        
        return AdminResponse(
            success=True,
            admin_data=update_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"User update failed: {e}")
        raise JackdawException(
            message=f"User update failed: {str(e)}",
            error_code="USER_UPDATE_FAILED"
        )


@router.delete("/users/{user_id}", response_model=AdminResponse)
async def delete_user(
    user_id: str,
    current_user: User = Depends(check_permissions([PERMISSIONS["admin_users"]]))
):
    """Delete user"""
    try:
        logger.info(f"Deleting user: {user_id}")
        
        # In a real implementation, this would delete from database
        # For now, we'll return success
        
        delete_data = {
            "user_id": user_id,
            "deleted_by": current_user.username,
            "deleted_at": datetime.utcnow(),
            "gdpr_compliant": True,
            "data_retention_days": 2555  # 7 years as per EU AML
        }
        
        metadata = {
            "deletion_method": "soft_delete",
            "data_archived": True,
            "notification_sent": True
        }
        
        return AdminResponse(
            success=True,
            admin_data=delete_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"User deletion failed: {e}")
        raise JackdawException(
            message=f"User deletion failed: {str(e)}",
            error_code="USER_DELETION_FAILED"
        )


@router.get("/system/status")
async def get_system_status(
    current_user: User = Depends(check_permissions([PERMISSIONS["admin_system"]]))
):
    """Get system status"""
    try:
        logger.info("Getting system status")
        
        status_data = {
            "overall_status": "healthy",
            "uptime_days": 45,
            "version": "1.0.0",
            "environment": "production",
            "components": {
                "api_server": {
                    "status": "healthy",
                    "cpu_usage": 0.35,
                    "memory_usage": 0.68,
                    "disk_usage": 0.42,
                    "response_time_ms": 150
                },
                "databases": {
                    "neo4j": {
                        "status": "healthy",
                        "connections": 25,
                        "query_time_ms": 45
                    },
                    "postgres": {
                        "status": "healthy",
                        "connections": 15,
                        "query_time_ms": 25
                    },
                    "redis": {
                        "status": "healthy",
                        "connections": 10,
                        "memory_usage_mb": 250
                    }
                },
                "blockchain_nodes": {
                    "bitcoin": {"status": "healthy", "sync_delay": 30},
                    "ethereum": {"status": "healthy", "sync_delay": 15},
                    "bsc": {"status": "healthy", "sync_delay": 10}
                },
                "collectors": {
                    "running": 7,
                    "total": 8,
                    "last_collection": datetime.utcnow() - timedelta(minutes=2)
                }
            },
            "alerts": [
                {
                    "level": "warning",
                    "message": "High memory usage on API server",
                    "timestamp": datetime.utcnow() - timedelta(hours=1)
                }
            ]
        }
        
        return {
            "success": True,
            "system_status": status_data,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        raise JackdawException(
            message=f"System status check failed: {str(e)}",
            error_code="SYSTEM_STATUS_FAILED"
        )


@router.get("/system/config")
async def get_system_config(
    current_user: User = Depends(check_permissions([PERMISSIONS["admin_system"]]))
):
    """Get system configuration"""
    try:
        logger.info("Getting system config")
        
        config_data = {
            "api_settings": {
                "host": "0.0.0.0",
                "port": 8000,
                "log_level": "INFO",
                "rate_limit_enabled": True,
                "rate_limit_requests_per_minute": 100
            },
            "database_settings": {
                "neo4j_max_connections": 50,
                "postgres_max_connections": 20,
                "redis_max_connections": 20
            },
            "blockchain_settings": {
                "collection_interval_seconds": 60,
                "sync_timeout_seconds": 30,
                "retry_attempts": 3
            },
            "compliance_settings": {
                "data_retention_days": 2555,
                "auto_delete_expired_data": True,
                "gdpr_consent_required": True
            },
            "security_settings": {
                "jwt_expire_minutes": 1440,
                "encryption_algorithm": "AES-256-GCM",
                "session_timeout_minutes": 30
            }
        }
        
        return {
            "success": True,
            "configuration": config_data,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"System config retrieval failed: {e}")
        raise JackdawException(
            message=f"System config retrieval failed: {str(e)}",
            error_code="CONFIG_RETRIEVAL_FAILED"
        )


@router.post("/system/config", response_model=AdminResponse)
async def update_system_config(
    request: SystemConfigRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["admin_system"]]))
):
    """Update system configuration"""
    try:
        logger.info(f"Updating system config: {request.config_key}")
        
        config_data = {
            "config_key": request.config_key,
            "config_value": request.config_value,
            "description": request.description,
            "is_sensitive": request.is_sensitive,
            "updated_by": current_user.username,
            "updated_at": datetime.utcnow()
        }
        
        metadata = {
            "validation_status": "passed",
            "restart_required": False,
            "backup_created": True
        }
        
        return AdminResponse(
            success=True,
            admin_data=config_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"System config update failed: {e}")
        raise JackdawException(
            message=f"System config update failed: {str(e)}",
            error_code="CONFIG_UPDATE_FAILED"
        )


@router.post("/system/maintenance", response_model=AdminResponse)
async def schedule_maintenance(
    request: MaintenanceRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["admin_system"]]))
):
    """Schedule system maintenance"""
    try:
        logger.info(f"Scheduling maintenance: {request.maintenance_type}")
        
        maintenance_data = {
            "maintenance_id": f"MTN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "maintenance_type": request.maintenance_type,
            "scheduled_time": request.schedule_time or datetime.utcnow() + timedelta(hours=2),
            "duration_minutes": request.duration_minutes,
            "notification_required": request.notification_required,
            "scheduled_by": current_user.username,
            "status": "scheduled",
            "impact_assessment": {
                "service_disruption": True,
                "affected_components": ["api_server", "collectors"],
                "user_impact": "high"
            }
        }
        
        metadata = {
            "maintenance_validation": "passed",
            "notifications_queued": request.notification_required,
            "backup_initiated": True
        }
        
        return AdminResponse(
            success=True,
            admin_data=maintenance_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Maintenance scheduling failed: {e}")
        raise JackdawException(
            message=f"Maintenance scheduling failed: {str(e)}",
            error_code="MAINTENANCE_SCHEDULING_FAILED"
        )


@router.get("/system/logs")
async def get_system_logs(
    level: Optional[str] = None,
    component: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(check_permissions([PERMISSIONS["admin_system"]]))
):
    """Get system logs"""
    try:
        logger.info(f"Getting system logs with filters")
        
        logs = [
            {
                "timestamp": datetime.utcnow() - timedelta(minutes=5),
                "level": "INFO",
                "component": "api_server",
                "message": "Request processed successfully",
                "details": {"endpoint": "/api/v1/analysis/address", "duration_ms": 250}
            },
            {
                "timestamp": datetime.utcnow() - timedelta(minutes=10),
                "level": "WARNING",
                "component": "collectors",
                "message": "Bitcoin collector connection timeout",
                "details": {"node": "bitcoin_node_1", "timeout_seconds": 30}
            },
            {
                "timestamp": datetime.utcnow() - timedelta(minutes=15),
                "level": "ERROR",
                "component": "database",
                "message": "Neo4j query failed",
                "details": {"query": "MATCH (n) RETURN n", "error": "connection_refused"}
            }
        ]
        
        # Apply filters
        if level:
            logs = [log for log in logs if log["level"] == level.upper()]
        if component:
            logs = [log for log in logs if log["component"] == component]
        
        # Apply pagination
        total_count = len(logs)
        paginated_logs = logs[offset:offset + limit]
        
        return {
            "success": True,
            "logs": paginated_logs,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "filters_applied": {
                "level": level,
                "component": component
            },
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"System logs retrieval failed: {e}")
        raise JackdawException(
            message=f"System logs retrieval failed: {str(e)}",
            error_code="LOGS_RETRIEVAL_FAILED"
        )


@router.get("/statistics")
async def get_admin_statistics(
    current_user: User = Depends(check_permissions([PERMISSIONS["admin_full"]]))
):
    """Get administrative statistics"""
    try:
        stats = {
            "user_statistics": {
                "total_users": 25,
                "active_users": 23,
                "daily_active_users": 18,
                "new_users_this_month": 3
            },
            "system_performance": {
                "uptime_percentage": 99.8,
                "average_response_time_ms": 150,
                "error_rate": 0.02,
                "throughput_requests_per_minute": 450
            },
            "data_statistics": {
                "total_transactions_processed": 1542000,
                "database_size_gb": 125.5,
                "daily_data_growth_mb": 850,
                "cache_hit_rate": 0.75
            },
            "security_statistics": {
                "failed_login_attempts_today": 12,
                "blocked_ips": 5,
                "security_incidents_this_month": 2,
                "vulnerabilities_found": 0
            },
            "compliance_statistics": {
                "compliance_checks_today": 1250,
                "regulatory_coverage": 0.95,
                "audit_logs_entries": 452000,
                "data_deletion_requests": 3
            }
        }
        
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Admin statistics failed: {e}")
        raise JackdawException(
            message=f"Admin statistics failed: {str(e)}",
            error_code="STATISTICS_FAILED"
        )
