# Bulk Import/Export API

The Tributary AI Service for DeepLake provides comprehensive bulk import and export functionality for datasets, allowing you to efficiently transfer large amounts of vector data in various formats.

## Overview

The import/export system supports:
- **Multiple formats**: CSV, JSON, and JSONL
- **Asynchronous processing**: Large imports/exports run in the background
- **Progress tracking**: Real-time status monitoring
- **Error handling**: Detailed error reporting and partial success handling
- **Streaming**: Efficient processing of large datasets
- **Filtering**: Export subsets of data based on metadata filters

## Supported Formats

### CSV Format
```csv
id,document_id,values,content,metadata,chunk_id,content_hash,content_type,language,chunk_index,chunk_count,model,created_at,updated_at
doc1,doc1,"[0.1,0.2,0.3]","Sample text","{""category"":""test""}",chunk1,hash123,text/plain,en,0,1,text-embedding-ada-002,2024-01-01T00:00:00Z,2024-01-01T00:00:00Z
```

### JSON Format
```json
[
  {
    "id": "doc1",
    "document_id": "doc1",
    "values": [0.1, 0.2, 0.3],
    "content": "Sample text",
    "metadata": {"category": "test"},
    "chunk_id": "chunk1",
    "content_hash": "hash123",
    "content_type": "text/plain",
    "language": "en",
    "chunk_index": 0,
    "chunk_count": 1,
    "model": "text-embedding-ada-002",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### JSONL Format
```jsonl
{"id": "doc1", "document_id": "doc1", "values": [0.1, 0.2, 0.3], "content": "Sample text", "metadata": {"category": "test"}}
{"id": "doc2", "document_id": "doc2", "values": [0.4, 0.5, 0.6], "content": "Another text", "metadata": {"category": "other"}}
```

## Import API

### Start Import Job

**Endpoint**: `POST /api/v1/datasets/{dataset_id}/import`

**Parameters**:
- `file`: The file to import (multipart/form-data)
- `format`: File format (`csv`, `json`, `jsonl`) - auto-detected if not specified
- `batch_size`: Number of vectors to process in each batch (default: 100, max: 1000)

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/import" \
  -H "Authorization: ApiKey your-api-key" \
  -F "file=@vectors.csv" \
  -F "format=csv" \
  -F "batch_size=500"
```

**Response**:
```json
{
  "job_id": "12345678-1234-1234-1234-123456789012",
  "dataset_id": "my-dataset",
  "status": "running",
  "total_rows": 0,
  "processed_rows": 0,
  "successful_rows": 0,
  "failed_rows": 0,
  "errors": [],
  "started_at": "2024-01-01T00:00:00Z",
  "completed_at": null,
  "format": "csv",
  "progress_percentage": 0.0
}
```

### Check Import Status

**Endpoint**: `GET /api/v1/import/{job_id}`

**Response**:
```json
{
  "job_id": "12345678-1234-1234-1234-123456789012",
  "dataset_id": "my-dataset",
  "status": "completed",
  "total_rows": 1000,
  "processed_rows": 1000,
  "successful_rows": 995,
  "failed_rows": 5,
  "errors": [
    {
      "row": 150,
      "error": "Vector dimension mismatch: expected 768, got 512",
      "data": {"id": "bad_vector", "values": [...]}
    }
  ],
  "started_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:05:30Z",
  "format": "csv",
  "progress_percentage": 100.0
}
```

### Import Status Values

- `running`: Import is in progress
- `completed`: Import finished successfully
- `completed_with_errors`: Import finished with some errors
- `failed`: Import failed completely

## Export API

### Start Export Job

**Endpoint**: `POST /api/v1/datasets/{dataset_id}/export`

**Parameters**:
- `format`: Export format (`csv`, `json`, `jsonl`)
- `limit`: Maximum number of vectors to export (optional)
- `filters`: JSON-encoded metadata filters (optional)

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/export" \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "limit": 1000,
    "filters": "{\"category\": \"important\"}"
  }'
```

**Response**:
```json
{
  "job_id": "87654321-4321-4321-4321-210987654321",
  "dataset_id": "my-dataset",
  "status": "running",
  "total_vectors": 1000,
  "exported_vectors": 0,
  "started_at": "2024-01-01T00:00:00Z",
  "completed_at": null,
  "format": "json",
  "download_url": null,
  "file_size": null,
  "progress_percentage": 0.0
}
```

### Check Export Status

**Endpoint**: `GET /api/v1/export/{job_id}`

**Response**:
```json
{
  "job_id": "87654321-4321-4321-4321-210987654321",
  "dataset_id": "my-dataset",
  "status": "completed",
  "total_vectors": 1000,
  "exported_vectors": 1000,
  "started_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:03:45Z",
  "format": "json",
  "download_url": "/api/v1/export/87654321-4321-4321-4321-210987654321/download",
  "file_size": 15728640,
  "progress_percentage": 100.0
}
```

### Download Export File

**Endpoint**: `GET /api/v1/export/{job_id}/download`

**Response**: File download with appropriate content-type

```bash
curl -X GET "http://localhost:8000/api/v1/export/87654321-4321-4321-4321-210987654321/download" \
  -H "Authorization: ApiKey your-api-key" \
  -o exported_vectors.json
