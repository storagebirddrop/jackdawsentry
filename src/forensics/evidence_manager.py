"""
Jackdaw Sentry - Evidence Management System
Professional evidence chain management and integrity verification
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set

logger = logging.getLogger(__name__)


class EvidenceStatus(Enum):
    """Evidence processing status"""

    COLLECTED = "collected"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class StorageType(Enum):
    """Evidence storage types"""

    LOCAL = "local"
    ENCRYPTED = "encrypted"
    CLOUD = "cloud"
    BLOCKCHAIN = "blockchain"
    DISTRIBUTED = "distributed"


class AccessLevel(Enum):
    """Evidence access levels"""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    CLASSIFIED = "classified"


@dataclass
class EvidenceChain:
    """Chain of custody for evidence tracking"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    evidence_id: str = ""
    entries: List[Dict[str, Any]] = field(default_factory=list)
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_broken: bool = False
    verification_hash: str = ""

    def add_entry(
        self, person: str, action: str, location: str, notes: str = ""
    ) -> None:
        """Add entry to chain of custody"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "person": person,
            "action": action,
            "location": location,
            "notes": notes,
            "entry_hash": self._calculate_entry_hash(person, action, location, notes),
        }
        self.entries.append(entry)
        self.last_updated = datetime.now(timezone.utc)
        self.verification_hash = self._calculate_chain_hash()

    def _calculate_entry_hash(
        self, person: str, action: str, location: str, notes: str
    ) -> str:
        """Calculate hash for individual entry"""
        data = f"{person}:{action}:{location}:{notes}:{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _calculate_chain_hash(self) -> str:
        """Calculate hash of entire chain"""
        chain_data = json.dumps(self.entries, sort_keys=True)
        return hashlib.sha256(chain_data.encode()).hexdigest()

    def verify_chain(self) -> bool:
        """Verify integrity of chain of custody"""
        if not self.entries:
            return True

        # Recalculate chain hash
        expected_hash = self._calculate_chain_hash()
        is_valid = expected_hash == self.verification_hash

        self.is_broken = not is_valid
        return is_valid


@dataclass
class EvidenceStorage:
    """Evidence storage information"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    evidence_id: str = ""
    storage_type: StorageType = StorageType.LOCAL
    location: str = ""
    encryption_key: Optional[str] = None
    checksum: str = ""
    backup_locations: List[str] = field(default_factory=list)
    access_log: List[Dict[str, Any]] = field(default_factory=list)
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    is_compressed: bool = False
    compression_ratio: float = 1.0

    def log_access(self, user: str, action: str, ip_address: str = "") -> None:
        """Log access to evidence storage"""
        access_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user,
            "action": action,
            "ip_address": ip_address,
        }
        self.access_log.append(access_entry)
        self.last_accessed = datetime.now(timezone.utc)

    def verify_checksum(self, file_path: str) -> bool:
        """Verify file checksum"""
        if not os.path.exists(file_path):
            return False

        try:
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            return file_hash == self.checksum
        except Exception as e:
            logger.error(f"Failed to verify checksum for {file_path}: {e}")
            return False


