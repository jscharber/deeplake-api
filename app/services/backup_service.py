"""
Backup and disaster recovery service.

Provides automated backup, restore, and disaster recovery capabilities
for DeepLake datasets, metadata, and system state.
"""

import asyncio
import os
import shutil
import tempfile
import tarfile
import gzip
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    boto3 = None
    ClientError = Exception
    HAS_BOTO3 = False

from app.config.settings import settings
from app.config.logging import get_logger, LoggingMixin
from app.services.deeplake_service import DeepLakeService
from app.services.cache_service import CacheService
from app.models.exceptions import BackupException


class BackupType(Enum):
    """Types of backups."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class BackupStatus(Enum):
    """Backup operation status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StorageBackend(Enum):
    """Storage backend types."""
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"


@dataclass
class BackupConfig:
    """Backup configuration."""
    enabled: bool = True
    schedule: str = "0 2 * * *"  # Daily at 2 AM
    retention_days: int = 30
    storage_backend: StorageBackend = StorageBackend.LOCAL
    storage_path: str = "/tmp/backups"
    compression: bool = True
    encryption: bool = False
    parallel_workers: int = 4
    
    # S3 configuration
    s3_bucket: Optional[str] = None
    s3_prefix: str = "deeplake-backups"
    s3_region: str = "us-east-1"
    
    # Retention policy
    daily_retention: int = 7
    weekly_retention: int = 4
    monthly_retention: int = 12
    
    # Disaster recovery
    cross_region_replication: bool = False
    secondary_region: Optional[str] = None


@dataclass
class BackupMetadata:
    """Backup metadata."""
    backup_id: str
    timestamp: datetime
    type: BackupType
    status: BackupStatus
    tenant_id: Optional[str] = None
    dataset_ids: List[str] = field(default_factory=list)
    size_bytes: int = 0
    compressed_size_bytes: int = 0
    checksum: Optional[str] = None
    duration_seconds: float = 0.0
    storage_path: str = ""
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RestoreOptions:
    """Restore operation options."""
    target_tenant: Optional[str] = None
    dataset_mapping: Dict[str, str] = field(default_factory=dict)
    overwrite_existing: bool = False
    verify_integrity: bool = True
    restore_indexes: bool = True
    restore_metadata: bool = True


