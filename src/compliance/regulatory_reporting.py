"""
Jackdaw Sentry - Regulatory Reporting Integration
Comprehensive regulatory reporting system for multiple jurisdictions
Automated report generation, submission, and tracking
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import aiohttp
import json
from enum import Enum

from src.api.database import get_neo4j_session, get_redis_connection
from src.api.config import settings

logger = logging.getLogger(__name__)


class RegulatoryJurisdiction(Enum):
    """Regulatory jurisdictions"""
    USA_FINCEN = "usa_fincen"
    USA_SEC = "usa_sec"
    USA_CFTC = "usa_cftc"
    UK_FCA = "uk_fca"
    EU_AML = "eu_aml"
    SINGAPORE_MAS = "singapore_mas"
    JAPAN_FSA = "japan_fsa"
    AUSTRALIA_AUSTRAC = "australia_austrac"
    CANADA_FINTRAC = "canada_fintrac"
    HONG_KONG_SFC = "hong_kong_sfc"


class ReportType(Enum):
    """Regulatory report types"""
    SAR = "sar"  # Suspicious Activity Report
    CTR = "ctr"  # Currency Transaction Report
    EBA = "eba"  # Electronic Banking Alert
    AML = "aml"  # Anti-Money Laundering Report
    CTF = "ctf"  # Counter-Terrorism Financing Report
    SANCTIONS = "sanctions"  # Sanctions Screening Report
    RISK_ASSESSMENT = "risk_assessment"  # Risk Assessment Report
    COMPLIANCE_AUDIT = "compliance_audit"  # Compliance Audit Report


class ReportStatus(Enum):
    """Report status"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    REJECTED = "rejected"
    RESUBMITTED = "resubmitted"