```

## Advanced Usage

### Filtering Exports

Export only vectors matching specific criteria:

```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/export" \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "jsonl",
    "filters": "{\"$and\": [{\"category\": \"documents\"}, {\"rating\": {\"$gte\": 4.0}}]}"
  }'
```

### Large Dataset Handling

For very large datasets:

1. **Use JSONL format** for streaming efficiency
2. **Set appropriate limits** to avoid memory issues
3. **Use filters** to export subsets
4. **Monitor progress** regularly

```bash
# Export in chunks
curl -X POST "http://localhost:8000/api/v1/datasets/large-dataset/export" \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "jsonl",
    "limit": 10000,
    "filters": "{\"chunk_index\": {\"$gte\": 0, \"$lt\": 10000}}"
  }'
```

### Batch Import Optimization

Optimize import performance:

```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/import" \
  -H "Authorization: ApiKey your-api-key" \
  -F "file=@large_vectors.jsonl" \
  -F "format=jsonl" \
  -F "batch_size=1000"  # Larger batches for better performance
```

## Error Handling

### Common Import Errors

1. **Dimension Mismatch**:
   ```json
   {
     "row": 42,
     "error": "Vector dimension mismatch: expected 768, got 512",
     "data": {"id": "vector_42", "values": [...]}
   }
   ```

2. **Invalid JSON**:
   ```json
   {
     "line": 15,
     "error": "Invalid JSON: Expecting ',' delimiter",
     "data": "malformed json line"
   }
   ```

3. **Missing Required Fields**:
   ```json
   {
     "row": 100,
     "error": "Missing required field: document_id",
     "data": {"id": "test", "values": [...]}
   }
   ```

### Handling Partial Failures

When imports complete with errors:

1. **Check the error details** in the job status
2. **Fix the problematic data** in your source file
3. **Re-import only the failed rows** if needed
4. **Use `skip_existing=true`** to avoid duplicates

## Monitoring and Metrics

The import/export system provides comprehensive metrics:

- **Job duration** and **throughput rates**
- **Success/failure ratios** by format and tenant
- **Error patterns** and **performance trends**
- **Resource usage** during processing

Access metrics via:
- **Prometheus endpoint**: `/api/v1/metrics/prometheus`
- **Grafana dashboards**: Pre-configured import/export dashboards
- **Service stats**: `/api/v1/stats`

## Best Practices

### Data Preparation

1. **Validate vector dimensions** before import
2. **Ensure consistent metadata schemas**
3. **Use meaningful IDs** and **document_ids**
4. **Test with small samples** first

### Performance Optimization

1. **Use appropriate batch sizes**:
   - Small files: 100-500 vectors per batch
   - Large files: 500-1000 vectors per batch

2. **Choose optimal formats**:
   - **CSV**: Simple data, good for spreadsheet tools
   - **JSON**: Complex metadata, human-readable
   - **JSONL**: Large datasets, streaming efficiency

3. **Implement retry logic** for failed imports

### Security Considerations

1. **Validate file contents** before import
2. **Set reasonable file size limits**
3. **Clean up temporary files** after processing
4. **Monitor import patterns** for abuse

### Data Integrity

1. **Backup datasets** before large imports
2. **Verify import results** with sample queries
3. **Maintain audit logs** of import/export operations
4. **Use checksums** for data validation

## Troubleshooting

### Common Issues

1. **Job Stuck in 'running' Status**:
   - Check service logs for errors
   - Verify file format and content
   - Check available disk space

2. **Import Performance Issues**:
   - Reduce batch size for memory-constrained environments
   - Check for very large vector dimensions
   - Monitor CPU and memory usage

3. **Export File Not Generated**:
   - Verify dataset has vectors to export
   - Check filter criteria aren't too restrictive
   - Ensure sufficient disk space for export files

### Debug Information

Enable debug logging:
```bash
export MONITORING_LOG_LEVEL=DEBUG
```

Check job status regularly:
```bash
# Monitor import progress
watch -n 5 'curl -s -H "Authorization: ApiKey your-key" \
  http://localhost:8000/api/v1/import/job-id | jq .progress_percentage'
```

## Administrative Operations

### Cleanup Old Jobs

Remove completed jobs and files:

```bash
curl -X POST "http://localhost:8000/api/v1/admin/cleanup-jobs" \
  -H "Authorization: ApiKey admin-key" \
  -H "Content-Type: application/json" \
  -d '{"max_age_hours": 24}'
```

### System Limits

Default system limits:
- **Maximum file size**: Limited by available disk space
- **Maximum vectors per import**: No hard limit (memory dependent)
- **Concurrent jobs**: No hard limit (CPU dependent)
- **Job retention**: 24 hours by default

## API Reference Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/datasets/{id}/import` | POST | Start import job |
| `/api/v1/import/{job_id}` | GET | Get import status |
| `/api/v1/datasets/{id}/export` | POST | Start export job |
| `/api/v1/export/{job_id}` | GET | Get export status |
| `/api/v1/export/{job_id}/download` | GET | Download export file |
| `/api/v1/admin/cleanup-jobs` | POST | Clean up old jobs (admin) |

This comprehensive import/export system provides the foundation for efficient bulk data operations while maintaining data integrity and providing excellent visibility into the process.