"""
Compliance Backup and Recovery Module

This module provides comprehensive backup and recovery functionality for compliance operations including:
- Automated backup scheduling
- Incremental and full backups
- Data integrity verification
- Disaster recovery procedures
- Backup encryption and security
"""

import asyncio
import gzip
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tarfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import aiofiles
import aiohttp
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class BackupType(Enum):
    """Backup type enumeration"""

    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class BackupStatus(Enum):
    """Backup status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecoveryType(Enum):
    """Recovery type enumeration"""

    FULL_RESTORE = "full_restore"
    PARTIAL_RESTORE = "partial_restore"
    POINT_IN_TIME = "point_in_time"
    SELECTIVE_RESTORE = "selective_restore"


@dataclass
class BackupConfig:
    """Backup configuration"""

    backup_type: BackupType
    source_paths: List[str]
    destination_path: str
    compression: bool = True
    encryption: bool = True
    retention_days: int = 30
    schedule_interval_hours: int = 24
    max_backup_size_gb: int = 10
    verify_integrity: bool = True
    exclude_patterns: List[str] = None


@dataclass
class BackupJob:
    """Backup job definition"""

    job_id: str
    config: BackupConfig
    status: BackupStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RecoveryJob:
    """Recovery job definition"""

    job_id: str
    backup_file: str
    recovery_type: RecoveryType
    target_path: str
    status: BackupStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    recovered_files: List[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ComplianceBackupEngine:
    """Compliance backup and recovery engine"""

    def __init__(self):
        self.backup_jobs = {}
        self.recovery_jobs = []
        self.backup_history = []
        self.encryption_key = None
        self.backup_dir = Path("./backups/compliance")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent_backups = 2
        self.backup_queue = asyncio.Queue()

        # Initialize encryption key
        self._initialize_encryption()

    def _initialize_encryption(self):
        """Initialize backup encryption"""
        try:
            # Generate or load encryption key
            key_file = self.backup_dir / "backup.key"

            if key_file.exists():
                with open(key_file, "rb") as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                with open(key_file, "wb") as f:
                    f.write(key)

            self.encryption_key = Fernet(key)
            logger.info("Backup encryption initialized")

        except Exception as e:
            logger.error(f"Failed to initialize backup encryption: {e}")
            self.encryption_key = None

    async def create_backup(self, config: BackupConfig) -> BackupJob:
        """Create and execute backup job"""
        try:
            # Generate unique job ID
            job_id = f"backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hash(str(config)) % 10000}"

            # Create backup job
            job = BackupJob(
                job_id=job_id,
                config=config,
                status=BackupStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                metadata={"config_hash": self._calculate_config_hash(config)},
            )

            # Add to active jobs
            self.backup_jobs[job_id] = job

            # Process backup
            await self._process_backup(job)

            # Move to history
            self.backup_history.append(job)
            if job_id in self.backup_jobs:
                del self.backup_jobs[job_id]

            return job

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise

    async def _process_backup(self, job: BackupJob):
        """Process backup job"""
        try:
            job.status = BackupStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)

            # Generate backup filename
            timestamp = job.started_at.strftime("%Y%m%d_%H%M%S")
            backup_filename = (
                f"compliance_backup_{job.config.backup_type.value}_{timestamp}"
            )

            if job.config.compression:
                backup_filename += ".tar.gz"
            else:
                backup_filename += ".tar"

            backup_path = self.backup_dir / backup_filename

            # Create backup
            if job.config.backup_type == BackupType.FULL:
                await self._create_full_backup(job, backup_path)
            elif job.config.backup_type == BackupType.INCREMENTAL:
                await self._create_incremental_backup(job, backup_path)
            elif job.config.backup_type == BackupType.DIFFERENTIAL:
                await self._create_differential_backup(job, backup_path)
            elif job.config.backup_type == BackupType.SNAPSHOT:
                await self._create_snapshot_backup(job, backup_path)

            # Compress if requested
            if job.config.compression and not backup_path.name.endswith(".gz"):
                compressed_path = await self._compress_backup(backup_path)
                backup_path = compressed_path

            # Encrypt if requested
            if job.config.encryption and self.encryption_key:
                encrypted_path = await self._encrypt_backup(backup_path)
                backup_path = encrypted_path

            # Verify integrity if requested
            if job.config.verify_integrity:
                await self._verify_backup_integrity(backup_path)

            # Update job status
            job.status = BackupStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.file_path = str(backup_path)
            job.file_size = backup_path.stat().st_size
            job.checksum = await self._calculate_file_checksum(backup_path)

            logger.info(f"Backup completed: {job.job_id} ({job.file_size} bytes)")

        except Exception as e:
            logger.error(f"Backup processing failed for {job.job_id}: {e}")
            job.status = BackupStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            raise

    async def _create_full_backup(self, job: BackupJob, backup_path: Path):
        """Create full backup"""
        try:
            logger.info(f"Creating full backup: {job.job_id}")

            # Create tar archive
            with tarfile.open(
                backup_path, "w:gz" if job.config.compression else "w"
            ) as tar:
                for source_path in job.config.source_paths:
                    source = Path(source_path)
                    if source.exists():
                        await self._add_to_tar(
                            tar, source, job.config.exclude_patterns or []
                        )

            logger.debug(f"Full backup created: {backup_path}")

        except Exception as e:
            logger.error(f"Full backup creation failed: {e}")
            raise

    async def _create_incremental_backup(self, job: BackupJob, backup_path: Path):
        """Create incremental backup"""
        try:
            logger.info(f"Creating incremental backup: {job.job_id}")

            # Find last full backup
            last_full_backup = await self._find_last_backup(BackupType.FULL)

            if not last_full_backup:
                logger.warning("No full backup found, creating full backup instead")
                await self._create_full_backup(job, backup_path)
                return

            # Get files modified since last backup
            modified_files = await self._get_modified_files(
                job.config.source_paths, last_full_backup.created_at
            )

            # Create incremental backup
            with tarfile.open(
                backup_path, "w:gz" if job.config.compression else "w"
            ) as tar:
                for file_path in modified_files:
                    file = Path(file_path)
                    if file.exists():
                        await self._add_to_tar(
                            tar, file, job.config.exclude_patterns or []
                        )

            logger.debug(f"Incremental backup created: {backup_path}")

        except Exception as e:
            logger.error(f"Incremental backup creation failed: {e}")
            raise

    async def _create_differential_backup(self, job: BackupJob, backup_path: Path):
        """Create differential backup"""
        try:
            logger.info(f"Creating differential backup: {job.job_id}")

            # Find last full backup
            last_full_backup = await self._find_last_backup(BackupType.FULL)

            if not last_full_backup:
                logger.warning("No full backup found, creating full backup instead")
                await self._create_full_backup(job, backup_path)
                return

            # Get files modified since last full backup
            modified_files = await self._get_modified_files(
                job.config.source_paths, last_full_backup.created_at
            )

            # Create differential backup
            with tarfile.open(
                backup_path, "w:gz" if job.config.compression else "w"
            ) as tar:
                for file_path in modified_files:
                    file = Path(file_path)
                    if file.exists():
                        await self._add_to_tar(
                            tar, file, job.config.exclude_patterns or []
                        )

            logger.debug(f"Differential backup created: {backup_path}")

        except Exception as e:
            logger.error(f"Differential backup creation failed: {e}")
            raise

    async def _create_snapshot_backup(self, job: BackupJob, backup_path: Path):
        """Create snapshot backup"""
        try:
            logger.info(f"Creating snapshot backup: {job.job_id}")

            # For databases, create database snapshots
            # For files, create file system snapshots

            # This is a simplified implementation
            # In production, you would use database-specific snapshot tools
            # and file system snapshot capabilities

            await self._create_full_backup(job, backup_path)

            logger.debug(f"Snapshot backup created: {backup_path}")

        except Exception as e:
            logger.error(f"Snapshot backup creation failed: {e}")
            raise

    async def _add_to_tar(
        self, tar: tarfile.TarFile, source: Path, exclude_patterns: List[str]
    ):
        """Add files to tar archive with exclusion patterns"""
        try:
            for item in source.rglob("*"):
                if item.is_file():
                    # Check exclusion patterns
                    if any(pattern in str(item) for pattern in exclude_patterns):
                        continue

                    # Add file to tar
                    tar.add(item, arcname=item.relative_to(source.parent))

        except Exception as e:
            logger.error(f"Failed to add {source} to tar: {e}")
            raise

    async def _compress_backup(self, backup_path: Path) -> Path:
        """Compress backup file"""
        try:
            compressed_path = backup_path.with_suffix(backup_path.suffix + ".gz")

            with open(backup_path, "rb") as f_in:
                with gzip.open(compressed_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove original file
            backup_path.unlink()

            return compressed_path

        except Exception as e:
            logger.error(f"Failed to compress backup: {e}")
            raise

    async def _encrypt_backup(self, backup_path: Path) -> Path:
        """Encrypt backup file"""
        try:
            if not self.encryption_key:
                raise ValueError("Encryption not initialized")

            encrypted_path = backup_path.with_suffix(backup_path.suffix + ".enc")

            # Read and encrypt file
            with open(backup_path, "rb") as f:
                file_data = f.read()

            encrypted_data = self.encryption_key.encrypt(file_data)

            with open(encrypted_path, "wb") as f:
                f.write(encrypted_data)

            # Remove original file
            backup_path.unlink()

            return encrypted_path

        except Exception as e:
            logger.error(f"Failed to encrypt backup: {e}")
            raise

    async def _verify_backup_integrity(self, backup_path: Path):
        """Verify backup file integrity"""
        try:
            # Calculate checksum
            checksum = await self._calculate_file_checksum(backup_path)

            # Verify file can be opened
            if backup_path.suffix == ".gz":
                with gzip.open(backup_path, "rb") as f:
                    # Read first few bytes to verify
                    f.read(1024)
            elif backup_path.suffix == ".enc":
                if not self.encryption_key:
                    raise ValueError(
                        "Cannot verify encrypted backup without encryption key"
                    )

                with open(backup_path, "rb") as f:
                    encrypted_data = f.read()

                decrypted_data = self.encryption_key.decrypt(encrypted_data)
                # Verify decrypted data
                if len(decrypted_data) == 0:
                    raise ValueError("Decrypted backup is empty")

            logger.debug(f"Backup integrity verified: {backup_path}")

        except Exception as e:
            logger.error(f"Backup integrity verification failed: {e}")
            raise

    async def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        try:
            sha256_hash = hashlib.sha256()

            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

            return sha256_hash.hexdigest()

        except Exception as e:
            logger.error(f"Failed to calculate checksum: {e}")
            raise

    async def _find_last_backup(self, backup_type: BackupType) -> Optional[BackupJob]:
        """Find last backup of specified type"""
        try:
            matching_backups = [
                job
                for job in self.backup_history
                if job.config.backup_type == backup_type
                and job.status == BackupStatus.COMPLETED
            ]

            if matching_backups:
                return max(matching_backups, key=lambda x: x.created_at)

            return None

        except Exception as e:
            logger.error(f"Failed to find last backup: {e}")
            return None

    async def _get_modified_files(
        self, source_paths: List[str], since: datetime
    ) -> List[str]:
        """Get files modified since specified time"""
        try:
            modified_files = []

            for source_path in source_paths:
                source = Path(source_path)
                if source.exists():
                    for file_path in source.rglob("*"):
                        if file_path.is_file():
                            file_mtime = datetime.fromtimestamp(
                                file_path.stat().st_mtime
                            )
                            if file_mtime > since:
                                modified_files.append(str(file_path))

            return modified_files

        except Exception as e:
            logger.error(f"Failed to get modified files: {e}")
            return []

    async def restore_backup(
        self, backup_file: str, target_path: str, recovery_type: RecoveryType
    ) -> RecoveryJob:
        """Restore from backup"""
        try:
            # Generate unique job ID
            job_id = f"recovery_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hash(backup_file) % 10000}"

            # Create recovery job
            job = RecoveryJob(
                job_id=job_id,
                backup_file=backup_file,
                recovery_type=recovery_type,
                target_path=target_path,
                status=BackupStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                recovered_files=[],
            )

            # Add to recovery jobs
            self.recovery_jobs.append(job)

            # Process recovery
            await self._process_recovery(job)

            return job

        except Exception as e:
            logger.error(f"Backup recovery failed: {e}")
            raise

    async def _process_recovery(self, job: RecoveryJob):
        """Process recovery job"""
        try:
            job.status = BackupStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)

            backup_path = Path(job.backup_file)

            # Decrypt if needed
            if backup_path.suffix == ".enc":
                if not self.encryption_key:
                    raise ValueError(
                        "Cannot restore encrypted backup without encryption key"
                    )

                decrypted_path = await self._decrypt_backup(backup_path)
                backup_path = decrypted_path

            # Decompress if needed
            if backup_path.suffix == ".gz":
                decompressed_path = await self._decompress_backup(backup_path)
                backup_path = decompressed_path

            # Extract backup
            target = Path(job.target_path)
            target.mkdir(parents=True, exist_ok=True)

            if backup_path.suffix in [".tar", ".tgz"]:
                await self._extract_tar_backup(backup_path, target)

            # Update job status
            job.status = BackupStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)

            # Get list of recovered files
            job.recovered_files = [str(f) for f in target.rglob("*") if f.is_file()]

            logger.info(
                f"Recovery completed: {job.job_id} ({len(job.recovered_files)} files)"
            )

        except Exception as e:
            logger.error(f"Recovery processing failed for {job.job_id}: {e}")
            job.status = BackupStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            raise

    async def _decrypt_backup(self, encrypted_path: Path) -> Path:
        """Decrypt backup file"""
        try:
            if not self.encryption_key:
                raise ValueError("Encryption not initialized")

            decrypted_path = encrypted_path.with_suffix(
                encrypted_path.suffix.replace(".enc", "")
            )

            # Read and decrypt file
            with open(encrypted_path, "rb") as f:
                encrypted_data = f.read()

            decrypted_data = self.encryption_key.decrypt(encrypted_data)

            with open(decrypted_path, "wb") as f:
                f.write(decrypted_data)

            return decrypted_path

        except Exception as e:
            logger.error(f"Failed to decrypt backup: {e}")
            raise

    async def _decompress_backup(self, compressed_path: Path) -> Path:
        """Decompress backup file"""
        try:
            decompressed_path = compressed_path.with_suffix(
                compressed_path.suffix.replace(".gz", "")
            )

            with gzip.open(compressed_path, "rb") as f_in:
                with open(decompressed_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            return decompressed_path

        except Exception as e:
            logger.error(f"Failed to decompress backup: {e}")
            raise

    async def _extract_tar_backup(self, backup_path: Path, target_path: Path):
        """Extract tar backup"""
        try:
            with tarfile.open(backup_path, "r:*") as tar:
                # Extract all members safely
                for member in tar.getmembers():
                    if member.isreg() or member.isdir():
                        tar.extract(member, target_path)

        except Exception as e:
            logger.error(f"Failed to extract tar backup: {e}")
            raise

    async def list_backups(
        self, backup_type: Optional[BackupType] = None, limit: int = 50
    ) -> List[BackupJob]:
        """List available backups"""
        try:
            backups = self.backup_history

            if backup_type:
                backups = [b for b in backups if b.config.backup_type == backup_type]

            # Sort by creation date (newest first)
            backups.sort(key=lambda x: x.created_at, reverse=True)

            return backups[:limit]

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []

    async def delete_backup(self, job_id: str) -> bool:
        """Delete backup"""
        try:
            # Find backup job
            backup_job = None
            for job in self.backup_history:
                if job.job_id == job_id:
                    backup_job = job
                    break

            if not backup_job:
                return False

            # Delete backup file
            if backup_job.file_path and Path(backup_job.file_path).exists():
                Path(backup_job.file_path).unlink()

            # Remove from history
            self.backup_history = [b for b in self.backup_history if b.job_id != job_id]

            logger.info(f"Backup deleted: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete backup {job_id}: {e}")
            return False

    async def cleanup_old_backups(self, days: int = 30) -> int:
        """Clean up old backups"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            deleted_count = 0

            # Check backup history
            for backup in self.backup_history[:]:
                if backup.created_at < cutoff_date:
                    # Delete backup file if exists
                    if backup.file_path and Path(backup.file_path).exists():
                        Path(backup.file_path).unlink()

                    # Remove from history
                    self.backup_history.remove(backup)
                    deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old backups")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0

    async def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics"""
        try:
            total_backups = len(self.backup_history)
            completed_backups = len(
                [b for b in self.backup_history if b.status == BackupStatus.COMPLETED]
            )
            failed_backups = len(
                [b for b in self.backup_history if b.status == BackupStatus.FAILED]
            )

            # Calculate total backup size
            total_size = sum(
                b.file_size or 0 for b in self.backup_history if b.file_size
            )

            # Calculate by backup type
            type_stats = {}
            for backup in self.backup_history:
                backup_type = backup.config.backup_type.value
                if backup_type not in type_stats:
                    type_stats[backup_type] = {"total": 0, "completed": 0, "failed": 0}
                type_stats[backup_type]["total"] += 1
                if backup.status == BackupStatus.COMPLETED:
                    type_stats[backup_type]["completed"] += 1
                elif backup.status == BackupStatus.FAILED:
                    type_stats[backup_type]["failed"] += 1

            # Recent backups (last 7 days)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            recent_backups = len(
                [b for b in self.backup_history if b.created_at > cutoff_date]
            )

            return {
                "total_backups": total_backups,
                "completed_backups": completed_backups,
                "failed_backups": failed_backups,
                "total_size_bytes": total_size,
                "recent_backups_7_days": recent_backups,
                "by_backup_type": type_stats,
                "success_rate": (
                    (completed_backups / total_backups * 100)
                    if total_backups > 0
                    else 0
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get backup statistics: {e}")
            return {"error": str(e)}

    def _calculate_config_hash(self, config: BackupConfig) -> str:
        """Calculate configuration hash"""
        try:
            config_str = json.dumps(
                {
                    "backup_type": config.backup_type.value,
                    "source_paths": sorted(config.source_paths),
                    "compression": config.compression,
                    "encryption": config.encryption,
                    "retention_days": config.retention_days,
                    "schedule_interval_hours": config.schedule_interval_hours,
                },
                sort_keys=True,
            )

            return hashlib.sha256(config_str.encode()).hexdigest()

        except Exception as e:
            logger.error(f"Failed to calculate config hash: {e}")
            return ""

    async def start_backup_scheduler(self):
        """Start automatic backup scheduler"""
        logger.info("Starting backup scheduler")

        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour

                # Check if any scheduled backups are due
                for backup in self.backup_history:
                    if (
                        backup.config.schedule_interval_hours > 0
                        and backup.status == BackupStatus.COMPLETED
                    ):

                        next_backup_time = backup.completed_at + timedelta(
                            hours=backup.config.schedule_interval_hours
                        )

                        if datetime.now(timezone.utc) >= next_backup_time:
                            # Create new backup with same configuration
                            await self.create_backup(backup.config)

            except Exception as e:
                logger.error(f"Backup scheduler error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying


# Global backup engine instance
compliance_backup_engine = ComplianceBackupEngine()
