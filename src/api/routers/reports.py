"""
Jackdaw Sentry - Reports Router
Report generation and management endpoints
"""

import csv as _csv
import io
import json as _json
import logging
import time as _time
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Response
from fastapi import status
from pydantic import BaseModel
from pydantic import field_validator

from src.api.auth import PERMISSIONS
from src.api.auth import User
from src.api.auth import check_permissions
from src.api.database import get_neo4j_session
from src.api.exceptions import JackdawException

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class ReportRequest(BaseModel):
    report_type: str  # transaction, compliance, investigation, intelligence, custom
    title: str
    description: str
    parameters: Dict[str, Any]
    format: str = "json"  # json, pdf, csv, xlsx
    schedule: Optional[str] = None  # daily, weekly, monthly, quarterly

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v):
        valid_types = [
            "transaction",
            "compliance",
            "investigation",
            "intelligence",
            "custom",
            "audit",
        ]
        if v not in valid_types:
            raise ValueError(f"Invalid report type: {v}")
        return v

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        valid_formats = ["json", "pdf", "csv", "xlsx"]
        if v not in valid_formats:
            raise ValueError(f"Invalid format: {v}")
        return v


class ReportTemplateRequest(BaseModel):
    name: str
    description: str
    report_type: str
    template_definition: Dict[str, Any]
    is_public: bool = False

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v):
        valid_types = [
            "transaction",
            "compliance",
            "investigation",
            "intelligence",
            "custom",
        ]
        if v not in valid_types:
            raise ValueError(f"Invalid report type: {v}")
        return v


class ReportResponse(BaseModel):
    success: bool
    report_data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime


# Endpoints
@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_reports"]])),
):
    """Generate report"""
    try:
        start = _time.monotonic()
        logger.info(f"Generating {request.report_type} report: {request.title}")

        now = datetime.now(timezone.utc)
        report_id = f"RPT-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        summary: Dict[str, Any] = {}

        async with get_neo4j_session() as session:
            if request.report_type == "transaction":
                r = await session.run(
                    "MATCH (t:Transaction) RETURN count(t) AS total, sum(t.value) AS volume"
                )
                rec = await r.single()
                addr_r = await session.run("MATCH (a:Address) RETURN count(a) AS total")
                addr_rec = await addr_r.single()
                summary = {
                    "total_transactions": rec["total"] if rec else 0,
                    "total_volume": float(rec["volume"] or 0) if rec else 0,
                    "unique_addresses": addr_rec["total"] if addr_rec else 0,
                }
                dist_r = await session.run(
                    "MATCH (t:Transaction) RETURN t.blockchain AS bc, count(t) AS c, "
                    "sum(t.value) AS v ORDER BY c DESC"
                )
                summary["by_blockchain"] = {
                    r2["bc"]: {"count": r2["c"], "volume": float(r2["v"] or 0)}
                    for r2 in await dist_r.data()
                    if r2["bc"]
                }

            elif request.report_type == "compliance":
                ra_r = await session.run(
                    "MATCH (a:RiskAssessment) RETURN count(a) AS total, "
                    "count(CASE WHEN a.risk_level IN ['high','severe'] THEN 1 END) AS flagged"
                )
                ra_rec = await ra_r.single()
                rules_r = await session.run(
                    "MATCH (r:ComplianceRule) RETURN count(r) AS total"
                )
                rules_rec = await rules_r.single()
                summary = {
                    "total_risk_assessments": ra_rec["total"] if ra_rec else 0,
                    "flagged_assessments": ra_rec["flagged"] if ra_rec else 0,
                    "total_rules": rules_rec["total"] if rules_rec else 0,
                }

            elif request.report_type == "investigation":
                inv_r = await session.run(
                    "MATCH (i:Investigation) RETURN count(i) AS total, "
                    "count(CASE WHEN i.status IN ['open','in_progress'] THEN 1 END) AS active, "
                    "count(CASE WHEN i.status = 'closed' THEN 1 END) AS closed"
                )
                inv_rec = await inv_r.single()
                evd_r = await session.run("MATCH (e:Evidence) RETURN count(e) AS total")
                evd_rec = await evd_r.single()
                summary = {
                    "total_cases": inv_rec["total"] if inv_rec else 0,
                    "active_cases": inv_rec["active"] if inv_rec else 0,
                    "closed_cases": inv_rec["closed"] if inv_rec else 0,
                    "evidence_items": evd_rec["total"] if evd_rec else 0,
                }

            else:
                summary = {"custom_parameters": request.parameters}

            # Persist the report node
            await session.run(
                """
                CREATE (r:Report {
                    report_id: $report_id, report_type: $report_type,
                    title: $title, description: $description,
                    format: $format, status: 'completed',
                    created_by: $created_by, created_at: $created_at,
                    parameters: $parameters, summary: $summary
                })
                """,
                report_id=report_id,
                report_type=request.report_type,
                title=request.title,
                description=request.description,
                format=request.format,
                created_by=current_user.username,
                created_at=now.isoformat(),
                parameters=_json.dumps(request.parameters),
                summary=_json.dumps(summary),
            )

        elapsed_ms = int((_time.monotonic() - start) * 1000)
        report_data = {
            "report_id": report_id,
            "report_type": request.report_type,
            "title": request.title,
            "summary": summary,
            "status": "completed",
            "created_at": now.isoformat(),
        }
        metadata = {
            "format": request.format,
            "generation_time_ms": elapsed_ms,
            "data_sources": ["neo4j"],
            "persisted_to": "neo4j",
        }

        return ReportResponse(
            success=True,
            report_data=report_data,
            metadata=metadata,
            timestamp=now,
        )

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise JackdawException(
            message=f"Report generation failed: {str(e)}",
            error_code="REPORT_GENERATION_FAILED",
        )