class EvidenceManager:
    """Professional evidence management system"""

    def __init__(self, db_pool=None, storage_path: str = "/var/lib/jackdaw/evidence"):
        self.db_pool = db_pool
        self.storage_path = storage_path
        self.chains: Dict[str, EvidenceChain] = {}
        self.storage: Dict[str, EvidenceStorage] = {}
        self.running = False
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour

        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)

        logger.info("EvidenceManager initialized")

    async def initialize(self) -> None:
        """Initialize evidence manager and database schema"""
        if self.db_pool:
            await self._create_database_schema()

        self.running = True
        logger.info("EvidenceManager started")

    async def shutdown(self) -> None:
        """Shutdown evidence manager"""
        self.running = False
        logger.info("EvidenceManager shutdown")

    async def _create_database_schema(self) -> None:
        """Create evidence management database tables"""
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS evidence_chains (
                id UUID PRIMARY KEY,
                evidence_id UUID NOT NULL,
                entries JSONB NOT NULL DEFAULT '[]',
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_broken BOOLEAN DEFAULT FALSE,
                verification_hash TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS evidence_storage (
                id UUID PRIMARY KEY,
                evidence_id UUID NOT NULL,
                storage_type TEXT NOT NULL,
                location TEXT NOT NULL,
                encryption_key TEXT,
                checksum TEXT NOT NULL,
                backup_locations JSONB DEFAULT '[]',
                access_log JSONB DEFAULT '[]',
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_accessed TIMESTAMP WITH TIME ZONE,
                size_bytes BIGINT DEFAULT 0,
                is_compressed BOOLEAN DEFAULT FALSE,
                compression_ratio FLOAT DEFAULT 1.0
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_evidence_chains_evidence ON evidence_chains(evidence_id);
            CREATE INDEX IF NOT EXISTS idx_evidence_storage_evidence ON evidence_storage(evidence_id);
            CREATE INDEX IF NOT EXISTS idx_evidence_storage_type ON evidence_storage(storage_type);
            """,
        ]

        async with self.db_pool.acquire() as conn:
            for query in schema_queries:
                await conn.execute(query)

        logger.info("Evidence management database schema created")

    async def create_chain(self, evidence_id: str) -> EvidenceChain:
        """Create new chain of custody"""
        chain = EvidenceChain(evidence_id=evidence_id)

        if self.db_pool:
            await self._save_chain_to_db(chain)

        self.chains[chain.id] = chain
        logger.info(f"Created evidence chain: {chain.id}")
        return chain

    async def add_chain_entry(
        self, chain_id: str, person: str, action: str, location: str, notes: str = ""
    ) -> None:
        """Add entry to chain of custody"""
        if chain_id not in self.chains:
            raise ValueError(f"Chain {chain_id} not found")

        chain = self.chains[chain_id]
        chain.add_entry(person, action, location, notes)

        if self.db_pool:
            await self._update_chain_in_db(chain)

        logger.info(f"Added entry to chain {chain_id}: {action} by {person}")

    async def verify_chain(self, chain_id: str) -> bool:
        """Verify chain of custody integrity"""
        if chain_id not in self.chains:
            raise ValueError(f"Chain {chain_id} not found")

        chain = self.chains[chain_id]
        is_valid = chain.verify_chain()

        if self.db_pool:
            await self._update_chain_in_db(chain)

        logger.info(f"Verified chain {chain_id}: {is_valid}")
        return is_valid

    async def store_evidence(
        self,
        evidence_id: str,
        file_path: str,
        storage_type: StorageType = StorageType.LOCAL,
        encryption_key: Optional[str] = None,
    ) -> EvidenceStorage:
        """Store evidence file with integrity verification"""
        if not os.path.exists(file_path):
            raise ValueError(f"Source file {file_path} does not exist")

        # Generate unique storage location
        storage_location = os.path.join(
            self.storage_path, evidence_id[:2], f"{evidence_id}.evidence"
        )
        os.makedirs(os.path.dirname(storage_location), exist_ok=True)

        # Copy file to storage location
        shutil.copy2(file_path, storage_location)

        # Calculate checksum
        with open(storage_location, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()

        # Get file size
        size_bytes = os.path.getsize(storage_location)

        storage = EvidenceStorage(
            evidence_id=evidence_id,
            storage_type=storage_type,
            location=storage_location,
            encryption_key=encryption_key,
            checksum=checksum,
            size_bytes=size_bytes,
        )

        if self.db_pool:
            await self._save_storage_to_db(storage)

        self.storage[storage.id] = storage
        logger.info(f"Stored evidence {evidence_id} at {storage_location}")
        return storage

    async def retrieve_evidence(
        self, storage_id: str, output_path: str, user: str
    ) -> bool:
        """Retrieve evidence file with access logging"""
        if storage_id not in self.storage:
            raise ValueError(f"Storage {storage_id} not found")

        storage = self.storage[storage_id]

        # Verify checksum before retrieval
        if not storage.verify_checksum(storage.location):
            logger.error(f"Checksum verification failed for storage {storage_id}")
            return False

        # Copy file to output location
        try:
            shutil.copy2(storage.location, output_path)

            # Log access
            storage.log_access(user, "retrieve")

            if self.db_pool:
                await self._update_storage_in_db(storage)

            logger.info(f"Retrieved evidence from storage {storage_id} by {user}")
            return True

        except Exception as e:
            logger.error(f"Failed to retrieve evidence from storage {storage_id}: {e}")
            return False

    async def create_backup(self, storage_id: str, backup_location: str) -> bool:
        """Create backup of evidence storage"""
        if storage_id not in self.storage:
            raise ValueError(f"Storage {storage_id} not found")

        storage = self.storage[storage_id]

        try:
            # Create backup
            shutil.copy2(storage.location, backup_location)

            # Add to backup locations
            storage.backup_locations.append(backup_location)

            if self.db_pool:
                await self._update_storage_in_db(storage)

            logger.info(f"Created backup for storage {storage_id} at {backup_location}")
            return True

        except Exception as e:
            logger.error(f"Failed to create backup for storage {storage_id}: {e}")
            return False

    async def get_chain(self, chain_id: str) -> Optional[EvidenceChain]:
        """Get chain of custody by ID"""
        if chain_id in self.chains:
            return self.chains[chain_id]

        if self.db_pool:
            chain = await self._load_chain_from_db(chain_id)
            if chain:
                self.chains[chain_id] = chain
                return chain

        return None

    async def get_storage(self, storage_id: str) -> Optional[EvidenceStorage]:
        """Get evidence storage by ID"""
        if storage_id in self.storage:
            return self.storage[storage_id]

        if self.db_pool:
            storage = await self._load_storage_from_db(storage_id)
            if storage:
                self.storage[storage_id] = storage
                return storage

        return None

    async def get_chain_by_evidence(self, evidence_id: str) -> Optional[EvidenceChain]:
        """Get chain of custody for evidence"""
        for chain in self.chains.values():
            if chain.evidence_id == evidence_id:
                return chain

        if self.db_pool:
            chain = await self._load_chain_by_evidence(evidence_id)
            if chain:
                self.chains[chain.id] = chain
                return chain

        return None

    async def get_storage_by_evidence(
        self, evidence_id: str
    ) -> Optional[EvidenceStorage]:
        """Get storage for evidence"""
        for storage in self.storage.values():
            if storage.evidence_id == evidence_id:
                return storage

        if self.db_pool:
            storage = await self._load_storage_by_evidence(evidence_id)
            if storage:
                self.storage[storage.id] = storage
                return storage

        return None

    async def audit_evidence(self, evidence_id: str) -> Dict[str, Any]:
        """Perform full audit of evidence"""
        audit_result = {
            "evidence_id": evidence_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "chain_integrity": False,
            "storage_integrity": False,
            "access_count": 0,
            "backup_count": 0,
            "issues": [],
        }

        # Check chain of custody
        chain = await self.get_chain_by_evidence(evidence_id)
        if chain:
            audit_result["chain_integrity"] = await self.verify_chain(chain.id)
            audit_result["chain_entries"] = len(chain.entries)
            if chain.is_broken:
                audit_result["issues"].append("Chain of custody is broken")
        else:
            audit_result["issues"].append("No chain of custody found")

        # Check storage integrity
        storage = await self.get_storage_by_evidence(evidence_id)
        if storage:
            audit_result["storage_integrity"] = storage.verify_checksum(
                storage.location
            )
            audit_result["access_count"] = len(storage.access_log)
            audit_result["backup_count"] = len(storage.backup_locations)
            audit_result["storage_size"] = storage.size_bytes

            if not audit_result["storage_integrity"]:
                audit_result["issues"].append("Storage checksum verification failed")
        else:
            audit_result["issues"].append("No storage found")

        return audit_result

    async def cleanup_expired_backups(self, days_old: int = 30) -> int:
        """Clean up old backup files"""
        cutoff_date = datetime.now(timezone.utc).timestamp() - (days_old * 24 * 3600)
        cleaned_count = 0

        for storage in self.storage.values():
            backups_to_remove = []

            for backup_path in storage.backup_locations:
                if os.path.exists(backup_path):
                    file_mtime = os.path.getmtime(backup_path)
                    if file_mtime < cutoff_date:
                        try:
                            os.remove(backup_path)
                            backups_to_remove.append(backup_path)
                            cleaned_count += 1
                        except Exception as e:
                            logger.error(f"Failed to remove backup {backup_path}: {e}")

            # Remove from storage record
            for backup_path in backups_to_remove:
                storage.backup_locations.remove(backup_path)

            if backups_to_remove and self.db_pool:
                await self._update_storage_in_db(storage)

        logger.info(f"Cleaned up {cleaned_count} expired backup files")
        return cleaned_count

    # Database helper methods
    async def _save_chain_to_db(self, chain: EvidenceChain) -> None:
        """Save chain to database"""
        query = """
        INSERT INTO evidence_chains 
        (id, evidence_id, entries, created_date, last_updated, is_broken, verification_hash)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (id) DO UPDATE SET
        entries = EXCLUDED.entries,
        last_updated = EXCLUDED.last_updated,
        is_broken = EXCLUDED.is_broken,
        verification_hash = EXCLUDED.verification_hash
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                chain.id,
                chain.evidence_id,
                json.dumps(chain.entries),
                chain.created_date,
                chain.last_updated,
                chain.is_broken,
                chain.verification_hash,
            )

    async def _update_chain_in_db(self, chain: EvidenceChain) -> None:
        """Update chain in database"""
        query = """
        UPDATE evidence_chains SET
        entries = $1, last_updated = $2, is_broken = $3, verification_hash = $4
        WHERE id = $5
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                json.dumps(chain.entries),
                chain.last_updated,
                chain.is_broken,
                chain.verification_hash,
                chain.id,
            )

    async def _save_storage_to_db(self, storage: EvidenceStorage) -> None:
        """Save storage to database"""
        query = """
        INSERT INTO evidence_storage 
        (id, evidence_id, storage_type, location, encryption_key, checksum, backup_locations,
         access_log, created_date, last_accessed, size_bytes, is_compressed, compression_ratio)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (id) DO UPDATE SET
        backup_locations = EXCLUDED.backup_locations,
        access_log = EXCLUDED.access_log,
        last_accessed = EXCLUDED.last_accessed,
        size_bytes = EXCLUDED.size_bytes,
        is_compressed = EXCLUDED.is_compressed,
        compression_ratio = EXCLUDED.compression_ratio
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                storage.id,
                storage.evidence_id,
                storage.storage_type.value,
                storage.location,
                storage.encryption_key,
                storage.checksum,
                json.dumps(storage.backup_locations),
                json.dumps(storage.access_log),
                storage.created_date,
                storage.last_accessed,
                storage.size_bytes,
                storage.is_compressed,
                storage.compression_ratio,
            )

    async def _update_storage_in_db(self, storage: EvidenceStorage) -> None:
        """Update storage in database"""
        query = """
        UPDATE evidence_storage SET
        backup_locations = $1, access_log = $2, last_accessed = $3
        WHERE id = $4
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                json.dumps(storage.backup_locations),
                json.dumps(storage.access_log),
                storage.last_accessed,
                storage.id,
            )

    async def _load_chain_from_db(self, chain_id: str) -> Optional[EvidenceChain]:
        """Load chain from database"""
        query = "SELECT * FROM evidence_chains WHERE id = $1"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, chain_id)
            if row:
                return EvidenceChain(
                    id=row["id"],
                    evidence_id=row["evidence_id"],
                    entries=json.loads(row["entries"]) if row["entries"] else [],
                    created_date=row["created_date"],
                    last_updated=row["last_updated"],
                    is_broken=row["is_broken"],
                    verification_hash=row["verification_hash"],
                )
        return None

    async def _load_storage_from_db(self, storage_id: str) -> Optional[EvidenceStorage]:
        """Load storage from database"""
        query = "SELECT * FROM evidence_storage WHERE id = $1"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, storage_id)
            if row:
                return EvidenceStorage(
                    id=row["id"],
                    evidence_id=row["evidence_id"],
                    storage_type=StorageType(row["storage_type"]),
                    location=row["location"],
                    encryption_key=row["encryption_key"],
                    checksum=row["checksum"],
                    backup_locations=(
                        json.loads(row["backup_locations"])
                        if row["backup_locations"]
                        else []
                    ),
                    access_log=(
                        json.loads(row["access_log"]) if row["access_log"] else []
                    ),
                    created_date=row["created_date"],
                    last_accessed=row["last_accessed"],
                    size_bytes=row["size_bytes"],
                    is_compressed=row["is_compressed"],
                    compression_ratio=row["compression_ratio"],
                )
        return None

    async def _load_chain_by_evidence(
        self, evidence_id: str
    ) -> Optional[EvidenceChain]:
        """Load chain by evidence ID"""
        query = "SELECT * FROM evidence_chains WHERE evidence_id = $1"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, evidence_id)
            if row:
                return EvidenceChain(
                    id=row["id"],
                    evidence_id=row["evidence_id"],
                    entries=json.loads(row["entries"]) if row["entries"] else [],
                    created_date=row["created_date"],
                    last_updated=row["last_updated"],
                    is_broken=row["is_broken"],
                    verification_hash=row["verification_hash"],
                )
        return None

    async def _load_storage_by_evidence(
        self, evidence_id: str
    ) -> Optional[EvidenceStorage]:
        """Load storage by evidence ID"""
        query = "SELECT * FROM evidence_storage WHERE evidence_id = $1"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, evidence_id)
            if row:
                return EvidenceStorage(
                    id=row["id"],
                    evidence_id=row["evidence_id"],
                    storage_type=StorageType(row["storage_type"]),
                    location=row["location"],
                    encryption_key=row["encryption_key"],
                    checksum=row["checksum"],
                    backup_locations=(
                        json.loads(row["backup_locations"])
                        if row["backup_locations"]
                        else []
                    ),
                    access_log=(
                        json.loads(row["access_log"]) if row["access_log"] else []
                    ),
                    created_date=row["created_date"],
                    last_accessed=row["last_accessed"],
                    size_bytes=row["size_bytes"],
                    is_compressed=row["is_compressed"],
                    compression_ratio=row["compression_ratio"],
                )
        return None


# Global evidence manager instance
_evidence_manager = None


def get_evidence_manager() -> EvidenceManager:
    """Get the global evidence manager instance"""
    global _evidence_manager
    if _evidence_manager is None:
        _evidence_manager = EvidenceManager()
    return _evidence_manager


# Re-export from forensic_engine for API compatibility
from src.forensics.forensic_engine import EvidenceType, EvidenceIntegrity  # noqa: E402, F401

# Aliases and additional types
ChainOfCustody = EvidenceChain


@dataclass
class Evidence:
    """Individual evidence artifact"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    status: str = ""
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert evidence to dictionary representation"""
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "file_path": self.file_path,
            "metadata": self.metadata
        }


@dataclass
class EvidenceStatistics:
    """Statistics for evidence items"""

    total_items: int = 0
    items_by_type: Dict[str, int] = field(default_factory=dict)
    items_by_status: Dict[str, int] = field(default_factory=dict)
    verified_count: int = 0
    tampered_count: int = 0
    total_size_bytes: int = 0
