"""
Jackdaw Sentry - Evidence Manager Unit Tests
Tests for evidence chain management and integrity verification
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import hashlib
import json

from src.forensics.evidence_manager import (
    EvidenceManager,
    EvidenceType,
    EvidenceIntegrity,
    Evidence,
    ChainOfCustody,
    EvidenceStatistics,
)


class TestEvidenceManager:
    """Test suite for EvidenceManager"""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock PostgreSQL connection pool"""
        return AsyncMock()

    @pytest.fixture
    def evidence_manager(self, mock_db_pool):
        """Create EvidenceManager instance with mocked dependencies"""
        with patch("src.forensics.evidence_manager.get_postgres_connection", return_value=mock_db_pool):
            return EvidenceManager(mock_db_pool)

    # ---- Initialization Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_manager_initializes(self, evidence_manager, mock_db_pool):
        """Test manager initialization creates required schema"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        await evidence_manager.initialize()
        
        # Verify schema creation queries were executed
        assert mock_conn.execute.call_count >= 1
        mock_pool.acquire.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_manager_shutdown(self, evidence_manager):
        """Test manager shutdown"""
        evidence_manager.running = True
        await evidence_manager.shutdown()
        assert evidence_manager.running is False

    # ---- Evidence Creation Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_evidence_success(self, evidence_manager, mock_db_pool):
        """Test successful evidence creation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": str(uuid4())}
        
        evidence_data = {
            "case_id": str(uuid4()),
            "title": "Bitcoin Transaction Evidence",
            "description": "Suspicious Bitcoin transaction related to fraud case",
            "evidence_type": "transaction_data",
            "source_location": "https://blockchain.info/tx/123456",
            "collection_date": datetime.now(timezone.utc),
            "collected_by": "investigator_123",
            "hash_value": "a1b2c3d4e5f6789012345678901234567890abcdef",
            "file_size_bytes": 1024,
            "metadata": {
                "transaction_hash": "1234567890abcdef",
                "block_number": 12345,
                "confirmations": 6
            },
            "tags": ["bitcoin", "transaction", "fraud"]
        }
        
        evidence = await evidence_manager.create_evidence(evidence_data)
        
        assert isinstance(evidence, Evidence)
        assert evidence.title == "Bitcoin Transaction Evidence"
        assert evidence.evidence_type == EvidenceType.TRANSACTION_DATA
        assert evidence.case_id == evidence_data["case_id"]
        assert evidence.collected_by == "investigator_123"
        assert evidence.hash_value == "a1b2c3d4e5f6789012345678901234567890abcdef"
        assert evidence.integrity_status == EvidenceIntegrity.UNKNOWN
        assert evidence.chain_of_custody_verified is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_evidence_with_file_hash(self, evidence_manager, mock_db_pool):
        """Test evidence creation with automatic file hashing"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": str(uuid4())}
        
        evidence_data = {
            "case_id": str(uuid4()),
            "title": "Evidence File",
            "description": "Evidence file for hashing",
            "evidence_type": "documents",
            "source_location": "/path/to/evidence.pdf",
            "collection_date": datetime.now(timezone.utc),
            "collected_by": "investigator_123",
            "file_size_bytes": 2048,
            "metadata": {}
        }
        
        # Mock file reading for hashing
        with patch("builtins.open", mock_open(read_data=b"test file content")):
            evidence = await evidence_manager.create_evidence(evidence_data)
        
        # Verify hash was calculated
        assert evidence.hash_value is not None
        assert len(evidence.hash_value) == 64  # SHA256 hex length

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_evidence_invalid_data(self, evidence_manager):
        """Test evidence creation with invalid data"""
        invalid_data = {
            "case_id": "",  # Empty required field
            "title": "",  # Empty required field
            "evidence_type": "invalid_type",  # Invalid enum value
            "source_location": "",  # Empty required field
            "collection_date": "not_a_datetime",  # Invalid date format
            "collected_by": ""  # Empty required field
        }
        
        with pytest.raises(ValueError, match="Case ID is required"):
            await evidence_manager.create_evidence(invalid_data)

    # ---- Evidence Retrieval Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_evidence_success(self, evidence_manager, mock_db_pool):
        """Test successful evidence retrieval"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        evidence_id = str(uuid4())
        mock_row = {
            "id": evidence_id,
            "case_id": str(uuid4()),
            "title": "Blockchain Analysis Report",
            "description": "Comprehensive blockchain analysis",
            "evidence_type": "address_analysis",
            "source_location": "internal_analysis",
            "collection_date": datetime.now(timezone.utc) - timedelta(days=5),
            "collected_by": "analyst_456",
            "hash_value": "b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c",
            "file_size_bytes": 4096,
            "integrity_status": "verified",
            "chain_of_custody_verified": True,
            "metadata": {"analysis_type": "cluster", "addresses_analyzed": 150},
            "tags": ["blockchain", "analysis", "cluster"],
            "created_date": datetime.now(timezone.utc) - timedelta(days=5),
            "last_updated": datetime.now(timezone.utc) - timedelta(days=1)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        evidence = await evidence_manager.get_evidence(evidence_id)
        
        assert evidence is not None
        assert evidence.id == evidence_id
        assert evidence.title == "Blockchain Analysis Report"
        assert evidence.evidence_type == EvidenceType.ADDRESS_ANALYSIS
        assert evidence.integrity_status == EvidenceIntegrity.VERIFIED
        assert evidence.chain_of_custody_verified is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_evidence_not_found(self, evidence_manager, mock_db_pool):
        """Test evidence retrieval when evidence doesn't exist"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        evidence = await evidence_manager.get_evidence("nonexistent_id")
        assert evidence is None

    # ---- Evidence Update Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_evidence_success(self, evidence_manager, mock_db_pool):
        """Test successful evidence update"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        evidence_id = str(uuid4())
        update_data = {
            "title": "Updated Evidence Title",
            "integrity_status": "verified",
            "notes": "Evidence verified and validated",
            "metadata": {"additional_info": "updated"}
        }
        
        # Mock existing evidence
        mock_conn.fetchrow.return_value = {"id": evidence_id}
        
        mock_row = {
            "id": evidence_id,
            "title": "Updated Evidence Title",
            "integrity_status": "verified",
            "notes": "Evidence verified and validated",
            "metadata": {"additional_info": "updated"},
            "last_updated": datetime.now(timezone.utc)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        updated_evidence = await evidence_manager.update_evidence(evidence_id, update_data)
        
        assert updated_evidence.title == "Updated Evidence Title"
        assert updated_evidence.integrity_status == EvidenceIntegrity.VERIFIED
        assert updated_evidence.notes == "Evidence verified and validated"

    # ---- Evidence Integrity Verification Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_evidence_integrity_success(self, evidence_manager, mock_db_pool):
        """Test successful evidence integrity verification"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        evidence_id = str(uuid4())
        original_hash = "a1b2c3d4e5f6789012345678901234567890abcdef"
        
        # Mock existing evidence
        mock_evidence = MagicMock(
            id=evidence_id,
            source_location="/path/to/evidence.pdf",
            hash_value=original_hash,
            integrity_status=EvidenceIntegrity.UNKNOWN
        )
        mock_conn.fetchrow.return_value = mock_evidence
        
        # Mock file reading for verification
        with patch("builtins.open", mock_open(read_data=b"test file content")):
            # Mock hash calculation (same as original)
            with patch("hashlib.sha256") as mock_sha256:
                mock_hash = MagicMock()
                mock_hash.hexdigest.return_value = original_hash
                mock_sha256.return_value = mock_hash
                
                result = await evidence_manager.verify_evidence_integrity(evidence_id)
        
        assert result["verified"] is True
        assert result["original_hash"] == original_hash
        assert result["current_hash"] == original_hash
        assert result["integrity_status"] == EvidenceIntegrity.VERIFIED

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_evidence_integrity_tampered(self, evidence_manager, mock_db_pool):
        """Test evidence integrity verification with tampered evidence"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        evidence_id = str(uuid4())
        original_hash = "a1b2c3d4e5f6789012345678901234567890abcdef"
        tampered_hash = "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c"
        
        # Mock existing evidence
        mock_evidence = MagicMock(
            id=evidence_id,
            source_location="/path/to/evidence.pdf",
            hash_value=original_hash,
            integrity_status=EvidenceIntegrity.UNKNOWN
        )
        mock_conn.fetchrow.return_value = mock_evidence
        
        # Mock file reading for verification
        with patch("builtins.open", mock_open(read_data=b"modified file content")):
            # Mock hash calculation (different from original)
            with patch("hashlib.sha256") as mock_sha256:
                mock_hash = MagicMock()
                mock_hash.hexdigest.return_value = tampered_hash
                mock_sha256.return_value = mock_hash
                
                result = await evidence_manager.verify_evidence_integrity(evidence_id)
        
        assert result["verified"] is False
        assert result["original_hash"] == original_hash
        assert result["current_hash"] == tampered_hash
        assert result["integrity_status"] == EvidenceIntegrity.TAMPERED

    # ---- Chain of Custody Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_add_custody_entry(self, evidence_manager, mock_db_pool):
        """Test adding chain of custody entry"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        evidence_id = str(uuid4())
        custody_data = {
            "evidence_id": evidence_id,
            "action": "collected",
            "performed_by": "investigator_123",
            "timestamp": datetime.now(timezone.utc),
            "location": "Evidence Lab",
            "notes": "Evidence collected from blockchain analysis",
            "signature": "digital_signature_123"
        }
        
        # Mock existing evidence
        mock_conn.fetchrow.return_value = {"id": evidence_id}
        mock_conn.execute.return_value = "INSERT 1"
        
        result = await evidence_manager.add_custody_entry(custody_data)
        
        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_custody_chain(self, evidence_manager, mock_db_pool):
        """Test retrieving chain of custody for evidence"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        evidence_id = str(uuid4())
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "evidence_id": evidence_id,
                "action": "collected",
                "performed_by": "investigator_123",
                "timestamp": datetime.now(timezone.utc) - timedelta(days=5),
                "location": "Crime Scene",
                "notes": "Initial collection",
                "signature": "signature_123"
            },
            {
                "id": str(uuid4()),
                "evidence_id": evidence_id,
                "action": "transferred",
                "performed_by": "officer_456",
                "timestamp": datetime.now(timezone.utc) - timedelta(days=4),
                "location": "Evidence Lab",
                "notes": "Transferred to lab for analysis",
                "signature": "signature_456"
            },
            {
                "id": str(uuid4()),
                "evidence_id": evidence_id,
                "action": "analyzed",
                "performed_by": "analyst_789",
                "timestamp": datetime.now(timezone.utc) - timedelta(days=3),
                "location": "Analysis Station",
                "notes": "Blockchain analysis completed",
                "signature": "signature_789"
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        custody_chain = await evidence_manager.get_custody_chain(evidence_id)
        
        assert len(custody_chain) == 3
        assert custody_chain[0].action == "collected"
        assert custody_chain[1].action == "transferred"
        assert custody_chain[2].action == "analyzed"

    # ---- Evidence Search Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_evidence_by_case(self, evidence_manager, mock_db_pool):
        """Test searching evidence by case ID"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "case_id": case_id,
                "title": "Evidence 1",
                "evidence_type": "transaction_data",
                "integrity_status": "verified",
                "created_date": datetime.now(timezone.utc) - timedelta(days=2)
            },
            {
                "id": str(uuid4()),
                "case_id": case_id,
                "title": "Evidence 2",
                "evidence_type": "address_analysis",
                "integrity_status": "verified",
                "created_date": datetime.now(timezone.utc) - timedelta(days=1)
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        evidence_list = await evidence_manager.search_evidence({"case_id": case_id})
        
        assert len(evidence_list) == 2
        for evidence in evidence_list:
            assert evidence.case_id == case_id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_evidence_by_type(self, evidence_manager, mock_db_pool):
        """Test searching evidence by evidence type"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "case_id": str(uuid4()),
                "title": "Transaction Evidence",
                "evidence_type": "transaction_data",
                "integrity_status": "verified",
                "created_date": datetime.now(timezone.utc) - timedelta(days=3)
            },
            {
                "id": str(uuid4()),
                "case_id": str(uuid4()),
                "title": "Another Transaction",
                "evidence_type": "transaction_data",
                "integrity_status": "verified",
                "created_date": datetime.now(timezone.utc) - timedelta(days=2)
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        evidence_list = await evidence_manager.search_evidence({"evidence_type": "transaction_data"})
        
        assert len(evidence_list) == 2
        for evidence in evidence_list:
            assert evidence.evidence_type == EvidenceType.TRANSACTION_DATA

    # ---- Evidence Statistics Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_statistics(self, evidence_manager, mock_db_pool):
        """Test evidence statistics calculation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        days = 30
        
        # Mock statistics query results
        mock_stats = {
            "total_evidence": 250,
            "evidence_by_type": {
                EvidenceType.TRANSACTION_DATA.value: 80,
                EvidenceType.ADDRESS_ANALYSIS.value: 60,
                EvidenceType.BLOCKCHAIN_DATA.value: 40,
                EvidenceType.NETWORK_TRAFFIC.value: 30,
                EvidenceType.COMMUNICATION_LOGS.value: 20,
                EvidenceType.DOCUMENTS.value: 15,
                EvidenceType.IMAGES.value: 5
            },
            "evidence_by_integrity": {
                EvidenceIntegrity.VERIFIED.value: 180,
                EvidenceIntegrity.UNKNOWN.value: 50,
                EvidenceIntegrity.TAMPERED.value: 15,
                EvidenceIntegrity.CORRUPTED.value: 5
            },
            "total_file_size_mb": 1024.5,
            "average_file_size_kb": 4098.0,
            "custody_chain_completion_rate": 0.92,
            "evidence_with_verified_hash": 200
        }
        mock_conn.fetchrow.return_value = mock_stats
        
        stats = await evidence_manager.get_statistics(days)
        
        assert isinstance(stats, EvidenceStatistics)
        assert stats.total_evidence == 250
        assert stats.evidence_by_type[EvidenceType.TRANSACTION_DATA.value] == 80
        assert stats.evidence_by_integrity[EvidenceIntegrity.VERIFIED.value] == 180
        assert stats.total_file_size_mb == 1024.5
        assert stats.custody_chain_completion_rate == 0.92

    # ---- Evidence Export Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_evidence_manifest(self, evidence_manager, mock_db_pool):
        """Test evidence manifest export"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        
        # Mock evidence for manifest
        mock_rows = [
            {
                "id": str(uuid4()),
                "case_id": case_id,
                "title": "Evidence 1",
                "evidence_type": "transaction_data",
                "collection_date": datetime.now(timezone.utc) - timedelta(days=5),
                "collected_by": "investigator_123",
                "hash_value": "hash123",
                "integrity_status": "verified",
                "chain_of_custody_verified": True
            },
            {
                "id": str(uuid4()),
                "case_id": case_id,
                "title": "Evidence 2",
                "evidence_type": "address_analysis",
                "collection_date": datetime.now(timezone.utc) - timedelta(days=3),
                "collected_by": "analyst_456",
                "hash_value": "hash456",
                "integrity_status": "verified",
                "chain_of_custody_verified": True
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        manifest = await evidence_manager.export_evidence_manifest(case_id)
        
        assert manifest["case_id"] == case_id
        assert len(manifest["evidence_items"]) == 2
        assert manifest["export_timestamp"] is not None
        assert manifest["total_evidence"] == 2
        assert manifest["verified_evidence"] == 2

    # ---- Error Handling Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_connection_error(self, evidence_manager, mock_db_pool):
        """Test handling of database connection errors"""
        mock_pool.acquire.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await evidence_manager.create_evidence({
                "case_id": str(uuid4()),
                "title": "Test Evidence",
                "description": "Test description",
                "evidence_type": "documents",
                "source_location": "/test/path",
                "collection_date": datetime.now(timezone.utc),
                "collected_by": "test_user"
            })

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_evidence_type_validation(self, evidence_manager):
        """Test validation of invalid evidence types"""
        invalid_evidence_data = {
            "case_id": str(uuid4()),
            "title": "Test Evidence",
            "description": "Test description",
            "evidence_type": "invalid_type",  # Invalid enum value
            "source_location": "/test/path",
            "collection_date": datetime.now(timezone.utc),
            "collected_by": "test_user"
        }
        
        with pytest.raises(ValueError, match="Invalid evidence type"):
            await evidence_manager.create_evidence(invalid_evidence_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_evidence_not_found_error(self, evidence_manager, mock_db_pool):
        """Test handling of evidence not found error"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        update_data = {"title": "Updated Title"}
        
        with pytest.raises(ValueError, match="Evidence not found"):
            await evidence_manager.update_evidence("nonexistent_id", update_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_file_access_error_during_hashing(self, evidence_manager, mock_db_pool):
        """Test handling of file access errors during hashing"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": str(uuid4())}
        
        evidence_data = {
            "case_id": str(uuid4()),
            "title": "File Evidence",
            "description": "Test file evidence",
            "evidence_type": "documents",
            "source_location": "/nonexistent/file.pdf",
            "collection_date": datetime.now(timezone.utc),
            "collected_by": "test_user",
            "file_size_bytes": 1024
        }
        
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError):
                await evidence_manager.create_evidence(evidence_data)


class TestEvidenceModel:
    """Test suite for Evidence data model"""

    @pytest.mark.unit
    def test_evidence_creation(self):
        """Test Evidence model creation"""
        evidence_data = {
            "id": str(uuid4()),
            "case_id": str(uuid4()),
            "title": "Critical Blockchain Evidence",
            "description": "Evidence from blockchain analysis in fraud investigation",
            "evidence_type": "transaction_data",
            "source_location": "https://blockchain.info/tx/abcdef123456",
            "collection_date": datetime.now(timezone.utc) - timedelta(days=2),
            "collected_by": "lead_investigator",
            "hash_value": "a1b2c3d4e5f6789012345678901234567890abcdef",
            "file_size_bytes": 2048,
            "integrity_status": "verified",
            "chain_of_custody_verified": True,
            "metadata": {
                "transaction_hash": "abcdef123456",
                "block_number": 67890,
                "confirmations": 12,
                "value_btc": 1.5
            },
            "tags": ["bitcoin", "transaction", "fraud", "critical"],
            "created_date": datetime.now(timezone.utc) - timedelta(days=2),
            "last_updated": datetime.now(timezone.utc) - timedelta(days=1)
        }
        
        evidence = Evidence(**evidence_data)
        
        assert evidence.id == evidence_data["id"]
        assert evidence.title == "Critical Blockchain Evidence"
        assert evidence.evidence_type == EvidenceType.TRANSACTION_DATA
        assert evidence.case_id == evidence_data["case_id"]
        assert evidence.collected_by == "lead_investigator"
        assert evidence.hash_value == "a1b2c3d4e5f6789012345678901234567890abcdef"
        assert evidence.integrity_status == EvidenceIntegrity.VERIFIED
        assert evidence.chain_of_custody_verified is True
        assert len(evidence.tags) == 4

    @pytest.mark.unit
    def test_evidence_optional_fields(self):
        """Test Evidence with optional fields"""
        evidence_data = {
            "id": str(uuid4()),
            "case_id": str(uuid4()),
            "title": "Simple Evidence",
            "description": "Simple evidence description",
            "evidence_type": "metadata",
            "source_location": "internal",
            "collection_date": datetime.now(timezone.utc),
            "collected_by": "user_123",
            "integrity_status": "unknown",
            "chain_of_custody_verified": False,
            "metadata": {},
            "tags": [],
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        evidence = Evidence(**evidence_data)
        
        assert evidence.hash_value is None
        assert evidence.file_size_bytes is None
        assert evidence.integrity_status == EvidenceIntegrity.UNKNOWN
        assert evidence.chain_of_custody_verified is False

    @pytest.mark.unit
    def test_evidence_enum_validation(self):
        """Test enum validation in Evidence"""
        with pytest.raises(ValueError):
            Evidence(
                id=str(uuid4()),
                case_id=str(uuid4()),
                title="Test Evidence",
                description="Test description",
                evidence_type="invalid_type",  # Invalid enum
                source_location="/test/path",
                collection_date=datetime.now(timezone.utc),
                collected_by="test_user",
                integrity_status="unknown",
                chain_of_custody_verified=False,
                metadata={},
                tags=[],
                created_date=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )


class TestChainOfCustodyModel:
    """Test suite for ChainOfCustody data model"""

    @pytest.mark.unit
    def test_chain_of_custody_creation(self):
        """Test ChainOfCustody model creation"""
        custody_data = {
            "id": str(uuid4()),
            "evidence_id": str(uuid4()),
            "action": "collected",
            "performed_by": "investigator_123",
            "timestamp": datetime.now(timezone.utc) - timedelta(days=5),
            "location": "Crime Scene - Office Building",
            "notes": "Evidence collected from suspect's computer",
            "signature": "digital_signature_abc123",
            "previous_entry_id": None,
            "next_entry_id": str(uuid4())
        }
        
        custody = ChainOfCustody(**custody_data)
        
        assert custody.id == custody_data["id"]
        assert custody.evidence_id == custody_data["evidence_id"]
        assert custody.action == "collected"
        assert custody.performed_by == "investigator_123"
        assert custody.location == "Crime Scene - Office Building"
        assert custody.signature == "digital_signature_abc123"
        assert custody.previous_entry_id is None
        assert custody.next_entry_id == custody_data["next_entry_id"]

    @pytest.mark.unit
    def test_chain_of_custody_actions(self):
        """Test different custody actions"""
        actions = ["collected", "transferred", "analyzed", "stored", "presented", "returned", "destroyed"]
        
        for action in actions:
            custody = ChainOfCustody(
                id=str(uuid4()),
                evidence_id=str(uuid4()),
                action=action,
                performed_by="test_user",
                timestamp=datetime.now(timezone.utc),
                location="Test Location",
                notes="Test notes",
                signature="test_signature"
            )
            assert custody.action == action


class TestEvidenceStatisticsModel:
    """Test suite for EvidenceStatistics data model"""

    @pytest.mark.unit
    def test_evidence_statistics_creation(self):
        """Test EvidenceStatistics model creation"""
        stats_data = {
            "total_evidence": 500,
            "evidence_by_type": {
                EvidenceType.TRANSACTION_DATA.value: 150,
                EvidenceType.ADDRESS_ANALYSIS.value: 100,
                EvidenceType.BLOCKCHAIN_DATA.value: 80,
                EvidenceType.NETWORK_TRAFFIC.value: 60,
                EvidenceType.COMMUNICATION_LOGS.value: 50,
                EvidenceType.DOCUMENTS.value: 40,
                EvidenceType.IMAGES.value: 15,
                EvidenceType.VIDEOS.value: 5
            },
            "evidence_by_integrity": {
                EvidenceIntegrity.VERIFIED.value: 400,
                EvidenceIntegrity.UNKNOWN.value: 70,
                EvidenceIntegrity.TAMPERED.value: 25,
                EvidenceIntegrity.CORRUPTED.value: 5
            },
            "total_file_size_mb": 2048.5,
            "average_file_size_kb": 8192.0,
            "custody_chain_completion_rate": 0.95,
            "evidence_with_verified_hash": 450
        }
        
        stats = EvidenceStatistics(**stats_data)
        
        assert stats.total_evidence == 500
        assert stats.evidence_by_type[EvidenceType.TRANSACTION_DATA.value] == 150
        assert stats.evidence_by_integrity[EvidenceIntegrity.VERIFIED.value] == 400
        assert stats.total_file_size_mb == 2048.5
        assert stats.average_file_size_kb == 8192.0
        assert stats.custody_chain_completion_rate == 0.95
        assert stats.evidence_with_verified_hash == 450

    @pytest.mark.unit
    def test_evidence_statistics_calculated_fields(self):
        """Test calculated fields in EvidenceStatistics"""
        stats = EvidenceStatistics(
            total_evidence=200,
            verified_evidence=180,
            total_file_size_mb=1000.0,
            custody_chain_complete=190
        )
        
        # Test calculated integrity rate
        expected_rate = 180 / 200  # 0.9
        assert abs(stats.evidence_by_integrity[EvidenceIntegrity.VERIFIED.value] - expected_rate) < 0.001
        
        # Test calculated average file size
        expected_avg = 1000.0 / 200 * 1024  # KB
        assert abs(stats.average_file_size_kb - expected_avg) < 0.001
        
        # Test calculated custody chain completion rate
        expected_custody_rate = 190 / 200  # 0.95
        assert abs(stats.custody_chain_completion_rate - expected_custody_rate) < 0.001