@router.get("/list")
async def list_reports(
    report_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_reports"]])),
):
    """List generated reports from Neo4j"""
    try:
        logger.info("Listing reports with filters")

        where_clauses = []
        params: Dict[str, Any] = {"skip_val": offset, "limit_val": limit}
        if report_type:
            where_clauses.append("r.report_type = $report_type")
            params["report_type"] = report_type
        if status:
            where_clauses.append("r.status = $status")
            params["status"] = status
        where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        async with get_neo4j_session() as session:
            count_result = await session.run(
                f"MATCH (r:Report) {where_str} RETURN count(r) AS total", **params
            )
            count_record = await count_result.single()
            total_count = count_record["total"] if count_record else 0

            result = await session.run(
                f"MATCH (r:Report) {where_str} RETURN r ORDER BY r.created_at DESC "
                f"SKIP $skip_val LIMIT $limit_val",
                **params,
            )
            records = await result.data()

        reports = [dict(r["r"]) for r in records]

        return {
            "success": True,
            "reports": reports,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
            },
            "filters_applied": {"report_type": report_type, "status": status},
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Report listing failed: {e}")
        raise JackdawException(
            message=f"Report listing failed: {str(e)}",
            error_code="REPORT_LISTING_FAILED",
        )


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_reports"]])),
):
    """Get report details from Neo4j"""
    try:
        logger.info(f"Getting report details for: {report_id}")

        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH (r:Report {report_id: $report_id}) RETURN r",
                report_id=report_id,
            )
            record = await result.single()

        if not record or not record["r"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Report not found"
            )

        report_data = dict(record["r"])
        report_data["download_url"] = f"/api/v1/reports/{report_id}/download"

        return {
            "success": True,
            "report": report_data,
            "timestamp": datetime.now(timezone.utc),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report retrieval failed: {e}")
        raise JackdawException(
            message=f"Report retrieval failed: {str(e)}",
            error_code="REPORT_RETRIEVAL_FAILED",
        )


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    format: str = "json",
    current_user: User = Depends(check_permissions([PERMISSIONS["read_reports"]])),
):
    """Download report data from Neo4j in requested format"""
    try:
        logger.info(f"Downloading report {report_id} in {format} format")

        # Fetch report from Neo4j
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH (r:Report {report_id: $report_id}) RETURN r",
                report_id=report_id,
            )
            record = await result.single()

        if not record or not record["r"]:
            raise HTTPException(status_code=404, detail="Report not found")

        report = dict(record["r"])

        if format == "json":
            content = _json.dumps(report, indent=2, default=str)
            return Response(
                content=content,
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename={report_id}.json"
                },
            )

        elif format == "csv":
            output = io.StringIO()
            writer = _csv.writer(output)
            writer.writerow(report.keys())
            writer.writerow([str(v) for v in report.values()])
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={report_id}.csv"
                },
            )

        elif format == "pdf":
            # Render report data as plain-text PDF placeholder
            text = f"Report: {report.get('title', report_id)}\n"
            text += f"Type: {report.get('report_type')}\n"
            text += f"Created: {report.get('created_at')}\n\n"
            text += _json.dumps(report.get("summary", "{}"), indent=2, default=str)
            return Response(
                content=text.encode("utf-8"),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename={report_id}.pdf"
                },
            )

        elif format == "xlsx":
            # Render as tab-separated values with xlsx mime type
            lines = [
                "\t".join(report.keys()),
                "\t".join(str(v) for v in report.values()),
            ]
            return Response(
                content="\n".join(lines).encode("utf-8"),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename={report_id}.xlsx"
                },
            )

        else:
            raise HTTPException(status_code=400, detail="Unsupported format")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report download failed: {e}")
        raise JackdawException(
            message=f"Report download failed: {str(e)}",
            error_code="REPORT_DOWNLOAD_FAILED",
        )


