"""
End-to-End Integration Testing
Tests complete investigation workflows and multi-blockchain analysis scenarios
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json
from datetime import datetime, timezone, timedelta


class TestInvestigationWorkflow:
    """Test complete investigation lifecycle"""

    def test_complete_investigation_workflow(self, client):
        """Test full investigation from creation to resolution"""
        # Step 1: Create investigation
        investigation_response = client.post("/api/v1/investigations", json={
            "title": "Suspicious Bitcoin Mixer Investigation",
            "description": "Investigation of potential mixing activity",
            "priority": "high",
            "addresses": ["bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"],
            "blockchain": "bitcoin",
            "time_range_start": "2024-01-01T00:00:00Z",
            "time_range_end": "2024-12-31T23:59:59Z",
            "tags": ["mixing", "high_risk"]
        })
        
        assert investigation_response.status_code == 201
        investigation = investigation_response.json()
        investigation_id = investigation["id"]
        
        # Step 2: Run comprehensive analysis
        analysis_response = client.post(f"/api/v1/investigations/{investigation_id}/analyze", json={
            "analysis_types": ["address_analysis", "pattern_detection", "cross_chain"],
            "include_attribution": True,
            "include_risk_scoring": True
        })
        
        assert analysis_response.status_code == 200
        analysis = analysis_response.json()
        
        # Should have analysis results
        assert "address_analysis" in analysis
        assert "pattern_detection" in analysis
        assert "cross_chain_analysis" in analysis
        assert "risk_assessment" in analysis
        
        # Step 3: Add evidence
        evidence_response = client.post(f"/api/v1/investigations/{investigation_id}/evidence", json={
            "type": "pattern_detection",
            "description": "Mixing pattern detected with high confidence",
            "data": {
                "pattern_type": "mixing",
                "confidence": 0.92,
                "mixing_service": "Tornado Cash",
                "evidence_transactions": ["0x...mix1", "0x...mix2"]
            },
            "source": "automated_analysis",
            "severity": "high"
        })
        
        assert evidence_response.status_code == 201
        evidence = evidence_response.json()
        assert evidence["type"] == "pattern_detection"
        assert evidence["severity"] == "high"
        
        # Step 4: Generate AI narrative
        narrative_response = client.post(f"/api/v1/investigations/{investigation_id}/narrative", json={
            "narrative_type": "investigation_summary",
            "include_evidence": True,
            "include_recommendations": True,
            "language": "english"
        })
        
        assert narrative_response.status_code == 200
        narrative = narrative_response.json()
        
        # Should have narrative content
        assert "narrative" in narrative
        assert "summary" in narrative["narrative"]
        assert "findings" in narrative["narrative"]
        assert "recommendations" in narrative["narrative"]
        
        # Step 5: Generate compliance report
        report_response = client.post(f"/api/v1/investigations/{investigation_id}/report", json={
            "report_type": "sar",
            "format": "pdf",
            "include_sensitive_data": False,
            "jurisdiction": "US"
        })
        
        assert report_response.status_code == 200
        report = report_response.json()
        
        # Should have report information
        assert "report_id" in report
        assert "download_url" in report
        assert "report_type" in report
        assert report["report_type"] == "sar"
        
        # Step 6: Update investigation status
        update_response = client.patch(f"/api/v1/investigations/{investigation_id}", json={
            "status": "ready_for_review",
            "assigned_to": "senior_analyst",
            "notes": "Investigation complete, ready for senior review"
        })
        
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["status"] == "ready_for_review"
        assert updated["assigned_to"] == "senior_analyst"
        
        # Step 7: Close investigation
        close_response = client.patch(f"/api/v1/investigations/{investigation_id}/close", json={
            "resolution": "suspicious_activity_confirmed",
            "resolution_notes": "Mixing activity confirmed, SAR filed",
            "closed_by": "senior_analyst",
            "follow_up_required": True,
            "follow_up_date": "2024-02-01T00:00:00Z"
        })
        
        assert close_response.status_code == 200
        closed = close_response.json()
        assert closed["status"] == "closed"
        assert closed["resolution"] == "suspicious_activity_confirmed"

    def test_cross_chain_investigation(self, client):
        """Test investigation spanning multiple blockchains"""
        # Create cross-chain investigation
        investigation_response = client.post("/api/v1/investigations", json={
            "title": "Cross-Chain Bridge Hopping Investigation",
            "description": "Analysis of suspicious bridge activity across chains",
            "priority": "critical",
            "addresses": [
                {"address": "1...btc_start", "blockchain": "bitcoin"},
                {"address": "0x...eth_bridge", "blockchain": "ethereum"},
                {"address": "9Wz...sol_end", "blockchain": "solana"}
            ],
            "blockchain": "multi",
            "time_range_start": "2024-01-01T00:00:00Z",
            "time_range_end": "2024-12-31T23:59:59Z"
        })
        
        assert investigation_response.status_code == 201
        investigation = investigation_response.json()
        investigation_id = investigation["id"]
        
        # Run cross-chain analysis
        analysis_response = client.post(f"/api/v1/investigations/{investigation_id}/analyze", json={
            "analysis_types": ["cross_chain", "bridge_tracking", "entity_linking"],
            "include_stablecoin_flows": True,
            "include_bridge_analysis": True
        })
        
        assert analysis_response.status_code == 200
        analysis = analysis_response.json()
        
        # Should have cross-chain results
        assert "cross_chain_analysis" in analysis
        assert "bridge_tracking" in analysis
        assert "entity_linking" in analysis
        assert "stablecoin_flows" in analysis
        
        # Generate cross-chain report
        report_response = client.post(f"/api/v1/investigations/{investigation_id}/report", json={
            "report_type": "cross_chain_analysis",
            "format": "html",
            "include_visualizations": True,
            "include_timeline": True
        })
        
        assert report_response.status_code == 200
        report = report_response.json()
        assert report["report_type"] == "cross_chain_analysis"

    def test_collaborative_investigation(self, client):
        """Test investigation with multiple analysts"""
        # Create investigation
        investigation_response = client.post("/api/v1/investigations", json={
            "title": "Team Investigation - Exchange Monitoring",
            "description": "Collaborative investigation of exchange-related activity",
            "priority": "medium",
            "addresses": ["1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"],
            "blockchain": "bitcoin",
            "team_members": ["analyst_001", "analyst_002", "analyst_003"],
            "time_range_start": "2024-01-01T00:00:00Z",
            "time_range_end": "2024-12-31T23:59:59Z"
        })
        
        assert investigation_response.status_code == 201
        investigation = investigation_response.json()
        investigation_id = investigation["id"]
        
        # Assign tasks to team members
        task_response = client.post(f"/api/v1/investigations/{investigation_id}/tasks", json={
            "tasks": [
                {
                    "title": "Address attribution research",
                    "assigned_to": "analyst_001",
                    "priority": "high",
                    "due_date": "2024-01-15T00:00:00Z"
                },
                {
                    "title": "Pattern analysis",
                    "assigned_to": "analyst_002", 
                    "priority": "medium",
                    "due_date": "2024-01-20T00:00:00Z"
                },
                {
                    "title": "Risk assessment",
                    "assigned_to": "analyst_003",
                    "priority": "high",
                    "due_date": "2024-01-18T00:00:00Z"
                }
            ]
        })
        
        assert task_response.status_code == 201
        tasks = task_response.json()
        assert len(tasks["tasks"]) == 3
        
        # Add comments and updates
        comment_response = client.post(f"/api/v1/investigations/{investigation_id}/comments", json={
            "comment": "Initial analysis shows exchange hot wallet activity",
            "author": "analyst_001",
            "mentions": ["analyst_002", "analyst_003"]
        })
        
        assert comment_response.status_code == 201
        comment = comment_response.json()
        assert comment["author"] == "analyst_001"

    def test_investigation_with_real_time_updates(self, client):
        """Test investigation with real-time monitoring"""
        # Create investigation with monitoring
        investigation_response = client.post("/api/v1/investigations", json={
            "title": "Real-time Monitoring Investigation",
            "description": "Monitor address for new activity",
            "priority": "high",
            "addresses": ["bc1q...monitor"],
            "blockchain": "bitcoin",
            "monitoring_enabled": True,
            "monitoring_duration_hours": 24,
            "alert_thresholds": {
                "risk_score": 0.7,
                "transaction_volume": 10000
            }
        })
        
        assert investigation_response.status_code == 201
        investigation = investigation_response.json()
        investigation_id = investigation["id"]
        
        # Start monitoring
        monitor_response = client.post(f"/api/v1/investigations/{investigation_id}/monitor", json={
            "enabled": True,
            "alert_channels": ["email", "slack"],
            "update_frequency": "real_time"
        })
        
        assert monitor_response.status_code == 200
        monitor = monitor_response.json()
        assert monitor["enabled"] is True
        
        # Check monitoring status
        status_response = client.get(f"/api/v1/investigations/{investigation_id}/monitoring/status")
        
        assert status_response.status_code == 200
        status = status_response.json()
        assert "monitoring_active" in status
        assert "alerts_triggered" in status


class TestComplianceWorkflows:
    """Test compliance and regulatory workflows"""

    def test_aml_compliance_workflow(self, client):
        """Test complete AML compliance workflow"""
        # Step 1: Address screening
        screening_response = client.post("/api/v1/compliance/screen", json={
            "addresses": ["bc1q...suspicious", "0x...suspicious"],
            "screening_types": ["sanctions", "pep", "risk_scoring"],
            "jurisdictions": ["US", "EU", "UK"],
            "include_evidence": True
        })
        
        assert screening_response.status_code == 200
        screening = screening_response.json()
        
        # Should have screening results
        assert "screening_results" in screening
        assert "overall_risk" in screening
        assert "recommendations" in screening
        
        # Step 2: Risk assessment
        risk_response = client.post("/api/v1/compliance/risk-assessment", json={
            "entity": {
                "addresses": ["bc1q...suspicious"],
                "entity_type": "individual",
                "jurisdiction": "US"
            },
            "assessment_type": "standard",
            "include_factors": ["transaction_patterns", "entity_attribution", "geographic_risk"]
        })
        
        assert risk_response.status_code == 200
        risk = risk_response.json()
        
        # Should have risk assessment
        assert "risk_score" in risk
        assert "risk_factors" in risk
        assert "risk_level" in risk
        assert 0.0 <= risk["risk_score"] <= 1.0
        
        # Step 3: Generate SAR if high risk
        if risk["risk_score"] > 0.7:
            sar_response = client.post("/api/v1/compliance/reports/sar", json={
                "suspicious_addresses": ["bc1q...suspicious"],
                "suspicion_reason": "Unusual transaction patterns detected",
                "reporting_period": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-31T23:59:59Z"
                },
                "filer_details": {
                    "name": "Test Financial Institution",
                    "address": "123 Main St, New York, NY",
                    "contact": "compliance@example.com"
                }
            })
            
            assert sar_response.status_code == 200
            sar = sar_response.json()
            assert "sar_id" in sar
            assert "filing_status" in sar

    def test_gdpr_compliance_workflow(self, client):
        """Test GDPR compliance workflow"""
        # Step 1: Data subject request
        dsr_response = client.post("/api/v1/compliance/gdpr/data-request", json={
            "request_type": "access",
            "data_subject_id": "user_12345",
            "request_details": {
                "name": "John Doe",
                "email": "john@example.com",
                "verification": "document_id_123"
            },
            "data_categories": ["transactions", "analysis_results", "investigations"]
        })
        
        assert dsr_response.status_code == 200
        dsr = dsr_response.json()
        assert "request_id" in dsr
        assert "status" in dsr
        
        # Step 2: Data export
        export_response = client.post("/api/v1/compliance/gdpr/data-export", json={
            "request_id": dsr["request_id"],
            "format": "json",
            "include_anonymized": True,
            "redaction_rules": ["sensitive_data", "third_party_info"]
        })
        
        assert export_response.status_code == 200
        export = export_response.json()
        assert "export_id" in export
        assert "download_url" in export
        assert "record_count" in export
        
        # Step 3: Data deletion request
        deletion_response = client.post("/api/v1/compliance/gdpr/delete-request", json={
            "data_subject_id": "user_12345",
            "reason": "withdrawal_of_consent",
            "verification": "document_id_456",
            "retention_exemption": False
        })
        
        assert deletion_response.status_code == 200
        deletion = deletion_response.json()
        assert "deletion_id" in deletion
        assert "status" in deletion

    def test_travel_rule_compliance(self, client):
        """Test Travel Rule compliance workflow"""
        # Step 1: Transaction reporting
        travel_response = client.post("/api/v1/compliance/travel-rule/report", json={
            "transaction": {
                "originator": {
                    "name": "Sender Name",
                    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                    "account_number": "ACC123456"
                },
                "beneficiary": {
                    "name": "Receiver Name", 
                    "address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
                    "account_number": "ACC789012"
                },
                "amount": 1000.0,
                "currency": "BTC",
                "blockchain": "bitcoin",
                "transaction_hash": "0x...tx_hash",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payment_method": "crypto_transfer"
            },
            "reporting_entity": {
                "name": "Financial Institution",
                "address": "123 Finance St",
                "contact": "compliance@example.com"
            }
        })
        
        assert travel_response.status_code == 200
        travel = travel_response.json()
        assert "report_id" in travel
        assert "compliance_status" in travel
        
        # Step 2: Information sharing
        sharing_response = client.post("/api/v1/compliance/travel-rule/share", json={
            "report_id": travel["report_id"],
            "beneficiary_institution": "Beneficiary Bank",
            "shared_fields": ["originator", "amount", "currency", "timestamp"],
            "purpose": "regulatory_compliance"
        })
        
        assert sharing_response.status_code == 200
        sharing = sharing_response.json()
        assert "sharing_id" in sharing
        assert "shared_with" in sharing


class TestMultiBlockchainAnalysis:
    """Test analysis across multiple blockchain ecosystems"""

    def test_ecosystem_comparison_analysis(self, client):
        """Test comparative analysis across blockchain ecosystems"""
        response = client.post("/api/v1/analysis/ecosystem-comparison", json={
            "addresses": {
                "bitcoin": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
                "ethereum": ["0x742d35Cc6634C0532925a3b8D4E7E0E0e9e0dF3"],
                "solana": ["9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"]
            },
            "analysis_types": ["risk_scoring", "pattern_detection", "entity_attribution"],
            "comparison_metrics": ["risk_levels", "pattern_types", "entity_categories"],
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have comparison results
        assert "ecosystem_comparison" in data
        assert "blockchain_analysis" in data
        assert "cross_ecosystem_patterns" in data
        
        # Validate comparison structure
        comparison = data["ecosystem_comparison"]
        assert "bitcoin" in comparison
        assert "ethereum" in comparison
        assert "solana" in comparison

    def test_defi_protocol_analysis(self, client):
        """Test DeFi protocol interaction analysis"""
        response = client.post("/api/v1/analysis/defi-protocols", json={
            "protocols": ["uniswap", "curve", "aave", "compound"],
            "addresses": ["0x...user_wallet"],
            "blockchain": "ethereum",
            "analysis_types": ["interaction_patterns", "volume_analysis", "risk_assessment"],
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have DeFi analysis
        assert "defi_interactions" in data
        assert "protocol_analysis" in data
        assert "risk_assessment" in data
        
        # Validate DeFi structure
        defi = data["defi_interactions"]
        assert isinstance(defi, list)
        if defi:
            interaction = defi[0]
            assert "protocol" in interaction
            assert "interaction_type" in interaction
            assert "volume" in interaction

    def test_privacy_tool_analysis(self, client):
        """Test privacy tool and mixing service analysis"""
        response = client.post("/api/v1/analysis/privacy-tools", json={
            "tools": ["tornado_cash", "wasabi", "samourai", "monero"],
            "addresses": ["bc1q...privacy_user"],
            "blockchain": "bitcoin",
            "analysis_depth": "deep",
            "include_attribution": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have privacy tool analysis
        assert "privacy_tool_usage" in data
        assert "anonymity_analysis" in data
        assert "risk_assessment" in data
        
        # Validate privacy analysis
        privacy = data["privacy_tool_usage"]
        assert isinstance(privacy, list)
        if privacy:
            tool = privacy[0]
            assert "tool_name" in tool
            assert "usage_count" in tool
            assert "anonymity_score" in tool

    def test_institutional_flow_analysis(self, client):
        """Test institutional and exchange flow analysis"""
        response = client.post("/api/v1/analysis/institutional-flows", json={
            "institutions": ["binance", "coinbase", "kraken", "gemini"],
            "addresses": ["1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"],
            "blockchain": "bitcoin",
            "flow_types": ["deposits", "withdrawals", "internal_transfers"],
            "include_volume_analysis": True,
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have institutional analysis
        assert "institutional_flows" in data
        assert "volume_analysis" in data
        assert "compliance_metrics" in data
        
        # Validate institutional structure
        institutional = data["institutional_flows"]
        assert isinstance(institutional, list)
        if institutional:
            flow = institutional[0]
            assert "institution" in flow
            assert "flow_type" in flow
            assert "volume" in flow


class TestPerformanceUnderLoad:
    """Test system performance under realistic load"""

    def test_concurrent_investigations(self, client):
        """Test multiple concurrent investigations"""
        import threading
        import time
        
        results = []
        
        def create_investigation():
            response = client.post("/api/v1/investigations", json={
                "title": f"Concurrent Investigation {threading.current_thread().ident}",
                "description": "Test investigation for load testing",
                "priority": "medium",
                "addresses": [f"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfN{threading.current_thread().ident}"],
                "blockchain": "bitcoin"
            })
            results.append(response.status_code)
        
        # Start 10 concurrent investigations
        threads = []
        start_time = time.time()
        
        for _ in range(10):
            thread = threading.Thread(target=create_investigation)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All investigations should succeed
        assert all(status == 201 for status in results)
        # Should complete within reasonable time
        assert total_time < 10.0

    def test_large_dataset_analysis(self, client):
        """Test analysis with large datasets"""
        # Create large address set
        addresses = [f"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfN{i:04d}" for i in range(100)]
        
        response = client.post("/api/v1/analysis/bulk", json={
            "addresses": addresses,
            "blockchain": "bitcoin",
            "analysis_types": ["risk_scoring", "pattern_detection"],
            "parallel_processing": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle large dataset
        assert "results" in data
        assert len(data["results"]) == len(addresses)
        assert "processing_metadata" in data
        
        # Validate processing metadata
        metadata = data["processing_metadata"]
        assert "processing_time" in metadata
        assert "parallel_workers" in metadata
        assert metadata["processing_time"] < 30.0  # Should complete within 30 seconds

    def test_real_time_monitoring_performance(self, client):
        """Test real-time monitoring performance"""
        # Set up monitoring for multiple addresses
        addresses = ["bc1q...monitor1", "bc1q...monitor2", "bc1q...monitor3"]
        
        setup_response = client.post("/api/v1/monitoring/setup", json={
            "addresses": addresses,
            "monitoring_types": ["transactions", "risk_changes", "pattern_detection"],
            "update_frequency": "real_time",
            "alert_thresholds": {
                "risk_score_change": 0.1,
                "new_pattern": True
            }
        })
        
        assert setup_response.status_code == 200
        setup = setup_response.json()
        assert "monitoring_id" in setup
        
        # Test monitoring performance
        start_time = time.time()
        
        # Simulate monitoring updates
        for i in range(50):
            update_response = client.post(f"/api/v1/monitoring/{setup['monitoring_id']}/update", json={
                "address": addresses[i % len(addresses)],
                "update_type": "risk_score",
                "new_value": 0.5 + (i * 0.01),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            assert update_response.status_code == 200
        
        end_time = time.time()
        update_time = end_time - start_time
        
        # Should handle updates efficiently
        assert update_time < 5.0  # 50 updates in < 5 seconds

    @pytest.mark.integration
    def test_end_to_end_with_real_data(self, client):
        """Test complete workflow with real blockchain data"""
        # This test requires actual blockchain connections
        
        # Step 1: Real address analysis
        analysis_response = client.post("/api/v1/analysis/address", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "include_patterns": True,
            "include_attribution": True,
            "include_transactions": True
        })
        
        assert analysis_response.status_code == 200
        analysis = analysis_response.json()
        
        # Step 2: Create investigation with real data
        investigation_response = client.post("/api/v1/investigations", json={
            "title": "Real Data Investigation",
            "description": "Investigation using real blockchain data",
            "priority": "medium",
            "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "blockchain": "bitcoin",
            "time_range_start": "2024-01-01T00:00:00Z",
            "time_range_end": "2024-12-31T23:59:59Z"
        })
        
        assert investigation_response.status_code == 201
        investigation = investigation_response.json()
        
        # Step 3: Generate comprehensive report
        report_response = client.post(f"/api/v1/investigations/{investigation['id']}/report", json={
            "report_type": "comprehensive",
            "format": "html",
            "include_visualizations": True,
            "include_raw_data": False
        })
        
        assert report_response.status_code == 200
        report = report_response.json()
        
        # Should have real data in report
        assert "report_id" in report
        assert "data_sources" in report
        assert "blockchain_data" in report["data_sources"]


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios"""

    def test_investigation_creation_error_handling(self, client):
        """Test error handling in investigation creation"""
        # Test with invalid data
        response = client.post("/api/v1/investigations", json={
            "title": "",  # Empty title
            "description": "Test",
            "priority": "invalid_priority",
            "addresses": [],  # Empty addresses
            "blockchain": "invalid_chain"
        })
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "validation_errors" in data

    def test_analysis_service_failure_recovery(self, client):
        """Test recovery from analysis service failures"""
        # Create investigation
        inv_response = client.post("/api/v1/investigations", json={
            "title": "Recovery Test Investigation",
            "description": "Test error recovery",
            "priority": "low",
            "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "blockchain": "bitcoin"
        })
        
        assert inv_response.status_code == 201
        investigation_id = inv_response.json()["id"]
        
        # Simulate service failure and retry
        response = client.post(f"/api/v1/investigations/{investigation_id}/analyze", json={
            "analysis_types": ["address_analysis"],
            "retry_on_failure": True,
            "max_retries": 3
        })
        
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 500, 503]

    def test_partial_analysis_completion(self, client):
        """Test handling of partial analysis completion"""
        # Create investigation
        inv_response = client.post("/api/v1/investigations", json={
            "title": "Partial Analysis Test",
            "description": "Test partial completion",
            "priority": "medium",
            "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "blockchain": "bitcoin"
        })
        
        investigation_id = inv_response.json()["id"]
        
        # Request multiple analysis types
        response = client.post(f"/api/v1/investigations/{investigation_id}/analyze", json={
            "analysis_types": ["address_analysis", "pattern_detection", "cross_chain", "entity_linking"],
            "allow_partial_completion": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should indicate completion status
        assert "completion_status" in data
        assert "completed_analyses" in data
        assert "failed_analyses" in data
        assert isinstance(data["completed_analyses"], list)

    def test_data_consistency_validation(self, client):
        """Test data consistency across analysis components"""
        # Create investigation
        inv_response = client.post("/api/v1/investigations", json={
            "title": "Consistency Test",
            "description": "Test data consistency",
            "priority": "medium",
            "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "blockchain": "bitcoin"
        })
        
        investigation_id = inv_response.json()["id"]
        
        # Run analysis with consistency checks
        response = client.post(f"/api/v1/investigations/{investigation_id}/analyze", json={
            "analysis_types": ["address_analysis", "pattern_detection"],
            "validate_consistency": True,
            "cross_validate_results": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have consistency validation
        assert "consistency_validation" in data
        assert "cross_validation" in data
        
        consistency = data["consistency_validation"]
        assert "is_consistent" in consistency
        assert "inconsistencies" in consistency
        assert isinstance(consistency["inconsistencies"], list)
