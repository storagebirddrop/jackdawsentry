"""
Jackdaw Sentry - Case Management and Evidence Tracking
Comprehensive case management system with evidence tracking
Chain of custody, evidence integrity, and investigation workflow
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
import json
import hashlib
from enum import Enum

from src.api.database import get_neo4j_session, get_redis_connection
from src.api.config import settings

logger = logging.getLogger(__name__)


class CaseStatus(Enum):
    """Case status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    PENDING_APPROVAL = "pending_approval"
    CLOSED = "closed"
    ARCHIVED = "archived"
    REOPENED = "reopened"


class CasePriority(Enum):
    """Case priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"


class CaseType(Enum):
    """Case types"""
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    MONEY_LAUNDERING = "money_laundering"
    TERRORISM_FINANCING = "terrorism_financing"
    FRAUD = "fraud"
    SANCTIONS_VIOLATION = "sanctions_violation"
    REGULATORY_REPORTING = "regulatory_reporting"
    INTERNAL_AUDIT = "internal_audit"
    EXTERNAL_REQUEST = "external_request"


class EvidenceType(Enum):
    """Evidence types"""
    TRANSACTION_DATA = "transaction_data"
    ADDRESS_ANALYSIS = "address_analysis"
    BLOCKCHAIN_DATA = "blockchain_data"
    SCREENING_RESULTS = "screening_results"
    DOCUMENTS = "documents"
    COMMUNICATIONS = "communications"
    EXTERNAL_REPORTS = "external_reports"
    ANALYTICS_OUTPUT = "analytics_output"
    USER_TESTIMONY = "user_testimony"
    SYSTEM_LOGS = "system_logs"


class EvidenceStatus(Enum):
    """Evidence status"""
    COLLECTED = "collected"
    PROCESSING = "processing"
    VERIFIED = "verified"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass
class Evidence:
    """Evidence item"""
    evidence_id: str
    case_id: str
    evidence_type: EvidenceType
    title: str
    description: str
    source: str
    collected_by: str
    collected_at: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: EvidenceStatus = EvidenceStatus.COLLECTED
    chain_of_custody: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    verified_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    
    def calculate_hash(self) -> str:
        """Calculate evidence hash for integrity"""
        evidence_str = json.dumps({
            'evidence_id': self.evidence_id,
            'case_id': self.case_id,
            'evidence_type': self.evidence_type.value,
            'title': self.title,
            'description': self.description,
            'source': self.source,
            'data': self.data,
            'collected_at': self.collected_at.isoformat()
        }, sort_keys=True)
        return hashlib.sha256(evidence_str.encode()).hexdigest()


@dataclass
class Case:
    """Investigation case"""
    case_id: str
    title: str
    description: str
    case_type: CaseType
    priority: CasePriority
    status: CaseStatus
    assigned_to: str
    created_by: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # Case details
    targets: List[str] = field(default_factory=list)  # Addresses, entities, etc.
    risk_score: float = 0.0
    regulatory_jurisdictions: List[str] = field(default_factory=list)
    related_cases: List[str] = field(default_factory=list)
    
    # Workflow
    workflow_steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    approvals: List[Dict[str, Any]] = field(default_factory=list)
    
    # Evidence
    evidence_count: int = 0
    key_evidence: List[str] = field(default_factory=list)
    
    # Reporting
    reports_generated: List[str] = field(default_factory=list)
    external_references: List[str] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CaseWorkflow:
    """Case workflow definition"""
    workflow_id: str
    name: str
    description: str
    case_type: CaseType
    steps: List[Dict[str, Any]] = field(default_factory=list)
    required_approvals: List[str] = field(default_factory=list)
    auto_assign: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class CaseManagementEngine:
    """Case management and evidence tracking engine"""
    
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour
        self.workflows_cache = {}
        
        # Initialize workflows
        self._initialize_workflows()
    
    def _initialize_workflows(self):
        """Initialize case workflows"""
        self.workflows_cache = {
            CaseType.SUSPICIOUS_ACTIVITY: CaseWorkflow(
                workflow_id="suspicious_activity_workflow",
                name="Suspicious Activity Investigation",
                description="Standard workflow for suspicious activity cases",
                case_type=CaseType.SUSPICIOUS_ACTIVITY,
                steps=[
                    {
                        'step_id': 1,
                        'name': 'Initial Assessment',
                        'description': 'Assess initial suspicious activity indicators',
                        'estimated_duration': timedelta(hours=4),
                        'required_evidence': ['transaction_data', 'screening_results'],
                        'actions': ['risk_assessment', 'pattern_analysis']
                    },
                    {
                        'step_id': 2,
                        'name': 'Evidence Collection',
                        'description': 'Collect and verify all relevant evidence',
                        'estimated_duration': timedelta(days=2),
                        'required_evidence': ['transaction_data', 'address_analysis', 'blockchain_data'],
                        'actions': ['data_collection', 'evidence_verification']
                    },
                    {
                        'step_id': 3,
                        'name': 'Investigation',
                        'description': 'Conduct detailed investigation',
                        'estimated_duration': timedelta(days=5),
                        'required_evidence': ['analytics_output', 'external_reports'],
                        'actions': ['deep_analysis', 'external_correlation']
                    },
                    {
                        'step_id': 4,
                        'name': 'Review and Decision',
                        'description': 'Review findings and make determination',
                        'estimated_duration': timedelta(days=1),
                        'required_evidence': ['user_testimony', 'system_logs'],
                        'actions': ['final_review', 'decision_making']
                    },
                    {
                        'step_id': 5,
                        'name': 'Reporting',
                        'description': 'Generate and submit required reports',
                        'estimated_duration': timedelta(days=2),
                        'required_evidence': ['documents'],
                        'actions': ['report_generation', 'regulatory_submission']
                    }
                ],
                required_approvals=['compliance_manager', 'legal_counsel'],
                auto_assign=True
            ),
            
            CaseType.MONEY_LAUNDERING: CaseWorkflow(
                workflow_id="money_laundering_workflow",
                name="Money Laundering Investigation",
                description="Enhanced workflow for money laundering cases",
                case_type=CaseType.MONEY_LAUNDERING,
                steps=[
                    {
                        'step_id': 1,
                        'name': 'ML Pattern Detection',
                        'description': 'Identify money laundering patterns',
                        'estimated_duration': timedelta(hours=8),
                        'required_evidence': ['transaction_data', 'analytics_output'],
                        'actions': ['ml_pattern_analysis', 'flow_tracing']
                    },
                    {
                        'step_id': 2,
                        'name': 'Source of Funds Investigation',
                        'description': 'Investigate source of funds',
                        'estimated_duration': timedelta(days=3),
                        'required_evidence': ['address_analysis', 'external_reports'],
                        'actions': ['source_tracing', 'entity_analysis']
                    },
                    {
                        'step_id': 3,
                        'name': 'Beneficiary Identification',
                        'description': 'Identify ultimate beneficiaries',
                        'estimated_duration': timedelta(days=4),
                        'required_evidence': ['blockchain_data', 'communications'],
                        'actions': ['beneficiary_analysis', 'network_mapping']
                    },
                    {
                        'step_id': 4,
                        'name': 'Regulatory Reporting',
                        'description': 'Prepare SAR and other regulatory reports',
                        'estimated_duration': timedelta(days=3),
                        'required_evidence': ['documents', 'system_logs'],
                        'actions': ['sar_preparation', 'regulatory_filing']
                    },
                    {
                        'step_id': 5,
                        'name': 'Law Enforcement Coordination',
                        'description': 'Coordinate with law enforcement if needed',
                        'estimated_duration': timedelta(days=2),
                        'required_evidence': ['external_reports', 'user_testimony'],
                        'actions': ['le_coordination', 'evidence_sharing']
                    }
                ],
                required_approvals=['compliance_manager', 'legal_counsel', 'senior_management'],
                auto_assign=True
            )
        }
    
    async def create_case(self, 
                         title: str,
                         description: str,
                         case_type: CaseType,
                         priority: CasePriority,
                         assigned_to: str,
                         created_by: str,
                         targets: List[str] = None,
                         due_date: datetime = None,
                         metadata: Dict[str, Any] = None) -> Case:
        """Create new investigation case"""
        try:
            case_id = f"case_{datetime.now(timezone.utc).timestamp()}"
            
            # Get workflow for case type
            workflow = self.workflows_cache.get(case_type)
            if not workflow:
                workflow = self._get_default_workflow(case_type)
            
            # Calculate due date if not provided
            if not due_date:
                total_duration = sum((step.get('estimated_duration', timedelta(days=1)) for step in workflow.steps), timedelta())
                due_date = datetime.now(timezone.utc) + total_duration
            
            # Create case
            case = Case(
                case_id=case_id,
                title=title,
                description=description,
                case_type=case_type,
                priority=priority,
                status=CaseStatus.OPEN,
                assigned_to=assigned_to,
                created_by=created_by,
                due_date=due_date,
                targets=targets or [],
                workflow_steps=workflow.steps,
                metadata=metadata or {}
            )
            
            # Store case
            await self._store_case(case)
            
            logger.info(f"Created case {case_id}: {title}")
            
            return case
            
        except Exception as e:
            logger.error(f"Failed to create case: {e}")
            raise
    
    async def add_evidence(self, 
                          case_id: str,
                          evidence_type: EvidenceType,
                          title: str,
                          description: str,
                          source: str,
                          collected_by: str,
                          data: Dict[str, Any] = None,
                          file_path: str = None,
                          tags: List[str] = None) -> Evidence:
        """Add evidence to case"""
        try:
            evidence_id = f"ev_{datetime.now(timezone.utc).timestamp()}"
            
            # Create evidence
            evidence = Evidence(
                evidence_id=evidence_id,
                case_id=case_id,
                evidence_type=evidence_type,
                title=title,
                description=description,
                source=source,
                collected_by=collected_by,
                collected_at=datetime.now(timezone.utc),
                data=data or {},
                file_path=file_path,
                tags=tags or []
            )
            
            # Calculate hash for integrity
            evidence.file_hash = evidence.calculate_hash()
            
            # Initialize chain of custody
            evidence.chain_of_custody.append({
                'action': 'collected',
                'performed_by': collected_by,
                'timestamp': evidence.collected_at.isoformat(),
                'location': 'system',
                'hash': evidence.file_hash,
                'notes': 'Evidence initially collected'
            })
            
            # Store evidence
            await self._store_evidence(evidence)
            
            # Update case evidence count
            await self._update_case_evidence_count(case_id)
            
            logger.info(f"Added evidence {evidence_id} to case {case_id}")
            
            return evidence
            
        except Exception as e:
            logger.error(f"Failed to add evidence: {e}")
            raise
    
    async def update_case_status(self, case_id: str, new_status: CaseStatus, updated_by: str, notes: str = None) -> bool:
        """Update case status"""
        try:
            case = await self._get_case(case_id)
            if not case:
                raise ValueError(f"Case {case_id} not found")
            
            old_status = case.status
            case.status = new_status
            case.updated_at = datetime.now(timezone.utc)
            
            # Add status change to notes
            status_note = f"Status changed from {old_status.value} to {new_status.value} by {updated_by}"
            if notes:
                status_note += f": {notes}"
            case.notes.append(status_note)
            
            # Handle special status transitions
            if new_status == CaseStatus.CLOSED:
                case.closed_at = datetime.now(timezone.utc)
            elif new_status == CaseStatus.REOPENED and case.closed_at:
                case.closed_at = None
            
            # Store updated case
            await self._store_case(case)
            
            logger.info(f"Updated case {case_id} status to {new_status.value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update case status: {e}")
            return False
    
    async def advance_case_workflow(self, case_id: str, advanced_by: str, notes: str = None) -> Dict[str, Any]:
        """Advance case to next workflow step"""
        try:
            case = await self._get_case(case_id)
            if not case:
                raise ValueError(f"Case {case_id} not found")
            
            workflow = self.workflows_cache.get(case.case_type)
            if not workflow:
                raise ValueError(f"No workflow found for case type {case.case_type.value}")
            
            current_step_index = case.current_step
            if current_step_index >= len(workflow.steps):
                return {
                    'success': False,
                    'message': 'Case is already at final step'
                }
            
            current_step = workflow.steps[current_step_index]
            next_step_index = current_step_index + 1
            
            # Check if current step is complete
            required_evidence = current_step.get('required_evidence', [])
            case_evidence = await self._get_case_evidence(case_id)
            
            missing_evidence = []
            for req_evidence in required_evidence:
                if not any(ev.evidence_type.value == req_evidence for ev in case_evidence):
                    missing_evidence.append(req_evidence)
            
            if missing_evidence:
                return {
                    'success': False,
                    'message': f'Missing required evidence: {", ".join(missing_evidence)}',
                    'current_step': current_step,
                    'missing_evidence': missing_evidence
                }
            
            # Advance to next step
            case.current_step = next_step_index
            case.updated_at = datetime.now(timezone.utc)
            
            # Add workflow advancement note
            advancement_note = f"Advanced from step {current_step_index} ({current_step['name']}) by {advanced_by}"
            if notes:
                advancement_note += f": {notes}"
            case.notes.append(advancement_note)
            
            # Store updated case
            await self._store_case(case)
            
            # Return next step info or completion
            if next_step_index < len(workflow.steps):
                next_step = workflow.steps[next_step_index]
                return {
                    'success': True,
                    'message': f'Advanced to step {next_step_index}: {next_step["name"]}',
                    'current_step': next_step_index,
                    'next_step': next_step,
                    'total_steps': len(workflow.steps)
                }
            else:
                # Workflow complete
                await self.update_case_status(case_id, CaseStatus.PENDING_APPROVAL, advanced_by, "Workflow completed")
                return {
                    'success': True,
                    'message': 'Workflow completed - case ready for approval',
                    'current_step': next_step_index,
                    'total_steps': len(workflow.steps),
                    'workflow_complete': True
                }
            
        except Exception as e:
            logger.error(f"Failed to advance case workflow: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_case_summary(self, case_id: str) -> Dict[str, Any]:
        """Get comprehensive case summary"""
        try:
            case = await self._get_case(case_id)
            if not case:
                raise ValueError(f"Case {case_id} not found")
            
            # Get case evidence
            evidence = await self._get_case_evidence(case_id)
            
            # Get workflow progress
            workflow = self.workflows_cache.get(case.case_type)
            workflow_progress = None
            if workflow:
                workflow_progress = {
                    'current_step': case.current_step,
                    'total_steps': len(workflow.steps),
                    'current_step_name': workflow.steps[case.current_step]['name'] if case.current_step < len(workflow.steps) else 'Completed',
                    'progress_percentage': (case.current_step / len(workflow.steps)) * 100 if workflow.steps else 0
                }
            
            # Calculate case metrics
            metrics = {
                'evidence_count': len(evidence),
                'evidence_by_type': {},
                'days_open': (datetime.now(timezone.utc) - case.created_at).days,
                'days_until_due': (case.due_date - datetime.now(timezone.utc)).days if case.due_date else None,
                'overdue': case.due_date and datetime.now(timezone.utc) > case.due_date
            }
            
            # Evidence by type
            for ev in evidence:
                ev_type = ev.evidence_type.value
                metrics['evidence_by_type'][ev_type] = metrics['evidence_by_type'].get(ev_type, 0) + 1
            
            return {
                'case': {
                    'case_id': case.case_id,
                    'title': case.title,
                    'description': case.description,
                    'case_type': case.case_type.value,
                    'priority': case.priority.value,
                    'status': case.status.value,
                    'assigned_to': case.assigned_to,
                    'created_by': case.created_by,
                    'created_at': case.created_at.isoformat(),
                    'updated_at': case.updated_at.isoformat(),
                    'due_date': case.due_date.isoformat() if case.due_date else None,
                    'closed_at': case.closed_at.isoformat() if case.closed_at else None,
                    'targets': case.targets,
                    'risk_score': case.risk_score,
                    'tags': case.tags,
                    'notes_count': len(case.notes)
                },
                'workflow': workflow_progress,
                'evidence': {
                    'total_count': len(evidence),
                    'by_type': metrics['evidence_by_type'],
                    'recent_evidence': [
                        {
                            'evidence_id': ev.evidence_id,
                            'title': ev.title,
                            'type': ev.evidence_type.value,
                            'collected_at': ev.collected_at.isoformat(),
                            'status': ev.status.value
                        }
                        for ev in sorted(evidence, key=lambda x: x.collected_at, reverse=True)[:5]
                    ]
                },
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to get case summary: {e}")
            raise
    
    async def search_cases(self, 
                          status: CaseStatus = None,
                          case_type: CaseType = None,
                          priority: CasePriority = None,
                          assigned_to: str = None,
                          tags: List[str] = None,
                          date_range: tuple = None,
                          limit: int = 50) -> List[Case]:
        """Search cases with filters"""
        try:
            # Get all cases (in production, this would use proper database queries)
            all_cases = await self._get_all_cases()
            
            filtered_cases = []
            for case in all_cases:
                # Apply filters
                if status and case.status != status:
                    continue
                if case_type and case.case_type != case_type:
                    continue
                if priority and case.priority != priority:
                    continue
                if assigned_to and case.assigned_to != assigned_to:
                    continue
                if tags and not any(tag in case.tags for tag in tags):
                    continue
                if date_range:
                    start_date, end_date = date_range
                    if case.created_at < start_date or case.created_at > end_date:
                        continue
                
                filtered_cases.append(case)
            
            # Sort by priority and creation date
            priority_order = {CasePriority.URGENT: 0, CasePriority.CRITICAL: 1, CasePriority.HIGH: 2, CasePriority.MEDIUM: 3, CasePriority.LOW: 4}
            filtered_cases.sort(key=lambda x: (priority_order.get(x.priority, 5), x.created_at), reverse=True)
            
            return filtered_cases[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search cases: {e}")
            return []
    
    def _get_default_workflow(self, case_type: CaseType) -> CaseWorkflow:
        """Get default workflow for case type"""
        return CaseWorkflow(
            workflow_id=f"default_{case_type.value}_workflow",
            name=f"Default {case_type.value.replace('_', ' ').title()} Workflow",
            description="Default workflow for case investigation",
            case_type=case_type,
            steps=[
                {
                    'step_id': 1,
                    'name': 'Initial Review',
                    'description': 'Initial case review and assessment',
                    'estimated_duration': timedelta(days=1),
                    'required_evidence': [],
                    'actions': ['initial_review']
                },
                {
                    'step_id': 2,
                    'name': 'Investigation',
                    'description': 'Conduct investigation',
                    'estimated_duration': timedelta(days=3),
                    'required_evidence': [],
                    'actions': ['investigation']
                },
                {
                    'step_id': 3,
                    'name': 'Resolution',
                    'description': 'Resolve case',
                    'estimated_duration': timedelta(days=1),
                    'required_evidence': [],
                    'actions': ['resolution']
                }
            ],
            required_approvals=['case_manager'],
            auto_assign=False
        )
    
    async def _store_case(self, case: Case):
        """Store case in database"""
        try:
            async with get_neo4j_session() as session:
                query = """
                MERGE (c:Case {case_id: $case_id})
                SET c.title = $title,
                    c.description = $description,
                    c.case_type = $case_type,
                    c.priority = $priority,
                    c.status = $status,
                    c.assigned_to = $assigned_to,
                    c.created_by = $created_by,
                    c.created_at = $created_at,
                    c.updated_at = $updated_at,
                    c.due_date = $due_date,
                    c.closed_at = $closed_at,
                    c.targets = $targets,
                    c.risk_score = $risk_score,
                    c.regulatory_jurisdictions = $regulatory_jurisdictions,
                    c.related_cases = $related_cases,
                    c.workflow_steps = $workflow_steps,
                    c.current_step = $current_step,
                    c.approvals = $approvals,
                    c.evidence_count = $evidence_count,
                    c.key_evidence = $key_evidence,
                    c.reports_generated = $reports_generated,
                    c.external_references = $external_references,
                    c.tags = $tags,
                    c.notes = $notes,
                    c.metadata = $metadata
                """
                await session.run(query, {
                    'case_id': case.case_id,
                    'title': case.title,
                    'description': case.description,
                    'case_type': case.case_type.value,
                    'priority': case.priority.value,
                    'status': case.status.value,
                    'assigned_to': case.assigned_to,
                    'created_by': case.created_by,
                    'created_at': case.created_at.isoformat(),
                    'updated_at': case.updated_at.isoformat(),
                    'due_date': case.due_date.isoformat() if case.due_date else None,
                    'closed_at': case.closed_at.isoformat() if case.closed_at else None,
                    'targets': case.targets,
                    'risk_score': case.risk_score,
                    'regulatory_jurisdictions': case.regulatory_jurisdictions,
                    'related_cases': case.related_cases,
                    'workflow_steps': json.dumps(case.workflow_steps),
                    'current_step': case.current_step,
                    'approvals': json.dumps(case.approvals),
                    'evidence_count': case.evidence_count,
                    'key_evidence': case.key_evidence,
                    'reports_generated': case.reports_generated,
                    'external_references': case.external_references,
                    'tags': case.tags,
                    'notes': case.notes,
                    'metadata': json.dumps(case.metadata)
                })
        except Exception as e:
            logger.error(f"Failed to store case: {e}")
            raise
    
    async def _get_case(self, case_id: str) -> Optional[Case]:
        """Get case from database"""
        try:
            async with get_neo4j_session() as session:
                query = "MATCH (c:Case {case_id: $case_id}) RETURN c"
                result = await session.run(query, {'case_id': case_id})
                record = await result.single()
                
                if record:
                    data = record['c']
                    return Case(
                        case_id=data['case_id'],
                        title=data['title'],
                        description=data['description'],
                        case_type=CaseType(data['case_type']),
                        priority=CasePriority(data['priority']),
                        status=CaseStatus(data['status']),
                        assigned_to=data['assigned_to'],
                        created_by=data['created_by'],
                        created_at=datetime.fromisoformat(data['created_at']),
                        updated_at=datetime.fromisoformat(data['updated_at']),
                        due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
                        closed_at=datetime.fromisoformat(data['closed_at']) if data.get('closed_at') else None,
                        targets=data.get('targets', []),
                        risk_score=data.get('risk_score', 0.0),
                        regulatory_jurisdictions=data.get('regulatory_jurisdictions', []),
                        related_cases=data.get('related_cases', []),
                        workflow_steps=json.loads(data.get('workflow_steps', '[]')),
                        current_step=data.get('current_step', 0),
                        approvals=json.loads(data.get('approvals', '[]')),
                        evidence_count=data.get('evidence_count', 0),
                        key_evidence=data.get('key_evidence', []),
                        reports_generated=data.get('reports_generated', []),
                        external_references=data.get('external_references', []),
                        tags=data.get('tags', []),
                        notes=data.get('notes', []),
                        metadata=json.loads(data.get('metadata', '{}'))
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get case: {e}")
            return None
    
    async def _get_all_cases(self) -> List[Case]:
        """Get all cases from database"""
        try:
            async with get_neo4j_session() as session:
                query = "MATCH (c:Case) RETURN c ORDER BY c.created_at DESC"
                result = await session.run(query)
                records = await result.data()
                
                cases = []
                for record in records:
                    data = record['c']
                    case = Case(
                        case_id=data['case_id'],
                        title=data['title'],
                        description=data['description'],
                        case_type=CaseType(data['case_type']),
                        priority=CasePriority(data['priority']),
                        status=CaseStatus(data['status']),
                        assigned_to=data['assigned_to'],
                        created_by=data['created_by'],
                        created_at=datetime.fromisoformat(data['created_at']),
                        updated_at=datetime.fromisoformat(data['updated_at']),
                        due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
                        closed_at=datetime.fromisoformat(data['closed_at']) if data.get('closed_at') else None,
                        targets=data.get('targets', []),
                        risk_score=data.get('risk_score', 0.0),
                        regulatory_jurisdictions=data.get('regulatory_jurisdictions', []),
                        related_cases=data.get('related_cases', []),
                        workflow_steps=json.loads(data.get('workflow_steps', '[]')),
                        current_step=data.get('current_step', 0),
                        approvals=json.loads(data.get('approvals', '[]')),
                        evidence_count=data.get('evidence_count', 0),
                        key_evidence=data.get('key_evidence', []),
                        reports_generated=data.get('reports_generated', []),
                        external_references=data.get('external_references', []),
                        tags=data.get('tags', []),
                        notes=data.get('notes', []),
                        metadata=json.loads(data.get('metadata', '{}'))
                    )
                    cases.append(case)
                
                return cases
        except Exception as e:
            logger.error(f"Failed to get all cases: {e}")
            return []
    
    async def _store_evidence(self, evidence: Evidence):
        """Store evidence in database"""
        try:
            async with get_neo4j_session() as session:
                query = """
                MERGE (e:Evidence {evidence_id: $evidence_id})
                SET e.case_id = $case_id,
                    e.evidence_type = $evidence_type,
                    e.title = $title,
                    e.description = $description,
                    e.source = $source,
                    e.collected_by = $collected_by,
                    e.collected_at = $collected_at,
                    e.data = $data,
                    e.file_path = $file_path,
                    e.file_hash = $file_hash,
                    e.metadata = $metadata,
                    e.status = $status,
                    e.chain_of_custody = $chain_of_custody,
                    e.tags = $tags,
                    e.verified_at = $verified_at,
                    e.archived_at = $archived_at
                """
                await session.run(query, {
                    'evidence_id': evidence.evidence_id,
                    'case_id': evidence.case_id,
                    'evidence_type': evidence.evidence_type.value,
                    'title': evidence.title,
                    'description': evidence.description,
                    'source': evidence.source,
                    'collected_by': evidence.collected_by,
                    'collected_at': evidence.collected_at.isoformat(),
                    'data': json.dumps(evidence.data),
                    'file_path': evidence.file_path,
                    'file_hash': evidence.file_hash,
                    'metadata': json.dumps(evidence.metadata),
                    'status': evidence.status.value,
                    'chain_of_custody': json.dumps(evidence.chain_of_custody),
                    'tags': evidence.tags,
                    'verified_at': evidence.verified_at.isoformat() if evidence.verified_at else None,
                    'archived_at': evidence.archived_at.isoformat() if evidence.archived_at else None
                })
        except Exception as e:
            logger.error(f"Failed to store evidence: {e}")
            raise
    
    async def _get_case_evidence(self, case_id: str) -> List[Evidence]:
        """Get all evidence for a case"""
        try:
            async with get_neo4j_session() as session:
                query = "MATCH (e:Evidence {case_id: $case_id}) RETURN e ORDER BY e.collected_at DESC"
                result = await session.run(query, {'case_id': case_id})
                records = await result.data()
                
                evidence_list = []
                for record in records:
                    data = record['e']
                    evidence = Evidence(
                        evidence_id=data['evidence_id'],
                        case_id=data['case_id'],
                        evidence_type=EvidenceType(data['evidence_type']),
                        title=data['title'],
                        description=data['description'],
                        source=data['source'],
                        collected_by=data['collected_by'],
                        collected_at=datetime.fromisoformat(data['collected_at']),
                        data=json.loads(data.get('data', '{}')),
                        file_path=data.get('file_path'),
                        file_hash=data.get('file_hash'),
                        metadata=json.loads(data.get('metadata', '{}')),
                        status=EvidenceStatus(data.get('status', 'collected')),
                        chain_of_custody=json.loads(data.get('chain_of_custody', '[]')),
                        tags=data.get('tags', []),
                        verified_at=datetime.fromisoformat(data['verified_at']) if data.get('verified_at') else None,
                        archived_at=datetime.fromisoformat(data['archived_at']) if data.get('archived_at') else None
                    )
                    evidence_list.append(evidence)
                
                return evidence_list
        except Exception as e:
            logger.error(f"Failed to get case evidence: {e}")
            return []
    
    async def _update_case_evidence_count(self, case_id: str):
        """Update case evidence count"""
        try:
            evidence = await self._get_case_evidence(case_id)
            evidence_count = len(evidence)
            
            async with get_neo4j_session() as session:
                query = """
                MATCH (c:Case {case_id: $case_id})
                SET c.evidence_count = $evidence_count,
                    c.updated_at = $updated_at
                """
                await session.run(query, {
                    'case_id': case_id,
                    'evidence_count': evidence_count,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            logger.error(f"Failed to update case evidence count: {e}")


# Global case management engine instance
_case_management_engine: Optional[CaseManagementEngine] = None


def get_case_management_engine() -> CaseManagementEngine:
    """Get global case management engine instance"""
    global _case_management_engine
    if _case_management_engine is None:
        _case_management_engine = CaseManagementEngine()
    return _case_management_engine
