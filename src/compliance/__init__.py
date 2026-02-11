"""
Compliance Module

This module provides comprehensive compliance and regulatory reporting capabilities
for blockchain forensics and financial crime detection, including:

- Regulatory Reporting Integration
- Case Management and Evidence Tracking
- Audit Trail and Compliance Logging
- Automated Risk Assessment Workflows
"""

from .regulatory_reporting import (
    RegulatoryJurisdiction,
    ReportType,
    ReportStatus,
    RegulatoryRequirement,
    RegulatoryReport,
    RegulatoryReportingEngine
)

from .case_management import (
    CaseStatus,
    CasePriority,
    CaseType,
    EvidenceType,
    EvidenceStatus,
    Evidence,
    Case,
    CaseWorkflow,
    CaseManagementEngine
)

from .audit_trail import (
    AuditEventType,
    AuditSeverity,
    ComplianceCategory,
    AuditEvent,
    ComplianceLog,
    AuditReport,
    AuditTrailEngine
)

from .automated_risk_assessment import (
    RiskLevel,
    RiskCategory,
    AssessmentStatus,
    TriggerType,
    RiskThreshold,
    RiskFactor,
    RiskAssessment,
    RiskWorkflow,
    WorkflowExecution,
    AutomatedRiskAssessmentEngine
)

__all__ = [
    # Regulatory Reporting
    "RegulatoryJurisdiction",
    "ReportType", 
    "ReportStatus",
    "RegulatoryRequirement",
    "RegulatoryReport",
    "RegulatoryReportingEngine",
    
    # Case Management
    "CaseStatus",
    "CasePriority",
    "CaseType",
    "EvidenceType",
    "EvidenceStatus",
    "Evidence",
    "Case",
    "CaseWorkflow",
    "CaseManagementEngine",
    
    # Audit Trail
    "AuditEventType",
    "AuditSeverity",
    "ComplianceCategory",
    "AuditEvent",
    "ComplianceLog",
    "AuditReport",
    "AuditTrailEngine",
    
    # Risk Assessment
    "RiskLevel",
    "RiskCategory",
    "AssessmentStatus",
    "TriggerType",
    "RiskThreshold",
    "RiskFactor",
    "RiskAssessment",
    "RiskWorkflow",
    "WorkflowExecution",
    "AutomatedRiskAssessmentEngine"
]

# Version information
__version__ = "1.0.0"
__author__ = "JackdawSentry Team"
__description__ = "Comprehensive compliance and regulatory reporting module"
