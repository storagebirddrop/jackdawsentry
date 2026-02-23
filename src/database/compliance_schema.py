"""
Compliance Module Neo4j Schema

This module defines the Neo4j database schema for compliance data including:
- Regulatory reports and their relationships
- Case management and evidence tracking
- Audit trail and compliance logging
- Risk assessment workflows
"""

import logging
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List

from neo4j import AsyncSession

logger = logging.getLogger(__name__)


class ComplianceSchemaManager:
    """Manages Neo4j schema for compliance module"""

    def __init__(self):
        self.constraints = []
        self.indexes = []
        self.schema_queries = []

    async def create_compliance_schema(self, session: AsyncSession):
        """Create complete compliance schema"""
        logger.info("Creating compliance module schema...")

        # Create constraints
        await self._create_constraints(session)

        # Create indexes
        await self._create_indexes(session)

        # Create schema validation
        await self._create_schema_validation(session)

        logger.info("Compliance schema created successfully")

    async def _create_constraints(self, session: AsyncSession):
        """Create uniqueness constraints"""
        constraints = [
            # Regulatory Report constraints
            """
            CREATE CONSTRAINT regulatory_report_id_unique 
            IF NOT EXISTS 
            FOR (r:RegulatoryReport) 
            REQUIRE r.report_id IS UNIQUE
            """,
            # Case constraints
            """
            CREATE CONSTRAINT case_id_unique 
            IF NOT EXISTS 
            FOR (c:Case) 
            REQUIRE c.case_id IS UNIQUE
            """,
            # Evidence constraints
            """
            CREATE CONSTRAINT evidence_id_unique 
            IF NOT EXISTS 
            FOR (e:Evidence) 
            REQUIRE e.evidence_id IS UNIQUE
            """,
            # Audit Event constraints
            """
            CREATE CONSTRAINT audit_event_id_unique 
            IF NOT EXISTS 
            FOR (a:AuditEvent) 
            REQUIRE a.event_id IS UNIQUE
            """,
            # Risk Assessment constraints
            """
            CREATE CONSTRAINT risk_assessment_id_unique 
            IF NOT EXISTS 
            FOR (r:RiskAssessment) 
            REQUIRE r.assessment_id IS UNIQUE
            """,
            # Risk Factor constraints
            """
            CREATE CONSTRAINT risk_factor_id_unique 
            IF NOT EXISTS 
            FOR (f:RiskFactor) 
            REQUIRE f.factor_id IS UNIQUE
            """,
            # Compliance Log constraints
            """
            CREATE CONSTRAINT compliance_log_id_unique 
            IF NOT EXISTS 
            FOR (l:ComplianceLog) 
            REQUIRE l.log_id IS UNIQUE
            """,
            # Risk Threshold constraints
            """
            CREATE CONSTRAINT risk_threshold_id_unique 
            IF NOT EXISTS 
            FOR (t:RiskThreshold) 
            REQUIRE t.threshold_id IS UNIQUE
            """,
            # Workflow constraints
            """
            CREATE CONSTRAINT workflow_id_unique 
            IF NOT EXISTS 
            FOR (w:Workflow) 
            REQUIRE w.workflow_id IS UNIQUE
            """,
            # Workflow Execution constraints
            """
            CREATE CONSTRAINT workflow_execution_id_unique 
            IF NOT EXISTS 
            FOR (e:WorkflowExecution) 
            REQUIRE e.execution_id IS UNIQUE
            """,
        ]

        for constraint in constraints:
            try:
                await session.run(constraint)
                logger.debug(f"Created constraint: {constraint[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to create constraint: {e}")

    async def _create_indexes(self, session: AsyncSession):
        """Create performance indexes"""
        indexes = [
            # Regulatory Report indexes
            """
            CREATE INDEX regulatory_report_jurisdiction 
            IF NOT EXISTS 
            FOR (r:RegulatoryReport) 
            ON (r.jurisdiction, r.report_type, r.status)
            """,
            """
            CREATE INDEX regulatory_report_entity 
            IF NOT EXISTS 
            FOR (r:RegulatoryReport) 
            ON (r.entity_id, r.entity_type)
            """,
            """
            CREATE INDEX regulatory_report_created 
            IF NOT EXISTS 
            FOR (r:RegulatoryReport) 
            ON (r.created_at)
            """,
            # Case indexes
            """
            CREATE INDEX case_status_priority 
            IF NOT EXISTS 
            FOR (c:Case) 
            ON (c.status, c.priority, c.created_at)
            """,
            """
            CREATE INDEX case_assignee 
            IF NOT EXISTS 
            FOR (c:Case) 
            ON (c.assigned_to, c.status)
            """,
            """
            CREATE INDEX case_type 
            IF NOT EXISTS 
            FOR (c:Case) 
            ON (c.case_type, c.created_at)
            """,
            # Evidence indexes
            """
            CREATE INDEX evidence_case_type 
            IF NOT EXISTS 
            FOR (e:Evidence) 
            ON (e.case_id, e.evidence_type, e.status)
            """,
            """
            CREATE INDEX evidence_collected 
            IF NOT EXISTS 
            FOR (e:Evidence) 
            ON (e.collected_by, e.collected_at)
            """,
            # Audit Event indexes
            """
            CREATE INDEX audit_event_type_severity 
            IF NOT EXISTS 
            FOR (a:AuditEvent) 
            ON (a.event_type, a.severity, a.timestamp)
            """,
            """
            CREATE INDEX audit_user_timestamp 
            IF NOT EXISTS 
            FOR (a:AuditEvent) 
            ON (a.user_id, a.timestamp)
            """,
            """
            CREATE INDEX audit_resource 
            IF NOT EXISTS 
            FOR (a:AuditEvent) 
            ON (a.resource_type, a.resource_id)
            """,
            # Risk Assessment indexes
            """
            CREATE INDEX risk_assessment_entity 
            IF NOT EXISTS 
            FOR (r:RiskAssessment) 
            ON (r.entity_id, r.entity_type, r.risk_level)
            """,
            """
            CREATE INDEX risk_assessment_level 
            IF NOT EXISTS 
            FOR (r:RiskAssessment) 
            ON (r.risk_level, r.overall_score, r.created_at)
            """,
            """
            CREATE INDEX risk_assessment_trigger 
            IF NOT EXISTS 
            FOR (r:RiskAssessment) 
            ON (r.trigger_type, r.status, r.created_at)
            """,
            # Risk Factor indexes
            """
            CREATE INDEX risk_factor_category 
            IF NOT EXISTS 
            FOR (f:RiskFactor) 
            ON (f.category, f.score, f.weight)
            """,
            # Compliance Log indexes
            """
            CREATE INDEX compliance_log_category 
            IF NOT EXISTS 
            FOR (l:ComplianceLog) 
            ON (l.category, l.action, l.timestamp)
            """,
            """
            CREATE INDEX compliance_log_subject 
            IF NOT EXISTS 
            FOR (l:ComplianceLog) 
            ON (l.data_subject_id, l.timestamp)
            """,
            # Workflow indexes
            """
            CREATE INDEX workflow_status 
            IF NOT EXISTS 
            FOR (w:Workflow) 
            ON (w.active, w.case_type)
            """,
            # Full-text search indexes
            """
            CREATE FULLTEXT INDEX case_search 
            IF NOT EXISTS 
            FOR (c:Case) 
            ON EACH [c.title, c.description]
            """,
            """
            CREATE FULLTEXT INDEX evidence_search 
            IF NOT EXISTS 
            FOR (e:Evidence) 
            ON EACH [e.description]
            """,
            """
            CREATE FULLTEXT INDEX audit_search 
            IF NOT EXISTS 
            FOR (a:AuditEvent) 
            ON EACH [a.description]
            """,
        ]

        for index in indexes:
            try:
                await session.run(index)
                logger.debug(f"Created index: {index[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to create index: {e}")

    async def _create_schema_validation(self, session: AsyncSession):
        """Create schema validation procedures"""
        # Note: Neo4j procedures would be created separately
        # This is a placeholder for schema validation setup
        logger.info("Schema validation setup placeholder")
        return

    async def verify_schema_integrity(self, session: AsyncSession) -> Dict[str, Any]:
        """Verify schema integrity and return status"""
        verification_results = {
            "constraints": {"valid": True, "issues": []},
            "indexes": {"valid": True, "issues": []},
            "data_integrity": {"valid": True, "issues": []},
        }

        # Verify constraints
        try:
            constraints_query = "SHOW CONSTRAINTS"
            result = await session.run(constraints_query)
            constraints = await result.data()

            expected_constraints = [
                "regulatory_report_id_unique",
                "case_id_unique",
                "evidence_id_unique",
                "audit_event_id_unique",
                "risk_assessment_id_unique",
                "risk_factor_id_unique",
                "compliance_log_id_unique",
                "risk_threshold_id_unique",
                "workflow_id_unique",
                "workflow_execution_id_unique",
            ]

            existing_constraints = [c["name"] for c in constraints]

            for expected in expected_constraints:
                if expected not in existing_constraints:
                    verification_results["constraints"]["valid"] = False
                    verification_results["constraints"]["issues"].append(
                        f"Missing constraint: {expected}"
                    )

        except Exception as e:
            verification_results["constraints"]["valid"] = False
            verification_results["constraints"]["issues"].append(
                f"Constraint verification failed: {e}"
            )

        # Verify indexes
        try:
            indexes_query = "SHOW INDEXES"
            result = await session.run(indexes_query)
            indexes = await result.data()

            expected_indexes = [
                "regulatory_report_jurisdiction",
                "regulatory_report_entity",
                "regulatory_report_created",
                "case_status_priority",
                "case_assignee",
                "case_type",
                "evidence_case_type",
                "evidence_collected",
                "audit_event_type_severity",
                "audit_user_timestamp",
                "audit_resource",
                "risk_assessment_entity",
                "risk_assessment_level",
                "risk_assessment_trigger",
                "risk_factor_category",
                "compliance_log_category",
                "compliance_log_subject",
                "workflow_status",
            ]

            existing_indexes = [i["name"] for i in indexes]

            for expected in expected_indexes:
                if expected not in existing_indexes:
                    verification_results["indexes"]["valid"] = False
                    verification_results["indexes"]["issues"].append(
                        f"Missing index: {expected}"
                    )

        except Exception as e:
            verification_results["indexes"]["valid"] = False
            verification_results["indexes"]["issues"].append(
                f"Index verification failed: {e}"
            )

        # Verify data integrity
        try:
            # Check for orphaned nodes
            orphaned_checks = [
                "MATCH (e:Evidence) WHERE NOT EXISTS((:Case)-[:HAS_EVIDENCE]->(e)) RETURN count(e) as orphaned_evidence",
                "MATCH (f:RiskFactor) WHERE NOT EXISTS((:RiskAssessment)-[:HAS_FACTOR]->(f)) RETURN count(f) as orphaned_factors",
                "MATCH (l:ComplianceLog) WHERE NOT EXISTS((:AuditEvent)-[:HAS_COMPLIANCE]->(l)) RETURN count(l) as orphaned_logs",
            ]

            for check in orphaned_checks:
                result = await session.run(check)
                record = await result.single()
                if record and list(record.values())[0] > 0:
                    verification_results["data_integrity"]["valid"] = False
                    verification_results["data_integrity"]["issues"].append(
                        f"Orphaned nodes detected: {check}"
                    )

        except Exception as e:
            verification_results["data_integrity"]["valid"] = False
            verification_results["data_integrity"]["issues"].append(
                f"Data integrity check failed: {e}"
            )

        return verification_results

    async def get_schema_statistics(self, session: AsyncSession) -> Dict[str, Any]:
        """Get comprehensive schema statistics"""
        statistics = {
            "node_counts": {},
            "relationship_counts": {},
            "constraint_count": 0,
            "index_count": 0,
            "storage_info": {},
        }

        # Get node counts
        node_queries = {
            "RegulatoryReport": "MATCH (r:RegulatoryReport) RETURN count(r) as count",
            "Case": "MATCH (c:Case) RETURN count(c) as count",
            "Evidence": "MATCH (e:Evidence) RETURN count(e) as count",
            "AuditEvent": "MATCH (a:AuditEvent) RETURN count(a) as count",
            "RiskAssessment": "MATCH (r:RiskAssessment) RETURN count(r) as count",
            "RiskFactor": "MATCH (f:RiskFactor) RETURN count(f) as count",
            "ComplianceLog": "MATCH (l:ComplianceLog) RETURN count(l) as count",
            "RiskThreshold": "MATCH (t:RiskThreshold) RETURN count(t) as count",
            "Workflow": "MATCH (w:Workflow) RETURN count(w) as count",
            "WorkflowExecution": "MATCH (e:WorkflowExecution) RETURN count(e) as count",
        }

        for label, query in node_queries.items():
            try:
                result = await session.run(query)
                record = await result.single()
                statistics["node_counts"][label] = record["count"] if record else 0
            except Exception as e:
                logger.warning(f"Failed to get count for {label}: {e}")
                statistics["node_counts"][label] = 0

        # Get relationship counts
        relationship_queries = {
            "HAS_FACTOR": "MATCH ()-[r:HAS_FACTOR]->() RETURN count(r) as count",
            "HAS_EVIDENCE": "MATCH ()-[r:HAS_EVIDENCE]->() RETURN count(r) as count",
            "HAS_COMPLIANCE": "MATCH ()-[r:HAS_COMPLIANCE]->() RETURN count(r) as count",
            "TRIGGERED": "MATCH ()-[r:TRIGGERED]->() RETURN count(r) as count",
            "HAS_WORKFLOW": "MATCH ()-[r:HAS_WORKFLOW]->() RETURN count(r) as count",
            "HAS_UPDATE": "MATCH ()-[r:HAS_UPDATE]->() RETURN count(r) as count",
        }

        for rel_type, query in relationship_queries.items():
            try:
                result = await session.run(query)
                record = await result.single()
                statistics["relationship_counts"][rel_type] = (
                    record["count"] if record else 0
                )
            except Exception as e:
                logger.warning(f"Failed to get count for {rel_type}: {e}")
                statistics["relationship_counts"][rel_type] = 0

        # Get constraint and index counts
        try:
            constraints_result = await session.run("SHOW CONSTRAINTS")
            constraints = await constraints_result.data()
            statistics["constraint_count"] = len(constraints)

            indexes_result = await session.run("SHOW INDEXES")
            indexes = await indexes_result.data()
            statistics["index_count"] = len(indexes)
        except Exception as e:
            logger.warning(f"Failed to get constraint/index counts: {e}")
            statistics["constraint_count"] = 0
            statistics["index_count"] = 0

        return statistics

    async def cleanup_old_data(self, session: AsyncSession, retention_days: int = 2555):
        """Clean up old data based on retention policy"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        cleanup_stats = {
            "audit_events_deleted": 0,
            "compliance_logs_deleted": 0,
            "cases_archived": 0,
            "errors": [],
        }

        try:
            # Archive old cases (instead of deleting)
            cases_query = """
            MATCH (c:Case)
            WHERE c.status = 'closed' AND c.updated_at < datetime($cutoff_date)
            SET c.status = 'archived'
            RETURN count(c) as archived_count
            """
            result = await session.run(cases_query, cutoff_date=cutoff_date.isoformat())
            record = await result.single()
            cleanup_stats["cases_archived"] = record["archived_count"] if record else 0

            # Delete old audit events (beyond retention period)
            audit_query = """
            MATCH (a:AuditEvent)
            WHERE a.timestamp < datetime($cutoff_date)
            DETACH DELETE a
            RETURN count(a) as deleted_count
            """
            result = await session.run(audit_query, cutoff_date=cutoff_date.isoformat())
            record = await result.single()
            cleanup_stats["audit_events_deleted"] = (
                record["deleted_count"] if record else 0
            )

            # Delete old compliance logs
            compliance_query = """
            MATCH (l:ComplianceLog)
            WHERE l.timestamp < datetime($cutoff_date)
            DETACH DELETE l
            RETURN count(l) as deleted_count
            """
            result = await session.run(
                compliance_query, cutoff_date=cutoff_date.isoformat()
            )
            record = await result.single()
            cleanup_stats["compliance_logs_deleted"] = (
                record["deleted_count"] if record else 0
            )

            logger.info(f"Cleanup completed: {cleanup_stats}")

        except Exception as e:
            error_msg = f"Cleanup failed: {e}"
            logger.error(error_msg)
            cleanup_stats["errors"].append(error_msg)

        return cleanup_stats


# Schema initialization function
async def initialize_compliance_schema(session: AsyncSession):
    """Initialize compliance module schema"""
    schema_manager = ComplianceSchemaManager()
    await schema_manager.create_compliance_schema(session)
    return schema_manager
