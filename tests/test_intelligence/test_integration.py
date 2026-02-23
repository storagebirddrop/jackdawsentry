"""
Jackdaw Sentry - Intelligence Integration Tests
Cross-module workflow validation and end-to-end testing for Phase 4 Intelligence Integration Hub
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.intelligence.victim_reports import get_victim_reports_db, VictimReportsDatabase
from src.intelligence.threat_feeds import get_threat_intelligence_manager, ThreatIntelligenceManager
from src.intelligence.cross_platform import get_cross_platform_attribution_engine, CrossPlatformAttributionEngine
from src.intelligence.professional_services import get_professional_services_manager, ProfessionalServicesManager


class TestIntelligenceIntegration:
    """Test suite for cross-module intelligence integration"""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock PostgreSQL connection pool"""
        return AsyncMock()

    @pytest.fixture
    async def intelligence_components(self, mock_db_pool):
        """Create all intelligence components with mocked dependencies"""
        with patch("src.intelligence.victim_reports.get_postgres_connection", return_value=mock_db_pool), \
             patch("src.intelligence.threat_feeds.get_postgres_connection", return_value=mock_db_pool), \
             patch("src.intelligence.cross_platform.get_postgres_connection", return_value=mock_db_pool), \
             patch("src.intelligence.professional_services.get_postgres_connection", return_value=mock_db_pool):
            
            victim_reports_db = VictimReportsDatabase(mock_db_pool)
            threat_manager = ThreatIntelligenceManager(mock_db_pool)
            attribution_engine = CrossPlatformAttributionEngine(mock_db_pool)
            services_manager = ProfessionalServicesManager(mock_db_pool)
            
            await victim_reports_db.initialize()
            await threat_manager.initialize()
            await attribution_engine.initialize()
            await services_manager.initialize()
            
            return {
                "victim_reports": victim_reports_db,
                "threat_feeds": threat_manager,
                "attribution": attribution_engine,
                "professional_services": services_manager
            }

    # ---- Victim Reports to Threat Intelligence Integration ----

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_victim_report_to_threat_intelligence_flow(self, intelligence_components, mock_db_pool):
        """Test integration between victim reports and threat intelligence"""
        victim_reports_db = intelligence_components["victim_reports"]
        threat_manager = intelligence_components["threat_feeds"]
        
        # Create a victim report with suspicious addresses
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Mock victim report creation
        report_data = {
            "report_type": "scam",
            "victim_contact": "victim@example.com",
            "incident_date": datetime.now(timezone.utc) - timedelta(days=5),
            "amount_lost": 5000.0,
            "currency": "BTC",
            "description": "Bitcoin investment scam",
            "related_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "severity": "high"
        }
        
        report_id = str(uuid4())
        mock_conn.fetchrow.return_value = {"id": report_id}
        
        report = await victim_reports_db.create_report(report_data)
        
        # Verify report was created
        assert report.id == report_id
        assert report.related_addresses == ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]
        
        # Query threat intelligence for the reported address
        mock_rows = [
            {
                "id": str(uuid4()),
                "feed_id": str(uuid4()),
                "feed_name": "Scam Database",
                "threat_type": "scam",
                "threat_level": "high",
                "title": "Bitcoin Investment Scam",
                "description": "Known Bitcoin investment scam",
                "indicators": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
                "first_seen": datetime.now(timezone.utc) - timedelta(days=30),
                "last_seen": datetime.now(timezone.utc) - timedelta(days=1),
                "confidence_score": 0.9,
                "source_url": "https://scamdb.example.com",
                "tags": ["bitcoin", "investment", "scam"],
                "metadata": {"category": "investment_scam"}
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        threat_items = await threat_manager.query_intelligence(
            "address", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", ["scam"], 30
        )
        
        # Verify threat intelligence was found
        assert len(threat_items) == 1
        assert threat_items[0].threat_type.value == "scam"
        assert "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" in threat_items[0].indicators
        assert threat_items[0].confidence_score == 0.9

    # ---- Cross-Platform Attribution Integration ----

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cross_platform_attribution_consolidation(self, intelligence_components, mock_db_pool):
        """Test cross-platform attribution consolidation from multiple sources"""
        victim_reports_db = intelligence_components["victim_reports"]
        threat_manager = intelligence_components["threat_feeds"]
        attribution_engine = intelligence_components["attribution"]
        
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Mock data from victim reports
        victim_report_data = [
            {
                "source": "victim_reports",
                "confidence_score": 0.8,
                "entity": "Scam Service A",
                "entity_type": "scam",
                "data": {"reports": 3, "verified": True},
                "last_updated": datetime.now(timezone.utc),
                "reliability_score": 0.7,
                "coverage_score": 0.6
            }
        ]
        
        # Mock data from threat intelligence
        threat_intel_data = [
            {
                "source": "threat_intelligence",
                "confidence_score": 0.9,
                "entity": "Scam Service A",
                "entity_type": "scam",
                "data": {"threat_level": "high", "category": "investment"},
                "last_updated": datetime.now(timezone.utc),
                "reliability_score": 0.8,
                "coverage_score": 0.9
            }
        ]
        
        # Combine sources for attribution
        all_source_data = victim_report_data + threat_intel_data
        mock_conn.fetch.return_value = all_source_data
        
        # Perform attribution analysis
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        blockchain = "bitcoin"
        sources = ["victim_reports", "threat_intelligence"]
        
        attribution = await attribution_engine.analyze_address(
            address, blockchain, sources, True, True, 30
        )
        
        # Verify attribution consolidation
        assert attribution.address == address
        assert attribution.blockchain == blockchain
        assert attribution.entity == "Scam Service A"
        assert attribution.confidence_score > 0.8  # Weighted average
        assert len(attribution.sources) == 2
        assert "victim_reports" in attribution.sources
        assert "threat_intelligence" in attribution.sources

    # ---- Professional Services Workflow Integration ----

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_professional_services_workflow(self, intelligence_components, mock_db_pool):
        """Test professional services workflow with intelligence integration"""
        victim_reports_db = intelligence_components["victim_reports"]
        services_manager = intelligence_components["professional_services"]
        
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Create a high-priority victim report
        report_data = {
            "report_type": "hack",
            "victim_contact": "victim@example.com",
            "incident_date": datetime.now(timezone.utc) - timedelta(days=2),
            "amount_lost": 50000.0,
            "currency": "ETH",
            "description": "Major cryptocurrency hack",
            "related_addresses": ["0x742d35Cc6634C0532925a3b844Bc454e4438f44e"],
            "severity": "critical"
        }
        
        report_id = str(uuid4())
        mock_conn.fetchrow.return_value = {"id": report_id}
        
        report = await victim_reports_db.create_report(report_data)
        
        # Create professional service request based on critical report
        service_data = {
            "service_type": "investigation",
            "title": "Cryptocurrency Hack Investigation",
            "description": "Investigation of major cryptocurrency hack affecting victim",
            "priority": "urgent",
            "requested_date": datetime.now(timezone.utc) + timedelta(days=1),
            "duration_hours": 80,
            "budget_range": "$20000-$50000",
            "required_expertise": ["blockchain_forensics", "hack_analysis"],
            "specific_requirements": ["Experience with Ethereum", "Court testimony"],
            "contact_info": {"email": "victim@example.com", "phone": "+1234567890"}
        }
        
        service_id = str(uuid4())
        mock_conn.fetchrow.return_value = {"id": service_id}
        
        service = await services_manager.create_service(service_data)
        
        # Verify service creation
        assert service.service_type.value == "investigation"
        assert service.priority == "urgent"
        assert service.estimated_duration == 80
        
        # Get available professionals for assignment
        mock_rows = [
            {
                "id": str(uuid4()),
                "name": "Dr. Blockchain Expert",
                "expertise_level": "expert",
                "specializations": ["blockchain_forensics", "hack_analysis"],
                "experience_years": 20,
                "hourly_rate": 300.0,
                "availability": {"available": True}
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        professionals = await services_manager.get_professionals(
            {"expertise_level": "expert", "specialization": "blockchain_forensics"}, 50
        )
        
        # Verify professional availability
        assert len(professionals) == 1
        assert professionals[0].expertise_level.value == "expert"
        assert "blockchain_forensics" in professionals[0].specializations

    # ---- End-to-End Intelligence Workflow ----

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_intelligence_workflow(self, intelligence_components, mock_db_pool):
        """Test complete end-to-end intelligence workflow"""
        victim_reports_db = intelligence_components["victim_reports"]
        threat_manager = intelligence_components["threat_feeds"]
        attribution_engine = intelligence_components["attribution"]
        services_manager = intelligence_components["professional_services"]
        
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Step 1: Victim reports a scam
        report_data = {
            "report_type": "scam",
            "victim_contact": "victim@example.com",
            "incident_date": datetime.now(timezone.utc) - timedelta(days=3),
            "amount_lost": 10000.0,
            "currency": "BTC",
            "description": "Bitcoin investment platform scam",
            "related_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "severity": "high"
        }
        
        report_id = str(uuid4())
        mock_conn.fetchrow.return_value = {"id": report_id}
        
        report = await victim_reports_db.create_report(report_data)
        assert report.id == report_id
        
        # Step 2: Threat intelligence confirms the address is malicious
        mock_rows = [
            {
                "id": str(uuid4()),
                "feed_id": str(uuid4()),
                "feed_name": "Threat Intelligence Feed",
                "threat_type": "scam",
                "threat_level": "high",
                "title": "Bitcoin Investment Platform Scam",
                "description": "Known scam platform",
                "indicators": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
                "first_seen": datetime.now(timezone.utc) - timedelta(days=60),
                "last_seen": datetime.now(timezone.utc) - timedelta(days=2),
                "confidence_score": 0.95,
                "source_url": "https://intel.example.com",
                "tags": ["bitcoin", "scam", "investment"],
                "metadata": {"platform": "fake-investment.com"}
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        threat_items = await threat_manager.query_intelligence(
            "address", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", ["scam"], 30
        )
        
        assert len(threat_items) == 1
        assert threat_items[0].confidence_score == 0.95
        
        # Step 3: Cross-platform attribution consolidates information
        source_data = [
            {
                "source": "victim_reports",
                "confidence_score": 0.8,
                "entity": "Fake Investment Platform",
                "entity_type": "scam",
                "data": {"reports": 5, "total_lost": 50000},
                "last_updated": datetime.now(timezone.utc),
                "reliability_score": 0.7,
                "coverage_score": 0.6
            },
            {
                "source": "threat_intelligence",
                "confidence_score": 0.95,
                "entity": "Fake Investment Platform",
                "entity_type": "scam",
                "data": {"platform": "fake-investment.com", "active_since": "2023-01"},
                "last_updated": datetime.now(timezone.utc),
                "reliability_score": 0.9,
                "coverage_score": 0.95
            }
        ]
        mock_conn.fetch.return_value = source_data
        
        attribution = await attribution_engine.analyze_address(
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "bitcoin", 
            ["victim_reports", "threat_intelligence"], True, True, 30
        )
        
        assert attribution.entity == "Fake Investment Platform"
        assert attribution.confidence_score > 0.85  # Weighted average
        assert len(attribution.sources) == 2
        
        # Step 4: Professional services engaged for investigation
        service_data = {
            "service_type": "investigation",
            "title": "Fake Investment Platform Investigation",
            "description": "Comprehensive investigation of scam platform",
            "priority": "high",
            "duration_hours": 60,
            "required_expertise": ["blockchain_analysis", "scam_investigation"],
            "contact_info": {"email": "victim@example.com"}
        }
        
        service_id = str(uuid4())
        mock_conn.fetchrow.return_value = {"id": service_id}
        
        service = await services_manager.create_service(service_data)
        assert service.service_type.value == "investigation"
        assert service.priority == "high"
        
        # Step 5: Verify workflow completion
        # All components should have processed the same address/entity
        assert report.related_addresses == ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]
        assert threat_items[0].indicators == ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]
        assert attribution.address == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        assert service.title == "Fake Investment Platform Investigation"

    # ---- Data Consistency Tests ----

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_data_consistency_across_modules(self, intelligence_components, mock_db_pool):
        """Test data consistency between intelligence modules"""
        victim_reports_db = intelligence_components["victim_reports"]
        threat_manager = intelligence_components["threat_feeds"]
        attribution_engine = intelligence_components["attribution"]
        
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Create consistent test data
        test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        test_entity = "Test Entity"
        
        # Step 1: Create victim report
        report_data = {
            "report_type": "fraud",
            "victim_contact": "test@example.com",
            "incident_date": datetime.now(timezone.utc) - timedelta(days=1),
            "description": "Test fraud case",
            "related_addresses": [test_address],
            "severity": "medium"
        }
        
        report_id = str(uuid4())
        mock_conn.fetchrow.return_value = {"id": report_id}
        
        report = await victim_reports_db.create_report(report_data)
        assert report.related_addresses == [test_address]
        
        # Step 2: Query threat intelligence
        mock_rows = [
            {
                "id": str(uuid4()),
                "feed_id": str(uuid4()),
                "feed_name": "Test Feed",
                "threat_type": "fraud",
                "threat_level": "medium",
                "title": "Test Fraud",
                "description": "Test fraud case",
                "indicators": [test_address],
                "first_seen": datetime.now(timezone.utc) - timedelta(days=30),
                "last_seen": datetime.now(timezone.utc) - timedelta(days=1),
                "confidence_score": 0.75,
                "source_url": "https://test.example.com",
                "tags": ["test", "fraud"],
                "metadata": {"entity": test_entity}
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        threat_items = await threat_manager.query_intelligence(
            "address", test_address, ["fraud"], 30
        )
        
        assert len(threat_items) == 1
        assert threat_items[0].indicators == [test_address]
        assert threat_items[0].metadata["entity"] == test_entity
        
        # Step 3: Perform attribution analysis
        source_data = [
            {
                "source": "victim_reports",
                "confidence_score": 0.7,
                "entity": test_entity,
                "entity_type": "fraud",
                "data": {"reports": 1},
                "last_updated": datetime.now(timezone.utc),
                "reliability_score": 0.6,
                "coverage_score": 0.5
            },
            {
                "source": "threat_intelligence",
                "confidence_score": 0.75,
                "entity": test_entity,
                "entity_type": "fraud",
                "data": {"threat_level": "medium"},
                "last_updated": datetime.now(timezone.utc),
                "reliability_score": 0.7,
                "coverage_score": 0.8
            }
        ]
        mock_conn.fetch.return_value = source_data
        
        attribution = await attribution_engine.analyze_address(
            test_address, "bitcoin", ["victim_reports", "threat_intelligence"], True, True, 30
        )
        
        # Verify data consistency
        assert attribution.address == test_address
        assert attribution.entity == test_entity
        assert attribution.entity_type == "fraud"
        assert len(attribution.sources) == 2

    # ---- Performance Integration Tests ----

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_performance_under_load(self, intelligence_components, mock_db_pool):
        """Test system performance under concurrent load"""
        victim_reports_db = intelligence_components["victim_reports"]
        threat_manager = intelligence_components["threat_feeds"]
        
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Create multiple concurrent requests
        import asyncio
        
        async def create_victim_report(index):
            report_data = {
                "report_type": "scam",
                "victim_contact": f"victim{index}@example.com",
                "incident_date": datetime.now(timezone.utc) - timedelta(days=index),
                "description": f"Test scam report {index}",
                "related_addresses": [f"test_address_{index}"],
                "severity": "medium"
            }
            
            report_id = str(uuid4())
            mock_conn.fetchrow.return_value = {"id": report_id}
            
            return await victim_reports_db.create_report(report_data)
        
        async def query_threat_intelligence(address):
            mock_rows = [
                {
                    "id": str(uuid4()),
                    "feed_id": str(uuid4()),
                    "feed_name": "Test Feed",
                    "threat_type": "scam",
                    "threat_level": "medium",
                    "title": "Test Scam",
                    "description": "Test scam",
                    "indicators": [address],
                    "first_seen": datetime.now(timezone.utc) - timedelta(days=30),
                    "last_seen": datetime.now(timezone.utc) - timedelta(days=1),
                    "confidence_score": 0.7,
                    "source_url": "https://test.example.com",
                    "tags": ["test", "scam"],
                    "metadata": {}
                }
            ]
            mock_conn.fetch.return_value = mock_rows
            
            return await threat_manager.query_intelligence("address", address, ["scam"], 30)
        
        # Run concurrent operations
        tasks = []
        
        # Create 10 victim reports concurrently
        for i in range(10):
            tasks.append(create_victim_report(i))
        
        # Query threat intelligence for 10 addresses concurrently
        for i in range(10):
            tasks.append(query_threat_intelligence(f"test_address_{i}"))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed successfully
        assert len(results) == 20
        
        # First 10 should be victim reports
        for i in range(10):
            assert isinstance(results[i], type(results[0]))  # Same type (VictimReport)
        
        # Last 10 should be threat intelligence results
        for i in range(10, 20):
            assert isinstance(results[i], list)  # List of threat items
            assert len(results[i]) == 1  # One result per query

    # ---- Error Handling Integration Tests ----

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_propagation_across_modules(self, intelligence_components, mock_db_pool):
        """Test error handling and propagation across integrated modules"""
        victim_reports_db = intelligence_components["victim_reports"]
        threat_manager = intelligence_components["threat_feeds"]
        
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Test database connection error in victim reports
        mock_conn.execute.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await victim_reports_db.create_report({
                "report_type": "scam",
                "victim_contact": "test@example.com",
                "incident_date": datetime.now(timezone.utc),
                "description": "Test report"
            })
        
        # Reset mock for next test
        mock_conn.reset_mock()
        
        # Test threat intelligence query error
        mock_conn.fetch.side_effect = Exception("Query failed")
        
        with pytest.raises(Exception, match="Query failed"):
            await threat_manager.query_intelligence("address", "test_address", ["scam"], 30)

    # ---- Data Validation Integration Tests ----

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_data_validation_across_modules(self, intelligence_components, mock_db_pool):
        """Test data validation consistency across modules"""
        victim_reports_db = intelligence_components["victim_reports"]
        threat_manager = intelligence_components["threat_feeds"]
        attribution_engine = intelligence_components["attribution"]
        
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Test invalid data in victim reports
        with pytest.raises(ValueError, match="Invalid report type"):
            await victim_reports_db.create_report({
                "report_type": "invalid_type",
                "victim_contact": "test@example.com",
                "incident_date": datetime.now(timezone.utc),
                "description": "Test report"
            })
        
        # Test invalid blockchain in attribution
        with pytest.raises(ValueError, match="Invalid blockchain"):
            await attribution_engine.analyze_address(
                "test_address", "invalid_blockchain", ["all"], True, True, 30
            )
        
        # Test invalid threat type in threat intelligence query
        mock_conn.fetch.return_value = []
        
        # This should not raise an error but return empty results
        results = await threat_manager.query_intelligence(
            "address", "test_address", ["invalid_type"], 30
        )
        
        assert len(results) == 0  # Empty results for invalid threat type
