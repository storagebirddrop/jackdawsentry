"""
Compliance Data Visualization Tools Module

This module provides comprehensive data visualization tools for compliance operations including:
- Interactive charts and graphs
- Real-time data visualization
- Custom visualization components
- Export capabilities for visualizations
- Advanced data analysis visualization
"""

import asyncio
import base64
import io
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class VisualizationType(Enum):
    """Visualization type enumeration"""

    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    DOUGHNUT_CHART = "doughnut_chart"
    RADAR_CHART = "radar_chart"
    SCATTER_PLOT = "scatter_plot"
    HEATMAP = "heatmap"
    TREEMAP = "treemap"
    SANKEY_DIAGRAM = "sankey_diagram"
    NETWORK_GRAPH = "network_graph"
    TIMELINE = "timeline"
    GAUGE_CHART = "gauge_chart"
    FUNNEL_CHART = "funnel_chart"


class DataFormat(Enum):
    """Data format enumeration"""

    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PNG = "png"
    SVG = "svg"
    PDF = "pdf"


@dataclass
class VisualizationConfig:
    """Visualization configuration"""

    viz_id: str
    title: str
    description: str
    viz_type: VisualizationType
    data_source: str
    config: Dict[str, Any]
    filters: Optional[Dict[str, Any]] = None
    interactive: bool = True
    real_time: bool = False
    export_formats: List[DataFormat] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class VisualizationData:
    """Visualization data definition"""

    viz_id: str
    data: Union[List[Dict], Dict[str, Any]]
    generated_at: datetime
    labels: Optional[List[str]] = None
    datasets: Optional[List[Dict[str, Any]]] = None
    options: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class VisualizationResult:
    """Visualization result definition"""

    viz_id: str
    success: bool
    data: VisualizationData
    render_time_ms: float
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ComplianceVisualizationEngine:
    """Compliance data visualization engine"""

    def __init__(self):
        self.visualizations = {}
        self.visualization_cache = {}
        self.cache_ttl_minutes = 15
        self.max_data_points = 10000
        self.default_colors = [
            "#3b82f6",
            "#10b981",
            "#f59e0b",
            "#ef4444",
            "#8b5cf6",
            "#ec4899",
            "#14b8a6",
            "#f97316",
            "#6366f1",
            "#84cc16",
        ]

        # Initialize default visualizations
        self._initialize_default_visualizations()

    def _initialize_default_visualizations(self):
        """Initialize default compliance visualizations"""

        # SAR Reports Trend
        sar_trend_viz = VisualizationConfig(
            viz_id="sar_reports_trend",
            title="SAR Reports Trend",
            description="Monthly SAR reports submission trend",
            viz_type=VisualizationType.LINE_CHART,
            data_source="regulatory_reports",
            config={
                "x_axis": "month",
                "y_axis": "count",
                "smooth": True,
                "fill": True,
                "tension": 0.4,
            },
            interactive=True,
            real_time=False,
            export_formats=[DataFormat.JSON, DataFormat.PNG, DataFormat.SVG],
        )

        # Risk Level Distribution
        risk_dist_viz = VisualizationConfig(
            viz_id="risk_level_distribution",
            title="Risk Level Distribution",
            description="Distribution of risk assessment levels",
            viz_type=VisualizationType.DOUGHNUT_CHART,
            data_source="risk_assessments",
            config={
                "labels": ["Low", "Medium", "High", "Critical", "Severe"],
                "colors": self.default_colors[:5],
            },
            interactive=True,
            real_time=False,
            export_formats=[DataFormat.JSON, DataFormat.PNG, DataFormat.SVG],
        )

        # Case Status Overview
        case_status_viz = VisualizationConfig(
            viz_id="case_status_overview",
            title="Case Status Overview",
            description="Current case status distribution",
            viz_type=VisualizationType.BAR_CHART,
            data_source="cases",
            config={
                "x_axis": "status",
                "y_axis": "count",
                "colors": self.default_colors,
            },
            interactive=True,
            real_time=True,
            export_formats=[DataFormat.JSON, DataFormat.PNG, DataFormat.SVG],
        )

        # Compliance Score Timeline
        compliance_timeline_viz = VisualizationConfig(
            viz_id="compliance_score_timeline",
            title="Compliance Score Timeline",
            description="Compliance score over time",
            viz_type=VisualizationType.LINE_CHART,
            data_source="compliance_metrics",
            config={
                "x_axis": "date",
                "y_axis": "score",
                "min": 0,
                "max": 100,
                "tension": 0.4,
            },
            interactive=True,
            real_time=False,
            export_formats=[DataFormat.JSON, DataFormat.PNG, DataFormat.SVG],
        )

        # Jurisdiction Breakdown
        jurisdiction_viz = VisualizationConfig(
            viz_id="jurisdiction_breakdown",
            title="Regulatory Jurisdiction Breakdown",
            description="Reports by regulatory jurisdiction",
            viz_type=VisualizationType.PIE_CHART,
            data_source="regulatory_reports",
            config={
                "labels": ["USA (FinCEN)", "UK (FCA)", "EU"],
                "colors": self.default_colors[:3],
            },
            interactive=True,
            real_time=False,
            export_formats=[DataFormat.JSON, DataFormat.PNG, DataFormat.SVG],
        )

        # Risk Assessment Heatmap
        risk_heatmap_viz = VisualizationConfig(
            viz_id="risk_assessment_heatmap",
            title="Risk Assessment Heatmap",
            description="Risk assessment heatmap by category and time",
            viz_type=VisualizationType.HEATMAP,
            data_source="risk_assessments",
            config={
                "x_axis": "time_period",
                "y_axis": "risk_category",
                "color_scale": "viridis",
            },
            interactive=True,
            real_time=False,
            export_formats=[DataFormat.JSON, DataFormat.PNG, DataFormat.SVG],
        )

        # Team Performance Radar
        team_radar_viz = VisualizationConfig(
            viz_id="team_performance_radar",
            title="Team Performance Radar",
            description="Team performance metrics across multiple dimensions",
            viz_type=VisualizationType.RADAR_CHART,
            data_source="team_metrics",
            config={
                "axes": [
                    "Cases Handled",
                    "Resolution Time",
                    "Accuracy",
                    "Efficiency",
                    "Quality",
                ],
                "min": 0,
                "max": 100,
            },
            interactive=True,
            real_time=False,
            export_formats=[DataFormat.JSON, DataFormat.PNG, DataFormat.SVG],
        )

        # Transaction Flow Sankey
        transaction_flow_viz = VisualizationConfig(
            viz_id="transaction_flow_sankey",
            title="Transaction Flow Analysis",
            description="Transaction flow visualization",
            viz_type=VisualizationType.SANKEY_DIAGRAM,
            data_source="transactions",
            config={
                "node_colors": self.default_colors,
                "link_colors": self.default_colors,
            },
            interactive=True,
            real_time=False,
            export_formats=[DataFormat.JSON, DataFormat.PNG, DataFormat.SVG],
        )

        # Deadline Timeline
        deadline_timeline_viz = VisualizationConfig(
            viz_id="deadline_timeline",
            title="Regulatory Deadline Timeline",
            description="Upcoming regulatory deadlines",
            viz_type=VisualizationType.TIMELINE,
            data_source="deadlines",
            config={"group_by": "jurisdiction", "color_by": "priority"},
            interactive=True,
            real_time=True,
            export_formats=[DataFormat.JSON, DataFormat.PNG, DataFormat.SVG],
        )

        # Compliance Gauge
        compliance_gauge_viz = VisualizationConfig(
            viz_id="compliance_gauge",
            title="Overall Compliance Score",
            description="Current compliance score gauge",
            viz_type=VisualizationType.GAUGE_CHART,
            data_source="compliance_metrics",
            config={
                "min": 0,
                "max": 100,
                "zones": [
                    {"min": 0, "max": 60, "color": "#ef4444"},
                    {"min": 60, "max": 80, "color": "#f59e0b"},
                    {"min": 80, "max": 100, "color": "#10b981"},
                ],
            },
            interactive=True,
            real_time=True,
            export_formats=[DataFormat.JSON, DataFormat.PNG, DataFormat.SVG],
        )

        # Case Resolution Funnel
        case_funnel_viz = VisualizationConfig(
            viz_id="case_resolution_funnel",
            title="Case Resolution Funnel",
            description="Case resolution process funnel",
            viz_type=VisualizationType.FUNNEL_CHART,
            data_source="cases",
            config={
                "stages": ["Created", "In Progress", "Under Review", "Resolved"],
                "colors": self.default_colors[:4],
            },
            interactive=True,
            real_time=False,
            export_formats=[DataFormat.JSON, DataFormat.PNG, DataFormat.SVG],
        )

        # Add all visualizations
        self.visualizations[sar_trend_viz.viz_id] = sar_trend_viz
        self.visualizations[risk_dist_viz.viz_id] = risk_dist_viz
        self.visualizations[case_status_viz.viz_id] = case_status_viz
        self.visualizations[compliance_timeline_viz.viz_id] = compliance_timeline_viz
        self.visualizations[jurisdiction_viz.viz_id] = jurisdiction_viz
        self.visualizations[risk_heatmap_viz.viz_id] = risk_heatmap_viz
        self.visualizations[team_radar_viz.viz_id] = team_radar_viz
        self.visualizations[transaction_flow_viz.viz_id] = transaction_flow_viz
        self.visualizations[deadline_timeline_viz.viz_id] = deadline_timeline_viz
        self.visualizations[compliance_gauge_viz.viz_id] = compliance_gauge_viz
        self.visualizations[case_funnel_viz.viz_id] = case_funnel_viz

    async def generate_visualization(
        self, viz_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> VisualizationResult:
        """Generate visualization data"""
        try:
            start_time = datetime.now(timezone.utc)

            # Get visualization configuration
            viz_config = self.visualizations.get(viz_id)
            if not viz_config:
                return VisualizationResult(
                    viz_id=viz_id,
                    success=False,
                    data=None,
                    render_time_ms=0,
                    error_message=f"Visualization not found: {viz_id}",
                )

            # Check cache
            cache_key = f"{viz_id}_{hash(str(filters))}" if filters else viz_id
            if cache_key in self.visualization_cache:
                cached_data = self.visualization_cache[cache_key]
                if datetime.now(timezone.utc) - cached_data["timestamp"] < timedelta(
                    minutes=self.cache_ttl_minutes
                ):
                    return VisualizationResult(
                        viz_id=viz_id,
                        success=True,
                        data=cached_data["data"],
                        render_time_ms=0,
                        metadata={"cached": True},
                    )

            # Generate data based on visualization type
            data = await self._generate_visualization_data(viz_config, filters)

            # Calculate render time
            render_time = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000

            # Create result
            result = VisualizationResult(
                viz_id=viz_id,
                success=True,
                data=data,
                render_time_ms=render_time,
                metadata={"cached": False},
            )

            # Cache result
            self.visualization_cache[cache_key] = {
                "data": data,
                "timestamp": datetime.now(timezone.utc),
            }

            return result

        except Exception as e:
            logger.error(f"Failed to generate visualization {viz_id}: {e}")
            return VisualizationResult(
                viz_id=viz_id,
                success=False,
                data=None,
                render_time_ms=0,
                error_message=str(e),
            )

    async def _generate_visualization_data(
        self, viz_config: VisualizationConfig, filters: Optional[Dict[str, Any]]
    ) -> VisualizationData:
        """Generate visualization data based on configuration"""
        try:
            if viz_config.viz_type == VisualizationType.LINE_CHART:
                return await self._generate_line_chart_data(viz_config, filters)
            elif viz_config.viz_type == VisualizationType.BAR_CHART:
                return await self._generate_bar_chart_data(viz_config, filters)
            elif viz_config.viz_type == VisualizationType.PIE_CHART:
                return await self._generate_pie_chart_data(viz_config, filters)
            elif viz_config.viz_type == VisualizationType.DOUGHNUT_CHART:
                return await self._generate_doughnut_chart_data(viz_config, filters)
            elif viz_config.viz_type == VisualizationType.RADAR_CHART:
                return await self._generate_radar_chart_data(viz_config, filters)
            elif viz_config.viz_type == VisualizationType.HEATMAP:
                return await self._generate_heatmap_data(viz_config, filters)
            elif viz_config.viz_type == VisualizationType.SANKEY_DIAGRAM:
                return await self._generate_sankey_data(viz_config, filters)
            elif viz_config.viz_type == VisualizationType.TIMELINE:
                return await self._generate_timeline_data(viz_config, filters)
            elif viz_config.viz_type == VisualizationType.GAUGE_CHART:
                return await self._generate_gauge_data(viz_config, filters)
            elif viz_config.viz_type == VisualizationType.FUNNEL_CHART:
                return await self._generate_funnel_data(viz_config, filters)
            else:
                raise ValueError(
                    f"Unsupported visualization type: {viz_config.viz_type}"
                )

        except Exception as e:
            logger.error(f"Failed to generate visualization data: {e}")
            raise

    async def _generate_line_chart_data(
        self, viz_config: VisualizationConfig, filters: Optional[Dict[str, Any]]
    ) -> VisualizationData:
        """Generate line chart data"""
        try:
            # Mock data generation
            labels = [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ]

            if viz_config.data_source == "regulatory_reports":
                data = [15, 22, 18, 25, 30, 28, 35, 32, 38, 42, 40, 45]
            elif viz_config.data_source == "compliance_metrics":
                data = [85, 87, 86, 89, 88, 90, 91, 89, 92, 90, 93, 95]
            else:
                data = [10, 15, 12, 18, 20, 25, 22, 28, 30, 35, 32, 38]

            datasets = [
                {
                    "label": viz_config.title,
                    "data": data,
                    "borderColor": self.default_colors[0],
                    "backgroundColor": self.default_colors[0] + "20",
                    "tension": viz_config.config.get("tension", 0.4),
                    "fill": viz_config.config.get("fill", False),
                }
            ]

            return VisualizationData(
                viz_id=viz_config.viz_id,
                data={"labels": labels, "datasets": datasets},
                labels=labels,
                datasets=datasets,
                options={
                    "responsive": True,
                    "plugins": {"legend": {"display": True}},
                    "scales": {
                        "y": {
                            "beginAtZero": viz_config.config.get("min", 0),
                            "max": viz_config.config.get("max", None),
                        }
                    },
                },
                generated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Failed to generate line chart data: {e}")
            raise

    async def _generate_bar_chart_data(
        self, viz_config: VisualizationConfig, filters: Optional[Dict[str, Any]]
    ) -> VisualizationData:
        """Generate bar chart data"""
        try:
            if viz_config.data_source == "cases":
                labels = ["Open", "In Progress", "Under Review", "Closed", "Archived"]
                data = [12, 18, 8, 25, 5]
            elif viz_config.data_source == "risk_assessments":
                labels = ["Low", "Medium", "High", "Critical", "Severe"]
                data = [120, 85, 45, 15, 5]
            else:
                labels = ["Category A", "Category B", "Category C", "Category D"]
                data = [25, 35, 20, 15]

            colors = viz_config.config.get("colors", self.default_colors[: len(labels)])

            datasets = [
                {
                    "label": viz_config.title,
                    "data": data,
                    "backgroundColor": colors,
                    "borderColor": colors,
                    "borderWidth": 1,
                }
            ]

            return VisualizationData(
                viz_id=viz_config.viz_id,
                data={"labels": labels, "datasets": datasets},
                labels=labels,
                datasets=datasets,
                options={
                    "responsive": True,
                    "plugins": {"legend": {"display": False}},
                    "scales": {"y": {"beginAtZero": True}},
                },
                generated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Failed to generate bar chart data: {e}")
            raise

    async def _generate_pie_chart_data(
        self, viz_config: VisualizationConfig, filters: Optional[Dict[str, Any]]
    ) -> VisualizationData:
        """Generate pie chart data"""
        try:
            labels = viz_config.config.get("labels", ["A", "B", "C", "D"])
            data = [30, 25, 20, 25]
            colors = viz_config.config.get("colors", self.default_colors[: len(labels)])

            datasets = [
                {
                    "data": data,
                    "backgroundColor": colors,
                    "borderColor": "#ffffff",
                    "borderWidth": 2,
                }
            ]

            return VisualizationData(
                viz_id=viz_config.viz_id,
                data={"labels": labels, "datasets": datasets},
                labels=labels,
                datasets=datasets,
                options={
                    "responsive": True,
                    "plugins": {"legend": {"position": "bottom"}},
                },
                generated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Failed to generate pie chart data: {e}")
            raise

    async def _generate_doughnut_chart_data(
        self, viz_config: VisualizationConfig, filters: Optional[Dict[str, Any]]
    ) -> VisualizationData:
        """Generate doughnut chart data"""
        try:
            labels = viz_config.config.get(
                "labels", ["Low", "Medium", "High", "Critical", "Severe"]
            )
            data = [120, 85, 45, 15, 5]
            colors = viz_config.config.get("colors", self.default_colors[: len(labels)])

            datasets = [
                {
                    "data": data,
                    "backgroundColor": colors,
                    "borderColor": "#ffffff",
                    "borderWidth": 2,
                }
            ]

            return VisualizationData(
                viz_id=viz_config.viz_id,
                data={"labels": labels, "datasets": datasets},
                labels=labels,
                datasets=datasets,
                options={
                    "responsive": True,
                    "plugins": {"legend": {"position": "bottom"}},
                    "cutout": "50%",
                },
                generated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Failed to generate doughnut chart data: {e}")
            raise

    async def _generate_radar_chart_data(
        self, viz_config: VisualizationConfig, filters: Optional[Dict[str, Any]]
    ) -> VisualizationData:
        """Generate radar chart data"""
        try:
            labels = viz_config.config.get(
                "axes", ["Metric 1", "Metric 2", "Metric 3", "Metric 4", "Metric 5"]
            )
            data = [85, 75, 90, 80, 70]

            datasets = [
                {
                    "label": viz_config.title,
                    "data": data,
                    "borderColor": self.default_colors[0],
                    "backgroundColor": self.default_colors[0] + "20",
                    "pointBackgroundColor": self.default_colors[0],
                    "pointBorderColor": "#fff",
                    "pointHoverBackgroundColor": "#fff",
                    "pointHoverBorderColor": self.default_colors[0],
                }
            ]

            return VisualizationData(
                viz_id=viz_config.viz_id,
                data={"labels": labels, "datasets": datasets},
                labels=labels,
                datasets=datasets,
                options={
                    "responsive": True,
                    "plugins": {"legend": {"display": True}},
                    "scales": {
                        "r": {
                            "beginAtZero": True,
                            "max": viz_config.config.get("max", 100),
                        }
                    },
                },
                generated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Failed to generate radar chart data: {e}")
            raise

    async def _generate_heatmap_data(
        self, viz_config: VisualizationConfig, filters: Optional[Dict[str, Any]]
    ) -> VisualizationData:
        """Generate heatmap data"""
        try:
            # Mock heatmap data
            x_labels = ["Week 1", "Week 2", "Week 3", "Week 4"]
            y_labels = [
                "Transaction Risk",
                "Address Risk",
                "Amount Risk",
                "Geographic Risk",
            ]

            data = [
                [0.2, 0.3, 0.4, 0.5],
                [0.1, 0.2, 0.3, 0.4],
                [0.3, 0.4, 0.5, 0.6],
                [0.4, 0.5, 0.6, 0.7],
            ]

            return VisualizationData(
                viz_id=viz_config.viz_id,
                data={
                    "x_labels": x_labels,
                    "y_labels": y_labels,
                    "data": data,
                    "color_scale": viz_config.config.get("color_scale", "viridis"),
                },
                generated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Failed to generate heatmap data: {e}")
            raise

    async def _generate_sankey_data(
        self, viz_config: VisualizationConfig, filters: Optional[Dict[str, Any]]
    ) -> VisualizationData:
        """Generate Sankey diagram data"""
        try:
            # Mock Sankey data
            nodes = [
                {"id": "source1", "name": "Source 1"},
                {"id": "source2", "name": "Source 2"},
                {"id": "intermediate1", "name": "Intermediate 1"},
                {"id": "intermediate2", "name": "Intermediate 2"},
                {"id": "target1", "name": "Target 1"},
                {"id": "target2", "name": "Target 2"},
            ]

            links = [
                {"source": "source1", "target": "intermediate1", "value": 30},
                {"source": "source2", "target": "intermediate2", "value": 25},
                {"source": "intermediate1", "target": "target1", "value": 20},
                {"source": "intermediate2", "target": "target2", "value": 15},
            ]

            return VisualizationData(
                viz_id=viz_config.viz_id,
                data={"nodes": nodes, "links": links},
                generated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Failed to generate Sankey data: {e}")
            raise

    async def _generate_timeline_data(
        self, viz_config: VisualizationConfig, filters: Optional[Dict[str, Any]]
    ) -> VisualizationData:
        """Generate timeline data"""
        try:
            # Mock timeline data
            events = [
                {
                    "date": "2024-01-15",
                    "title": "SAR Report Due",
                    "jurisdiction": "USA",
                    "priority": "high",
                },
                {
                    "date": "2024-01-20",
                    "title": "Quarterly Report",
                    "jurisdiction": "EU",
                    "priority": "medium",
                },
                {
                    "date": "2024-01-25",
                    "title": "Annual Review",
                    "jurisdiction": "UK",
                    "priority": "low",
                },
                {
                    "date": "2024-02-01",
                    "title": "Monthly Report",
                    "jurisdiction": "USA",
                    "priority": "medium",
                },
            ]

            return VisualizationData(
                viz_id=viz_config.viz_id,
                data={"events": events},
                generated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Failed to generate timeline data: {e}")
            raise

    async def _generate_gauge_data(
        self, viz_config: VisualizationConfig, filters: Optional[Dict[str, Any]]
    ) -> VisualizationData:
        """Generate gauge chart data"""
        try:
            # Mock gauge data
            value = 87.5  # Compliance score
            zones = viz_config.config.get(
                "zones",
                [
                    {"min": 0, "max": 60, "color": "#ef4444"},
                    {"min": 60, "max": 80, "color": "#f59e0b"},
                    {"min": 80, "max": 100, "color": "#10b981"},
                ],
            )

            return VisualizationData(
                viz_id=viz_config.viz_id,
                data={
                    "value": value,
                    "min": viz_config.config.get("min", 0),
                    "max": viz_config.config.get("max", 100),
                    "zones": zones,
                },
                generated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Failed to generate gauge data: {e}")
            raise

    async def _generate_funnel_data(
        self, viz_config: VisualizationConfig, filters: Optional[Dict[str, Any]]
    ) -> VisualizationData:
        """Generate funnel chart data"""
        try:
            labels = viz_config.config.get(
                "stages", ["Stage 1", "Stage 2", "Stage 3", "Stage 4"]
            )
            data = [100, 75, 50, 25]  # Decreasing values for funnel
            colors = viz_config.config.get("colors", self.default_colors[: len(labels)])

            datasets = [
                {
                    "label": viz_config.title,
                    "data": data,
                    "backgroundColor": colors,
                    "borderColor": colors,
                    "borderWidth": 1,
                }
            ]

            return VisualizationData(
                viz_id=viz_config.viz_id,
                data={"labels": labels, "datasets": datasets},
                labels=labels,
                datasets=datasets,
                options={"responsive": True, "plugins": {"legend": {"display": False}}},
                generated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Failed to generate funnel data: {e}")
            raise

    async def export_visualization(
        self, viz_id: str, format: DataFormat, filters: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Export visualization in specified format"""
        try:
            # Generate visualization data
            result = await self.generate_visualization(viz_id, filters)

            if not result.success:
                raise ValueError(
                    f"Failed to generate visualization: {result.error_message}"
                )

            # Export based on format
            if format == DataFormat.JSON:
                return await self._export_to_json(result.data)
            elif format == DataFormat.CSV:
                return await self._export_to_csv(result.data)
            elif format == DataFormat.EXCEL:
                return await self._export_to_excel(result.data)
            elif format == DataFormat.PNG:
                return await self._export_to_png(result.data)
            elif format == DataFormat.SVG:
                return await self._export_to_svg(result.data)
            elif format == DataFormat.PDF:
                return await self._export_to_pdf(result.data)
            else:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            logger.error(f"Failed to export visualization {viz_id}: {e}")
            raise

    async def _export_to_json(self, data: VisualizationData) -> bytes:
        """Export visualization data to JSON"""
        try:
            export_data = {
                "viz_id": data.viz_id,
                "generated_at": data.generated_at.isoformat(),
                "data": data.data,
                "metadata": data.metadata,
            }
            return json.dumps(export_data, indent=2, default=str).encode("utf-8")
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            raise

    async def _export_to_csv(self, data: VisualizationData) -> bytes:
        """Export visualization data to CSV"""
        try:
            if not data.labels or not data.datasets:
                raise ValueError("Cannot export chart data to CSV")

            # Create CSV content
            output = io.StringIO()

            # Write header
            header = ["Label"] + [f"Dataset_{i}" for i in range(len(data.datasets))]
            output.write(",".join(header) + "\n")

            # Write data rows
            for i, label in enumerate(data.labels):
                row = [label]
                for dataset in data.datasets:
                    row.append(str(dataset["data"][i]))
                output.write(",".join(row) + "\n")

            return output.getvalue().encode("utf-8")
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            raise

    async def _export_to_excel(self, data: VisualizationData) -> bytes:
        """Export visualization data to Excel"""
        try:
            # This would require openpyxl or similar library
            # For now, return CSV as fallback
            return await self._export_to_csv(data)
        except Exception as e:
            logger.error(f"Failed to export to Excel: {e}")
            raise

    async def _export_to_png(self, data: VisualizationData) -> bytes:
        """Export visualization to PNG"""
        try:
            # This would require a charting library that can render to image
            # For now, return placeholder
            return b"PNG export not implemented yet"
        except Exception as e:
            logger.error(f"Failed to export to PNG: {e}")
            raise

    async def _export_to_svg(self, data: VisualizationData) -> bytes:
        """Export visualization to SVG"""
        try:
            # This would require a charting library that can render to SVG
            # For now, return placeholder
            return b"SVG export not implemented yet"
        except Exception as e:
            logger.error(f"Failed to export to SVG: {e}")
            raise

    async def _export_to_pdf(self, data: VisualizationData) -> bytes:
        """Export visualization to PDF"""
        try:
            # This would require a PDF generation library
            # For now, return placeholder
            return b"PDF export not implemented yet"
        except Exception as e:
            logger.error(f"Failed to export to PDF: {e}")
            raise

    async def create_custom_visualization(self, config: VisualizationConfig) -> bool:
        """Create custom visualization"""
        try:
            self.visualizations[config.viz_id] = config
            logger.info(f"Created custom visualization: {config.viz_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create custom visualization: {e}")
            return False

    async def delete_visualization(self, viz_id: str) -> bool:
        """Delete visualization"""
        try:
            if viz_id in self.visualizations:
                del self.visualizations[viz_id]

                # Clear from cache
                keys_to_remove = [
                    k for k in self.visualization_cache.keys() if k.startswith(viz_id)
                ]
                for key in keys_to_remove:
                    del self.visualization_cache[key]

                logger.info(f"Deleted visualization: {viz_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete visualization {viz_id}: {e}")
            return False

    async def list_visualizations(self) -> List[Dict[str, Any]]:
        """List all available visualizations"""
        try:
            visualizations = []
            for viz_id, config in self.visualizations.items():
                visualizations.append(
                    {
                        "viz_id": viz_id,
                        "title": config.title,
                        "description": config.description,
                        "viz_type": config.viz_type.value,
                        "data_source": config.data_source,
                        "interactive": config.interactive,
                        "real_time": config.real_time,
                        "export_formats": (
                            [f.value for f in config.export_formats]
                            if config.export_formats
                            else []
                        ),
                    }
                )
            return visualizations
        except Exception as e:
            logger.error(f"Failed to list visualizations: {e}")
            return []

    async def clear_cache(self) -> int:
        """Clear visualization cache"""
        try:
            cache_size = len(self.visualization_cache)
            self.visualization_cache.clear()
            logger.info(f"Cleared {cache_size} cached visualizations")
            return cache_size
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0

    async def get_visualization_statistics(self) -> Dict[str, Any]:
        """Get visualization statistics"""
        try:
            total_viz = len(self.visualizations)
            cache_size = len(self.visualization_cache)

            viz_types = defaultdict(int)
            for config in self.visualizations.values():
                viz_types[config.viz_type.value] += 1

            data_sources = defaultdict(int)
            for config in self.visualizations.values():
                data_sources[config.data_source] += 1

            return {
                "total_visualizations": total_viz,
                "cached_visualizations": cache_size,
                "visualization_types": dict(viz_types),
                "data_sources": dict(data_sources),
                "interactive_viz": len(
                    [c for c in self.visualizations.values() if c.interactive]
                ),
                "real_time_viz": len(
                    [c for c in self.visualizations.values() if c.real_time]
                ),
            }
        except Exception as e:
            logger.error(f"Failed to get visualization statistics: {e}")
            return {"error": str(e)}


# Global visualization engine instance
compliance_visualization_engine = ComplianceVisualizationEngine()
