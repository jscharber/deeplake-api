"""
HTTP API endpoints for bulk import/export operations.
"""

from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from fastapi.responses import FileResponse

from app.config.logging import get_logger
from app.models.schemas import BaseResponse
from app.services.import_export_service import ImportExportService, ImportJobStatus, ExportJobStatus
from app.services.deeplake_service import DeepLakeService
from app.api.http.dependencies import get_current_tenant, authorize_operation, get_deeplake_service, get_metrics_service
from app.services.metrics_service import MetricsService

logger = get_logger(__name__)
router = APIRouter()

# Services will be injected via dependencies


@router.post(
    "/datasets/{dataset_id}/import",
    response_model=ImportJobStatus,
    summary="Import vectors from file",
    description="Import vectors from CSV or JSON/JSONL file"
)
async def import_vectors(
    dataset_id: str,
    file: UploadFile = File(...),
    format: str = Query(None, description="File format (auto-detected if not specified)"),
    batch_size: int = Query(100, ge=1, le=1000, description="Batch size for processing"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("write_vectors"))
) -> ImportJobStatus:
    """Import vectors from uploaded file."""
    try:
        # Create import/export service instance
        import_export_service = ImportExportService(deeplake_service)
        
        # Track import request
        metrics_service.track_import_request(dataset_id, tenant_id)
        
        # Auto-detect format from filename if not specified
        if not format:
            if file.filename.endswith('.csv'):
                format = 'csv'
            elif file.filename.endswith('.json'):
                format = 'json'
            elif file.filename.endswith('.jsonl'):
                format = 'jsonl'
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Could not determine file format. Please specify format parameter or use .csv, .json, or .jsonl extension"
                )
        
        # Validate format
        if format not in ['csv', 'json', 'jsonl']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format}. Supported formats: csv, json, jsonl"
            )
        
        # Start import job
        if format == 'csv':
            job = await import_export_service.import_csv(
                dataset_id=dataset_id,
                file=file,
                tenant_id=tenant_id,
                batch_size=batch_size
            )
        else:
            job = await import_export_service.import_json(
                dataset_id=dataset_id,
                file=file,
                tenant_id=tenant_id,
                batch_size=batch_size
            )
        
        logger.info(
            "Started import job",
            job_id=job.job_id,
            dataset_id=dataset_id,
            format=format,
            tenant_id=tenant_id
        )
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import failed: {e}")
        metrics_service.track_error("import_error", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/import/{job_id}",
    response_model=ImportJobStatus,
    summary="Get import job status",
    description="Get the status of an import job"
)
async def get_import_status(
    job_id: str,
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    auth_info: dict = Depends(authorize_operation("read_vectors"))
) -> ImportJobStatus:
    """Get import job status."""
    try:
        # Create import/export service instance
        import_export_service = ImportExportService(deeplake_service)
        job = await import_export_service.get_import_status(job_id)
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get import status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/datasets/{dataset_id}/export",
    response_model=ExportJobStatus,
    summary="Export vectors to file",
    description="Export vectors to CSV or JSON/JSONL file"
)
async def export_vectors(
    dataset_id: str,
    format: str = Query("json", description="Export format: csv, json, or jsonl"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of vectors to export"),
    filters: Optional[str] = Query(None, description="JSON-encoded metadata filters"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    metrics_service: MetricsService = Depends(get_metrics_service),
    auth_info: dict = Depends(authorize_operation("read_vectors"))
) -> ExportJobStatus:
    """Export vectors to file."""
    try:
        # Create import/export service instance
        import_export_service = ImportExportService(deeplake_service)
        
        # Track export request
        metrics_service.track_export_request(dataset_id, tenant_id)
        
        # Validate format
        if format not in ['csv', 'json', 'jsonl']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format}. Supported formats: csv, json, jsonl"
            )
        
        # Parse filters if provided
        parsed_filters = None
        if filters:
            try:
                import json
                parsed_filters = json.loads(filters)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in filters parameter")
        
        # Start export job
        if format == 'csv':
            job = await import_export_service.export_csv(
                dataset_id=dataset_id,
                tenant_id=tenant_id,
                filters=parsed_filters,
                limit=limit
            )
        else:
            job = await import_export_service.export_json(
                dataset_id=dataset_id,
                tenant_id=tenant_id,
                filters=parsed_filters,
                limit=limit,
                format=format
            )
        
        logger.info(
            "Started export job",
            job_id=job.job_id,
            dataset_id=dataset_id,
            format=format,
            tenant_id=tenant_id
        )
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        metrics_service.track_error("export_error", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/export/{job_id}",
    response_model=ExportJobStatus,
    summary="Get export job status",
    description="Get the status of an export job"
)
async def get_export_status(
    job_id: str,
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    auth_info: dict = Depends(authorize_operation("read_vectors"))
) -> ExportJobStatus:
    """Get export job status."""
    try:
        # Create import/export service instance
        import_export_service = ImportExportService(deeplake_service)
        job = await import_export_service.get_export_status(job_id)
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get export status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/export/{job_id}/download",
    summary="Download exported file",
    description="Download the exported file for a completed export job"
)
async def download_export(
    job_id: str,
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    auth_info: dict = Depends(authorize_operation("read_vectors"))
) -> FileResponse:
    """Download exported file."""
    try:
        # Create import/export service instance
        import_export_service = ImportExportService(deeplake_service)
        file_path, content_type = await import_export_service.download_export(job_id)
        
        # Get job info for filename
        job = await import_export_service.get_export_status(job_id)
        filename = f"deeplake_export_{job.dataset_id}_{job_id}.{job.format}"
        
        return FileResponse(
            path=str(file_path),
            media_type=content_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cleanup task
@router.post(
    "/admin/cleanup-jobs",
    response_model=BaseResponse,
    summary="Clean up old import/export jobs",
    description="Remove old completed jobs and their associated files (admin only)"
)
async def cleanup_jobs(
    background_tasks: BackgroundTasks,
    max_age_hours: int = Query(24, ge=1, description="Maximum age of jobs to keep (hours)"),
    tenant_id: str = Depends(get_current_tenant),
    deeplake_service: DeepLakeService = Depends(get_deeplake_service),
    auth_info: dict = Depends(authorize_operation("admin"))
) -> BaseResponse:
    """Clean up old import/export jobs."""
    # Admin permission is already checked by authorize_operation("admin")
    # Create import/export service instance
    import_export_service = ImportExportService(deeplake_service)
    
    # Schedule cleanup in background
    background_tasks.add_task(
        import_export_service.cleanup_old_jobs,
        max_age_hours=max_age_hours
    )
    
    return BaseResponse(
        success=True,
        message=f"Cleanup scheduled for jobs older than {max_age_hours} hours"
    )