"""
Jackdaw Sentry - Forensic Report Generator
Professional court-defensible report generation with templates
"""

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set

logger = logging.getLogger(__name__)


class ReportType(Enum):
    """Types of forensic reports"""

    SUMMARY = "summary"
    DETAILED = "detailed"
    EXPERT_WITNESS = "expert_witness"
    COURT_SUBMISSION = "court_submission"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    EVIDENCE_CHAIN = "evidence_chain"
    ATTRIBUTION = "attribution"


class ReportFormat(Enum):
    """Report output formats"""

    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    XML = "xml"
    DOCX = "docx"
    MARKDOWN = "markdown"


class ReportStatus(Enum):
    """Report generation status"""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FINAL = "final"
    ARCHIVED = "archived"


@dataclass
class ReportTemplate:
    """Report template definition"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    report_type: ReportType = ReportType.SUMMARY
    format: ReportFormat = ReportFormat.PDF
    template_content: str = ""
    sections: List[Dict[str, Any]] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    styling: Dict[str, Any] = field(default_factory=dict)
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    is_active: bool = True
    version: str = "1.0"

    def validate_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate report data against template requirements"""
        errors = []

        for field in self.required_fields:
            if field not in data or data[field] is None or data[field] == "":
                errors.append(f"Required field missing: {field}")

        return errors


