"""
Backup and disaster recovery API endpoints.
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path
from pydantic import BaseModel, Field
from datetime import datetime

from app.config.logging import get_logger
from app.services.backup_service import (
    BackupService, BackupType, BackupStatus, RestoreOptions,
    BackupMetadata, BackupConfig
)
from app.api.http.dependencies import (
    get_current_tenant, authorize_operation, get_backup_service
)
from app.models.exceptions import BackupException

logger = get_logger(__name__)
router = APIRouter(tags=["backup"])


class CreateBackupRequest(BaseModel):
    """Request to create a backup."""
    type: BackupType = BackupType.FULL
    dataset_ids: Optional[List[str]] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RestoreBackupRequest(BaseModel):
    """Request to restore a backup."""
    backup_id: str
    target_tenant: Optional[str] = None
    dataset_mapping: Optional[Dict[str, str]] = None
    overwrite_existing: bool = False
    verify_integrity: bool = True
    restore_indexes: bool = True
    restore_metadata: bool = True


class BackupResponse(BaseModel):
    """Backup information response."""
    backup_id: str
    timestamp: datetime
    type: str
    status: str
    tenant_id: Optional[str]
    dataset_ids: List[str]
    size_bytes: int
    compressed_size_bytes: int
    checksum: Optional[str]
    duration_seconds: float
    storage_path: str
    error_message: Optional[str]
    metadata: Dict[str, Any]


class BackupStatusResponse(BaseModel):
    """Backup status response."""
    backup_id: str
    status: str
    progress: Optional[float] = None
    current_operation: Optional[str] = None
    error_message: Optional[str] = None


class RestoreStatusResponse(BaseModel):
    """Restore status response."""
    restore_id: str
    status: str
    progress: Optional[float] = None
    current_operation: Optional[str] = None
    error_message: Optional[str] = None




@router.post("/backups", response_model=Dict[str, str])
async def create_backup(
    request: CreateBackupRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant),
    backup_service: BackupService = Depends(get_backup_service),
    auth_info: dict = Depends(authorize_operation("backup"))
) -> Dict[str, str]:
    """Create a new backup."""
    try:
        # Add metadata
        metadata = request.metadata or {}
        metadata.update({
            "created_by": auth_info.get("user_id", "system"),
            "description": request.description or f"Backup created at {datetime.now().isoformat()}"
        })
        
        # Create backup asynchronously
        backup_id = await backup_service.create_backup(
            backup_type=request.type,
            tenant_id=tenant_id,
            dataset_ids=request.dataset_ids,
            metadata=metadata
        )
        
        logger.info(
            f"Backup created",
            backup_id=backup_id,
            tenant_id=tenant_id,
            type=request.type.value
        )
        
        return {
            "backup_id": backup_id,
            "message": "Backup created successfully",
            "status": "completed"
        }
        
    except BackupException as e:
        logger.error(f"Backup creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during backup creation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/backups", response_model=List[BackupResponse])
async def list_backups(
    limit: int = Query(50, ge=1, le=1000),
    tenant_id: str = Depends(get_current_tenant),
    backup_service: BackupService = Depends(get_backup_service),
    auth_info: dict = Depends(authorize_operation("backup"))
) -> List[BackupResponse]:
    """List backups for the current tenant."""
    try:
        backups = await backup_service.list_backups(tenant_id=tenant_id, limit=limit)
        
        return [
            BackupResponse(
                backup_id=backup.backup_id,
                timestamp=backup.timestamp,
                type=backup.type.value,
                status=backup.status.value,
                tenant_id=backup.tenant_id,
                dataset_ids=backup.dataset_ids,
                size_bytes=backup.size_bytes,
                compressed_size_bytes=backup.compressed_size_bytes,
                checksum=backup.checksum,
                duration_seconds=backup.duration_seconds,
                storage_path=backup.storage_path,
                error_message=backup.error_message,
                metadata=backup.metadata
            )
            for backup in backups
        ]
        
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        raise HTTPException(status_code=500, detail="Failed to list backups")


@router.get("/backups/{backup_id}", response_model=BackupResponse)
async def get_backup(
    backup_id: str = Path(..., description="Backup ID"),
    tenant_id: str = Depends(get_current_tenant),
    backup_service: BackupService = Depends(get_backup_service),
    auth_info: dict = Depends(authorize_operation("backup"))
) -> BackupResponse:
    """Get backup details."""
    try:
        backup = await backup_service.get_backup_status(backup_id)
        
        if not backup:
            raise HTTPException(status_code=404, detail="Backup not found")
        
        # Check if user has access to this backup
        if backup.tenant_id != tenant_id and not auth_info.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return BackupResponse(
            backup_id=backup.backup_id,
            timestamp=backup.timestamp,
            type=backup.type.value,
            status=backup.status.value,
            tenant_id=backup.tenant_id,
            dataset_ids=backup.dataset_ids,
            size_bytes=backup.size_bytes,
            compressed_size_bytes=backup.compressed_size_bytes,
            checksum=backup.checksum,
            duration_seconds=backup.duration_seconds,
            storage_path=backup.storage_path,
            error_message=backup.error_message,
            metadata=backup.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backup {backup_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get backup")


@router.post("/backups/{backup_id}/restore", response_model=Dict[str, str])
async def restore_backup(
    backup_id: str = Path(..., description="Backup ID"),
    request: RestoreBackupRequest = ...,
    background_tasks: BackgroundTasks = ...,
    tenant_id: str = Depends(get_current_tenant),
    backup_service: BackupService = Depends(get_backup_service),
    auth_info: dict = Depends(authorize_operation("restore"))
) -> Dict[str, str]:
    """Restore from backup."""
    try:
        # Validate backup exists and user has access
        backup = await backup_service.get_backup_status(backup_id)
        if not backup:
            raise HTTPException(status_code=404, detail="Backup not found")
        
        if backup.tenant_id != tenant_id and not auth_info.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Set up restore options
        restore_options = RestoreOptions(
            target_tenant=request.target_tenant or tenant_id,
            dataset_mapping=request.dataset_mapping or {},
            overwrite_existing=request.overwrite_existing,
            verify_integrity=request.verify_integrity,
            restore_indexes=request.restore_indexes,
            restore_metadata=request.restore_metadata
        )
        
        # Perform restore
        success = await backup_service.restore_backup(backup_id, restore_options)
        
        if success:
            logger.info(
                f"Backup restored successfully",
                backup_id=backup_id,
                tenant_id=tenant_id,
                target_tenant=restore_options.target_tenant
            )
            
            return {
                "message": "Backup restored successfully",
                "backup_id": backup_id,
                "status": "completed"
            }
        else:
            raise HTTPException(status_code=500, detail="Restore failed")
            
    except HTTPException:
        raise
    except BackupException as e:
        logger.error(f"Restore failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during restore: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/backups/{backup_id}")
async def delete_backup(
    backup_id: str = Path(..., description="Backup ID"),
    tenant_id: str = Depends(get_current_tenant),
    backup_service: BackupService = Depends(get_backup_service),
    auth_info: dict = Depends(authorize_operation("backup"))
) -> Dict[str, str]:
    """Delete a backup."""
    try:
        # Validate backup exists and user has access
        backup = await backup_service.get_backup_status(backup_id)
        if not backup:
            raise HTTPException(status_code=404, detail="Backup not found")
        
        if backup.tenant_id != tenant_id and not auth_info.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete backup
        success = await backup_service.delete_backup(backup_id)
        
        if success:
            logger.info(f"Backup deleted", backup_id=backup_id, tenant_id=tenant_id)
            return {"message": "Backup deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Delete failed")
            
    except HTTPException:
        raise
    except BackupException as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during delete: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/backups/{backup_id}/cancel")
async def cancel_backup(
    backup_id: str = Path(..., description="Backup ID"),
    tenant_id: str = Depends(get_current_tenant),
    backup_service: BackupService = Depends(get_backup_service),
    auth_info: dict = Depends(authorize_operation("backup"))
) -> Dict[str, str]:
    """Cancel an active backup."""
    try:
        # Validate backup exists and user has access
        backup = await backup_service.get_backup_status(backup_id)
        if not backup:
            raise HTTPException(status_code=404, detail="Backup not found")
        
        if backup.tenant_id != tenant_id and not auth_info.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Cancel backup
        success = await backup_service.cancel_backup(backup_id)
        
        if success:
            logger.info(f"Backup cancelled", backup_id=backup_id, tenant_id=tenant_id)
            return {"message": "Backup cancelled successfully"}
        else:
            raise HTTPException(status_code=400, detail="Backup cannot be cancelled")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel backup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Admin endpoints
@router.get("/admin/backups", response_model=List[BackupResponse])
async def admin_list_backups(
    limit: int = Query(100, ge=1, le=1000),
    tenant_filter: Optional[str] = Query(None, description="Filter by tenant ID"),
    backup_service: BackupService = Depends(get_backup_service),
    auth_info: dict = Depends(authorize_operation("admin"))
) -> List[BackupResponse]:
    """List all backups (admin only)."""
    try:
        backups = await backup_service.list_backups(tenant_id=tenant_filter, limit=limit)
        
        return [
            BackupResponse(
                backup_id=backup.backup_id,
                timestamp=backup.timestamp,
                type=backup.type.value,
                status=backup.status.value,
                tenant_id=backup.tenant_id,
                dataset_ids=backup.dataset_ids,
                size_bytes=backup.size_bytes,
                compressed_size_bytes=backup.compressed_size_bytes,
                checksum=backup.checksum,
                duration_seconds=backup.duration_seconds,
                storage_path=backup.storage_path,
                error_message=backup.error_message,
                metadata=backup.metadata
            )
            for backup in backups
        ]
        
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        raise HTTPException(status_code=500, detail="Failed to list backups")


@router.post("/admin/backups/cleanup")
async def admin_cleanup_backups(
    background_tasks: BackgroundTasks,
    backup_service: BackupService = Depends(get_backup_service),
    auth_info: dict = Depends(authorize_operation("admin"))
) -> Dict[str, str]:
    """Clean up old backups based on retention policy (admin only)."""
    try:
        # Schedule cleanup in background
        background_tasks.add_task(backup_service.cleanup_old_backups)
        
        logger.info("Backup cleanup scheduled")
        
        return {"message": "Backup cleanup scheduled"}
        
    except Exception as e:
        logger.error(f"Failed to schedule backup cleanup: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule cleanup")


@router.get("/admin/backups/stats")
async def admin_backup_stats(
    backup_service: BackupService = Depends(get_backup_service),
    auth_info: dict = Depends(authorize_operation("admin"))
) -> Dict[str, Any]:
    """Get backup system statistics (admin only)."""
    try:
        backups = await backup_service.list_backups(limit=1000)
        
        # Calculate statistics
        total_backups = len(backups)
        completed_backups = len([b for b in backups if b.status == "completed"])
        failed_backups = len([b for b in backups if b.status == "failed"])
        total_size = sum(b.size_bytes for b in backups if b.status == "completed")
        compressed_size = sum(b.compressed_size_bytes for b in backups if b.status == "completed")
        
        # Group by type
        type_stats = {}
        for backup in backups:
            backup_type = backup.type
            if backup_type not in type_stats:
                type_stats[backup_type] = {"count": 0, "size": 0}
            type_stats[backup_type]["count"] += 1
            if backup.status == "completed":
                type_stats[backup_type]["size"] += backup.size_bytes
        
        return {
            "total_backups": total_backups,
            "completed_backups": completed_backups,
            "failed_backups": failed_backups,
            "success_rate": completed_backups / total_backups if total_backups > 0 else 0,
            "total_size_bytes": total_size,
            "compressed_size_bytes": compressed_size,
            "compression_ratio": compressed_size / total_size if total_size > 0 else 0,
            "type_breakdown": type_stats,
            "storage_backend": backup_service.config.storage_backend.value,
            "retention_days": backup_service.config.retention_days
        }
        
    except Exception as e:
        logger.error(f"Failed to get backup stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get backup stats")


@router.get("/config")
async def get_backup_config(
    backup_service: BackupService = Depends(get_backup_service),
    auth_info: dict = Depends(authorize_operation("backup"))
) -> Dict[str, Any]:
    """Get backup configuration."""
    try:
        config = backup_service.config
        
        return {
            "enabled": config.enabled,
            "schedule": config.schedule,
            "retention_days": config.retention_days,
            "storage_backend": config.storage_backend.value,
            "compression": config.compression,
            "encryption": config.encryption,
            "parallel_workers": config.parallel_workers,
            "cross_region_replication": config.cross_region_replication
        }
        
    except Exception as e:
        logger.error(f"Failed to get backup config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get backup config")


@router.post("/test-backup")
async def test_backup_system(
    tenant_id: str = Depends(get_current_tenant),
    backup_service: BackupService = Depends(get_backup_service),
    auth_info: dict = Depends(authorize_operation("backup"))
) -> Dict[str, Any]:
    """Test backup system functionality."""
    try:
        # Test backup service initialization
        if not backup_service._initialized:
            await backup_service.initialize()
        
        # Test storage backend connectivity
        storage_test = {"storage_backend": backup_service.config.storage_backend.value}
        
        if backup_service.config.storage_backend.value == "s3":
            try:
                if backup_service._s3_client:
                    backup_service._s3_client.head_bucket(Bucket=backup_service.config.s3_bucket)
                    storage_test["s3_connectivity"] = "success"
                else:
                    storage_test["s3_connectivity"] = "not_configured"
            except Exception as e:
                storage_test["s3_connectivity"] = f"failed: {e}"
        
        return {
            "backup_service_initialized": backup_service._initialized,
            "storage_backend": backup_service.config.storage_backend.value,
            "storage_path": backup_service.config.storage_path,
            "storage_test": storage_test,
            "active_backups": len(backup_service.active_backups),
            "backup_history": len(backup_service.backup_history)
        }
        
    except Exception as e:
        logger.error(f"Backup system test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup system test failed: {e}")