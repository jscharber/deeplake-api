"""
Bulk import/export service for datasets.

Supports importing and exporting vectors in various formats:
- CSV: Simple tabular format for vectors and metadata
- JSON: Structured format with full metadata support
- JSONL: Line-delimited JSON for streaming large datasets
"""

import csv
import json
import io
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, AsyncIterator, Tuple
from pathlib import Path
import aiofiles
import numpy as np
from fastapi import UploadFile, HTTPException
from pydantic import BaseModel, Field

from app.config.logging import get_logger, LoggingMixin
from app.config.settings import settings
from app.models.schemas import VectorCreate, VectorResponse, DatasetResponse
from app.models.exceptions import ValidationException, StorageException
from app.services.deeplake_service import DeepLakeService


class ImportJobStatus(BaseModel):
    """Import job status model."""
    job_id: str
    dataset_id: str
    status: str  # pending, running, completed, failed
    total_rows: int = 0
    processed_rows: int = 0
    successful_rows: int = 0
    failed_rows: int = 0
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None
    format: str  # csv, json, jsonl
    
    @property
    def progress_percentage(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return (self.processed_rows / self.total_rows) * 100


class ExportJobStatus(BaseModel):
    """Export job status model."""
    job_id: str
    dataset_id: str
    status: str  # pending, running, completed, failed
    total_vectors: int = 0
    exported_vectors: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    format: str  # csv, json, jsonl
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    
    @property
    def progress_percentage(self) -> float:
        if self.total_vectors == 0:
            return 0.0
        return (self.exported_vectors / self.total_vectors) * 100


class ImportExportService(LoggingMixin):
    """Service for bulk import/export operations."""
    
    def __init__(self, deeplake_service: DeepLakeService):
        super().__init__()
        self.deeplake_service = deeplake_service
        self.import_jobs: Dict[str, ImportJobStatus] = {}
        self.export_jobs: Dict[str, ExportJobStatus] = {}
        self.export_path = Path("/tmp/deeplake_exports")
        self.export_path.mkdir(exist_ok=True)
        
        # Initialize metrics service
        try:
            from app.services.metrics_service import MetricsService
            self.metrics_service = MetricsService()
        except ImportError:
            self.metrics_service = None
        
    async def import_csv(
        self,
        dataset_id: str,
        file: UploadFile,
        tenant_id: Optional[str] = None,
        batch_size: Optional[int] = None
    ) -> ImportJobStatus:
        """Import vectors from CSV file."""
        job_id = str(uuid.uuid4())
        job = ImportJobStatus(
            job_id=job_id,
            dataset_id=dataset_id,
            status="running",
            started_at=datetime.now(timezone.utc),
            format="csv"
        )
        self.import_jobs[job_id] = job
        
        # Set default batch size
        if batch_size is None:
            batch_size = settings.performance.import_batch_size
        
        # Run import in background
        asyncio.create_task(self._process_csv_import(job, dataset_id, file, tenant_id, batch_size))
        
        return job
    
    async def import_json(
        self,
        dataset_id: str,
        file: UploadFile,
        tenant_id: Optional[str] = None,
        batch_size: Optional[int] = None
    ) -> ImportJobStatus:
        """Import vectors from JSON/JSONL file."""
        job_id = str(uuid.uuid4())
        job = ImportJobStatus(
            job_id=job_id,
            dataset_id=dataset_id,
            status="running",
            started_at=datetime.now(timezone.utc),
            format="json" if file.filename.endswith('.json') else "jsonl"
        )
        self.import_jobs[job_id] = job
        
        # Set default batch size
        if batch_size is None:
            batch_size = settings.performance.import_batch_size
        
        # Run import in background
        asyncio.create_task(self._process_json_import(job, dataset_id, file, tenant_id, batch_size))
        
        return job
    
    async def export_csv(
        self,
        dataset_id: str,
        tenant_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> ExportJobStatus:
        """Export vectors to CSV file."""
        job_id = str(uuid.uuid4())
        job = ExportJobStatus(
            job_id=job_id,
            dataset_id=dataset_id,
            status="running",
            started_at=datetime.now(timezone.utc),
            format="csv"
        )
        self.export_jobs[job_id] = job
        
        # Run export in background
        asyncio.create_task(self._process_csv_export(job, dataset_id, tenant_id, filters, limit))
        
        return job
    
    async def export_json(
        self,
        dataset_id: str,
        tenant_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        format: str = "json"  # json or jsonl
    ) -> ExportJobStatus:
        """Export vectors to JSON/JSONL file."""
        job_id = str(uuid.uuid4())
        job = ExportJobStatus(
            job_id=job_id,
            dataset_id=dataset_id,
            status="running",
            started_at=datetime.now(timezone.utc),
            format=format
        )
        self.export_jobs[job_id] = job
        
        # Run export in background
        asyncio.create_task(self._process_json_export(job, dataset_id, tenant_id, filters, limit))
        
        return job
    
    async def get_import_status(self, job_id: str) -> ImportJobStatus:
        """Get import job status."""
        if job_id not in self.import_jobs:
            raise HTTPException(status_code=404, detail=f"Import job {job_id} not found")
        return self.import_jobs[job_id]
    
    async def get_export_status(self, job_id: str) -> ExportJobStatus:
        """Get export job status."""
        if job_id not in self.export_jobs:
            raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")
        return self.export_jobs[job_id]
    
    async def _process_csv_import(
        self,
        job: ImportJobStatus,
        dataset_id: str,
        file: UploadFile,
        tenant_id: Optional[str],
        batch_size: int
    ):
        """Process CSV import in background."""
        try:
            # Get dataset info
            dataset = await self.deeplake_service.get_dataset(dataset_id, tenant_id)
            dimensions = dataset.dimensions
            
            # Read CSV content
            content = await file.read()
            csv_reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
            
            # Count total rows
            rows = list(csv_reader)
            job.total_rows = len(rows)
            
            # Process in batches
            batch = []
            for row_num, row in enumerate(rows):
                try:
                    # Parse vector values
                    vector_values = json.loads(row.get('values', '[]'))
                    if len(vector_values) != dimensions:
                        raise ValidationException(
                            f"Vector dimension mismatch: expected {dimensions}, got {len(vector_values)}"
                        )
                    
                    # Parse metadata
                    metadata = {}
                    metadata_str = row.get('metadata', '{}')
                    if metadata_str:
                        metadata = json.loads(metadata_str)
                    
                    # Create vector object
                    vector = VectorCreate(
                        id=row.get('id'),
                        document_id=row.get('document_id', row.get('id', str(uuid.uuid4()))),
                        values=vector_values,
                        content=row.get('content'),
                        metadata=metadata,
                        chunk_id=row.get('chunk_id'),
                        content_hash=row.get('content_hash'),
                        content_type=row.get('content_type'),
                        language=row.get('language'),
                        chunk_index=int(row.get('chunk_index', 0)) if row.get('chunk_index') else None,
                        chunk_count=int(row.get('chunk_count', 1)) if row.get('chunk_count') else None,
                        model=row.get('model')
                    )
                    
                    batch.append(vector)
                    
                    # Process batch if full
                    if len(batch) >= batch_size:
                        await self._insert_batch(job, dataset_id, batch, tenant_id)
                        batch = []
                    
                    job.processed_rows += 1
                    
                except Exception as e:
                    job.failed_rows += 1
                    job.errors.append({
                        "row": row_num + 2,  # +2 for header and 0-indexing
                        "error": str(e),
                        "data": row
                    })
                    self.logger.error(f"Error processing row {row_num + 2}: {e}")
            
            # Process remaining batch
            if batch:
                await self._insert_batch(job, dataset_id, batch, tenant_id)
            
            # Update job status
            job.status = "completed" if job.failed_rows == 0 else "completed_with_errors"
            job.completed_at = datetime.now(timezone.utc)
            
            # Record metrics
            if self.metrics_service:
                duration = (job.completed_at - job.started_at).total_seconds()
                self.metrics_service.record_import_job(
                    dataset_id=dataset_id,
                    format=job.format,
                    status=job.status,
                    duration=duration,
                    rows_processed=job.processed_rows,
                    tenant_id=tenant_id
                )
            
        except Exception as e:
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            job.errors.append({
                "error": str(e),
                "type": "general_error"
            })
            
            # Record failed job metrics
            if self.metrics_service:
                duration = (job.completed_at - job.started_at).total_seconds()
                self.metrics_service.record_import_job(
                    dataset_id=dataset_id,
                    format=job.format,
                    status="failed",
                    duration=duration,
                    rows_processed=job.processed_rows,
                    tenant_id=tenant_id
                )
            
            self.logger.error(f"Import job {job.job_id} failed: {e}")
    
    async def _process_json_import(
        self,
        job: ImportJobStatus,
        dataset_id: str,
        file: UploadFile,
        tenant_id: Optional[str],
        batch_size: int
    ):
        """Process JSON/JSONL import in background."""
        try:
            # Get dataset info
            dataset = await self.deeplake_service.get_dataset(dataset_id, tenant_id)
            dimensions = dataset.dimensions
            
            # Read file content
            content = await file.read()
            
            if job.format == "json":
                # Parse entire JSON array
                try:
                    data = json.loads(content.decode('utf-8'))
                    if not isinstance(data, list):
                        raise ValidationException("JSON file must contain an array of vectors")
                    rows = data
                except json.JSONDecodeError as e:
                    raise ValidationException(f"Invalid JSON format: {e}")
            else:
                # Parse JSONL (one JSON object per line)
                rows = []
                for line_num, line in enumerate(content.decode('utf-8').strip().split('\n')):
                    if line:
                        try:
                            rows.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            job.errors.append({
                                "line": line_num + 1,
                                "error": f"Invalid JSON: {e}",
                                "data": line
                            })
            
            job.total_rows = len(rows)
            
            # Process in batches
            batch = []
            for row_num, row in enumerate(rows):
                try:
                    # Validate and create vector
                    vector_values = row.get('values', [])
                    if len(vector_values) != dimensions:
                        raise ValidationException(
                            f"Vector dimension mismatch: expected {dimensions}, got {len(vector_values)}"
                        )
                    
                    vector = VectorCreate(
                        id=row.get('id'),
                        document_id=row.get('document_id', row.get('id', str(uuid.uuid4()))),
                        values=vector_values,
                        content=row.get('content'),
                        metadata=row.get('metadata', {}),
                        chunk_id=row.get('chunk_id'),
                        content_hash=row.get('content_hash'),
                        content_type=row.get('content_type'),
                        language=row.get('language'),
                        chunk_index=row.get('chunk_index'),
                        chunk_count=row.get('chunk_count'),
                        model=row.get('model')
                    )
                    
                    batch.append(vector)
                    
                    # Process batch if full
                    if len(batch) >= batch_size:
                        await self._insert_batch(job, dataset_id, batch, tenant_id)
                        batch = []
                    
                    job.processed_rows += 1
                    
                except Exception as e:
                    job.failed_rows += 1
                    job.errors.append({
                        "row": row_num + 1,
                        "error": str(e),
                        "data": row
                    })
                    self.logger.error(f"Error processing row {row_num + 1}: {e}")
            
            # Process remaining batch
            if batch:
                await self._insert_batch(job, dataset_id, batch, tenant_id)
            
            # Update job status
            job.status = "completed" if job.failed_rows == 0 else "completed_with_errors"
            job.completed_at = datetime.now(timezone.utc)
            
            # Record metrics
            if self.metrics_service:
                duration = (job.completed_at - job.started_at).total_seconds()
                self.metrics_service.record_import_job(
                    dataset_id=dataset_id,
                    format=job.format,
                    status=job.status,
                    duration=duration,
                    rows_processed=job.processed_rows,
                    tenant_id=tenant_id
                )
            
        except Exception as e:
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            job.errors.append({
                "error": str(e),
                "type": "general_error"
            })
            
            # Record failed job metrics
            if self.metrics_service:
                duration = (job.completed_at - job.started_at).total_seconds()
                self.metrics_service.record_import_job(
                    dataset_id=dataset_id,
                    format=job.format,
                    status="failed",
                    duration=duration,
                    rows_processed=job.processed_rows,
                    tenant_id=tenant_id
                )
            
            self.logger.error(f"Import job {job.job_id} failed: {e}")
    
    async def _insert_batch(
        self,
        job: ImportJobStatus,
        dataset_id: str,
        batch: List[VectorCreate],
        tenant_id: Optional[str]
    ):
        """Insert a batch of vectors."""
        try:
            from app.models.schemas import VectorBatchInsert
            batch_request = VectorBatchInsert(
                vectors=batch,
                skip_existing=True,
                overwrite=False
            )
            
            result = await self.deeplake_service.batch_insert_vectors(
                dataset_id=dataset_id,
                batch_insert=batch_request,
                tenant_id=tenant_id
            )
            
            job.successful_rows += result.inserted_count
            job.failed_rows += result.failed_count
            
            if result.error_messages:
                for error in result.error_messages:
                    job.errors.append({
                        "error": error,
                        "type": "batch_error"
                    })
            
        except Exception as e:
            job.failed_rows += len(batch)
            job.errors.append({
                "error": str(e),
                "type": "batch_insert_error",
                "batch_size": len(batch)
            })
            self.logger.error(f"Batch insert failed: {e}")
    
    async def _process_csv_export(
        self,
        job: ExportJobStatus,
        dataset_id: str,
        tenant_id: Optional[str],
        filters: Optional[Dict[str, Any]],
        limit: Optional[int]
    ):
        """Process CSV export in background."""
        try:
            # Create export file
            file_path = self.export_path / f"{job.job_id}.csv"
            
            # Get total count
            stats = await self.deeplake_service.get_dataset_stats(dataset_id, tenant_id)
            job.total_vectors = min(stats.vector_count, limit) if limit else stats.vector_count
            
            # Write CSV file
            async with aiofiles.open(file_path, 'w', newline='') as f:
                # Write header
                header = [
                    'id', 'document_id', 'values', 'content', 'metadata',
                    'chunk_id', 'content_hash', 'content_type', 'language',
                    'chunk_index', 'chunk_count', 'model', 'created_at', 'updated_at'
                ]
                await f.write(','.join(header) + '\n')
                
                # Export vectors in batches
                offset = 0
                batch_size = 100
                
                while offset < job.total_vectors:
                    # Get batch of vectors
                    vectors = await self.deeplake_service.list_vectors(
                        dataset_id=dataset_id,
                        tenant_id=tenant_id,
                        offset=offset,
                        limit=min(batch_size, job.total_vectors - offset),
                        filters=filters
                    )
                    
                    # Write vectors to CSV
                    for vector in vectors:
                        row = [
                            vector.id,
                            vector.document_id,
                            json.dumps(vector.values),
                            vector.content or '',
                            json.dumps(vector.metadata),
                            vector.chunk_id or '',
                            vector.content_hash or '',
                            vector.content_type or '',
                            vector.language or '',
                            str(vector.chunk_index) if vector.chunk_index is not None else '',
                            str(vector.chunk_count) if vector.chunk_count is not None else '',
                            vector.model or '',
                            vector.created_at.isoformat(),
                            vector.updated_at.isoformat()
                        ]
                        
                        # Escape values containing commas or quotes
                        escaped_row = []
                        for value in row:
                            if ',' in str(value) or '"' in str(value):
                                escaped_row.append(f'"{str(value).replace('"', '""')}"')
                            else:
                                escaped_row.append(str(value))
                        
                        await f.write(','.join(escaped_row) + '\n')
                        job.exported_vectors += 1
                    
                    offset += batch_size
            
            # Update job status
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.file_size = file_path.stat().st_size
            job.download_url = f"/api/v1/export/{job.job_id}/download"
            
            # Record metrics
            if self.metrics_service:
                duration = (job.completed_at - job.started_at).total_seconds()
                self.metrics_service.record_export_job(
                    dataset_id=dataset_id,
                    format=job.format,
                    status=job.status,
                    duration=duration,
                    vectors_exported=job.exported_vectors,
                    tenant_id=tenant_id
                )
            
        except Exception as e:
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            
            # Record failed job metrics
            if self.metrics_service:
                duration = (job.completed_at - job.started_at).total_seconds()
                self.metrics_service.record_export_job(
                    dataset_id=dataset_id,
                    format=job.format,
                    status="failed",
                    duration=duration,
                    vectors_exported=job.exported_vectors,
                    tenant_id=tenant_id
                )
            
            self.logger.error(f"Export job {job.job_id} failed: {e}")
    
    async def _process_json_export(
        self,
        job: ExportJobStatus,
        dataset_id: str,
        tenant_id: Optional[str],
        filters: Optional[Dict[str, Any]],
        limit: Optional[int]
    ):
        """Process JSON/JSONL export in background."""
        try:
            # Create export file
            extension = "json" if job.format == "json" else "jsonl"
            file_path = self.export_path / f"{job.job_id}.{extension}"
            
            # Get total count
            stats = await self.deeplake_service.get_dataset_stats(dataset_id, tenant_id)
            job.total_vectors = min(stats.vector_count, limit) if limit else stats.vector_count
            
            # Write file
            async with aiofiles.open(file_path, 'w') as f:
                if job.format == "json":
                    await f.write('[\n')
                
                # Export vectors in batches
                offset = 0
                batch_size = 100
                first_item = True
                
                while offset < job.total_vectors:
                    # Get batch of vectors
                    vectors = await self.deeplake_service.list_vectors(
                        dataset_id=dataset_id,
                        tenant_id=tenant_id,
                        offset=offset,
                        limit=min(batch_size, job.total_vectors - offset),
                        filters=filters
                    )
                    
                    # Write vectors
                    for vector in vectors:
                        vector_dict = {
                            "id": vector.id,
                            "document_id": vector.document_id,
                            "values": vector.values,
                            "content": vector.content,
                            "metadata": vector.metadata,
                            "chunk_id": vector.chunk_id,
                            "content_hash": vector.content_hash,
                            "content_type": vector.content_type,
                            "language": vector.language,
                            "chunk_index": vector.chunk_index,
                            "chunk_count": vector.chunk_count,
                            "model": vector.model,
                            "created_at": vector.created_at.isoformat(),
                            "updated_at": vector.updated_at.isoformat()
                        }
                        
                        # Remove None values
                        vector_dict = {k: v for k, v in vector_dict.items() if v is not None}
                        
                        if job.format == "json":
                            if not first_item:
                                await f.write(',\n')
                            await f.write('  ' + json.dumps(vector_dict, ensure_ascii=False))
                            first_item = False
                        else:  # JSONL
                            await f.write(json.dumps(vector_dict, ensure_ascii=False) + '\n')
                        
                        job.exported_vectors += 1
                    
                    offset += batch_size
                
                if job.format == "json":
                    await f.write('\n]')
            
            # Update job status
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.file_size = file_path.stat().st_size
            job.download_url = f"/api/v1/export/{job.job_id}/download"
            
            # Record metrics
            if self.metrics_service:
                duration = (job.completed_at - job.started_at).total_seconds()
                self.metrics_service.record_export_job(
                    dataset_id=dataset_id,
                    format=job.format,
                    status=job.status,
                    duration=duration,
                    vectors_exported=job.exported_vectors,
                    tenant_id=tenant_id
                )
            
        except Exception as e:
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            
            # Record failed job metrics
            if self.metrics_service:
                duration = (job.completed_at - job.started_at).total_seconds()
                self.metrics_service.record_export_job(
                    dataset_id=dataset_id,
                    format=job.format,
                    status="failed",
                    duration=duration,
                    vectors_exported=job.exported_vectors,
                    tenant_id=tenant_id
                )
            
            self.logger.error(f"Export job {job.job_id} failed: {e}")
    
    async def download_export(self, job_id: str) -> Tuple[Path, str]:
        """Get export file path and content type for download."""
        if job_id not in self.export_jobs:
            raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")
        
        job = self.export_jobs[job_id]
        if job.status != "completed":
            raise HTTPException(status_code=400, detail=f"Export job {job_id} is not completed")
        
        # Determine file extension and content type
        if job.format == "csv":
            file_path = self.export_path / f"{job_id}.csv"
            content_type = "text/csv"
        elif job.format == "json":
            file_path = self.export_path / f"{job_id}.json"
            content_type = "application/json"
        else:  # jsonl
            file_path = self.export_path / f"{job_id}.jsonl"
            content_type = "application/x-ndjson"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Export file not found")
        
        return file_path, content_type
    
    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old import/export jobs and files."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        # Clean up import jobs
        job_ids_to_remove = []
        for job_id, job in self.import_jobs.items():
            if job.completed_at and job.completed_at < cutoff_time:
                job_ids_to_remove.append(job_id)
        
        for job_id in job_ids_to_remove:
            del self.import_jobs[job_id]
        
        # Clean up export jobs and files
        job_ids_to_remove = []
        for job_id, job in self.export_jobs.items():
            if job.completed_at and job.completed_at < cutoff_time:
                job_ids_to_remove.append(job_id)
                
                # Remove export file
                for extension in ['csv', 'json', 'jsonl']:
                    file_path = self.export_path / f"{job_id}.{extension}"
                    if file_path.exists():
                        file_path.unlink()
        
        for job_id in job_ids_to_remove:
            del self.export_jobs[job_id]
        
        self.logger.info(f"Cleaned up {len(job_ids_to_remove)} old jobs")


# Import required for type hints
from datetime import timedelta