@dataclass
class ReportSection:
    """Individual report section"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    content: str = ""
    section_type: str = "text"  # text, table, chart, image, evidence_list
    order: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_required: bool = True
    word_count: int = 0
    generated_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def calculate_word_count(self) -> int:
        """Calculate word count for section"""
        self.word_count = len(self.content.split())
        return self.word_count


@dataclass
class GeneratedReport:
    """Generated forensic report"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str = ""
    template_id: str = ""
    title: str = ""
    report_type: ReportType = ReportType.SUMMARY
    format: ReportFormat = ReportFormat.PDF
    status: ReportStatus = ReportStatus.DRAFT
    sections: List[ReportSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    generated_by: str = ""
    reviewed_by: Optional[str] = None
    reviewed_date: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    is_court_ready: bool = False
    confidence_score: float = 0.0
    total_word_count: int = 0

    def calculate_totals(self) -> None:
        """Calculate report totals"""
        self.total_word_count = sum(section.word_count for section in self.sections)

    def add_review(self, reviewer: str) -> None:
        """Add review to report"""
        self.reviewed_by = reviewer
        self.reviewed_date = datetime.now(timezone.utc)
        self.status = ReportStatus.REVIEW

    def approve(self, approver: str) -> None:
        """Approve report for final use"""
        self.approved_by = approver
        self.approved_date = datetime.now(timezone.utc)
        self.status = ReportStatus.APPROVED


class ReportGenerator:
    """Professional forensic report generation system"""

    def __init__(self, db_pool=None, output_path: str = "/var/lib/jackdaw/reports"):
        self.db_pool = db_pool
        self.output_path = output_path
        self.templates: Dict[str, ReportTemplate] = {}
        self.reports: Dict[str, GeneratedReport] = {}
        self.running = False
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour

        # Ensure output directory exists
        os.makedirs(output_path, exist_ok=True)

        logger.info("ReportGenerator initialized")

    async def initialize(self) -> None:
        """Initialize report generator and database schema"""
        if self.db_pool:
            await self._create_database_schema()

        # Load default templates
        await self._load_default_templates()

        self.running = True
        logger.info("ReportGenerator started")

    async def shutdown(self) -> None:
        """Shutdown report generator"""
        self.running = False
        logger.info("ReportGenerator shutdown")

    async def _create_database_schema(self) -> None:
        """Create report generation database tables"""
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS report_templates (
                id UUID PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                report_type TEXT NOT NULL,
                format TEXT NOT NULL,
                template_content TEXT,
                sections JSONB DEFAULT '[]',
                required_fields JSONB DEFAULT '[]',
                optional_fields JSONB DEFAULT '[]',
                styling JSONB DEFAULT '{}',
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_by TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                version TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS generated_reports (
                id UUID PRIMARY KEY,
                case_id UUID NOT NULL,
                template_id UUID REFERENCES report_templates(id),
                title TEXT NOT NULL,
                report_type TEXT NOT NULL,
                format TEXT NOT NULL,
                status TEXT NOT NULL,
                sections JSONB DEFAULT '[]',
                metadata JSONB DEFAULT '{}',
                generated_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                generated_by TEXT NOT NULL,
                reviewed_by TEXT,
                reviewed_date TIMESTAMP WITH TIME ZONE,
                approved_by TEXT,
                approved_date TIMESTAMP WITH TIME ZONE,
                file_path TEXT,
                file_size BIGINT,
                checksum TEXT,
                is_court_ready BOOLEAN DEFAULT FALSE,
                confidence_score FLOAT DEFAULT 0.0,
                total_word_count INTEGER DEFAULT 0
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_report_templates_type ON report_templates(report_type);
            CREATE INDEX IF NOT EXISTS idx_report_templates_active ON report_templates(is_active);
            CREATE INDEX IF NOT EXISTS idx_generated_reports_case ON generated_reports(case_id);
            CREATE INDEX IF NOT EXISTS idx_generated_reports_status ON generated_reports(status);
            CREATE INDEX IF NOT EXISTS idx_generated_reports_type ON generated_reports(report_type);
            """,
        ]

        async with self.db_pool.acquire() as conn:
            for query in schema_queries:
                await conn.execute(query)

        logger.info("Report generation database schema created")

    async def _load_default_templates(self) -> None:
        """Load default report templates"""
        default_templates = [
            {
                "name": "Court Submission Template",
                "description": "Standard template for court submissions",
                "report_type": ReportType.COURT_SUBMISSION,
                "format": ReportFormat.PDF,
                "template_content": self._get_court_template_content(),
                "sections": [
                    {"title": "Executive Summary", "type": "text", "required": True},
                    {"title": "Case Background", "type": "text", "required": True},
                    {
                        "title": "Evidence Analysis",
                        "type": "evidence_list",
                        "required": True,
                    },
                    {"title": "Technical Findings", "type": "text", "required": True},
                    {"title": "Conclusions", "type": "text", "required": True},
                    {
                        "title": "Expert Qualifications",
                        "type": "text",
                        "required": True,
                    },
                ],
                "required_fields": [
                    "case_id",
                    "evidence_list",
                    "findings",
                    "conclusions",
                ],
                "created_by": "system",
            },
            {
                "name": "Expert Witness Report",
                "description": "Template for expert witness testimony",
                "report_type": ReportType.EXPERT_WITNESS,
                "format": ReportFormat.PDF,
                "template_content": self._get_expert_template_content(),
                "sections": [
                    {
                        "title": "Expert Qualifications",
                        "type": "text",
                        "required": True,
                    },
                    {"title": "Case Summary", "type": "text", "required": True},
                    {"title": "Methodology", "type": "text", "required": True},
                    {"title": "Analysis Results", "type": "text", "required": True},
                    {
                        "title": "Opinions and Conclusions",
                        "type": "text",
                        "required": True,
                    },
                ],
                "required_fields": [
                    "qualifications",
                    "methodology",
                    "analysis",
                    "opinions",
                ],
                "created_by": "system",
            },
            {
                "name": "Technical Analysis Report",
                "description": "Detailed technical analysis template",
                "report_type": ReportType.TECHNICAL,
                "format": ReportFormat.HTML,
                "template_content": self._get_technical_template_content(),
                "sections": [
                    {"title": "Technical Overview", "type": "text", "required": True},
                    {"title": "Data Sources", "type": "table", "required": True},
                    {"title": "Analysis Methods", "type": "text", "required": True},
                    {"title": "Results", "type": "chart", "required": False},
                    {"title": "Technical Details", "type": "text", "required": True},
                ],
                "required_fields": ["overview", "data_sources", "methods", "results"],
                "created_by": "system",
            },
        ]

        for template_data in default_templates:
            template = ReportTemplate(
                name=template_data["name"],
                description=template_data["description"],
                report_type=template_data["report_type"],
                format=template_data["format"],
                template_content=template_data["template_content"],
                sections=template_data["sections"],
                required_fields=template_data["required_fields"],
                created_by=template_data["created_by"],
            )

            self.templates[template.id] = template

            if self.db_pool:
                await self._save_template_to_db(template)

        logger.info(f"Loaded {len(default_templates)} default templates")

    async def create_template(self, template_data: Dict[str, Any]) -> ReportTemplate:
        """Create new report template"""
        template = ReportTemplate(
            name=template_data["name"],
            description=template_data.get("description", ""),
            report_type=ReportType(template_data["report_type"]),
            format=ReportFormat(template_data["format"]),
            template_content=template_data.get("template_content", ""),
            sections=template_data.get("sections", []),
            required_fields=template_data.get("required_fields", []),
            optional_fields=template_data.get("optional_fields", []),
            styling=template_data.get("styling", {}),
            created_by=template_data["created_by"],
            version=template_data.get("version", "1.0"),
        )

        if self.db_pool:
            await self._save_template_to_db(template)

        self.templates[template.id] = template
        logger.info(f"Created report template: {template.name}")
        return template

    async def generate_report(
        self,
        case_id: str,
        template_id: str,
        report_data: Dict[str, Any],
        generated_by: str,
    ) -> GeneratedReport:
        """Generate forensic report from template"""
        template = await self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Validate data against template
        validation_errors = template.validate_data(report_data)
        if validation_errors:
            raise ValueError(f"Template validation failed: {validation_errors}")

        # Create report sections
        sections = []
        for section_config in template.sections:
            section = ReportSection(
                title=section_config["title"],
                section_type=section_config["type"],
                order=len(sections),
                is_required=section_config.get("required", True),
            )

            # Generate section content based on type
            if section.section_type == "text":
                section.content = report_data.get(
                    section_config["title"].lower().replace(" ", "_"), ""
                )
            elif section.section_type == "evidence_list":
                section.content = self._generate_evidence_list(
                    report_data.get("evidence_list", [])
                )
            elif section.section_type == "table":
                section.content = self._generate_table(
                    report_data.get(
                        section_config["title"].lower().replace(" ", "_"), []
                    )
                )
            elif section.section_type == "chart":
                section.content = self._generate_chart_data(
                    report_data.get(
                        section_config["title"].lower().replace(" ", "_"), {}
                    )
                )

            section.calculate_word_count()
            sections.append(section)

        # Create report
        report = GeneratedReport(
            case_id=case_id,
            template_id=template_id,
            title=report_data.get("title", f"Report for Case {case_id}"),
            report_type=template.report_type,
            format=template.format,
            sections=sections,
            metadata=report_data.get("metadata", {}),
            generated_by=generated_by,
            confidence_score=report_data.get("confidence_score", 0.0),
        )

        report.calculate_totals()

        # Generate file
        file_path = await self._generate_report_file(report, template)
        report.file_path = file_path

        if os.path.exists(file_path):
            report.file_size = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                import hashlib

                report.checksum = hashlib.sha256(f.read()).hexdigest()

        if self.db_pool:
            await self._save_report_to_db(report)

        self.reports[report.id] = report
        logger.info(f"Generated report: {report.id}")
        return report

    async def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        """Get report template by ID"""
        if template_id in self.templates:
            return self.templates[template_id]

        if self.db_pool:
            template = await self._load_template_from_db(template_id)
            if template:
                self.templates[template_id] = template
                return template

        return None

    async def get_report(self, report_id: str) -> Optional[GeneratedReport]:
        """Get generated report by ID"""
        if report_id in self.reports:
            return self.reports[report_id]

        if self.db_pool:
            report = await self._load_report_from_db(report_id)
            if report:
                self.reports[report_id] = report
                return report

        return None

    async def search_templates(self, filters: Dict[str, Any]) -> List[ReportTemplate]:
        """Search report templates"""
        if self.db_pool:
            return await self._search_templates_db(filters)

        # In-memory search
        results = []
        for template in self.templates.values():
            if not template.is_active:
                continue

            match = True

            if (
                "report_type" in filters
                and template.report_type.value != filters["report_type"]
            ):
                match = False
            if "format" in filters and template.format.value != filters["format"]:
                match = False
            if "created_by" in filters and template.created_by != filters["created_by"]:
                match = False

            if match:
                results.append(template)

        return results

    async def search_reports(self, filters: Dict[str, Any]) -> List[GeneratedReport]:
        """Search generated reports"""
        if self.db_pool:
            return await self._search_reports_db(filters)

        # In-memory search
        results = []
        for report in self.reports.values():
            match = True

            if "case_id" in filters and report.case_id != filters["case_id"]:
                match = False
            if (
                "report_type" in filters
                and report.report_type.value != filters["report_type"]
            ):
                match = False
            if "status" in filters and report.status.value != filters["status"]:
                match = False
            if (
                "generated_by" in filters
                and report.generated_by != filters["generated_by"]
            ):
                match = False

            if match:
                results.append(report)

        return results

    async def update_report_status(
        self, report_id: str, new_status: ReportStatus, user: str
    ) -> None:
        """Update report status"""
        if report_id not in self.reports:
            raise ValueError(f"Report {report_id} not found")

        report = self.reports[report_id]

        if new_status == ReportStatus.REVIEW:
            report.add_review(user)
        elif new_status == ReportStatus.APPROVED:
            report.approve(user)
        else:
            report.status = new_status

        if self.db_pool:
            await self._update_report_status_db(report_id, new_status, user)

        logger.info(f"Updated report {report_id} status to {new_status.value}")

    def _generate_evidence_list(self, evidence_list: List[Dict[str, Any]]) -> str:
        """Generate formatted evidence list"""
        if not evidence_list:
            return "No evidence items to display."

        content = "## Evidence Items\n\n"
        for i, evidence in enumerate(evidence_list, 1):
            content += f"{i}. **{evidence.get('title', 'Untitled')}**\n"
            content += f"   - Type: {evidence.get('type', 'Unknown')}\n"
            content += f"   - Date: {evidence.get('date', 'Unknown')}\n"
            content += (
                f"   - Description: {evidence.get('description', 'No description')}\n\n"
            )

        return content

    def _generate_table(self, table_data: List[Dict[str, Any]]) -> str:
        """Generate formatted table"""
        if not table_data:
            return "No data to display in table."

        # Create markdown table
        headers = list(table_data[0].keys())
        content = "| " + " | ".join(headers) + " |\n"
        content += "|" + "|".join(["-" * len(h) for h in headers]) + "|\n"

        for row in table_data:
            values = [str(row.get(h, "")) for h in headers]
            content += "| " + " | ".join(values) + " |\n"

        return content

    def _generate_chart_data(self, chart_data: Dict[str, Any]) -> str:
        """Generate chart placeholder"""
        return (
            f"## Chart Data\n\nChart configuration: {json.dumps(chart_data, indent=2)}"
        )

    async def _generate_report_file(
        self, report: GeneratedReport, template: ReportTemplate
    ) -> str:
        """Generate actual report file"""
        file_name = f"{report.id}.{report.format.value}"
        file_path = os.path.join(self.output_path, file_name)

        # Generate content based on format
        if report.format == ReportFormat.HTML:
            content = self._generate_html_report(report, template)
        elif report.format == ReportFormat.MARKDOWN:
            content = self._generate_markdown_report(report, template)
        elif report.format == ReportFormat.JSON:
            content = self._generate_json_report(report, template)
        else:
            # Default to markdown for other formats
            content = self._generate_markdown_report(report, template)

        # Write file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path

    def _generate_html_report(
        self, report: GeneratedReport, template: ReportTemplate
    ) -> str:
        """Generate HTML report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; border-bottom: 2px solid #ccc; }}
                .metadata {{ background: #f5f5f5; padding: 10px; border-radius: 5px; }}
                .section {{ margin: 20px 0; }}
                .word-count {{ font-size: 0.8em; color: #888; }}
            </style>
        </head>
        <body>
            <h1>{report.title}</h1>
            
            <div class="metadata">
                <p><strong>Generated:</strong> {report.generated_date.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Generated By:</strong> {report.generated_by}</p>
                <p><strong>Case ID:</strong> {report.case_id}</p>
                <p><strong>Confidence Score:</strong> {report.confidence_score:.2f}</p>
                <p><strong>Total Word Count:</strong> {report.total_word_count}</p>
            </div>
        """

        for section in sorted(report.sections, key=lambda s: s.order):
            content_with_br = section.content.replace("\n", "<br>")
            html += f"""
            <div class="section">
                <h2>{section.title}</h2>
                <div class="word-count">Words: {section.word_count}</div>
                <div>{content_with_br}</div>
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html

    def _generate_markdown_report(
        self, report: GeneratedReport, template: ReportTemplate
    ) -> str:
        """Generate Markdown report"""
        markdown = f"# {report.title}\n\n"
        markdown += (
            f"**Generated:** {report.generated_date.strftime('%Y-%m-%d %H:%M:%S')}  \n"
        )
        markdown += f"**Generated By:** {report.generated_by}  \n"
        markdown += f"**Case ID:** {report.case_id}  \n"
        markdown += f"**Confidence Score:** {report.confidence_score:.2f}  \n"
        markdown += f"**Total Word Count:** {report.total_word_count}\n\n"

        for section in sorted(report.sections, key=lambda s: s.order):
            markdown += f"## {section.title}\n\n"
            markdown += f"*Words: {section.word_count}*\n\n"
            markdown += f"{section.content}\n\n"

        return markdown

    def _generate_json_report(
        self, report: GeneratedReport, template: ReportTemplate
    ) -> str:
        """Generate JSON report"""
        return json.dumps(
            {
                "id": report.id,
                "title": report.title,
                "case_id": report.case_id,
                "report_type": report.report_type.value,
                "status": report.status.value,
                "generated_date": report.generated_date.isoformat(),
                "generated_by": report.generated_by,
                "confidence_score": report.confidence_score,
                "total_word_count": report.total_word_count,
                "sections": [
                    {
                        "title": s.title,
                        "type": s.section_type,
                        "content": s.content,
                        "word_count": s.word_count,
                        "order": s.order,
                    }
                    for s in sorted(report.sections, key=lambda sec: sec.order)
                ],
                "metadata": report.metadata,
            },
            indent=2,
        )

    def _get_court_template_content(self) -> str:
        """Get court submission template content"""
        return """
        # COURT SUBMISSION REPORT
        
        ## Executive Summary
        [Brief overview of case and key findings]
        
        ## Case Background
        [Detailed case background and context]
        
        ## Evidence Analysis
        [Analysis of all evidence presented]
        
        ## Technical Findings
        [Technical analysis and results]
        
        ## Conclusions
        [Final conclusions and opinions]
        
        ## Expert Qualifications
        [Expert qualifications and experience]
        """

    def _get_expert_template_content(self) -> str:
        """Get expert witness template content"""
        return """
        # EXPERT WITNESS REPORT
        
        ## Expert Qualifications
        [Detailed expert qualifications]
        
        ## Case Summary
        [Summary of the case]
        
        ## Methodology
        [Methods used for analysis]
        
        ## Analysis Results
        [Detailed analysis results]
        
        ## Opinions and Conclusions
        [Expert opinions and conclusions]
        """

    def _get_technical_template_content(self) -> str:
        """Get technical analysis template content"""
        return """
        # TECHNICAL ANALYSIS REPORT
        
        ## Technical Overview
        [Technical overview of the analysis]
        
        ## Data Sources
        [List and description of data sources]
        
        ## Analysis Methods
        [Methods used for technical analysis]
        
        ## Results
        [Analysis results and findings]
        
        ## Technical Details
        [Detailed technical information]
        """

    # Database helper methods
    async def _save_template_to_db(self, template: ReportTemplate) -> None:
        """Save template to database"""
        query = """
        INSERT INTO report_templates 
        (id, name, description, report_type, format, template_content, sections,
         required_fields, optional_fields, styling, created_date, created_by, is_active, version)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        description = EXCLUDED.description,
        template_content = EXCLUDED.template_content,
        sections = EXCLUDED.sections,
        required_fields = EXCLUDED.required_fields,
        optional_fields = EXCLUDED.optional_fields,
        styling = EXCLUDED.styling,
        is_active = EXCLUDED.is_active,
        version = EXCLUDED.version
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                template.id,
                template.name,
                template.description,
                template.report_type.value,
                template.format.value,
                template.template_content,
                json.dumps(template.sections),
                json.dumps(template.required_fields),
                json.dumps(template.optional_fields),
                json.dumps(template.styling),
                template.created_date,
                template.created_by,
                template.is_active,
                template.version,
            )

    async def _save_report_to_db(self, report: GeneratedReport) -> None:
        """Save report to database"""
        query = """
        INSERT INTO generated_reports 
        (id, case_id, template_id, title, report_type, format, status, sections, metadata,
         generated_date, generated_by, reviewed_by, reviewed_date, approved_by, approved_date,
         file_path, file_size, checksum, is_court_ready, confidence_score, total_word_count)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
        ON CONFLICT (id) DO UPDATE SET
        status = EXCLUDED.status,
        sections = EXCLUDED.sections,
        metadata = EXCLUDED.metadata,
        reviewed_by = EXCLUDED.reviewed_by,
        reviewed_date = EXCLUDED.reviewed_date,
        approved_by = EXCLUDED.approved_by,
        approved_date = EXCLUDED.approved_date,
        file_path = EXCLUDED.file_path,
        file_size = EXCLUDED.file_size,
        checksum = EXCLUDED.checksum,
        is_court_ready = EXCLUDED.is_court_ready,
        confidence_score = EXCLUDED.confidence_score,
        total_word_count = EXCLUDED.total_word_count
        """

        sections_data = [
            {
                "title": s.title,
                "content": s.content,
                "type": s.section_type,
                "order": s.order,
                "word_count": s.word_count,
                "is_required": s.is_required,
            }
            for s in report.sections
        ]

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                report.id,
                report.case_id,
                report.template_id,
                report.title,
                report.report_type.value,
                report.format.value,
                report.status.value,
                json.dumps(sections_data),
                json.dumps(report.metadata),
                report.generated_date,
                report.generated_by,
                report.reviewed_by,
                report.reviewed_date,
                report.approved_by,
                report.approved_date,
                report.file_path,
                report.file_size,
                report.checksum,
                report.is_court_ready,
                report.confidence_score,
                report.total_word_count,
            )

    async def _load_template_from_db(
        self, template_id: str
    ) -> Optional[ReportTemplate]:
        """Load template from database"""
        query = "SELECT * FROM report_templates WHERE id = $1"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, template_id)
            if row:
                return ReportTemplate(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    report_type=ReportType(row["report_type"]),
                    format=ReportFormat(row["format"]),
                    template_content=row["template_content"],
                    sections=json.loads(row["sections"]) if row["sections"] else [],
                    required_fields=(
                        json.loads(row["required_fields"])
                        if row["required_fields"]
                        else []
                    ),
                    optional_fields=(
                        json.loads(row["optional_fields"])
                        if row["optional_fields"]
                        else []
                    ),
                    styling=json.loads(row["styling"]) if row["styling"] else {},
                    created_date=row["created_date"],
                    created_by=row["created_by"],
                    is_active=row["is_active"],
                    version=row["version"],
                )
        return None

    async def _load_report_from_db(self, report_id: str) -> Optional[GeneratedReport]:
        """Load report from database"""
        query = "SELECT * FROM generated_reports WHERE id = $1"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, report_id)
            if row:
                sections_data = json.loads(row["sections"]) if row["sections"] else []
                sections = []

                for section_data in sections_data:
                    section = ReportSection(
                        title=section_data["title"],
                        content=section_data["content"],
                        section_type=section_data["type"],
                        order=section_data["order"],
                        word_count=section_data["word_count"],
                        is_required=section_data["is_required"],
                    )
                    sections.append(section)

                return GeneratedReport(
                    id=row["id"],
                    case_id=row["case_id"],
                    template_id=row["template_id"],
                    title=row["title"],
                    report_type=ReportType(row["report_type"]),
                    format=ReportFormat(row["format"]),
                    status=ReportStatus(row["status"]),
                    sections=sections,
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    generated_date=row["generated_date"],
                    generated_by=row["generated_by"],
                    reviewed_by=row["reviewed_by"],
                    reviewed_date=row["reviewed_date"],
                    approved_by=row["approved_by"],
                    approved_date=row["approved_date"],
                    file_path=row["file_path"],
                    file_size=row["file_size"],
                    checksum=row["checksum"],
                    is_court_ready=row["is_court_ready"],
                    confidence_score=row["confidence_score"],
                    total_word_count=row["total_word_count"],
                )
        return None

    async def _search_templates_db(
        self, filters: Dict[str, Any]
    ) -> List[ReportTemplate]:
        """Search templates in database"""
        conditions = ["is_active = TRUE"]
        params = []
        param_idx = 1

        if "report_type" in filters:
            conditions.append(f"report_type = ${param_idx}")
            params.append(filters["report_type"])
            param_idx += 1

        if "format" in filters:
            conditions.append(f"format = ${param_idx}")
            params.append(filters["format"])
            param_idx += 1

        if "created_by" in filters:
            conditions.append(f"created_by = ${param_idx}")
            params.append(filters["created_by"])
            param_idx += 1

        where_clause = "WHERE " + " AND ".join(conditions)
        query = (
            f"SELECT * FROM report_templates {where_clause} ORDER BY created_date DESC"
        )

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            templates = []
            for row in rows:
                template = ReportTemplate(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    report_type=ReportType(row["report_type"]),
                    format=ReportFormat(row["format"]),
                    template_content=row["template_content"],
                    sections=json.loads(row["sections"]) if row["sections"] else [],
                    required_fields=(
                        json.loads(row["required_fields"])
                        if row["required_fields"]
                        else []
                    ),
                    optional_fields=(
                        json.loads(row["optional_fields"])
                        if row["optional_fields"]
                        else []
                    ),
                    styling=json.loads(row["styling"]) if row["styling"] else {},
                    created_date=row["created_date"],
                    created_by=row["created_by"],
                    is_active=row["is_active"],
                    version=row["version"],
                )
                templates.append(template)

            return templates

    async def _search_reports_db(
        self, filters: Dict[str, Any]
    ) -> List[GeneratedReport]:
        """Search reports in database"""
        conditions = []
        params = []
        param_idx = 1

        if "case_id" in filters:
            conditions.append(f"case_id = ${param_idx}")
            params.append(filters["case_id"])
            param_idx += 1

        if "report_type" in filters:
            conditions.append(f"report_type = ${param_idx}")
            params.append(filters["report_type"])
            param_idx += 1

        if "status" in filters:
            conditions.append(f"status = ${param_idx}")
            params.append(filters["status"])
            param_idx += 1

        if "generated_by" in filters:
            conditions.append(f"generated_by = ${param_idx}")
            params.append(filters["generated_by"])
            param_idx += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT * FROM generated_reports {where_clause} ORDER BY generated_date DESC"

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            reports = []
            for row in rows:
                sections_data = json.loads(row["sections"]) if row["sections"] else []
                sections = []

                for section_data in sections_data:
                    section = ReportSection(
                        title=section_data["title"],
                        content=section_data["content"],
                        section_type=section_data["type"],
                        order=section_data["order"],
                        word_count=section_data["word_count"],
                        is_required=section_data["is_required"],
                    )
                    sections.append(section)

                report = GeneratedReport(
                    id=row["id"],
                    case_id=row["case_id"],
                    template_id=row["template_id"],
                    title=row["title"],
                    report_type=ReportType(row["report_type"]),
                    format=ReportFormat(row["format"]),
                    status=ReportStatus(row["status"]),
                    sections=sections,
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    generated_date=row["generated_date"],
                    generated_by=row["generated_by"],
                    reviewed_by=row["reviewed_by"],
                    reviewed_date=row["reviewed_date"],
                    approved_by=row["approved_by"],
                    approved_date=row["approved_date"],
                    file_path=row["file_path"],
                    file_size=row["file_size"],
                    checksum=row["checksum"],
                    is_court_ready=row["is_court_ready"],
                    confidence_score=row["confidence_score"],
                    total_word_count=row["total_word_count"],
                )
                reports.append(report)

            return reports

    async def _update_report_status_db(
        self, report_id: str, new_status: ReportStatus, user: str
    ) -> None:
        """Update report status in database"""
        if new_status == ReportStatus.REVIEW:
            query = """
            UPDATE generated_reports SET 
            status = $1, reviewed_by = $2, reviewed_date = NOW()
            WHERE id = $3
            """
            async with self.db_pool.acquire() as conn:
                await conn.execute(query, new_status.value, user, report_id)

        elif new_status == ReportStatus.APPROVED:
            query = """
            UPDATE generated_reports SET 
            status = $1, approved_by = $2, approved_date = NOW()
            WHERE id = $3
            """
            async with self.db_pool.acquire() as conn:
                await conn.execute(query, new_status.value, user, report_id)

        else:
            query = "UPDATE generated_reports SET status = $1 WHERE id = $2"
            async with self.db_pool.acquire() as conn:
                await conn.execute(query, new_status.value, report_id)


# Global report generator instance
_report_generator = None


def get_report_generator() -> ReportGenerator:
    """Get the global report generator instance"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator


# Aliases and additional types for API compatibility
ForensicReport = GeneratedReport


@dataclass
class ReportStatistics:
    """Statistics for generated reports"""

    total_reports: int = 0
    reports_by_type: Dict[str, int] = field(default_factory=dict)
    reports_by_status: Dict[str, int] = field(default_factory=dict)
    reports_by_format: Dict[str, int] = field(default_factory=dict)
    average_generation_time_seconds: float = 0.0
    total_pages: int = 0