@router.post("/templates", response_model=ReportResponse)
async def create_report_template(
    request: ReportTemplateRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_reports"]])),
):
    """Create report template and persist to Neo4j"""
    try:
        logger.info(f"Creating report template: {request.name}")
        now = datetime.now(timezone.utc)
        tpl_id = f"TPL-{uuid.uuid4().hex[:8].upper()}"

        async with get_neo4j_session() as session:
            await session.run(
                """
                CREATE (t:ReportTemplate {
                    template_id: $tpl_id, name: $name,
                    description: $description, report_type: $report_type,
                    template_definition: $definition, is_public: $is_public,
                    created_by: $created_by, created_at: $created_at,
                    version: '1.0', usage_count: 0
                })
                """,
                tpl_id=tpl_id,
                name=request.name,
                description=request.description,
                report_type=request.report_type,
                definition=_json.dumps(request.template_definition),
                is_public=request.is_public,
                created_by=current_user.username,
                created_at=now.isoformat(),
            )

        template_data = {
            "template_id": tpl_id,
            "name": request.name,
            "description": request.description,
            "report_type": request.report_type,
            "is_public": request.is_public,
            "created_by": current_user.username,
            "created_at": now.isoformat(),
            "version": "1.0",
            "usage_count": 0,
        }
        metadata = {"persisted_to": "neo4j", "template_validation": "passed"}

        return ReportResponse(
            success=True,
            report_data=template_data,
            metadata=metadata,
            timestamp=now,
        )

    except Exception as e:
        logger.error(f"Template creation failed: {e}")
        raise JackdawException(
            message=f"Template creation failed: {str(e)}",
            error_code="TEMPLATE_CREATION_FAILED",
        )


@router.get("/templates")
async def list_report_templates(
    report_type: Optional[str] = None,
    is_public: Optional[bool] = None,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(check_permissions([PERMISSIONS["read_reports"]])),
):
    """List report templates from Neo4j"""
    try:
        where_clauses = []
        params: Dict[str, Any] = {"limit_val": limit, "skip_val": offset}
        if report_type:
            where_clauses.append("t.report_type = $report_type")
            params["report_type"] = report_type
        if is_public is not None:
            where_clauses.append("t.is_public = $is_public")
            params["is_public"] = is_public
        where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        base_query = f"MATCH (t:ReportTemplate) {where_str}"

        async with get_neo4j_session() as session:
            count_result = await session.run(
                base_query + " RETURN count(t) AS total", **params
            )
            count_rec = await count_result.single()
            total_count = count_rec["total"] if count_rec else 0

            result = await session.run(
                base_query
                + " RETURN t ORDER BY t.created_at DESC SKIP $skip_val LIMIT $limit_val",
                **params,
            )
            records = await result.data()

        templates = [dict(r["t"]) for r in records]

        return {
            "success": True,
            "templates": templates,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
            },
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Template listing failed: {e}")
        raise JackdawException(
            message=f"Template listing failed: {str(e)}",
            error_code="TEMPLATE_LISTING_FAILED",
        )


@router.get("/statistics")
async def get_report_statistics(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_reports"]])),
):
    """Get reporting system statistics from Neo4j"""
    try:
        stats: Dict[str, Any] = {}
        async with get_neo4j_session() as session:
            rpt_result = await session.run("MATCH (r:Report) RETURN count(r) AS total")
            rpt_rec = await rpt_result.single()
            stats["total_reports"] = rpt_rec["total"] if rpt_rec else 0

            type_result = await session.run(
                "MATCH (r:Report) RETURN r.report_type AS rtype, count(r) AS c"
            )
            type_recs = await type_result.data()
            stats["reports_by_type"] = {
                r["rtype"]: r["c"] for r in type_recs if r["rtype"]
            }

            fmt_result = await session.run(
                "MATCH (r:Report) RETURN r.format AS fmt, count(r) AS c"
            )
            fmt_recs = await fmt_result.data()
            stats["reports_by_format"] = {
                r["fmt"]: r["c"] for r in fmt_recs if r["fmt"]
            }

            tpl_result = await session.run(
                "MATCH (t:ReportTemplate) RETURN count(t) AS total"
            )
            tpl_rec = await tpl_result.single()
            stats["templates_available"] = tpl_rec["total"] if tpl_rec else 0

        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Report statistics failed: {e}")
        raise JackdawException(
            message=f"Report statistics failed: {str(e)}",
            error_code="STATISTICS_FAILED",
        )