class BackupService(LoggingMixin):
    """Service for backup and disaster recovery operations."""
    
    def __init__(
        self,
        deeplake_service: DeepLakeService,
        cache_service: Optional[CacheService] = None
    ):
        super().__init__()
        self.deeplake_service = deeplake_service
        self.cache_service = cache_service
        self.config = self._load_config()
        self.backup_history: List[BackupMetadata] = []
        self.active_backups: Dict[str, BackupMetadata] = {}
        self._s3_client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize backup service."""
        if self._initialized:
            return
        
        try:
            # Create backup directory
            Path(self.config.storage_path).mkdir(parents=True, exist_ok=True)
            
            # Initialize S3 client if needed
            if self.config.storage_backend == StorageBackend.S3:
                if not HAS_BOTO3:
                    raise BackupException("boto3 is required for S3 storage backend")
                    
                self._s3_client = boto3.client(
                    's3',
                    region_name=self.config.s3_region
                )
                
                # Verify bucket access
                try:
                    self._s3_client.head_bucket(Bucket=self.config.s3_bucket)
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        # Create bucket if it doesn't exist
                        self._s3_client.create_bucket(Bucket=self.config.s3_bucket)
                        self.logger.info(f"Created S3 bucket: {self.config.s3_bucket}")
            
            # Load existing backup history
            await self._load_backup_history()
            
            self._initialized = True
            self.logger.info("Backup service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize backup service: {e}")
            raise BackupException(f"Backup service initialization failed: {e}")
    
    def _load_config(self) -> BackupConfig:
        """Load backup configuration."""
        return BackupConfig(
            enabled=getattr(settings, 'backup_enabled', True),
            storage_backend=StorageBackend(getattr(settings, 'backup_storage', 'local')),
            storage_path=getattr(settings, 'backup_path', '/tmp/backups'),
            s3_bucket=getattr(settings, 'backup_s3_bucket', None),
            s3_region=getattr(settings, 'backup_s3_region', 'us-east-1'),
            retention_days=getattr(settings, 'backup_retention_days', 30),
            compression=getattr(settings, 'backup_compression', True),
            encryption=getattr(settings, 'backup_encryption', False),
        )
    
    async def create_backup(
        self,
        backup_type: BackupType = BackupType.FULL,
        tenant_id: Optional[str] = None,
        dataset_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a backup.
        
        Args:
            backup_type: Type of backup to create
            tenant_id: Specific tenant to backup (None for all)
            dataset_ids: Specific datasets to backup (None for all)
            metadata: Additional metadata to include
            
        Returns:
            backup_id: Unique identifier for the backup
        """
        if not self._initialized:
            await self.initialize()
        
        backup_id = self._generate_backup_id()
        start_time = datetime.now()
        
        backup_metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=start_time,
            type=backup_type,
            status=BackupStatus.PENDING,
            tenant_id=tenant_id,
            dataset_ids=dataset_ids or [],
            metadata=metadata or {}
        )
        
        self.active_backups[backup_id] = backup_metadata
        
        try:
            # Update status to running
            backup_metadata.status = BackupStatus.RUNNING
            
            # Create backup based on type
            if backup_type == BackupType.FULL:
                await self._create_full_backup(backup_metadata, tenant_id, dataset_ids)
            elif backup_type == BackupType.INCREMENTAL:
                await self._create_incremental_backup(backup_metadata, tenant_id, dataset_ids)
            elif backup_type == BackupType.SNAPSHOT:
                await self._create_snapshot_backup(backup_metadata, tenant_id, dataset_ids)
            else:
                raise BackupException(f"Unsupported backup type: {backup_type}")
            
            # Calculate duration
            backup_metadata.duration_seconds = (datetime.now() - start_time).total_seconds()
            backup_metadata.status = BackupStatus.COMPLETED
            
            # Store backup metadata
            await self._store_backup_metadata(backup_metadata)
            
            # Add to history
            self.backup_history.append(backup_metadata)
            
            self.logger.info(
                f"Backup completed successfully",
                backup_id=backup_id,
                type=backup_type.value,
                duration=backup_metadata.duration_seconds,
                size=backup_metadata.size_bytes
            )
            
            return backup_id
            
        except Exception as e:
            backup_metadata.status = BackupStatus.FAILED
            backup_metadata.error_message = str(e)
            backup_metadata.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            self.logger.error(
                f"Backup failed",
                backup_id=backup_id,
                error=str(e),
                duration=backup_metadata.duration_seconds
            )
            
            raise BackupException(f"Backup failed: {e}")
            
        finally:
            # Remove from active backups
            self.active_backups.pop(backup_id, None)
    
    async def _create_full_backup(
        self,
        backup_metadata: BackupMetadata,
        tenant_id: Optional[str],
        dataset_ids: Optional[List[str]]
    ):
        """Create a full backup."""
        backup_dir = Path(self.config.storage_path) / backup_metadata.backup_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Get datasets to backup
            datasets_to_backup = await self._get_datasets_to_backup(tenant_id, dataset_ids)
            
            total_size = 0
            
            # Backup each dataset
            for dataset_info in datasets_to_backup:
                dataset_id = dataset_info["id"]
                dataset_tenant = dataset_info["tenant_id"]
                
                self.logger.info(f"Backing up dataset: {dataset_id}")
                
                # Get dataset
                dataset = await self.deeplake_service.get_dataset(dataset_id, dataset_tenant)
                
                # Create dataset backup directory
                dataset_backup_dir = backup_dir / f"dataset_{dataset_id}"
                dataset_backup_dir.mkdir(exist_ok=True)
                
                # Export dataset data
                dataset_size = await self._backup_dataset(
                    dataset,
                    dataset_info,
                    dataset_backup_dir
                )
                
                total_size += dataset_size
                backup_metadata.dataset_ids.append(dataset_id)
            
            # Backup system metadata
            system_metadata_size = await self._backup_system_metadata(backup_dir)
            total_size += system_metadata_size
            
            # Create backup archive
            archive_path = await self._create_backup_archive(backup_dir, backup_metadata)
            
            # Calculate final size
            backup_metadata.size_bytes = total_size
            backup_metadata.compressed_size_bytes = os.path.getsize(archive_path)
            backup_metadata.storage_path = str(archive_path)
            
            # Calculate checksum
            backup_metadata.checksum = await self._calculate_checksum(archive_path)
            
            # Upload to remote storage if configured
            if self.config.storage_backend != StorageBackend.LOCAL:
                await self._upload_backup(archive_path, backup_metadata)
            
            # Clean up temporary directory
            shutil.rmtree(backup_dir)
            
        except Exception as e:
            # Clean up on failure
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            raise
    
    async def _create_incremental_backup(
        self,
        backup_metadata: BackupMetadata,
        tenant_id: Optional[str],
        dataset_ids: Optional[List[str]]
    ):
        """Create an incremental backup."""
        # Find last full backup
        last_full_backup = self._find_last_backup(BackupType.FULL, tenant_id)
        if not last_full_backup:
            # No full backup exists, create one instead
            self.logger.info("No full backup found, creating full backup instead")
            return await self._create_full_backup(backup_metadata, tenant_id, dataset_ids)
        
        # Implementation for incremental backup
        # This would compare current state with last backup and only backup changes
        # For now, fall back to full backup
        return await self._create_full_backup(backup_metadata, tenant_id, dataset_ids)
    
    async def _create_snapshot_backup(
        self,
        backup_metadata: BackupMetadata,
        tenant_id: Optional[str],
        dataset_ids: Optional[List[str]]
    ):
        """Create a snapshot backup."""
        # Create a point-in-time snapshot
        # This could use DeepLake's versioning features if available
        return await self._create_full_backup(backup_metadata, tenant_id, dataset_ids)
    
    async def _backup_dataset(
        self,
        dataset: Any,
        dataset_info: Dict[str, Any],
        backup_dir: Path
    ) -> int:
        """Backup a single dataset."""
        total_size = 0
        
        # Export dataset metadata
        metadata_file = backup_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(dataset_info, f, indent=2, default=str)
        
        total_size += metadata_file.stat().st_size
        
        # Export dataset data
        data_file = backup_dir / "data.json"
        
        # Get all vectors and metadata
        vectors = []
        try:
            # Use the dataset's iteration capabilities
            for i in range(len(dataset)):
                item = {
                    "id": str(i),
                    "vector": dataset.embedding[i].numpy().tolist(),
                    "metadata": dataset.metadata[i].data() if hasattr(dataset.metadata[i], 'data') else {}
                }
                vectors.append(item)
        except Exception as e:
            self.logger.warning(f"Error exporting dataset vectors: {e}")
        
        # Save vectors to file
        with open(data_file, 'w') as f:
            json.dump(vectors, f, indent=2)
        
        total_size += data_file.stat().st_size
        
        # Export schema information
        schema_file = backup_dir / "schema.json"
        schema_info = {
            "embedding_shape": getattr(dataset.embedding, 'shape', None),
            "embedding_dtype": str(getattr(dataset.embedding, 'dtype', None)),
            "metadata_schema": getattr(dataset.metadata, 'schema', None),
            "tensor_names": list(dataset.tensors.keys()) if hasattr(dataset, 'tensors') else []
        }
        
        with open(schema_file, 'w') as f:
            json.dump(schema_info, f, indent=2, default=str)
        
        total_size += schema_file.stat().st_size
        
        return total_size
    
    async def _backup_system_metadata(self, backup_dir: Path) -> int:
        """Backup system metadata."""
        system_dir = backup_dir / "system"
        system_dir.mkdir(exist_ok=True)
        
        total_size = 0
        
        # Backup configuration
        config_file = system_dir / "config.json"
        config_data = {
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "settings": {
                "embedding_dimension": getattr(settings, 'embedding_dimension', 1536),
                "default_distance_metric": getattr(settings, 'default_distance_metric', 'cosine'),
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        total_size += config_file.stat().st_size
        
        # Backup cache state if available
        if self.cache_service:
            try:
                cache_file = system_dir / "cache_state.json"
                cache_data = await self._export_cache_state()
                
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                
                total_size += cache_file.stat().st_size
                
            except Exception as e:
                self.logger.warning(f"Failed to backup cache state: {e}")
        
        return total_size
    
    async def _create_backup_archive(
        self,
        backup_dir: Path,
        backup_metadata: BackupMetadata
    ) -> str:
        """Create compressed backup archive."""
        archive_name = f"{backup_metadata.backup_id}.tar.gz"
        archive_path = Path(self.config.storage_path) / archive_name
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(backup_dir, arcname=backup_metadata.backup_id)
        
        return str(archive_path)
    
    async def _upload_backup(self, archive_path: str, backup_metadata: BackupMetadata):
        """Upload backup to remote storage."""
        if self.config.storage_backend == StorageBackend.S3:
            await self._upload_to_s3(archive_path, backup_metadata)
        else:
            raise BackupException(f"Unsupported storage backend: {self.config.storage_backend}")
    
    async def _upload_to_s3(self, archive_path: str, backup_metadata: BackupMetadata):
        """Upload backup to S3."""
        s3_key = f"{self.config.s3_prefix}/{backup_metadata.backup_id}.tar.gz"
        
        try:
            self._s3_client.upload_file(
                archive_path,
                self.config.s3_bucket,
                s3_key,
                ExtraArgs={
                    'Metadata': {
                        'backup-id': backup_metadata.backup_id,
                        'timestamp': backup_metadata.timestamp.isoformat(),
                        'type': backup_metadata.type.value
                    }
                }
            )
            
            # Update storage path to S3 location
            backup_metadata.storage_path = f"s3://{self.config.s3_bucket}/{s3_key}"
            
            # Remove local copy after successful upload
            if os.path.exists(archive_path):
                os.remove(archive_path)
                
        except Exception as e:
            raise BackupException(f"Failed to upload backup to S3: {e}")
    
    async def restore_backup(
        self,
        backup_id: str,
        options: Optional[RestoreOptions] = None
    ) -> bool:
        """
        Restore from backup.
        
        Args:
            backup_id: ID of backup to restore
            options: Restore options
            
        Returns:
            Success status
        """
        if not self._initialized:
            await self.initialize()
        
        options = options or RestoreOptions()
        
        try:
            # Find backup metadata
            backup_metadata = self._find_backup_by_id(backup_id)
            if not backup_metadata:
                raise BackupException(f"Backup not found: {backup_id}")
            
            self.logger.info(f"Starting restore from backup: {backup_id}")
            
            # Download backup if needed
            local_path = await self._download_backup(backup_metadata)
            
            # Extract backup
            restore_dir = Path(tempfile.mkdtemp())
            
            try:
                with tarfile.open(local_path, 'r:gz') as tar:
                    tar.extractall(restore_dir)
                
                # Restore datasets
                backup_content_dir = restore_dir / backup_id
                await self._restore_datasets(backup_content_dir, options)
                
                # Restore system metadata if requested
                if options.restore_metadata:
                    await self._restore_system_metadata(backup_content_dir)
                
                self.logger.info(f"Restore completed successfully: {backup_id}")
                return True
                
            finally:
                # Clean up temporary directory
                shutil.rmtree(restore_dir)
                
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            raise BackupException(f"Restore failed: {e}")
    
    async def _restore_datasets(self, backup_dir: Path, options: RestoreOptions):
        """Restore datasets from backup."""
        # Find dataset directories
        dataset_dirs = [d for d in backup_dir.iterdir() if d.is_dir() and d.name.startswith('dataset_')]
        
        for dataset_dir in dataset_dirs:
            dataset_id = dataset_dir.name.replace('dataset_', '')
            target_tenant = options.target_tenant
            
            # Apply dataset mapping if specified
            if dataset_id in options.dataset_mapping:
                new_dataset_id = options.dataset_mapping[dataset_id]
                dataset_id = new_dataset_id
            
            await self._restore_single_dataset(dataset_dir, dataset_id, target_tenant, options)
    
    async def _restore_single_dataset(
        self,
        dataset_dir: Path,
        dataset_id: str,
        target_tenant: Optional[str],
        options: RestoreOptions
    ):
        """Restore a single dataset."""
        try:
            # Load dataset metadata
            metadata_file = dataset_dir / "metadata.json"
            with open(metadata_file, 'r') as f:
                original_metadata = json.load(f)
            
            # Determine target tenant
            if not target_tenant:
                target_tenant = original_metadata.get("tenant_id", "default")
            
            # Check if dataset exists
            try:
                existing_dataset = await self.deeplake_service.get_dataset(dataset_id, target_tenant)
                if existing_dataset and not options.overwrite_existing:
                    self.logger.warning(f"Dataset {dataset_id} already exists, skipping restore")
                    return
            except:
                # Dataset doesn't exist, which is fine
                pass
            
            # Load schema
            schema_file = dataset_dir / "schema.json"
            with open(schema_file, 'r') as f:
                schema_info = json.load(f)
            
            # Create new dataset
            await self.deeplake_service.create_dataset(
                dataset_id=dataset_id,
                tenant_id=target_tenant,
                description=original_metadata.get("description", "Restored dataset"),
                metadata=original_metadata.get("metadata", {})
            )
            
            # Load and restore data
            data_file = dataset_dir / "data.json"
            with open(data_file, 'r') as f:
                vectors_data = json.load(f)
            
            # Restore vectors in batches
            batch_size = 100
            for i in range(0, len(vectors_data), batch_size):
                batch = vectors_data[i:i + batch_size]
                
                vectors = [item["vector"] for item in batch]
                metadata = [item["metadata"] for item in batch]
                
                await self.deeplake_service.add_vectors(
                    dataset_id=dataset_id,
                    tenant_id=target_tenant,
                    vectors=vectors,
                    metadata=metadata
                )
            
            # Restore indexes if requested
            if options.restore_indexes:
                # This would restore any index configuration
                pass
            
            self.logger.info(f"Restored dataset: {dataset_id} with {len(vectors_data)} vectors")
            
        except Exception as e:
            self.logger.error(f"Failed to restore dataset {dataset_id}: {e}")
            raise
    
    async def list_backups(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 50
    ) -> List[BackupMetadata]:
        """List available backups."""
        if not self._initialized:
            await self.initialize()
        
        backups = self.backup_history.copy()
        
        # Filter by tenant if specified
        if tenant_id:
            backups = [b for b in backups if b.tenant_id == tenant_id]
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.timestamp, reverse=True)
        
        return backups[:limit]
    
    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup."""
        backup_metadata = self._find_backup_by_id(backup_id)
        if not backup_metadata:
            raise BackupException(f"Backup not found: {backup_id}")
        
        try:
            # Delete from storage
            if self.config.storage_backend == StorageBackend.S3:
                await self._delete_from_s3(backup_metadata)
            else:
                # Delete local file
                if os.path.exists(backup_metadata.storage_path):
                    os.remove(backup_metadata.storage_path)
            
            # Remove from history
            self.backup_history = [b for b in self.backup_history if b.backup_id != backup_id]
            
            self.logger.info(f"Deleted backup: {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_id}: {e}")
            raise BackupException(f"Failed to delete backup: {e}")
    
    async def cleanup_old_backups(self):
        """Clean up old backups based on retention policy."""
        cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
        
        old_backups = [
            b for b in self.backup_history
            if b.timestamp < cutoff_date and b.status == BackupStatus.COMPLETED
        ]
        
        for backup in old_backups:
            try:
                await self.delete_backup(backup.backup_id)
                self.logger.info(f"Cleaned up old backup: {backup.backup_id}")
            except Exception as e:
                self.logger.error(f"Failed to cleanup backup {backup.backup_id}: {e}")
    
    def _generate_backup_id(self) -> str:
        """Generate unique backup ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{timestamp}_{os.urandom(4).hex()}"
    
    def _find_backup_by_id(self, backup_id: str) -> Optional[BackupMetadata]:
        """Find backup by ID."""
        for backup in self.backup_history:
            if backup.backup_id == backup_id:
                return backup
        return None
    
    def _find_last_backup(
        self,
        backup_type: BackupType,
        tenant_id: Optional[str] = None
    ) -> Optional[BackupMetadata]:
        """Find the most recent backup of specified type."""
        candidates = [
            b for b in self.backup_history
            if b.type == backup_type and b.status == BackupStatus.COMPLETED
        ]
        
        if tenant_id:
            candidates = [b for b in candidates if b.tenant_id == tenant_id]
        
        if not candidates:
            return None
        
        return max(candidates, key=lambda x: x.timestamp)
    
    async def _get_datasets_to_backup(
        self,
        tenant_id: Optional[str],
        dataset_ids: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Get list of datasets to backup."""
        if dataset_ids:
            # Backup specific datasets
            datasets = []
            for dataset_id in dataset_ids:
                try:
                    dataset_info = await self.deeplake_service.get_dataset_info(dataset_id, tenant_id)
                    datasets.append(dataset_info)
                except Exception as e:
                    self.logger.warning(f"Failed to get dataset info for {dataset_id}: {e}")
            return datasets
        else:
            # Backup all datasets for tenant
            if tenant_id:
                return await self.deeplake_service.list_datasets(tenant_id)
            else:
                # Backup all datasets (admin operation)
                # This would need admin privileges
                return []
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def _download_backup(self, backup_metadata: BackupMetadata) -> str:
        """Download backup from remote storage if needed."""
        if backup_metadata.storage_path.startswith('s3://'):
            # Download from S3
            local_path = Path(tempfile.mkdtemp()) / f"{backup_metadata.backup_id}.tar.gz"
            
            bucket_name = backup_metadata.storage_path.split('/')[2]
            s3_key = '/'.join(backup_metadata.storage_path.split('/')[3:])
            
            self._s3_client.download_file(bucket_name, s3_key, str(local_path))
            return str(local_path)
        else:
            # Local file
            return backup_metadata.storage_path
    
    async def _export_cache_state(self) -> Dict[str, Any]:
        """Export cache state for backup."""
        if not self.cache_service:
            return {}
        
        # Export cache keys and metadata
        # This is a simplified version - real implementation would be more comprehensive
        return {
            "cache_type": "redis",
            "exported_at": datetime.now().isoformat(),
            "note": "Cache state backup not fully implemented"
        }
    
    async def _store_backup_metadata(self, backup_metadata: BackupMetadata):
        """Store backup metadata."""
        metadata_file = Path(self.config.storage_path) / f"{backup_metadata.backup_id}_metadata.json"
        
        with open(metadata_file, 'w') as f:
            json.dump({
                "backup_id": backup_metadata.backup_id,
                "timestamp": backup_metadata.timestamp.isoformat(),
                "type": backup_metadata.type.value,
                "status": backup_metadata.status.value,
                "tenant_id": backup_metadata.tenant_id,
                "dataset_ids": backup_metadata.dataset_ids,
                "size_bytes": backup_metadata.size_bytes,
                "compressed_size_bytes": backup_metadata.compressed_size_bytes,
                "checksum": backup_metadata.checksum,
                "duration_seconds": backup_metadata.duration_seconds,
                "storage_path": backup_metadata.storage_path,
                "error_message": backup_metadata.error_message,
                "metadata": backup_metadata.metadata
            }, f, indent=2)
    
    async def _load_backup_history(self):
        """Load backup history from metadata files."""
        metadata_files = Path(self.config.storage_path).glob("*_metadata.json")
        
        for metadata_file in metadata_files:
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                
                backup_metadata = BackupMetadata(
                    backup_id=data["backup_id"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    type=BackupType(data["type"]),
                    status=BackupStatus(data["status"]),
                    tenant_id=data.get("tenant_id"),
                    dataset_ids=data.get("dataset_ids", []),
                    size_bytes=data.get("size_bytes", 0),
                    compressed_size_bytes=data.get("compressed_size_bytes", 0),
                    checksum=data.get("checksum"),
                    duration_seconds=data.get("duration_seconds", 0.0),
                    storage_path=data.get("storage_path", ""),
                    error_message=data.get("error_message"),
                    metadata=data.get("metadata", {})
                )
                
                self.backup_history.append(backup_metadata)
                
            except Exception as e:
                self.logger.warning(f"Failed to load backup metadata from {metadata_file}: {e}")
    
    async def _delete_from_s3(self, backup_metadata: BackupMetadata):
        """Delete backup from S3."""
        if backup_metadata.storage_path.startswith('s3://'):
            bucket_name = backup_metadata.storage_path.split('/')[2]
            s3_key = '/'.join(backup_metadata.storage_path.split('/')[3:])
            
            self._s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
    
    async def _restore_system_metadata(self, backup_dir: Path):
        """Restore system metadata."""
        system_dir = backup_dir / "system"
        if not system_dir.exists():
            return
        
        # Restore configuration if needed
        config_file = system_dir / "config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Apply configuration if needed
            self.logger.info(f"Restored system config from backup")
    
    async def get_backup_status(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get status of a backup operation."""
        # Check active backups first
        if backup_id in self.active_backups:
            return self.active_backups[backup_id]
        
        # Check completed backups
        return self._find_backup_by_id(backup_id)
    
    async def cancel_backup(self, backup_id: str) -> bool:
        """Cancel an active backup operation."""
        if backup_id in self.active_backups:
            backup_metadata = self.active_backups[backup_id]
            backup_metadata.status = BackupStatus.CANCELLED
            self.logger.info(f"Cancelled backup: {backup_id}")
            return True
        return False
    
    async def close(self):
        """Close the backup service."""
        self._initialized = False
        if self._s3_client:
            self._s3_client = None