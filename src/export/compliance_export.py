"""
Compliance Data Export Module

This module provides comprehensive data export functionality for compliance operations including:
- Regulatory report exports in multiple formats
- Case data export with evidence
- Risk assessment data export
- Audit trail export for compliance verification
- Bulk data export for regulatory submissions
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
import csv
import io
import zipfile
import pandas as pd
from pathlib import Path
import aiofiles
import aiohttp

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Export format types"""
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    PDF = "pdf"
    EXCEL = "excel"
    ZIP = "zip"


class ExportType(Enum):
    """Export data types"""
    REGULATORY_REPORTS = "regulatory_reports"
    CASE_DATA = "case_data"
    RISK_ASSESSMENTS = "risk_assessments"
    AUDIT_TRAIL = "audit_trail"
    EVIDENCE = "evidence"
    COMPLIANCE_SUMMARY = "compliance_summary"
    CUSTOM_EXPORT = "custom_export"


@dataclass
class ExportRequest:
    """Export request definition"""
    export_id: str
    export_type: ExportType
    format: ExportFormat
    filters: Dict[str, Any]
    date_range: Optional[Dict[str, str]] = None
    include_sensitive: bool = False
    compression: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ExportResult:
    """Export result definition"""
    export_id: str
    status: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    record_count: Optional[int] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ComplianceExportEngine:
    """Compliance data export engine"""

    def __init__(self):
        self.export_queue = asyncio.Queue()
        self.active_exports = {}
        self.export_history = []
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.export_dir = Path("./exports/compliance")
        self.export_dir.mkdir(parents=True, exist_ok=True)

    async def create_export(self, request: ExportRequest) -> ExportResult:
        """Create and process export request"""
        try:
            # Initialize export result
            result = ExportResult(
                export_id=request.export_id,
                status="pending",
                created_at=datetime.utcnow(),
                metadata=request.metadata
            )
            
            # Add to active exports
            self.active_exports[request.export_id] = result
            
            # Process export
            await self._process_export(request, result)
            
            # Move to history
            self.export_history.append(result)
            if request.export_id in self.active_exports:
                del self.active_exports[request.export_id]
            
            return result
            
        except Exception as e:
            logger.error(f"Export failed for {request.export_id}: {e}")
            
            # Update result with error
            if request.export_id in self.active_exports:
                self.active_exports[request.export_id].status = "failed"
                self.active_exports[request.export_id].error_message = str(e)
                self.active_exports[request.export_id].completed_at = datetime.utcnow()
            
            raise

    async def _process_export(self, request: ExportRequest, result: ExportResult):
        """Process export request"""
        try:
            result.status = "processing"
            
            # Get data based on export type
            data = await self._get_export_data(request)
            
            # Format data based on requested format
            file_path = await self._format_export_data(request, data)
            
            # Compress if requested
            if request.compression:
                file_path = await self._compress_export(file_path)
            
            # Get file info
            file_size = Path(file_path).stat().st_size
            record_count = len(data) if isinstance(data, list) else 1
            
            # Update result
            result.status = "completed"
            result.file_path = file_path
            result.file_size = file_size
            result.record_count = record_count
            result.completed_at = datetime.utcnow()
            
            logger.info(f"Export completed: {request.export_id} ({file_size} bytes)")
            
        except Exception as e:
            logger.error(f"Export processing failed for {request.export_id}: {e}")
            result.status = "failed"
            result.error_message = str(e)
            result.completed_at = datetime.utcnow()
            raise

    async def _get_export_data(self, request: ExportRequest) -> Union[List[Dict], Dict]:
        """Get data for export based on type"""
        if request.export_type == ExportType.REGULATORY_REPORTS:
            return await self._get_regulatory_reports(request)
        elif request.export_type == ExportType.CASE_DATA:
            return await self._get_case_data(request)
        elif request.export_type == ExportType.RISK_ASSESSMENTS:
            return await self._get_risk_assessments(request)
        elif request.export_type == ExportType.AUDIT_TRAIL:
            return await self._get_audit_trail(request)
        elif request.export_type == ExportType.EVIDENCE:
            return await self._get_evidence(request)
        elif request.export_type == ExportType.COMPLIANCE_SUMMARY:
            return await self._get_compliance_summary(request)
        else:
            raise ValueError(f"Unsupported export type: {request.export_type}")

    async def _get_regulatory_reports(self, request: ExportRequest) -> List[Dict]:
        """Get regulatory reports data"""
        try:
            from src.api.routers.compliance import router
            
            await router.regulatory_engine.initialize()
            
            # Apply filters
            filters = request.filters or {}
            date_range = request.date_range or {}
            
            # Get reports
            reports = await router.regulatory_engine.get_reports(
                jurisdiction=filters.get("jurisdiction"),
                report_type=filters.get("report_type"),
                status=filters.get("status"),
                start_date=date_range.get("start_date"),
                end_date=date_range.get("end_date"),
                limit=filters.get("limit", 1000)
            )
            
            # Convert to export format
            export_data = []
            for report in reports:
                report_data = {
                    "report_id": report.report_id,
                    "jurisdiction": report.jurisdiction.value,
                    "report_type": report.report_type.value,
                    "status": report.status.value,
                    "entity_id": report.entity_id,
                    "entity_type": report.entity_type,
                    "submitted_by": report.submitted_by,
                    "submitted_at": report.submitted_at.isoformat() if report.submitted_at else None,
                    "created_at": report.created_at.isoformat(),
                    "updated_at": report.updated_at.isoformat() if report.updated_at else None,
                    "content": report.content if request.include_sensitive else "REDACTED"
                }
                export_data.append(report_data)
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to get regulatory reports: {e}")
            raise

    async def _get_case_data(self, request: ExportRequest) -> List[Dict]:
        """Get case data"""
        try:
            from src.api.routers.compliance import router
            
            await router.case_engine.initialize()
            
            # Apply filters
            filters = request.filters or {}
            date_range = request.date_range or {}
            
            # Get cases
            cases = await router.case_engine.get_cases(
                case_type=filters.get("case_type"),
                status=filters.get("status"),
                priority=filters.get("priority"),
                assigned_to=filters.get("assigned_to"),
                start_date=date_range.get("start_date"),
                end_date=date_range.get("end_date"),
                limit=filters.get("limit", 1000)
            )
            
            # Convert to export format
            export_data = []
            for case in cases:
                case_data = {
                    "case_id": case.case_id,
                    "title": case.title,
                    "description": case.description,
                    "case_type": case.case_type,
                    "status": case.status.value,
                    "priority": case.priority.value,
                    "assigned_to": case.assigned_to,
                    "created_by": case.created_by,
                    "created_at": case.created_at.isoformat(),
                    "updated_at": case.updated_at.isoformat() if case.updated_at else None,
                    "evidence_count": len(case.evidence) if hasattr(case, 'evidence') else 0
                }
                
                # Include evidence if requested
                if request.include_sensitive and hasattr(case, 'evidence'):
                    case_data["evidence"] = [
                        {
                            "evidence_id": ev.evidence_id,
                            "evidence_type": ev.evidence_type,
                            "description": ev.description,
                            "status": ev.status.value,
                            "collected_by": ev.collected_by,
                            "collected_at": ev.collected_at.isoformat()
                        }
                        for ev in case.evidence
                    ]
                
                export_data.append(case_data)
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to get case data: {e}")
            raise

    async def _get_risk_assessments(self, request: ExportRequest) -> List[Dict]:
        """Get risk assessment data"""
        try:
            from src.api.routers.compliance import router
            
            await router.risk_engine.initialize()
            
            # Apply filters
            filters = request.filters or {}
            date_range = request.date_range or {}
            
            # Get assessments
            assessments = await router.risk_engine.get_assessments(
                entity_id=filters.get("entity_id"),
                entity_type=filters.get("entity_type"),
                risk_level=filters.get("risk_level"),
                status=filters.get("status"),
                start_date=date_range.get("start_date"),
                end_date=date_range.get("end_date"),
                limit=filters.get("limit", 1000)
            )
            
            # Convert to export format
            export_data = []
            for assessment in assessments:
                assessment_data = {
                    "assessment_id": assessment.assessment_id,
                    "entity_id": assessment.entity_id,
                    "entity_type": assessment.entity_type,
                    "overall_score": assessment.overall_score,
                    "risk_level": assessment.risk_level.value,
                    "status": assessment.status.value,
                    "trigger_type": assessment.trigger_type.value,
                    "confidence": assessment.confidence,
                    "created_at": assessment.created_at.isoformat(),
                    "updated_at": assessment.updated_at.isoformat() if assessment.updated_at else None
                }
                
                # Include risk factors if requested
                if request.include_sensitive and hasattr(assessment, 'risk_factors'):
                    assessment_data["risk_factors"] = [
                        {
                            "factor_id": factor.factor_id,
                            "category": factor.category.value,
                            "weight": factor.weight,
                            "score": factor.score,
                            "description": factor.description,
                            "data_source": factor.data_source
                        }
                        for factor in assessment.risk_factors
                    ]
                
                export_data.append(assessment_data)
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to get risk assessments: {e}")
            raise

    async def _get_audit_trail(self, request: ExportRequest) -> List[Dict]:
        """Get audit trail data"""
        try:
            from src.api.routers.compliance import router
            
            await router.audit_engine.initialize()
            
            # Apply filters
            filters = request.filters or {}
            date_range = request.date_range or {}
            
            # Get audit events
            events = await router.audit_engine.get_events(
                event_type=filters.get("event_type"),
                severity=filters.get("severity"),
                user_id=filters.get("user_id"),
                resource_type=filters.get("resource_type"),
                start_date=date_range.get("start_date"),
                end_date=date_range.get("end_date"),
                limit=filters.get("limit", 10000)
            )
            
            # Convert to export format
            export_data = []
            for event in events:
                event_data = {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "description": event.description,
                    "severity": event.severity,
                    "user_id": event.user_id,
                    "resource_type": event.resource_type,
                    "resource_id": event.resource_id,
                    "timestamp": event.timestamp.isoformat(),
                    "ip_address": getattr(event, 'ip_address', None),
                    "user_agent": getattr(event, 'user_agent', None)
                }
                
                # Include details if requested
                if request.include_sensitive and hasattr(event, 'details'):
                    event_data["details"] = event.details
                
                export_data.append(event_data)
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            raise

    async def _get_evidence(self, request: ExportRequest) -> List[Dict]:
        """Get evidence data"""
        try:
            from src.api.routers.compliance import router
            
            await router.case_engine.initialize()
            
            # Apply filters
            filters = request.filters or {}
            
            # Get evidence
            evidence = await router.case_engine.get_evidence(
                case_id=filters.get("case_id"),
                evidence_type=filters.get("evidence_type"),
                status=filters.get("status"),
                limit=filters.get("limit", 1000)
            )
            
            # Convert to export format
            export_data = []
            for ev in evidence:
                evidence_data = {
                    "evidence_id": ev.evidence_id,
                    "case_id": ev.case_id,
                    "evidence_type": ev.evidence_type,
                    "description": ev.description,
                    "status": ev.status.value,
                    "collected_by": ev.collected_by,
                    "collected_at": ev.collected_at.isoformat(),
                    "created_at": ev.created_at.isoformat(),
                    "updated_at": ev.updated_at.isoformat() if ev.updated_at else None
                }
                
                # Include content if requested and not too large
                if request.include_sensitive and hasattr(ev, 'content'):
                    content_size = len(str(ev.content))
                    if content_size < 1000000:  # 1MB limit
                        evidence_data["content"] = ev.content
                    else:
                        evidence_data["content"] = f"CONTENT_TOO_LARGE ({content_size} bytes)"
                
                export_data.append(evidence_data)
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to get evidence: {e}")
            raise

    async def _get_compliance_summary(self, request: ExportRequest) -> Dict:
        """Get compliance summary data"""
        try:
            from src.api.routers.compliance import router
            
            await router.regulatory_engine.initialize()
            await router.case_engine.initialize()
            await router.risk_engine.initialize()
            await router.audit_engine.initialize()
            
            # Get summary statistics
            summary = {
                "period": request.date_range or {
                    "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                    "end_date": datetime.utcnow().isoformat()
                },
                "regulatory_reports": await router.regulatory_engine.get_report_statistics(),
                "cases": await router.case_engine.get_case_statistics(),
                "risk_assessments": await router.risk_engine.get_risk_summary(),
                "audit_events": await router.audit_engine.get_event_statistics(),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get compliance summary: {e}")
            raise

    async def _format_export_data(self, request: ExportRequest, data: Union[List[Dict], Dict]) -> str:
        """Format data based on requested format"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{request.export_type.value}_{timestamp}"
        
        if request.format == ExportFormat.JSON:
            return await self._export_to_json(data, filename)
        elif request.format == ExportFormat.CSV:
            return await self._export_to_csv(data, filename)
        elif request.format == ExportFormat.XML:
            return await self._export_to_xml(data, filename)
        elif request.format == ExportFormat.EXCEL:
            return await self._export_to_excel(data, filename)
        elif request.format == ExportFormat.PDF:
            return await self._export_to_pdf(data, filename)
        else:
            raise ValueError(f"Unsupported export format: {request.format}")

    async def _export_to_json(self, data: Union[List[Dict], Dict], filename: str) -> str:
        """Export data to JSON format"""
        file_path = self.export_dir / f"{filename}.json"
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            json_data = {
                "export_metadata": {
                    "exported_at": datetime.utcnow().isoformat(),
                    "record_count": len(data) if isinstance(data, list) else 1,
                    "format": "json"
                },
                "data": data
            }
            await f.write(json.dumps(json_data, indent=2, default=str))
        
        return str(file_path)

    async def _export_to_csv(self, data: Union[List[Dict], Dict], filename: str) -> str:
        """Export data to CSV format"""
        file_path = self.export_dir / f"{filename}.csv"
        
        if isinstance(data, dict):
            data = [data]
        
        if not data:
            # Create empty CSV with headers
            async with aiofiles.open(file_path, 'w', encoding='utf-8', newline='') as f:
                await f.write("No data available\n")
            return str(file_path)
        
        # Get headers from first record
        headers = set()
        for record in data:
            headers.update(record.keys())
        
        headers = sorted(list(headers))
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8', newline='') as f:
            # Write header
            await f.write(','.join(headers) + '\n')
            
            # Write data rows
            for record in data:
                row_values = []
                for header in headers:
                    value = record.get(header, '')
                    # Handle nested objects and lists
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    # Escape commas and quotes in strings
                    if isinstance(value, str):
                        value = value.replace('"', '""')
                        if ',' in value:
                            value = f'"{value}"'
                    row_values.append(str(value))
                
                await f.write(','.join(row_values) + '\n')
        
        return str(file_path)

    async def _export_to_xml(self, data: Union[List[Dict], Dict], filename: str) -> str:
        """Export data to XML format"""
        file_path = self.export_dir / f"{filename}.xml"
        
        def dict_to_xml(d, root_name="root"):
            """Convert dictionary to XML"""
            xml_parts = [f'<{root_name}>']
            
            for key, value in d.items():
                if isinstance(value, dict):
                    xml_parts.append(dict_to_xml(value, key))
                elif isinstance(value, list):
                    xml_parts.append(f'<{key}>')
                    for item in value:
                        if isinstance(item, dict):
                            xml_parts.append(dict_to_xml(item, 'item'))
                        else:
                            xml_parts.append(f'<item>{str(item)}</item>')
                    xml_parts.append(f'</{key}>')
                else:
                    xml_parts.append(f'<{key}>{str(value)}</{key}>')
            
            xml_parts.append(f'</{root_name}>')
            return ''.join(xml_parts)
        
        xml_content = dict_to_xml({
            "export_metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "record_count": len(data) if isinstance(data, list) else 1,
                "format": "xml"
            },
            "data": data
        })
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            await f.write(xml_content)
        
        return str(file_path)

    async def _export_to_excel(self, data: Union[List[Dict], Dict], filename: str) -> str:
        """Export data to Excel format"""
        file_path = self.export_dir / f"{filename}.xlsx"
        
        if isinstance(data, dict):
            data = [data]
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Save to Excel
        df.to_excel(file_path, index=False, engine='openpyxl')
        
        return str(file_path)

    async def _export_to_pdf(self, data: Union[List[Dict], Dict], filename: str) -> str:
        """Export data to PDF format"""
        file_path = self.export_dir / f"{filename}.pdf"
        
        try:
            # Import reportlab for PDF generation
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            import io
            
            # Create PDF document
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Add title
            title = Paragraph(f"Compliance Export - {filename}", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Add metadata
            metadata = [
                ["Exported At:", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")],
                ["Record Count:", str(len(data) if isinstance(data, list) else 1)],
                ["Format:", "PDF"]
            ]
            
            metadata_table = Table(metadata)
            metadata_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), '#f0f0f0'),
                ('TEXTCOLOR', (0, 0), (-1, -1), '#000000'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ]))
            story.append(metadata_table)
            story.append(Spacer(1, 12))
            
            # Add data table
            if isinstance(data, list) and data:
                # Get headers
                headers = list(data[0].keys())
                table_data = [headers]
                
                # Add data rows
                for record in data:
                    row = []
                    for header in headers:
                        value = record.get(header, '')
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value)
                        row.append(str(value))
                    table_data.append(row)
                
                # Create table
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), '#f0f0f0'),
                    ('TEXTCOLOR', (0, 0), (-1, -1), '#000000'),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, 'black'),
                ]))
                story.append(table)
            
            # Build PDF
            doc.build(story)
            
            # Save to file
            with open(file_path, 'wb') as f:
                f.write(buffer.getvalue())
            
            return str(file_path)
            
        except ImportError:
            # Fallback to text file if reportlab not available
            text_file_path = self.export_dir / f"{filename}.txt"
            async with aiofiles.open(text_file_path, 'w', encoding='utf-8') as f:
                await f.write(f"Compliance Export - {filename}\n")
                await f.write(f"Exported At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n")
                await f.write(f"Record Count: {len(data) if isinstance(data, list) else 1}\n")
                await f.write("\n" + "="*50 + "\n")
                
                if isinstance(data, list):
                    for i, record in enumerate(data, 1):
                        await f.write(f"Record {i}:\n")
                        for key, value in record.items():
                            await f.write(f"  {key}: {value}\n")
                        await f.write("\n")
                else:
                    for key, value in data.items():
                        await f.write(f"{key}: {value}\n")
            
            return str(text_file_path)

    async def _compress_export(self, file_path: str) -> str:
        """Compress export file"""
        zip_path = file_path.replace(file_path.suffix, '.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, Path(file_path).name)
        
        # Remove original file
        Path(file_path).unlink()
        
        return zip_path

    async def get_export_status(self, export_id: str) -> Optional[ExportResult]:
        """Get export status"""
        # Check active exports
        if export_id in self.active_exports:
            return self.active_exports[export_id]
        
        # Check export history
        for result in self.export_history:
            if result.export_id == export_id:
                return result
        
        return None

    async def list_exports(self, limit: int = 50) -> List[ExportResult]:
        """List recent exports"""
        # Combine active and completed exports
        all_exports = list(self.active_exports.values()) + self.export_history
        
        # Sort by creation date (newest first)
        all_exports.sort(key=lambda x: x.created_at, reverse=True)
        
        return all_exports[:limit]

    async def delete_export(self, export_id: str) -> bool:
        """Delete export file and record"""
        try:
            # Get export result
            result = await self.get_export_status(export_id)
            if not result:
                return False
            
            # Delete file if exists
            if result.file_path and Path(result.file_path).exists():
                Path(result.file_path).unlink()
            
            # Remove from active exports
            if export_id in self.active_exports:
                del self.active_exports[export_id]
            
            # Remove from history
            self.export_history = [r for r in self.export_history if r.export_id != export_id]
            
            logger.info(f"Export deleted: {export_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete export {export_id}: {e}")
            return False

    async def cleanup_old_exports(self, days: int = 30) -> int:
        """Clean up old export files"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            deleted_count = 0
            
            # Check export history
            for result in self.export_history[:]:
                if result.created_at < cutoff_date:
                    # Delete file if exists
                    if result.file_path and Path(result.file_path).exists():
                        Path(result.file_path).unlink()
                    
                    # Remove from history
                    self.export_history.remove(result)
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old exports")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old exports: {e}")
            return 0


# Global export engine instance
compliance_export_engine = ComplianceExportEngine()
