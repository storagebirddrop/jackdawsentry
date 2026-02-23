"""
Compliance Visualization API Router

Endpoints for compliance data visualization including:
- Visualization listing and generation
- Data retrieval for charts
- Export visualizations in multiple formats
- Custom visualization management
"""

import logging
from datetime import datetime
from datetime import timezone
from functools import lru_cache
from typing import Any
from typing import Dict
from typing import Optional

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import Response

from src.api.auth import User
from src.api.auth import check_permissions
from src.api.auth import get_current_user
from src.visualization.compliance_visualization import ComplianceVisualizationEngine
from src.visualization.compliance_visualization import DataFormat
from src.visualization.compliance_visualization import VisualizationConfig
from src.visualization.compliance_visualization import VisualizationType

logger = logging.getLogger(__name__)

router = APIRouter()


@lru_cache(maxsize=1)
def get_viz_engine() -> ComplianceVisualizationEngine:
    """Dependency provider for ComplianceVisualizationEngine."""
    return ComplianceVisualizationEngine()


@router.get("/list")
async def list_visualizations(
    viz_engine: ComplianceVisualizationEngine = Depends(get_viz_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """List available visualizations"""
    try:
        visualizations = []
        for viz_id, config in viz_engine.visualizations.items():
            visualizations.append(
                {
                    "viz_id": config.viz_id,
                    "title": config.title,
                    "description": config.description,
                    "viz_type": config.viz_type.value,
                    "data_source": config.data_source,
                }
            )
        return {
            "success": True,
            "visualizations": visualizations,
            "total": len(visualizations),
        }
    except Exception as e:
        logger.error(f"Failed to list visualizations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/{viz_id}")
async def generate_visualization(
    viz_id: str,
    filters: Optional[Dict[str, Any]] = Body(None),
    viz_engine: ComplianceVisualizationEngine = Depends(get_viz_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Generate visualization data"""
    try:
        result = await viz_engine.generate_visualization(viz_id, filters=filters)
        if not result.success:
            raise HTTPException(
                status_code=500, detail=result.error_message or "Generation failed"
            )
        return {
            "success": True,
            "viz_id": result.viz_id,
            "data": result.data.data if result.data else None,
            "labels": result.data.labels if result.data else None,
            "datasets": result.data.datasets if result.data else None,
            "generation_time_ms": result.generation_time_ms,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate visualization {viz_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{viz_id}")
async def get_visualization_data(
    viz_id: str,
    viz_engine: ComplianceVisualizationEngine = Depends(get_viz_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Get visualization data (cached if available)"""
    try:
        if viz_id in viz_engine.visualization_cache:
            cached = viz_engine.visualization_cache[viz_id]
            return {
                "success": True,
                "viz_id": viz_id,
                "data": cached.get("data") if isinstance(cached, dict) else cached,
                "source": "cache",
            }
        result = await viz_engine.generate_visualization(viz_id)
        if not result.success:
            raise HTTPException(
                status_code=500, detail=result.error_message or "Generation failed"
            )
        return {
            "success": True,
            "viz_id": result.viz_id,
            "data": result.data.data if result.data else None,
            "source": "generated",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get visualization data {viz_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/{viz_id}")
async def export_visualization(
    viz_id: str,
    export_format: str = "json",
    viz_engine: ComplianceVisualizationEngine = Depends(get_viz_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Export visualization in specified format"""
    try:
        data_format = DataFormat(export_format)
        content = await viz_engine.export_visualization(viz_id, data_format)

        media_types = {
            "json": "application/json",
            "csv": "text/csv",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "png": "image/png",
            "svg": "image/svg+xml",
            "pdf": "application/pdf",
        }
        media_type = media_types.get(export_format, "application/octet-stream")
        return Response(content=content, media_type=media_type)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Unsupported format: {export_format}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export visualization {viz_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{viz_id}")
async def delete_visualization(
    viz_id: str,
    viz_engine: ComplianceVisualizationEngine = Depends(get_viz_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"])),
):
    """Delete a visualization"""
    try:
        success = await viz_engine.delete_visualization(viz_id)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Visualization {viz_id} not found"
            )
        return {"success": True, "message": f"Visualization {viz_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete visualization {viz_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_visualization_statistics(
    viz_engine: ComplianceVisualizationEngine = Depends(get_viz_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Get visualization statistics"""
    try:
        type_counts = {}
        for config in viz_engine.visualizations.values():
            vt = config.viz_type.value
            type_counts[vt] = type_counts.get(vt, 0) + 1
        return {
            "success": True,
            "statistics": {
                "total_visualizations": len(viz_engine.visualizations),
                "cached_visualizations": len(viz_engine.visualization_cache),
                "by_type": type_counts,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to get visualization statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom")
async def create_custom_visualization(
    config_data: Dict[str, Any],
    viz_engine: ComplianceVisualizationEngine = Depends(get_viz_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Create a custom visualization"""
    try:
        config = VisualizationConfig(
            viz_id=config_data["viz_id"],
            title=config_data["title"],
            description=config_data.get("description", ""),
            viz_type=VisualizationType(config_data["viz_type"]),
            data_source=config_data.get("data_source", "custom"),
            config=config_data.get("config", {}),
        )
        success = await viz_engine.create_custom_visualization(config)
        if not success:
            raise HTTPException(
                status_code=400, detail="Failed to create visualization"
            )
        return {
            "success": True,
            "viz_id": config.viz_id,
            "message": "Custom visualization created",
        }
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid config: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create custom visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_visualization_cache(
    viz_engine: ComplianceVisualizationEngine = Depends(get_viz_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"])),
):
    """Clear visualization cache"""
    try:
        count = await viz_engine.clear_cache()
        return {
            "success": True,
            "cleared_count": count,
            "message": "Visualization cache cleared",
        }
    except Exception as e:
        logger.error(f"Failed to clear visualization cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def visualization_health_check(
    viz_engine: ComplianceVisualizationEngine = Depends(get_viz_engine),
):
    """Visualization service health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "compliance_visualization",
        "visualizations_count": len(viz_engine.visualizations),
    }
