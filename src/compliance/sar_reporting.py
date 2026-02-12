"""
Jackdaw Sentry - SAR Template System and Report Generation
Suspicious Activity Reporting (SAR) templates and automated report generation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from decimal import Decimal

from src.api.database import get_neo4j_session, get_redis_connection
from src.api.config import settings

logger = logging.getLogger(__name__)


class SARType(Enum):
    """SAR report types"""
    SAR = "sar"  # Suspicious Activity Report
    CTR = "ctr"  # Currency Transaction Report
    CTR_EXEMPT = "ctr_exempt"  # CTR Exemption
    CMIR = "cmir"  # Currency and Monetary Instrument Report
    FBAR = "fbar"  # Foreign Bank Account Report
    FORM_8300 = "form_8300"  # Report of Cash Payments Over $10,000
    FORM_114 = "form_114"  # Report of Foreign Bank and Financial Accounts
    CUSTOM_SAR = "custom_sar"  # Custom SAR format


class SuspiciousActivityType(Enum):
    """Types of suspicious activities"""
    MONEY_LAUNDERING = "money_laundering"
    TERRORISM_FINANCING = "terrorism_financing"
    FRAUD = "fraud"
    IDENTITY_THEFT = "identity_theft"
    CYBER_CRIME = "cyber_crime"
    TAX_EVASION = "tax_evasion"
    CORRUPTION = "corruption"
    SANCTIONS_EVASION = "sanctions_evasion"
    STRUCTURING = "structuring"
    UNUSUAL_TRANSACTIONS = "unusual_transactions"
    HIGH_RISK_CUSTOMER = "high_risk_customer"
    UNKNOWN_SUSPICIOUS = "unknown_suspicious"


class SARStatus(Enum):
    """SAR report status"""
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class RegulatoryJurisdiction(Enum):
    """Regulatory jurisdictions"""
    USA = "usa"  # FinCEN
    UK = "uk"  # FCA, NCA
    EU = "eu"  # AMLD, FIU
    CANADA = "canada"  # FINTRAC
    AUSTRALIA = "australia"  # AUSTRAC
    SINGAPORE = "singapore"  # MAS
    JAPAN = "japan"  # JFSA
    SWITZERLAND = "switzerland"  # FINMA
    HONG_KONG = "hong_kong"  # HKMA
    CUSTOM = "custom"


@dataclass
class SARField:
    """SAR template field"""
    field_id: str
    field_name: str
    field_type: str  # text, number, date, select, textarea, currency
    required: bool
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    options: List[str] = field(default_factory=list)
    default_value: Any = None
    description: str = ""
    help_text: str = ""


@dataclass
class SARTemplate:
    """SAR report template"""
    template_id: str
    template_name: str
    sar_type: SARType
    jurisdiction: RegulatoryJurisdiction
    version: str
    fields: List[SARField] = field(default_factory=list)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SARReport:
    """SAR report instance"""
    report_id: str
    template_id: str
    sar_type: SARType
    jurisdiction: RegulatoryJurisdiction
    status: SARStatus
    filing_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    submitted_date: Optional[datetime] = None
    acknowledged_date: Optional[datetime] = None
    data: Dict[str, Any] = field(default_factory=dict)
    attachments: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    reviewed_by: str = ""
    approved_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SuspiciousActivity:
    """Suspicious activity data for SAR"""
    activity_id: str
    activity_type: SuspiciousActivityType
    description: str
    amount: Optional[float] = None
    currency: str = "USD"
    date_detected: datetime = field(default_factory=datetime.utcnow)
    addresses: List[str] = field(default_factory=list)
    transactions: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SARManager:
    """SAR template and report management system"""
    
    def __init__(self):
        self.templates = {}  # SAR templates
        self.reports = {}  # SAR reports
        self.activities = {}  # Suspicious activities
        
        # Configuration
        self.default_jurisdiction = RegulatoryJurisdiction.USA
        self.auto_generate_threshold = 10000  # USD
        self.due_date_days = 30  # Days to file SAR
        self.cache_ttl = 3600  # 1 hour
        
        # Initialize templates
        self._initialize_templates()
        
        # Initialize sample data
        self._initialize_sample_data()
    
    def _initialize_templates(self):
        """Initialize SAR templates for different jurisdictions"""
        # USA FinCEN SAR Template
        us_sar_template = SARTemplate(
            template_id="us_fincen_sar_v1",
            template_name="FinCEN SAR Template",
            sar_type=SARType.SAR,
            jurisdiction=RegulatoryJurisdiction.USA,
            version="1.0",
            sections=[
                {
                    "section_id": "filing_institution",
                    "section_name": "Filing Institution Information",
                    "fields": [
                        "institution_name", "institution_address", "institution_city", 
                        "institution_state", "institution_zip", "institution_country",
                        "institution_phone", "institution_email", "contact_person"
                    ]
                },
                {
                    "section_id": "suspicious_activity",
                    "section_name": "Suspicious Activity Information",
                    "fields": [
                        "activity_type", "activity_description", "date_range_start", 
                        "date_range_end", "total_amount", "currency", "transaction_count"
                    ]
                },
                {
                    "section_id": "subject_information",
                    "section_name": "Subject Information",
                    "fields": [
                        "subject_name", "subject_address", "subject_city", "subject_state",
                        "subject_zip", "subject_country", "subject_dob", "subject_ssn",
                        "subject_identification", "subject_occupation"
                    ]
                },
                {
                    "section_id": "transaction_details",
                    "section_name": "Transaction Details",
                    "fields": [
                        "transaction_amount", "transaction_date", "transaction_method",
                        "account_numbers", "routing_numbers", "beneficiary_info"
                    ]
                },
                {
                    "section_id": "suspicious_indicators",
                    "section_name": "Suspicious Indicators",
                    "fields": [
                        "indicators", "behavioral_patterns", "transaction_patterns",
                        "red_flags", "anomalies"
                    ]
                }
            ]
        )
        
        # Add fields to template
        us_sar_template.fields = [
            SARField("institution_name", "Institution Name", "text", True),
            SARField("institution_address", "Institution Address", "text", True),
            SARField("institution_city", "Institution City", "text", True),
            SARField("institution_state", "Institution State", "select", True, {"options": ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]}),
            SARField("institution_zip", "Institution ZIP", "text", True, {"validation_rules": {"pattern": r"^\d{5}(-\d{4})?$"}}),
            SARField("institution_country", "Institution Country", "text", True),
            SARField("institution_phone", "Institution Phone", "text", True),
            SARField("institution_email", "Institution Email", "email", True),
            SARField("contact_person", "Contact Person", "text", True),
            SARField("activity_type", "Activity Type", "select", True, {"options": [t.value for t in SuspiciousActivityType]}),
            SARField("activity_description", "Activity Description", "textarea", True, {"validation_rules": {"min_length": 100}}),
            SARField("date_range_start", "Date Range Start", "date", True),
            SARField("date_range_end", "Date Range End", "date", True),
            SARField("total_amount", "Total Amount", "currency", True, {"validation_rules": {"min": 0}}),
            SARField("currency", "Currency", "select", True, {"options": ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF"], "default_value": "USD"}),
            SARField("transaction_count", "Transaction Count", "number", True, {"validation_rules": {"min": 1}}),
            SARField("subject_name", "Subject Name", "text", False),
            SARField("subject_address", "Subject Address", "text", False),
            SARField("subject_city", "Subject City", "text", False),
            SARField("subject_state", "Subject State", "select", False, {"options": ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]}),
            SARField("subject_zip", "Subject ZIP", "text", False),
            SARField("subject_country", "Subject Country", "text", False),
            SARField("subject_dob", "Subject Date of Birth", "date", False),
            SARField("subject_ssn", "Subject SSN", "text", False, {"validation_rules": {"pattern": r"^\d{3}-\d{2}-\d{4}$"}}),
            SARField("subject_identification", "Subject Identification", "text", False),
            SARField("subject_occupation", "Subject Occupation", "text", False),
            SARField("transaction_amount", "Transaction Amount", "currency", False),
            SARField("transaction_date", "Transaction Date", "date", False),
            SARField("transaction_method", "Transaction Method", "select", False, {"options": ["cash", "wire", "ach", "check", "crypto", "other"]}),
            SARField("account_numbers", "Account Numbers", "text", False),
            SARField("routing_numbers", "Routing Numbers", "text", False),
            SARField("beneficiary_info", "Beneficiary Information", "textarea", False),
            SARField("indicators", "Indicators", "textarea", False),
            SARField("behavioral_patterns", "Behavioral Patterns", "textarea", False),
            SARField("transaction_patterns", "Transaction Patterns", "textarea", False),
            SARField("red_flags", "Red Flags", "textarea", False),
            SARField("anomalies", "Anomalies", "textarea", False)
        ]
        
        # UK FCA SAR Template
        uk_sar_template = SARTemplate(
            template_id="uk_fca_sar_v1",
            template_name="UK FCA SAR Template",
            sar_type=SARType.SAR,
            jurisdiction=RegulatoryJurisdiction.UK,
            version="1.0",
            sections=[
                {
                    "section_id": "firm_details",
                    "section_name": "Firm Details",
                    "fields": ["firm_name", "firm_address", "firm_postcode", "firm_phone", "firm_email"]
                },
                {
                    "section_id": "suspicious_activity",
                    "section_name": "Suspicious Activity",
                    "fields": ["activity_type", "activity_description", "date_range", "amount_gbp"]
                },
                {
                    "section_id": "subject_details",
                    "section_name": "Subject Details",
                    "fields": ["subject_name", "subject_address", "subject_dob", "subject_identification"]
                }
            ]
        )
        
        # Add UK template fields
        uk_sar_template.fields = [
            SARField("firm_name", "Firm Name", "text", True),
            SARField("firm_address", "Firm Address", "text", True),
            SARField("firm_postcode", "Firm Postcode", "text", True),
            SARField("firm_phone", "Firm Phone", "text", True),
            SARField("firm_email", "Firm Email", "email", True),
            SARField("activity_type", "Activity Type", "select", True, {"options": [t.value for t in SuspiciousActivityType]}),
            SARField("activity_description", "Activity Description", "textarea", True),
            SARField("date_range", "Date Range", "text", True),
            SARField("amount_gbp", "Amount (GBP)", "currency", True),
            SARField("subject_name", "Subject Name", "text", False),
            SARField("subject_address", "Subject Address", "text", False),
            SARField("subject_dob", "Subject Date of Birth", "date", False),
            SARField("subject_identification", "Subject Identification", "text", False)
        ]
        
        # Store templates
        self.templates[us_sar_template.template_id] = us_sar_template
        self.templates[uk_sar_template.template_id] = uk_sar_template
    
    def _initialize_sample_data(self):
        """Initialize with sample SAR data"""
        # Sample suspicious activities
        sample_activities = [
            {
                'activity_id': 'ACT-001',
                'activity_type': SuspiciousActivityType.MONEY_LAUNDERING,
                'description': 'Multiple high-value transactions with no apparent business purpose',
                'amount': 50000.0,
                'currency': 'USD',
                'addresses': ['1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'],
                'transactions': ['tx_001', 'tx_002', 'tx_003'],
                'evidence': ['pattern_analysis', 'high_frequency', 'round_amounts'],
                'risk_score': 0.85,
                'confidence': 0.9
            },
            {
                'activity_id': 'ACT-002',
                'activity_type': SuspiciousActivityType.STRUCTURING,
                'description': 'Multiple transactions just below reporting threshold',
                'amount': 9500.0,
                'currency': 'USD',
                'addresses': ['1B1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb'],
                'transactions': ['tx_004', 'tx_005', 'tx_006', 'tx_007'],
                'evidence': ['structuring_pattern', 'threshold_avoidance'],
                'risk_score': 0.75,
                'confidence': 0.8
            }
        ]
        
        # Load sample activities
        for activity_data in sample_activities:
            activity = SuspiciousActivity(**activity_data)
            self.activities[activity.activity_id] = activity
    
    async def create_sar_report(self, template_id: str, activity_ids: List[str], additional_data: Dict[str, Any] = None) -> SARReport:
        """Create a new SAR report"""
        try:
            # Validate template
            if template_id not in self.templates:
                raise ValueError(f"Template {template_id} not found")
            
            template = self.templates[template_id]
            
            # Get activities
            activities = []
            for activity_id in activity_ids:
                if activity_id in self.activities:
                    activities.append(self.activities[activity_id])
            
            if not activities:
                raise ValueError("No valid activities found")
            
            # Calculate due date
            due_date = datetime.now(timezone.utc) + timedelta(days=self.due_date_days)
            
            # Auto-populate fields from activities
            auto_data = await self._auto_populate_fields(activities, template)
            
            # Merge with additional data
            report_data = {**auto_data, **(additional_data or {})}
            
            # Create report
            report_id = str(uuid.uuid4())
            report = SARReport(
                report_id=report_id,
                template_id=template_id,
                sar_type=template.sar_type,
                jurisdiction=template.jurisdiction,
                status=SARStatus.DRAFT,
                due_date=due_date,
                data=report_data,
                metadata={
                    'activity_ids': activity_ids,
                    'auto_generated': True,
                    'total_amount': sum(activity.amount for activity in activities if activity.amount),
                    'activity_types': [activity.activity_type.value for activity in activities]
                }
            )
            
            # Store report
            self.reports[report_id] = report
            
            # Cache update
            await self.cache_sar_data()
            
            return report
            
        except Exception as e:
            logger.error(f"Error creating SAR report: {e}")
            raise
    
    async def _auto_populate_fields(self, activities: List[SuspiciousActivity], template: SARTemplate) -> Dict[str, Any]:
        """Auto-populate SAR fields from activities"""
        auto_data = {}
        
        # Calculate total amount
        total_amount = sum(activity.amount for activity in activities if activity.amount)
        if total_amount > 0:
            auto_data['total_amount'] = total_amount
            auto_data['currency'] = activities[0].currency if activities else 'USD'
        
        # Set date range
        dates = [activity.date_detected for activity in activities]
        if dates:
            auto_data['date_range_start'] = min(dates).isoformat()
            auto_data['date_range_end'] = max(dates).isoformat()
        
        # Set transaction count
        total_transactions = sum(len(activity.transactions) for activity in activities)
        if total_transactions > 0:
            auto_data['transaction_count'] = total_transactions
        
        # Combine activity descriptions
        descriptions = [activity.description for activity in activities]
        if descriptions:
            auto_data['activity_description'] = ' | '.join(descriptions)
        
        # Set activity types
        activity_types = list(set(activity.activity_type.value for activity in activities))
        if activity_types:
            auto_data['activity_type'] = activity_types[0] if len(activity_types) == 1 else 'multiple'
        
        # Combine evidence
        all_evidence = []
        for activity in activities:
            all_evidence.extend(activity.evidence)
        if all_evidence:
            auto_data['indicators'] = ', '.join(all_evidence)
        
        # Set high-risk indicators
        high_risk_activities = [activity for activity in activities if activity.risk_score > 0.7]
        if high_risk_activities:
            auto_data['red_flags'] = f"High risk activities detected (risk scores: {[round(a.risk_score, 2) for a in high_risk_activities]})"
        
        return auto_data
    
    async def update_sar_report(self, report_id: str, data: Dict[str, Any], status: SARStatus = None) -> SARReport:
        """Update an existing SAR report"""
        try:
            if report_id not in self.reports:
                raise ValueError(f"Report {report_id} not found")
            
            report = self.reports[report_id]
            
            # Update data
            if data:
                report.data.update(data)
            
            # Update status
            if status:
                report.status = status
                if status == SARStatus.SUBMITTED:
                    report.submitted_date = datetime.now(timezone.utc)
                elif status == SARStatus.APPROVED:
                    report.approved_by = "system"  # Would be actual user
                elif status == SARStatus.ACKNOWLEDGED:
                    report.acknowledged_date = datetime.now(timezone.utc)
            
            report.updated_at = datetime.now(timezone.utc)
            
            # Cache update
            await self.cache_sar_data()
            
            return report
            
        except Exception as e:
            logger.error(f"Error updating SAR report {report_id}: {e}")
            raise
    
    async def validate_sar_report(self, report_id: str) -> Dict[str, Any]:
        """Validate SAR report against template requirements"""
        try:
            if report_id not in self.reports:
                return {'valid': False, 'errors': ['Report not found']}
            
            report = self.reports[report_id]
            template = self.templates[report.template_id]
            
            errors = []
            warnings = []
            
            # Validate required fields
            for field in template.fields:
                if field.required:
                    if field.field_id not in report.data or not report.data[field.field_id]:
                        errors.append(f"Required field '{field.field_name}' is missing")
                    else:
                        # Validate field type and rules
                        field_errors = await self._validate_field(field, report.data[field.field_id])
                        errors.extend(field_errors)
            
            # Validate business rules
            if 'date_range_start' in report.data and 'date_range_end' in report.data:
                start_date = datetime.fromisoformat(report.data['date_range_start'])
                end_date = datetime.fromisoformat(report.data['date_range_end'])
                if start_date > end_date:
                    errors.append("Date range start cannot be after end date")
            
            # Check for warnings
            if 'total_amount' in report.data and report.data['total_amount'] > 100000:
                warnings.append("High amount transaction detected")
            
            if 'transaction_count' in report.data and report.data['transaction_count'] > 100:
                warnings.append("High transaction count detected")
            
            is_valid = len(errors) == 0
            
            return {
                'valid': is_valid,
                'errors': errors,
                'warnings': warnings,
                'validation_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error validating SAR report {report_id}: {e}")
            return {'valid': False, 'errors': [str(e)]}
    
    async def _validate_field(self, field: SARField, value: Any) -> List[str]:
        """Validate individual field"""
        errors = []
        
        try:
            # Type validation
            if field.field_type == 'email':
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, value):
                    errors.append(f"Invalid email format for {field.field_name}")
            
            elif field.field_type == 'number':
                try:
                    num_value = float(value)
                    if 'min' in field.validation_rules and num_value < field.validation_rules['min']:
                        errors.append(f"Value for {field.field_name} is below minimum")
                    if 'max' in field.validation_rules and num_value > field.validation_rules['max']:
                        errors.append(f"Value for {field.field_name} is above maximum")
                except (ValueError, TypeError):
                    errors.append(f"Invalid number format for {field.field_name}")
            
            elif field.field_type == 'date':
                try:
                    datetime.fromisoformat(value)
                except (ValueError, TypeError):
                    errors.append(f"Invalid date format for {field.field_name}")
            
            elif field.field_type == 'currency':
                try:
                    Decimal(str(value))
                    if 'min' in field.validation_rules and Decimal(str(value)) < Decimal(str(field.validation_rules['min'])):
                        errors.append(f"Currency value for {field.field_name} is below minimum")
                except (ValueError, TypeError):
                    errors.append(f"Invalid currency format for {field.field_name}")
            
            # Pattern validation
            if 'pattern' in field.validation_rules:
                import re
                if not re.match(field.validation_rules['pattern'], str(value)):
                    errors.append(f"Value for {field.field_name} does not match required pattern")
            
            # Length validation
            if 'min_length' in field.validation_rules and len(str(value)) < field.validation_rules['min_length']:
                errors.append(f"Value for {field.field_name} is too short")
            
        except Exception as e:
            errors.append(f"Validation error for {field.field_name}: {str(e)}")
        
        return errors
    
    async def generate_sar_report_pdf(self, report_id: str) -> bytes:
        """Generate PDF version of SAR report"""
        try:
            if report_id not in self.reports:
                raise ValueError(f"Report {report_id} not found")
            
            report = self.reports[report_id]
            template = self.templates[report.template_id]
            
            # This would generate a PDF using a library like ReportLab or WeasyPrint
            # For now, return a placeholder
            pdf_content = f"SAR Report PDF for {report_id}".encode()
            
            return pdf_content
            
        except Exception as e:
            logger.error(f"Error generating PDF for SAR report {report_id}: {e}")
            raise
    
    async def submit_sar_report(self, report_id: str, submission_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Submit SAR report to regulatory authority"""
        try:
            # Validate report first
            validation = await self.validate_sar_report(report_id)
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors'],
                    'warnings': validation['warnings']
                }
            
            # Update report status
            report = await self.update_sar_report(report_id, submission_data or {}, SARStatus.SUBMITTED)
            
            # This would integrate with actual regulatory submission APIs
            # For now, simulate submission
            submission_result = {
                'success': True,
                'submission_id': f"SUB-{datetime.now(timezone.utc).timestamp()}",
                'submitted_at': datetime.now(timezone.utc).isoformat(),
                'report_id': report_id,
                'jurisdiction': report.jurisdiction.value,
                'confirmation_number': f"CONF-{uuid.uuid4().hex[:8].upper()}"
            }
            
            # Update report with submission info
            report.metadata.update(submission_result)
            
            return submission_result
            
        except Exception as e:
            logger.error(f"Error submitting SAR report {report_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_sar_statistics(self, time_range: int = 30) -> Dict[str, Any]:
        """Get SAR reporting statistics"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=time_range)
            
            # Filter reports by date range
            recent_reports = [report for report in self.reports.values() if report.created_at >= cutoff_date]
            
            # Calculate statistics
            total_reports = len(recent_reports)
            submitted_reports = len([r for r in recent_reports if r.status == SARStatus.SUBMITTED])
            approved_reports = len([r for r in recent_reports if r.status == SARStatus.APPROVED])
            
            # Status breakdown
            status_breakdown = {}
            for report in recent_reports:
                status = report.status.value
                status_breakdown[status] = status_breakdown.get(status, 0) + 1
            
            # Jurisdiction breakdown
            jurisdiction_breakdown = {}
            for report in recent_reports:
                jurisdiction = report.jurisdiction.value
                jurisdiction_breakdown[jurisdiction] = jurisdiction_breakdown.get(jurisdiction, 0) + 1
            
            # SAR type breakdown
            sar_type_breakdown = {}
            for report in recent_reports:
                sar_type = report.sar_type.value
                sar_type_breakdown[sar_type] = sar_type_breakdown.get(sar_type, 0) + 1
            
            # Average processing time
            processing_times = []
            for report in recent_reports:
                if report.submitted_date:
                    processing_time = (report.submitted_date - report.created_at).days
                    processing_times.append(processing_time)
            
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            return {
                'time_range_days': time_range,
                'total_reports': total_reports,
                'submitted_reports': submitted_reports,
                'approved_reports': approved_reports,
                'submission_rate': (submitted_reports / total_reports * 100) if total_reports > 0 else 0,
                'approval_rate': (approved_reports / submitted_reports * 100) if submitted_reports > 0 else 0,
                'status_breakdown': status_breakdown,
                'jurisdiction_breakdown': jurisdiction_breakdown,
                'sar_type_breakdown': sar_type_breakdown,
                'average_processing_days': avg_processing_time,
                'statistics_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting SAR statistics: {e}")
            return {'error': str(e)}
    
    async def cache_sar_data(self):
        """Cache SAR data in Redis"""
        try:
            async with get_redis_connection() as redis:
                # Cache statistics
                stats = {
                    'total_templates': len(self.templates),
                    'total_reports': len(self.reports),
                    'total_activities': len(self.activities),
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                await redis.setex("sar_stats", self.cache_ttl, json.dumps(stats))
                
                # Cache report counts by status
                status_counts = {}
                for report in self.reports.values():
                    status = report.status.value
                    status_counts[status] = status_counts.get(status, 0) + 1
                await redis.setex("sar_status_counts", self.cache_ttl, json.dumps(status_counts))
                
        except Exception as e:
            logger.error(f"Error caching SAR data: {e}")
    
    async def get_cached_sar_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached SAR data from Redis"""
        try:
            async with get_redis_connection() as redis:
                cached = await redis.get(cache_key)
                return json.loads(cached) if cached else None
        except Exception as e:
            logger.error(f"Error getting cached SAR data: {e}")
            return None


# Global SAR manager instance
_sar_manager: Optional[SARManager] = None


def get_sar_manager() -> SARManager:
    """Get global SAR manager instance"""
    global _sar_manager
    if _sar_manager is None:
        _sar_manager = SARManager()
    return _sar_manager
