"""
Case Management and Evidence Tracking Tests

Comprehensive test suite for the case management engine including:
- Case creation and lifecycle management
- Evidence tracking with chain of custody
- Workflow steps and approval processes
- Search and filtering capabilities
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from src.compliance.case_management import (
    CaseManagementEngine,
    CaseStatus,
    CasePriority,
    CaseType,
    EvidenceType,
    EvidenceStatus,
    Evidence,
    Case,
    CaseWorkflow
)


class TestCaseManagementEngine:
    """Test suite for CaseManagementEngine"""

    @pytest.fixture
    async def engine(self):
        """Create test engine instance"""
        engine = CaseManagementEngine()
        await engine.initialize()
        yield engine
        # Cleanup if needed

    @pytest.fixture
    def sample_case_data(self):
        """Create sample case data"""
        return {
            "title": "Suspicious Transaction Investigation",
            "description": "Investigation of unusual transaction patterns detected in blockchain analysis",
            "case_type": "suspicious_activity",
            "priority": "high",
            "assigned_to": "investigator_001",
            "tags": ["suspicious", "high_value", "blockchain_analysis"],
            "metadata": {
                "initial_detection": "automated_monitoring",
                "risk_score": 0.85,
                "transaction_count": 15
            }
        }

    @pytest.fixture
    def sample_evidence_data(self):
        """Create sample evidence data"""
        return {
            "transaction_hash": "0x1234567890abcdef",
            "amount": 50000.00,
            "timestamp": "2024-01-15T10:30:00Z",
            "addresses": ["0xsender", "0xreceiver"],
            "risk_indicators": ["high_value", "rapid_movement", "new_counterparty"],
            "blockchain_data": {
                "block_number": 12345,
                "gas_used": 21000,
                "gas_price": "20 gwei"
            }
        }

    class TestCaseCreation:
        """Test case creation functionality"""

        @pytest.mark.asyncio
        async def test_create_suspicious_activity_case(self, engine, sample_case_data):
            """Test creating suspicious activity case"""
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system",
                tags=sample_case_data["tags"],
                metadata=sample_case_data["metadata"]
            )

            assert case.case_id is not None
            assert case.title == sample_case_data["title"]
            assert case.description == sample_case_data["description"]
            assert case.case_type == sample_case_data["case_type"]
            assert case.priority == CasePriority.HIGH
            assert case.assigned_to == sample_case_data["assigned_to"]
            assert case.created_by == "system"
            assert case.status == CaseStatus.OPEN
            assert case.tags == sample_case_data["tags"]
            assert case.metadata == sample_case_data["metadata"]
            assert case.created_at is not None
            assert case.updated_at is not None

        @pytest.mark.asyncio
        async def test_create_sanctions_screening_case(self, engine):
            """Test creating sanctions screening case"""
            case = await engine.create_case(
                title="Sanctions List Match",
                description="Address flagged on sanctions watchlist",
                case_type="sanctions_screening",
                priority=CasePriority.CRITICAL,
                assigned_to="compliance_officer",
                created_by="automated_system",
                tags=["sanctions", "critical", "immediate_action"]
            )

            assert case.case_type == "sanctions_screening"
            assert case.priority == CasePriority.CRITICAL
            assert case.status == CaseStatus.OPEN

        @pytest.mark.asyncio
        async def test_create_case_with_invalid_priority(self, engine, sample_case_data):
            """Test error handling for invalid priority"""
            with pytest.raises(ValueError):
                await engine.create_case(
                    title=sample_case_data["title"],
                    description=sample_case_data["description"],
                    case_type=sample_case_data["case_type"],
                    priority="invalid_priority",
                    assigned_to=sample_case_data["assigned_to"],
                    created_by="system"
                )

        @pytest.mark.asyncio
        async def test_create_case_missing_required_fields(self, engine):
            """Test error handling for missing required fields"""
            with pytest.raises(ValueError):
                await engine.create_case(
                    title="",  # Empty title
                    description="Test description",
                    case_type="suspicious_activity",
                    priority=CasePriority.MEDIUM,
                    assigned_to="investigator",
                    created_by="system"
                )

    class TestCaseRetrieval:
        """Test case retrieval functionality"""

        @pytest.mark.asyncio
        async def test_get_case_by_id(self, engine, sample_case_data):
            """Test getting case by ID"""
            # Create case
            original_case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            # Retrieve case
            retrieved_case = await engine.get_case(original_case.case_id)

            assert retrieved_case.case_id == original_case.case_id
            assert retrieved_case.title == original_case.title
            assert retrieved_case.description == original_case.description
            assert retrieved_case.status == original_case.status

        @pytest.mark.asyncio
        async def test_get_nonexistent_case(self, engine):
            """Test getting nonexistent case"""
            case = await engine.get_case("nonexistent_case_id")
            assert case is None

        @pytest.mark.asyncio
        async def test_get_cases_by_status(self, engine, sample_case_data):
            """Test getting cases by status"""
            # Create cases with different statuses
            open_case = await engine.create_case(
                title="Open Case",
                description="Test open case",
                case_type="suspicious_activity",
                priority=CasePriority.MEDIUM,
                assigned_to="investigator",
                created_by="system"
            )

            closed_case = await engine.create_case(
                title="Closed Case",
                description="Test closed case",
                case_type="sanctions_screening",
                priority=CasePriority.LOW,
                assigned_to="investigator",
                created_by="system"
            )
            await engine.update_case_status(closed_case.case_id, CaseStatus.CLOSED, "test_user")

            # Get open cases
            open_cases = await engine.get_cases_by_status(CaseStatus.OPEN)
            open_case_ids = [c.case_id for c in open_cases]
            assert open_case.case_id in open_case_ids
            assert closed_case.case_id not in open_case_ids

        @pytest.mark.asyncio
        async def test_get_cases_by_assignee(self, engine, sample_case_data):
            """Test getting cases by assignee"""
            # Create cases for different assignees
            case1 = await engine.create_case(
                title="Case 1",
                description="Test case 1",
                case_type="suspicious_activity",
                priority=CasePriority.MEDIUM,
                assigned_to="investigator_1",
                created_by="system"
            )

            case2 = await engine.create_case(
                title="Case 2",
                description="Test case 2",
                case_type="sanctions_screening",
                priority=CasePriority.HIGH,
                assigned_to="investigator_2",
                created_by="system"
            )

            # Get cases for investigator_1
            investigator1_cases = await engine.get_cases_by_assignee("investigator_1")
            case_ids = [c.case_id for c in investigator1_cases]
            assert case1.case_id in case_ids
            assert case2.case_id not in case_ids

        @pytest.mark.asyncio
        async def test_search_cases(self, engine, sample_case_data):
            """Test case search functionality"""
            # Create test cases
            await engine.create_case(
                title="Bitcoin Investigation",
                description="Investigation of Bitcoin transactions",
                case_type="suspicious_activity",
                priority=CasePriority.HIGH,
                assigned_to="investigator",
                created_by="system",
                tags=["bitcoin", "cryptocurrency"]
            )

            await engine.create_case(
                title="Ethereum Analysis",
                description="Analysis of Ethereum smart contracts",
                case_type="fraud_investigation",
                priority=CasePriority.MEDIUM,
                assigned_to="analyst",
                created_by="system",
                tags=["ethereum", "smart_contracts"]
            )

            # Search for "Bitcoin"
            bitcoin_cases = await engine.search_cases("Bitcoin")
            assert len(bitcoin_cases) == 1
            assert "Bitcoin" in bitcoin_cases[0].title

            # Search by tag
            crypto_cases = await engine.search_cases("cryptocurrency", search_tags=True)
            assert len(crypto_cases) == 1
            assert "bitcoin" in crypto_cases[0].tags

    class TestCaseStatusManagement:
        """Test case status management functionality"""

        @pytest.mark.asyncio
        async def test_update_case_status(self, engine, sample_case_data):
            """Test updating case status"""
            # Create case
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            # Update status
            updated_case = await engine.update_case_status(
                case.case_id,
                CaseStatus.IN_PROGRESS,
                updated_by="investigator",
                notes="Started investigation"
            )

            assert updated_case.status == CaseStatus.IN_PROGRESS
            assert updated_case.updated_at > case.updated_at

        @pytest.mark.asyncio
        async def test_status_transition_validation(self, engine, sample_case_data):
            """Test status transition validation"""
            # Create case
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            # Invalid transition (OPEN -> CLOSED without IN_PROGRESS)
            with pytest.raises(ValueError):
                await engine.update_case_status(
                    case.case_id,
                    CaseStatus.CLOSED,
                    updated_by="investigator"
                )

            # Valid transition
            await engine.update_case_status(
                case.case_id,
                CaseStatus.IN_PROGRESS,
                updated_by="investigator"
            )
            await engine.update_case_status(
                case.case_id,
                CaseStatus.CLOSED,
                updated_by="investigator",
                notes="Investigation completed"
            )

        @pytest.mark.asyncio
        async def test_get_case_history(self, engine, sample_case_data):
            """Test getting case status history"""
            # Create case
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            # Update status multiple times
            await engine.update_case_status(
                case.case_id,
                CaseStatus.IN_PROGRESS,
                updated_by="investigator",
                notes="Started investigation"
            )

            await engine.update_case_status(
                case.case_id,
                CaseStatus.UNDER_REVIEW,
                updated_by="supervisor",
                notes="Ready for review"
            )

            # Get history
            history = await engine.get_case_history(case.case_id)
            assert len(history) >= 2  # Initial creation + updates
            
            status_changes = [h for h in history if "status" in h]
            assert len(status_changes) == 2
            assert status_changes[0]["new_status"] == CaseStatus.IN_PROGRESS.value
            assert status_changes[1]["new_status"] == CaseStatus.UNDER_REVIEW.value

    class TestEvidenceManagement:
        """Test evidence management functionality"""

        @pytest.mark.asyncio
        async def test_add_evidence_to_case(self, engine, sample_case_data, sample_evidence_data):
            """Test adding evidence to case"""
            # Create case
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            # Add evidence
            evidence = await engine.add_evidence(
                case_id=case.case_id,
                evidence_type=EvidenceType.TRANSACTION_DATA,
                description="Suspicious transaction evidence",
                content=sample_evidence_data,
                collected_by="investigator",
                source="blockchain_analysis",
                tags=["suspicious", "high_value"]
            )

            assert evidence.evidence_id is not None
            assert evidence.case_id == case.case_id
            assert evidence.evidence_type == EvidenceType.TRANSACTION_DATA
            assert evidence.description == "Suspicious transaction evidence"
            assert evidence.content == sample_evidence_data
            assert evidence.collected_by == "investigator"
            assert evidence.source == "blockchain_analysis"
            assert evidence.status == EvidenceStatus.PENDING_REVIEW
            assert evidence.tags == ["suspicious", "high_value"]
            assert evidence.collected_at is not None

        @pytest.mark.asyncio
        async def test_add_multiple_evidence_types(self, engine, sample_case_data):
            """Test adding different types of evidence"""
            # Create case
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            # Add transaction evidence
            transaction_evidence = await engine.add_evidence(
                case_id=case.case_id,
                evidence_type=EvidenceType.TRANSACTION_DATA,
                description="Transaction records",
                content={"hash": "0x123", "amount": 1000},
                collected_by="investigator"
            )

            # Add document evidence
            document_evidence = await engine.add_evidence(
                case_id=case.case_id,
                evidence_type=EvidenceType.DOCUMENT,
                description="KYC documents",
                content={"document_type": "passport", "number": "ABC123"},
                collected_by="compliance_officer"
            )

            # Add screenshot evidence
            screenshot_evidence = await engine.add_evidence(
                case_id=case.case_id,
                evidence_type=EvidenceType.SCREENSHOT,
                description="Wallet interface screenshot",
                content={"image_url": "https://example.com/screenshot.png"},
                collected_by="investigator"
            )

            assert transaction_evidence.evidence_type == EvidenceType.TRANSACTION_DATA
            assert document_evidence.evidence_type == EvidenceType.DOCUMENT
            assert screenshot_evidence.evidence_type == EvidenceType.SCREENSHOT

        @pytest.mark.asyncio
        async def test_get_case_evidence(self, engine, sample_case_data, sample_evidence_data):
            """Test getting evidence for a case"""
            # Create case
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            # Add multiple evidence items
            evidence1 = await engine.add_evidence(
                case_id=case.case_id,
                evidence_type=EvidenceType.TRANSACTION_DATA,
                description="Evidence 1",
                content=sample_evidence_data,
                collected_by="investigator"
            )

            evidence2 = await engine.add_evidence(
                case_id=case.case_id,
                evidence_type=EvidenceType.DOCUMENT,
                description="Evidence 2",
                content={"document": "test"},
                collected_by="compliance_officer"
            )

            # Get all evidence
            all_evidence = await engine.get_case_evidence(case.case_id)
            evidence_ids = [e.evidence_id for e in all_evidence]
            assert evidence1.evidence_id in evidence_ids
            assert evidence2.evidence_id in evidence_ids
            assert len(all_evidence) == 2

        @pytest.mark.asyncio
        async def test_update_evidence_status(self, engine, sample_case_data, sample_evidence_data):
            """Test updating evidence status"""
            # Create case and evidence
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            evidence = await engine.add_evidence(
                case_id=case.case_id,
                evidence_type=EvidenceType.TRANSACTION_DATA,
                description="Test evidence",
                content=sample_evidence_data,
                collected_by="investigator"
            )

            # Update evidence status
            updated_evidence = await engine.update_evidence_status(
                evidence.evidence_id,
                EvidenceStatus.VERIFIED,
                updated_by="supervisor",
                notes="Evidence verified and authenticated"
            )

            assert updated_evidence.status == EvidenceStatus.VERIFIED
            assert updated_evidence.updated_at > evidence.updated_at

        @pytest.mark.asyncio
        async def test_evidence_chain_of_custody(self, engine, sample_case_data, sample_evidence_data):
            """Test evidence chain of custody tracking"""
            # Create case and evidence
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            evidence = await engine.add_evidence(
                case_id=case.case_id,
                evidence_type=EvidenceType.TRANSACTION_DATA,
                description="Test evidence",
                content=sample_evidence_data,
                collected_by="investigator"
            )

            # Update evidence status multiple times to track custody
            await engine.update_evidence_status(
                evidence.evidence_id,
                EvidenceStatus.UNDER_REVIEW,
                updated_by="supervisor",
                notes="Evidence under review"
            )

            await engine.update_evidence_status(
                evidence.evidence_id,
                EvidenceStatus.VERIFIED,
                updated_by="senior_analyst",
                notes="Evidence verified"
            )

            # Get chain of custody
            custody_chain = await engine.get_evidence_custody_chain(evidence.evidence_id)
            assert len(custody_chain) >= 2  # Initial collection + updates
            
            # Verify custody entries
            collection_entry = custody_chain[0]
            assert collection_entry["action"] == "collected"
            assert collection_entry["user"] == "investigator"

            review_entry = custody_chain[1]
            assert review_entry["action"] == "status_updated"
            assert review_entry["new_status"] == EvidenceStatus.UNDER_REVIEW.value

    class TestWorkflowManagement:
        """Test workflow management functionality"""

        @pytest.mark.asyncio
        async def test_create_workflow(self, engine):
            """Test creating case workflow"""
            workflow_steps = [
                "initial_review",
                "evidence_collection",
                "analysis",
                "supervisor_review",
                "final_decision"
            ]

            workflow = await engine.create_workflow(
                name="Standard Investigation Workflow",
                description="Standard workflow for suspicious activity investigations",
                case_type="suspicious_activity",
                steps=workflow_steps,
                approval_required=True,
                approvers=["supervisor", "compliance_manager"]
            )

            assert workflow.workflow_id is not None
            assert workflow.name == "Standard Investigation Workflow"
            assert workflow.case_type == "suspicious_activity"
            assert workflow.steps == workflow_steps
            assert workflow.approval_required is True
            assert workflow.approvers == ["supervisor", "compliance_manager"]

        @pytest.mark.asyncio
        async def test_advance_workflow(self, engine, sample_case_data):
            """Test advancing case workflow"""
            # Create case
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            # Create and assign workflow
            workflow_steps = ["initial_review", "evidence_collection", "analysis"]
            workflow = await engine.create_workflow(
                name="Test Workflow",
                description="Test workflow",
                case_type=sample_case_data["case_type"],
                steps=workflow_steps
            )

            # Start workflow
            await engine.start_workflow(case.case_id, workflow.workflow_id)

            # Advance workflow
            current_step = await engine.get_current_workflow_step(case.case_id)
            assert current_step == "initial_review"

            await engine.advance_workflow(
                case.case_id,
                step="evidence_collection",
                advanced_by="investigator",
                notes="Initial review completed"
            )

            current_step = await engine.get_current_workflow_step(case.case_id)
            assert current_step == "evidence_collection"

        @pytest.mark.asyncio
        async def test_workflow_approval_required(self, engine, sample_case_data):
            """Test workflow approval requirements"""
            # Create case
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            # Create workflow with approval requirement
            workflow_steps = ["analysis", "supervisor_approval", "final_decision"]
            workflow = await engine.create_workflow(
                name="Approval Workflow",
                description="Workflow requiring approval",
                case_type=sample_case_data["case_type"],
                steps=workflow_steps,
                approval_required=True,
                approvers=["supervisor"]
            )

            # Start workflow
            await engine.start_workflow(case.case_id, workflow.workflow_id)

            # Try to advance to approval step without approval
            with pytest.raises(ValueError):
                await engine.advance_workflow(
                    case.case_id,
                    step="final_decision",
                    advanced_by="investigator"
                )

            # Add approval
            await engine.add_workflow_approval(
                case.case_id,
                step="supervisor_approval",
                approved_by="supervisor",
                notes="Approved for final decision"
            )

            # Now should be able to advance
            await engine.advance_workflow(
                case.case_id,
                step="final_decision",
                advanced_by="investigator"
            )

    class TestCaseAnalytics:
        """Test case analytics and reporting"""

        @pytest.mark.asyncio
        async def test_get_case_statistics(self, engine, sample_case_data):
            """Test getting case statistics"""
            # Create test cases with different statuses and priorities
            await engine.create_case(
                title="High Priority Case",
                description="High priority investigation",
                case_type="suspicious_activity",
                priority=CasePriority.HIGH,
                assigned_to="investigator",
                created_by="system"
            )

            await engine.create_case(
                title="Medium Priority Case",
                description="Medium priority investigation",
                case_type="sanctions_screening",
                priority=CasePriority.MEDIUM,
                assigned_to="analyst",
                created_by="system"
            )

            # Get statistics
            stats = await engine.get_case_statistics()
            
            assert "total_cases" in stats
            assert "cases_by_status" in stats
            assert "cases_by_priority" in stats
            assert "cases_by_type" in stats
            assert "cases_by_assignee" in stats
            
            assert stats["total_cases"] >= 2
            assert stats["cases_by_priority"][CasePriority.HIGH.value] >= 1
            assert stats["cases_by_priority"][CasePriority.MEDIUM.value] >= 1

        @pytest.mark.asyncio
        async def test_get_evidence_statistics(self, engine, sample_case_data, sample_evidence_data):
            """Test getting evidence statistics"""
            # Create case and evidence
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            await engine.add_evidence(
                case_id=case.case_id,
                evidence_type=EvidenceType.TRANSACTION_DATA,
                description="Transaction evidence",
                content=sample_evidence_data,
                collected_by="investigator"
            )

            await engine.add_evidence(
                case_id=case.case_id,
                evidence_type=EvidenceType.DOCUMENT,
                description="Document evidence",
                content={"document": "test"},
                collected_by="compliance_officer"
            )

            # Get evidence statistics
            stats = await engine.get_evidence_statistics()
            
            assert "total_evidence" in stats
            assert "evidence_by_type" in stats
            assert "evidence_by_status" in stats
            assert "evidence_by_collector" in stats
            
            assert stats["total_evidence"] >= 2
            assert stats["evidence_by_type"][EvidenceType.TRANSACTION_DATA.value] >= 1
            assert stats["evidence_by_type"][EvidenceType.DOCUMENT.value] >= 1

    class TestErrorHandling:
        """Test error handling scenarios"""

        @pytest.mark.asyncio
        async def test_database_connection_error(self, engine):
            """Test handling of database connection errors"""
            with patch.object(engine, 'neo4j_session', None):
                with pytest.raises(Exception):
                    await engine.create_case(
                        title="Test Case",
                        description="Test description",
                        case_type="suspicious_activity",
                        priority=CasePriority.MEDIUM,
                        assigned_to="investigator",
                        created_by="system"
                    )

        @pytest.mark.asyncio
        async def test_evidence_integrity_verification(self, engine, sample_case_data, sample_evidence_data):
            """Test evidence integrity verification"""
            # Create case and evidence
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )

            evidence = await engine.add_evidence(
                case_id=case.case_id,
                evidence_type=EvidenceType.TRANSACTION_DATA,
                description="Test evidence",
                content=sample_evidence_data,
                collected_by="investigator"
            )

            # Verify integrity
            integrity_result = await engine.verify_evidence_integrity(evidence.evidence_id)
            assert integrity_result["valid"] is True
            assert integrity_result["hash"] is not None

            # Test tampered evidence
            with patch.object(engine, '_calculate_evidence_hash', return_value="tampered_hash"):
                integrity_result = await engine.verify_evidence_integrity(evidence.evidence_id)
                assert integrity_result["valid"] is False

    class TestPerformance:
        """Test performance characteristics"""

        @pytest.mark.asyncio
        async def test_bulk_case_creation(self, engine, sample_case_data):
            """Test bulk case creation performance"""
            import time
            
            start_time = time.time()
            
            # Create 10 cases concurrently
            tasks = []
            for i in range(10):
                task = engine.create_case(
                    title=f"Case {i}",
                    description=f"Test case {i}",
                    case_type="suspicious_activity",
                    priority=CasePriority.MEDIUM,
                    assigned_to="investigator",
                    created_by="system"
                )
                tasks.append(task)
            
            cases = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert len(cases) == 10
            assert duration < 5.0  # Should complete within 5 seconds
            assert all(c.status == CaseStatus.OPEN for c in cases)

        @pytest.mark.asyncio
        async def test_bulk_evidence_addition(self, engine, sample_case_data, sample_evidence_data):
            """Test bulk evidence addition performance"""
            import time
            
            # Create case
            case = await engine.create_case(
                title=sample_case_data["title"],
                description=sample_case_data["description"],
                case_type=sample_case_data["case_type"],
                priority=CasePriority.HIGH,
                assigned_to=sample_case_data["assigned_to"],
                created_by="system"
            )
            
            start_time = time.time()
            
            # Add 20 evidence items concurrently
            tasks = []
            for i in range(20):
                evidence_data = sample_evidence_data.copy()
                evidence_data["transaction_hash"] = f"0x{i:040d}"
                
                task = engine.add_evidence(
                    case_id=case.case_id,
                    evidence_type=EvidenceType.TRANSACTION_DATA,
                    description=f"Evidence {i}",
                    content=evidence_data,
                    collected_by="investigator"
                )
                tasks.append(task)
            
            evidence_items = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert len(evidence_items) == 20
            assert duration < 8.0  # Should complete within 8 seconds
            assert all(e.status == EvidenceStatus.PENDING_REVIEW for e in evidence_items)