@dataclass
class RegulatoryRequirement:
    """Regulatory requirement"""
    jurisdiction: RegulatoryJurisdiction
    report_type: ReportType
    filing_deadline: timedelta  # Time from trigger to filing deadline
    required_fields: List[str] = field(default_factory=list)
    format_requirements: Dict[str, Any] = field(default_factory=dict)
    submission_methods: List[str] = field(default_factory=list)
    contact_info: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegulatoryReport:
    """Regulatory report"""
    report_id: str
    jurisdiction: RegulatoryJurisdiction
    report_type: ReportType
    status: ReportStatus
    case_id: str
    triggered_by: str  # Transaction, address, or pattern that triggered the report
    filing_deadline: datetime
    submission_deadline: datetime
    report_data: Dict[str, Any] = field(default_factory=dict)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    submission_history: List[Dict[str, Any]] = field(default_factory=list)
    reviewer_comments: List[str] = field(default_factory=list)
    external_reference: Optional[str] = None  # Reference number from regulatory body
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RegulatoryReportingEngine:
    """Regulatory reporting engine"""
    
    def __init__(self):
        self.session = None
        self.cache_ttl = 3600  # 1 hour
        self.requirements_cache = {}
        self.report_templates = {}
        
        # Initialize regulatory requirements
        self._initialize_regulatory_requirements()
        self._initialize_report_templates()
    
    def _initialize_regulatory_requirements(self):
        """Initialize regulatory requirements by jurisdiction"""
        self.requirements_cache = {
            # USA FINCEN Requirements
            RegulatoryJurisdiction.USA_FINCEN: {
                ReportType.SAR: RegulatoryRequirement(
                    jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                    report_type=ReportType.SAR,
                    filing_deadline=timedelta(days=30),
                    required_fields=[
                        'suspicious_activity_details',
                        'transaction_amount',
                        'date_range',
                        'involved_parties',
                        'suspicion_reasons'
                    ],
                    format_requirements={
                        'format': 'electronic',
                        'max_file_size': '10MB',
                        'accepted_formats': ['PDF', 'XML']
                    },
                    submission_methods=['electronic_filing', 'secure_upload'],
                    contact_info={
                        'phone': '1-800-767-2825',
                        'email': 'fincen@fincen.gov',
                        'website': 'https://www.fincen.gov'
                    }
                ),
                ReportType.CTR: RegulatoryRequirement(
                    jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                    report_type=ReportType.CTR,
                    filing_deadline=timedelta(days=15),
                    required_fields=[
                        'transaction_amount',
                        'transaction_date',
                        'customer_information',
                        'business_type'
                    ],
                    format_requirements={
                        'format': 'electronic',
                        'max_file_size': '5MB',
                        'accepted_formats': ['PDF', 'CSV']
                    },
                    submission_methods=['electronic_filing'],
                    contact_info={
                        'phone': '1-800-767-2825',
                        'email': 'fincen@fincen.gov'
                    }
                )
            },
            
            # UK FCA Requirements
            RegulatoryJurisdiction.UK_FCA: {
                ReportType.SAR: RegulatoryRequirement(
                    jurisdiction=RegulatoryJurisdiction.UK_FCA,
                    report_type=ReportType.SAR,
                    filing_deadline=timedelta(days=7),  # UK has shorter deadline
                    required_fields=[
                        'suspicious_activity_details',
                        'transaction_amount',
                        'date_range',
                        'involved_parties',
                        'suspicion_reasons',
                        'narrative_description'
                    ],
                    format_requirements={
                        'format': 'electronic',
                        'max_file_size': '20MB',
                        'accepted_formats': ['PDF', 'DOC', 'DOCX']
                    },
                    submission_methods=['online_portal', 'secure_email'],
                    contact_info={
                        'phone': '+44 20 7066 9200',
                        'email': 'sart@fca.org.uk',
                        'website': 'https://www.fca.org.uk'
                    }
                )
            },
            
            # Singapore MAS Requirements
            RegulatoryJurisdiction.SINGAPORE_MAS: {
                ReportType.SAR: RegulatoryRequirement(
                    jurisdiction=RegulatoryJurisdiction.SINGAPORE_MAS,
                    report_type=ReportType.SAR,
                    filing_deadline=timedelta(days=14),
                    required_fields=[
                        'suspicious_activity_details',
                        'transaction_amount',
                        'date_range',
                        'involved_parties',
                        'suspicion_reasons',
                        'local_context'
                    ],
                    format_requirements={
                        'format': 'electronic',
                        'max_file_size': '15MB',
                        'accepted_formats': ['PDF', 'XML']
                    },
                    submission_methods=['online_portal'],
                    contact_info={
                        'phone': '+65 6595 5765',
                        'email': 'suspicious_transactions@mas.gov.sg',
                        'website': 'https://www.mas.gov.sg'
                    }
                )
            }
        }
    
    def _initialize_report_templates(self):
        """Initialize report templates"""
        self.report_templates = {
            'usa_fincen_sar': {
                'sections': [
                    'reporting_institution',
                    'suspicious_activity',
                    'transaction_details',
                    'involved_parties',
                    'suspicion_narrative'
                ],
                'required_fields': [
                    'institution_name',
                    'institution_address',
                    'suspicion_reasons',
                    'transaction_amount',
                    'transaction_dates',
                    'involved_addresses'
                ]
            },
            'uk_fca_sar': {
                'sections': [
                    'reporting_entity',
                    'suspicious_activity',
                    'transaction_information',
                    'client_information',
                    'detailed_narrative'
                ],
                'required_fields': [
                    'entity_name',
                    'entity_registration',
                    'suspicion_details',
                    'transaction_amounts',
                    'client_details'
                ]
            }
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def create_regulatory_report(self, 
                                    jurisdiction: RegulatoryJurisdiction,
                                    report_type: ReportType,
                                    case_id: str,
                                    triggered_by: str,
                                    report_data: Dict[str, Any]) -> RegulatoryReport:
        """Create regulatory report"""
        try:
            report_id = f"reg_{jurisdiction.value}_{report_type.value}_{datetime.utcnow().timestamp()}"
            
            # Get regulatory requirements
            requirement = self._get_regulatory_requirement(jurisdiction, report_type)
            if not requirement:
                raise ValueError(f"No requirements found for {jurisdiction.value} {report_type.value}")
            
            # Calculate deadlines
            triggered_time = datetime.utcnow()
            filing_deadline = triggered_time + requirement.filing_deadline
            submission_deadline = filing_deadline + timedelta(days=1)  # Buffer for submission
            
            # Validate report data
            validation_result = await self._validate_report_data(report_data, requirement)
            if not validation_result['valid']:
                raise ValueError(f"Report data validation failed: {validation_result['errors']}")
            
            # Create report
            report = RegulatoryReport(
                report_id=report_id,
                jurisdiction=jurisdiction,
                report_type=report_type,
                status=ReportStatus.DRAFT,
                case_id=case_id,
                triggered_by=triggered_by,
                filing_deadline=filing_deadline,
                submission_deadline=submission_deadline,
                report_data=report_data,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Store report
            await self._store_report(report)
            
            logger.info(f"Created regulatory report {report_id} for {jurisdiction.value} {report_type.value}")
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to create regulatory report: {e}")
            raise
    
    async def submit_report(self, report_id: str, submitter_id: str) -> Dict[str, Any]:
        """Submit regulatory report"""
        try:
            # Get report
            report = await self._get_report(report_id)
            if not report:
                raise ValueError(f"Report {report_id} not found")
            
            # Validate report is ready for submission
            if report.status not in [ReportStatus.DRAFT, ReportStatus.REJECTED]:
                raise ValueError(f"Report {report_id} is not ready for submission")
            
            # Get submission requirements
            requirement = self._get_regulatory_requirement(report.jurisdiction, report.report_type)
            
            # Format report for submission
            formatted_report = await self._format_report_for_submission(report, requirement)
            
            # Submit to regulatory body
            submission_result = await self._submit_to_regulatory_body(
                report.jurisdiction,
                report.report_type,
                formatted_report,
                requirement
            )
            
            if submission_result['success']:
                # Update report status
                report.status = ReportStatus.SUBMITTED
                report.submitted_at = datetime.utcnow()
                report.updated_at = datetime.utcnow()
                report.external_reference = submission_result.get('reference_number')
                
                # Add to submission history
                report.submission_history.append({
                    'submitted_at': report.submitted_at.isoformat(),
                    'submitter_id': submitter_id,
                    'method': submission_result.get('method'),
                    'reference_number': submission_result.get('reference_number'),
                    'status': 'submitted'
                })
                
                # Store updated report
                await self._store_report(report)
                
                logger.info(f"Successfully submitted report {report_id} to {report.jurisdiction.value}")
                
                return {
                    'success': True,
                    'report_id': report_id,
                    'reference_number': submission_result.get('reference_number'),
                    'submitted_at': report.submitted_at.isoformat(),
                    'next_deadline': report.filing_deadline.isoformat()
                }
            else:
                raise Exception(f"Submission failed: {submission_result.get('error')}")
            
        except Exception as e:
            logger.error(f"Failed to submit report {report_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'report_id': report_id
            }
    
    async def check_report_status(self, report_id: str) -> Dict[str, Any]:
        """Check report status with regulatory body"""
        try:
            report = await self._get_report(report_id)
            if not report:
                raise ValueError(f"Report {report_id} not found")
            
            if not report.external_reference:
                return {
                    'report_id': report_id,
                    'status': report.status.value,
                    'message': 'No external reference available'
                }
            
            # Check with regulatory body
            status_result = await self._check_regulatory_status(
                report.jurisdiction,
                report.external_reference
            )
            
            if status_result['success']:
                # Update report status if changed
                new_status = self._map_regulatory_status(status_result['status'])
                if new_status != report.status:
                    old_status = report.status
                    report.status = new_status
                    report.updated_at = datetime.utcnow()
                    
                    # Add to submission history
                    report.submission_history.append({
                        'updated_at': report.updated_at.isoformat(),
                        'old_status': old_status.value,
                        'new_status': new_status.value,
                        'regulatory_status': status_result['status']
                    })
                    
                    await self._store_report(report)
                
                return {
                    'report_id': report_id,
                    'status': report.status.value,
                    'regulatory_status': status_result['status'],
                    'last_updated': report.updated_at.isoformat(),
                    'next_action': self._get_next_action(report.status)
                }
            else:
                return {
                    'report_id': report_id,
                    'status': report.status.value,
                    'error': status_result.get('error')
                }
            
        except Exception as e:
            logger.error(f"Failed to check report status {report_id}: {e}")
            return {
                'report_id': report_id,
                'error': str(e)
            }
    
    async def get_upcoming_deadlines(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get upcoming filing deadlines"""
        try:
            cutoff_date = datetime.utcnow() + timedelta(days=days_ahead)
            
            # Get all reports
            all_reports = await self._get_all_reports()
            
            upcoming_deadlines = []
            for report in all_reports:
                if report.status in [ReportStatus.DRAFT, ReportStatus.PENDING_REVIEW]:
                    if report.filing_deadline <= cutoff_date:
                        days_remaining = (report.filing_deadline - datetime.utcnow()).days
                        urgency = 'high' if days_remaining <= 7 else 'medium' if days_remaining <= 14 else 'low'
                        
                        upcoming_deadlines.append({
                            'report_id': report.report_id,
                            'jurisdiction': report.jurisdiction.value,
                            'report_type': report.report_type.value,
                            'filing_deadline': report.filing_deadline.isoformat(),
                            'days_remaining': days_remaining,
                            'urgency': urgency,
                            'status': report.status.value,
                            'case_id': report.case_id
                        })
            
            # Sort by urgency and deadline
            upcoming_deadlines.sort(key=lambda x: (x['urgency'], x['days_remaining']))
            
            return upcoming_deadlines
            
        except Exception as e:
            logger.error(f"Failed to get upcoming deadlines: {e}")
            return []
    
    def _get_regulatory_requirement(self, jurisdiction: RegulatoryJurisdiction, report_type: ReportType) -> Optional[RegulatoryRequirement]:
        """Get regulatory requirement"""
        jurisdiction_requirements = self.requirements_cache.get(jurisdiction, {})
        return jurisdiction_requirements.get(report_type)
    
    async def _validate_report_data(self, report_data: Dict[str, Any], requirement: RegulatoryRequirement) -> Dict[str, Any]:
        """Validate report data against requirements"""
        errors = []
        warnings = []
        
        # Check required fields
        for field in requirement.required_fields:
            if field not in report_data or not report_data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Check format requirements
        format_reqs = requirement.format_requirements
        if 'max_file_size' in format_reqs:
            # Simulate file size check
            pass
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    async def _format_report_for_submission(self, report: RegulatoryReport, requirement: RegulatoryRequirement) -> Dict[str, Any]:
        """Format report for submission"""
        template_key = f"{report.jurisdiction.value}_{report.report_type.value}"
        template = self.report_templates.get(template_key)
        
        if template:
            # Use template to format report
            formatted_data = {}
            for section in template['sections']:
                formatted_data[section] = report.report_data.get(section, {})
            
            return formatted_data
        else:
            # Return raw data if no template
            return report.report_data
    
    async def _submit_to_regulatory_body(self, 
                                       jurisdiction: RegulatoryJurisdiction,
                                       report_type: ReportType,
                                       formatted_report: Dict[str, Any],
                                       requirement: RegulatoryRequirement) -> Dict[str, Any]:
        """Submit report to regulatory body"""
        try:
            # Simulate submission to regulatory body
            # In production, this would integrate with actual regulatory APIs
            
            submission_methods = requirement.submission_methods
            preferred_method = submission_methods[0] if submission_methods else 'electronic_filing'
            
            # Simulate successful submission
            reference_number = f"{jurisdiction.value.upper()}-{datetime.utcnow().strftime('%Y%m%d')}-{int(datetime.utcnow().timestamp())}"
            
            return {
                'success': True,
                'method': preferred_method,
                'reference_number': reference_number,
                'submitted_at': datetime.utcnow().isoformat(),
                'acknowledged_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Regulatory submission failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _check_regulatory_status(self, jurisdiction: RegulatoryJurisdiction, reference_number: str) -> Dict[str, Any]:
        """Check status with regulatory body"""
        try:
            # Simulate status check
            # In production, this would integrate with actual regulatory APIs
            
            # Simulate different statuses
            statuses = ['acknowledged', 'under_review', 'completed']
            current_status = statuses[datetime.utcnow().second % len(statuses)]
            
            return {
                'success': True,
                'status': current_status,
                'last_updated': datetime.utcnow().isoformat(),
                'next_action': None
            }
            
        except Exception as e:
            logger.error(f"Regulatory status check failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _map_regulatory_status(self, regulatory_status: str) -> ReportStatus:
        """Map regulatory status to internal status"""
        status_mapping = {
            'acknowledged': ReportStatus.ACKNOWLEDGED,
            'under_review': ReportStatus.UNDER_REVIEW,
            'completed': ReportStatus.COMPLETED,
            'rejected': ReportStatus.REJECTED
        }
        return status_mapping.get(regulatory_status, ReportStatus.SUBMITTED)
    
    def _get_next_action(self, status: ReportStatus) -> Optional[str]:
        """Get next action based on status"""
        action_mapping = {
            ReportStatus.DRAFT: 'Complete report and submit for review',
            ReportStatus.PENDING_REVIEW: 'Awaiting internal review',
            ReportStatus.SUBMITTED: 'Awaiting regulatory acknowledgment',
            ReportStatus.ACKNOWLEDGED: 'Regulatory body has acknowledged receipt',
            ReportStatus.UNDER_REVIEW: 'Regulatory body is reviewing the report',
            ReportStatus.COMPLETED: 'Report processing completed',
            ReportStatus.REJECTED: 'Review and resubmit report',
            ReportStatus.RESUBMITTED: 'Resubmitted report under review'
        }
        return action_mapping.get(status)
    
    async def _store_report(self, report: RegulatoryReport):
        """Store report in database"""
        try:
            async with get_neo4j_session() as session:
                query = """
                MERGE (r:RegulatoryReport {report_id: $report_id})
                SET r.jurisdiction = $jurisdiction,
                    r.report_type = $report_type,
                    r.status = $status,
                    r.case_id = $case_id,
                    r.triggered_by = $triggered_by,
                    r.filing_deadline = $filing_deadline,
                    r.submission_deadline = $submission_deadline,
                    r.report_data = $report_data,
                    r.external_reference = $external_reference,
                    r.created_at = $created_at,
                    r.updated_at = $updated_at,
                    r.submitted_at = $submitted_at,
                    r.completed_at = $completed_at
                """
                await session.run(query, {
                    'report_id': report.report_id,
                    'jurisdiction': report.jurisdiction.value,
                    'report_type': report.report_type.value,
                    'status': report.status.value,
                    'case_id': report.case_id,
                    'triggered_by': report.triggered_by,
                    'filing_deadline': report.filing_deadline.isoformat(),
                    'submission_deadline': report.submission_deadline.isoformat(),
                    'report_data': json.dumps(report.report_data),
                    'external_reference': report.external_reference,
                    'created_at': report.created_at.isoformat(),
                    'updated_at': report.updated_at.isoformat(),
                    'submitted_at': report.submitted_at.isoformat() if report.submitted_at else None,
                    'completed_at': report.completed_at.isoformat() if report.completed_at else None
                })
        except Exception as e:
            logger.error(f"Failed to store report: {e}")
            raise
    
    async def _get_report(self, report_id: str) -> Optional[RegulatoryReport]:
        """Get report from database"""
        try:
            async with get_neo4j_session() as session:
                query = """
                MATCH (r:RegulatoryReport {report_id: $report_id})
                RETURN r
                """
                result = await session.run(query, {'report_id': report_id})
                record = await result.single()
                
                if record:
                    data = record['r']
                    return RegulatoryReport(
                        report_id=data['report_id'],
                        jurisdiction=RegulatoryJurisdiction(data['jurisdiction']),
                        report_type=ReportType(data['report_type']),
                        status=ReportStatus(data['status']),
                        case_id=data['case_id'],
                        triggered_by=data['triggered_by'],
                        filing_deadline=datetime.fromisoformat(data['filing_deadline']),
                        submission_deadline=datetime.fromisoformat(data['submission_deadline']),
                        report_data=json.loads(data['report_data']),
                        external_reference=data.get('external_reference'),
                        created_at=datetime.fromisoformat(data['created_at']),
                        updated_at=datetime.fromisoformat(data['updated_at']),
                        submitted_at=datetime.fromisoformat(data['submitted_at']) if data.get('submitted_at') else None,
                        completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get report: {e}")
            return None
    
    async def _get_all_reports(self) -> List[RegulatoryReport]:
        """Get all reports from database"""
        try:
            async with get_neo4j_session() as session:
                query = "MATCH (r:RegulatoryReport) RETURN r ORDER BY r.created_at DESC"
                result = await session.run(query)
                records = await result.data()
                
                reports = []
                for record in records:
                    data = record['r']
                    report = RegulatoryReport(
                        report_id=data['report_id'],
                        jurisdiction=RegulatoryJurisdiction(data['jurisdiction']),
                        report_type=ReportType(data['report_type']),
                        status=ReportStatus(data['status']),
                        case_id=data['case_id'],
                        triggered_by=data['triggered_by'],
                        filing_deadline=datetime.fromisoformat(data['filing_deadline']),
                        submission_deadline=datetime.fromisoformat(data['submission_deadline']),
                        report_data=json.loads(data['report_data']),
                        external_reference=data.get('external_reference'),
                        created_at=datetime.fromisoformat(data['created_at']),
                        updated_at=datetime.fromisoformat(data['updated_at']),
                        submitted_at=datetime.fromisoformat(data['submitted_at']) if data.get('submitted_at') else None,
                        completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None
                    )
                    reports.append(report)
                
                return reports
        except Exception as e:
            logger.error(f"Failed to get all reports: {e}")
            return []


# Global regulatory reporting engine instance
_regulatory_reporting_engine: Optional[RegulatoryReportingEngine] = None


def get_regulatory_reporting_engine() -> RegulatoryReportingEngine:
    """Get global regulatory reporting engine instance"""
    global _regulatory_reporting_engine
    if _regulatory_reporting_engine is None:
        _regulatory_reporting_engine = RegulatoryReportingEngine()
    return _regulatory_reporting_engine
