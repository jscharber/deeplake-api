# Error Codes Reference

This document provides a comprehensive reference for all error codes used in the Tributary AI Service for DeepLake, including their meanings, causes, and recommended solutions.

## 📋 Error Code Format

Error codes follow the format: `{CATEGORY}_{SPECIFIC_ERROR}`

- **Category**: Broad category of the error (e.g., DATASET, VECTOR, AUTH)
- **Specific Error**: Specific error within the category

Example: `DATASET_NOT_FOUND`, `VECTOR_DIMENSION_MISMATCH`

## 🔍 Error Response Format

All API errors return a consistent JSON structure:

```json
{
  "success": false,
  "error_code": "DATASET_NOT_FOUND",
  "message": "Dataset 'my-dataset' not found for tenant 'my-tenant'",
  "details": {
    "dataset_id": "my-dataset",
    "tenant_id": "my-tenant",
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "request_id": "req-123-456-789",
  "support_url": "https://docs.example.com/errors/DATASET_NOT_FOUND"
}
```

## 🗂️ Error Categories

### Authentication Errors (AUTH_*)

#### AUTH_MISSING_CREDENTIALS
- **HTTP Status**: 401
- **Description**: No authentication credentials provided
- **Cause**: Missing Authorization header or API key
- **Solution**: Include valid API key in Authorization header

```bash
# Correct usage
curl -H "Authorization: ApiKey your-api-key" \
     http://localhost:8000/api/v1/datasets
```

#### AUTH_INVALID_CREDENTIALS
- **HTTP Status**: 401
- **Description**: Invalid or expired authentication credentials
- **Cause**: Incorrect API key format or expired token
- **Solution**: Verify API key format and expiration

#### AUTH_INSUFFICIENT_PERMISSIONS
- **HTTP Status**: 403
- **Description**: Insufficient permissions for the requested operation
- **Cause**: API key lacks required permissions
- **Solution**: Contact administrator to grant necessary permissions

#### AUTH_TENANT_NOT_FOUND
- **HTTP Status**: 404
- **Description**: Tenant not found for the provided credentials
- **Cause**: Invalid tenant ID or tenant doesn't exist
- **Solution**: Verify tenant ID and ensure tenant exists

### Dataset Errors (DATASET_*)

#### DATASET_NOT_FOUND
- **HTTP Status**: 404
- **Description**: Dataset not found
- **Cause**: Dataset doesn't exist or access denied
- **Solution**: Verify dataset ID and permissions

```json
{
  "error_code": "DATASET_NOT_FOUND",
  "message": "Dataset 'my-dataset' not found",
  "details": {
    "dataset_id": "my-dataset",
    "tenant_id": "my-tenant",
    "available_datasets": ["dataset1", "dataset2"]
  }
}
```

#### DATASET_ALREADY_EXISTS
- **HTTP Status**: 409
- **Description**: Dataset with the same name already exists
- **Cause**: Attempting to create dataset with existing name
- **Solution**: Use different name or update existing dataset

#### DATASET_INVALID_NAME
- **HTTP Status**: 400
- **Description**: Invalid dataset name format
- **Cause**: Dataset name contains invalid characters or format
- **Solution**: Use valid naming convention (alphanumeric, hyphens, underscores)

```python
# Valid dataset names
valid_names = [
    "my-dataset",
    "my_dataset",
    "dataset123",
    "user-docs-v1"
]

# Invalid dataset names
invalid_names = [
    "my dataset",    # spaces not allowed
    "my@dataset",    # special characters
    "",              # empty name
    "a" * 256        # too long
]
```

#### DATASET_INVALID_DIMENSION
- **HTTP Status**: 400
- **Description**: Invalid embedding dimension
- **Cause**: Dimension is not a positive integer or exceeds limits
- **Solution**: Use valid dimension (1-4096)

#### DATASET_CREATION_FAILED
- **HTTP Status**: 500
- **Description**: Failed to create dataset
- **Cause**: Internal error during dataset creation
- **Solution**: Retry operation or contact support

### Vector Errors (VECTOR_*)

#### VECTOR_NOT_FOUND
- **HTTP Status**: 404
- **Description**: Vector not found
- **Cause**: Vector ID doesn't exist in dataset
- **Solution**: Verify vector ID exists in dataset

#### VECTOR_DIMENSION_MISMATCH
- **HTTP Status**: 400
- **Description**: Vector dimension doesn't match dataset dimension
- **Cause**: Vector has wrong number of dimensions
- **Solution**: Ensure vector matches dataset dimension

```json
{
  "error_code": "VECTOR_DIMENSION_MISMATCH",
  "message": "Vector dimension mismatch: expected 1536, got 768",
  "details": {
    "expected_dimension": 1536,
    "actual_dimension": 768,
    "vector_index": 0
  }
}
```

#### VECTOR_INVALID_FORMAT
- **HTTP Status**: 400
- **Description**: Invalid vector format
- **Cause**: Vector contains non-numeric values or invalid structure
- **Solution**: Ensure vector is list of numbers

```python
# Valid vector formats
valid_vectors = [
    [0.1, 0.2, 0.3],           # List of floats
    [1, 2, 3],                 # List of integers
    np.array([0.1, 0.2, 0.3])  # NumPy array
]

# Invalid vector formats
invalid_vectors = [
    ["a", "b", "c"],           # Strings
    [0.1, None, 0.3],          # None values
    [0.1, float('inf'), 0.3],  # Infinity
    [0.1, float('nan'), 0.3]   # NaN
]
```

#### VECTOR_BATCH_TOO_LARGE
- **HTTP Status**: 413
- **Description**: Batch size exceeds maximum limit
- **Cause**: Too many vectors in single request
- **Solution**: Split into smaller batches (max 1000 vectors)

#### VECTOR_INSERTION_FAILED
- **HTTP Status**: 500
- **Description**: Failed to insert vectors
- **Cause**: Internal error during vector insertion
- **Solution**: Retry operation or contact support

### Search Errors (SEARCH_*)

#### SEARCH_QUERY_INVALID
- **HTTP Status**: 400
- **Description**: Invalid search query parameters
- **Cause**: Invalid query vector, k value, or other parameters
- **Solution**: Verify query parameters are valid

```json
{
  "error_code": "SEARCH_QUERY_INVALID",
  "message": "Invalid search parameters",
  "details": {
    "errors": [
      {
        "field": "k",
        "message": "k must be between 1 and 1000",
        "value": 2000
      },
      {
        "field": "query_vector",
        "message": "query_vector must have 1536 dimensions",
        "value": 768
      }
    ]
  }
}
```

#### SEARCH_FILTER_INVALID
- **HTTP Status**: 400
- **Description**: Invalid metadata filter
- **Cause**: Malformed filter expression
- **Solution**: Use valid filter syntax

```python
# Valid filters
valid_filters = [
    {"category": "tech"},
    {"score": {"$gte": 0.8}},
    {"category": {"$in": ["tech", "ai"]}},
    {"$and": [{"category": "tech"}, {"score": {"$gt": 0.5}}]}
]

# Invalid filters
invalid_filters = [
    {"category": {"$unknown": "tech"}},  # Unknown operator
    {"score": {"$gte": "invalid"}},      # Invalid type
    {"$and": "invalid"}                  # Invalid structure
]
```

#### SEARCH_TIMEOUT
- **HTTP Status**: 408
- **Description**: Search operation timed out
- **Cause**: Query took too long to execute
- **Solution**: Reduce search scope or increase timeout

#### SEARCH_INDEX_NOT_READY
- **HTTP Status**: 503
- **Description**: Search index is not ready
- **Cause**: Index is still building or corrupted
- **Solution**: Wait for index to complete or rebuild

### Rate Limiting Errors (RATE_LIMIT_*)

#### RATE_LIMIT_EXCEEDED
- **HTTP Status**: 429
- **Description**: Rate limit exceeded
- **Cause**: Too many requests in time window
- **Solution**: Wait before retrying or upgrade plan

```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded: 1000 requests per minute",
  "details": {
    "limit": 1000,
    "window": "1 minute",
    "retry_after": 60,
    "reset_at": "2024-01-01T12:01:00Z"
  }
}
```

#### RATE_LIMIT_QUOTA_EXCEEDED
- **HTTP Status**: 429
- **Description**: Monthly quota exceeded
- **Cause**: Exceeded monthly request/storage quota
- **Solution**: Upgrade plan or wait for quota reset

### Import/Export Errors (IMPORT_*, EXPORT_*)

#### IMPORT_FILE_INVALID
- **HTTP Status**: 400
- **Description**: Invalid import file format
- **Cause**: Unsupported file format or corrupted file
- **Solution**: Use supported formats (JSON, CSV, Parquet)

#### IMPORT_DATA_INVALID
- **HTTP Status**: 400
- **Description**: Invalid data in import file
- **Cause**: Data doesn't match expected schema
- **Solution**: Verify data format and schema

#### EXPORT_DATASET_EMPTY
- **HTTP Status**: 400
- **Description**: Cannot export empty dataset
- **Cause**: Dataset has no vectors to export
- **Solution**: Add vectors before exporting

#### EXPORT_FORMAT_UNSUPPORTED
- **HTTP Status**: 400
- **Description**: Unsupported export format
- **Cause**: Requested format not supported
- **Solution**: Use supported formats (JSON, CSV, Parquet)

### Backup Errors (BACKUP_*)

#### BACKUP_NOT_FOUND
- **HTTP Status**: 404
- **Description**: Backup not found
- **Cause**: Backup ID doesn't exist or access denied
- **Solution**: Verify backup ID and permissions

#### BACKUP_CREATION_FAILED
- **HTTP Status**: 500
- **Description**: Failed to create backup
- **Cause**: Storage error or insufficient permissions
- **Solution**: Check storage configuration and permissions

#### BACKUP_RESTORE_FAILED
- **HTTP Status**: 500
- **Description**: Failed to restore from backup
- **Cause**: Corrupted backup or restore error
- **Solution**: Verify backup integrity and retry

### Storage Errors (STORAGE_*)

#### STORAGE_UNAVAILABLE
- **HTTP Status**: 503
- **Description**: Storage service unavailable
- **Cause**: DeepLake service is down or unreachable
- **Solution**: Check service status and retry

#### STORAGE_QUOTA_EXCEEDED
- **HTTP Status**: 413
- **Description**: Storage quota exceeded
- **Cause**: Dataset size exceeds storage limits
- **Solution**: Upgrade storage plan or delete unused data

#### STORAGE_PERMISSION_DENIED
- **HTTP Status**: 403
- **Description**: Storage permission denied
- **Cause**: Insufficient permissions for storage operation
- **Solution**: Check storage credentials and permissions

### Validation Errors (VALIDATION_*)

#### VALIDATION_SCHEMA_MISMATCH
- **HTTP Status**: 400
- **Description**: Data doesn't match schema
- **Cause**: Invalid data structure or types
- **Solution**: Ensure data matches expected schema

#### VALIDATION_REQUIRED_FIELD_MISSING
- **HTTP Status**: 400
- **Description**: Required field missing
- **Cause**: Missing required field in request
- **Solution**: Include all required fields

#### VALIDATION_FIELD_TYPE_INVALID
- **HTTP Status**: 400
- **Description**: Invalid field type
- **Cause**: Field has wrong data type
- **Solution**: Use correct data type for field

### Service Errors (SERVICE_*)

#### SERVICE_UNAVAILABLE
- **HTTP Status**: 503
- **Description**: Service temporarily unavailable
- **Cause**: Service is down for maintenance or overloaded
- **Solution**: Wait and retry or check service status

#### SERVICE_TIMEOUT
- **HTTP Status**: 504
- **Description**: Service timeout
- **Cause**: Operation took too long to complete
- **Solution**: Retry with smaller request or increase timeout

#### SERVICE_INTERNAL_ERROR
- **HTTP Status**: 500
- **Description**: Internal service error
- **Cause**: Unexpected error in service
- **Solution**: Contact support with request ID

## 🔧 Error Handling Best Practices

### Client-Side Error Handling

```python
import asyncio
from deeplake_api import DeepLakeClient, DeepLakeError

async def handle_api_errors():
    client = DeepLakeClient(api_key="your-api-key")
    
    try:
        await client.create_dataset(
            name="test-dataset",
            embedding_dimension=1536
        )
    except DeepLakeError as e:
        if e.error_code == "DATASET_ALREADY_EXISTS":
            print("Dataset already exists, continuing...")
        elif e.error_code == "AUTH_INSUFFICIENT_PERMISSIONS":
            print("Insufficient permissions, contact admin")
            return
        elif e.error_code == "RATE_LIMIT_EXCEEDED":
            print(f"Rate limited, waiting {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
            # Retry the operation
        else:
            print(f"Unexpected error: {e.error_code} - {e.message}")
            raise
```

### Retry Strategies

```python
import asyncio
import random
from typing import Type, Callable

class RetryableError(Exception):
    """Base class for retryable errors"""
    pass

class RateLimitError(RetryableError):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after

async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
):
    """Retry function with exponential backoff"""
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except RateLimitError as e:
            if attempt == max_retries:
                raise
            await asyncio.sleep(e.retry_after)
        except RetryableError:
            if attempt == max_retries:
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
            
            # Add jitter to prevent thundering herd
            if jitter:
                delay *= (0.5 + random.random() * 0.5)
            
            await asyncio.sleep(delay)
```

### Circuit Breaker Pattern

```python
import time
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

## 📊 Error Monitoring

### Error Tracking

```python
import logging
from typing import Dict, Any

class ErrorTracker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_counts = {}
    
    def track_error(self, error_code: str, details: Dict[str, Any] = None):
        """Track error occurrence"""
        self.error_counts[error_code] = self.error_counts.get(error_code, 0) + 1
        
        self.logger.error(
            "API Error occurred",
            extra={
                "error_code": error_code,
                "error_count": self.error_counts[error_code],
                "details": details or {}
            }
        )
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics"""
        return self.error_counts.copy()
```

### Error Dashboards

Common error metrics to monitor:

- **Error Rate**: Percentage of requests resulting in errors
- **Error Distribution**: Breakdown of errors by type
- **Error Trends**: Error patterns over time
- **Recovery Time**: Time to recover from errors

## 📞 Support

### When to Contact Support

**Immediate Support Required:**
- SERVICE_INTERNAL_ERROR
- STORAGE_UNAVAILABLE
- Data corruption issues
- Security incidents

**Self-Service First:**
- DATASET_NOT_FOUND
- VECTOR_DIMENSION_MISMATCH
- VALIDATION_* errors
- RATE_LIMIT_EXCEEDED

### Support Information

- **Error Documentation**: Each error code links to detailed documentation
- **Support Portal**: [support.example.com](https://support.example.com)
- **GitHub Issues**: [github.com/your-org/deeplake-api/issues](https://github.com/your-org/deeplake-api/issues)
- **Community Forum**: [community.example.com](https://community.example.com)
- **Emergency Support**: [emergency@example.com](mailto:emergency@example.com)

## 🔗 Related Documentation

- [API Reference](../api/http/README.md)
- [Troubleshooting Guide](../troubleshooting.md)
- [Authentication Guide](../authentication.md)
- [Rate Limiting](../features/rate-limiting.md)
- [Monitoring Guide](../monitoring.md)

## 📋 Error Code Index

### Quick Reference Table

| Error Code | HTTP Status | Category | Description |
|------------|-------------|----------|-------------|
| AUTH_MISSING_CREDENTIALS | 401 | Auth | Missing authentication |
| AUTH_INVALID_CREDENTIALS | 401 | Auth | Invalid credentials |
| AUTH_INSUFFICIENT_PERMISSIONS | 403 | Auth | Insufficient permissions |
| DATASET_NOT_FOUND | 404 | Dataset | Dataset not found |
| DATASET_ALREADY_EXISTS | 409 | Dataset | Dataset already exists |
| VECTOR_DIMENSION_MISMATCH | 400 | Vector | Vector dimension mismatch |
| VECTOR_BATCH_TOO_LARGE | 413 | Vector | Batch size too large |
| SEARCH_QUERY_INVALID | 400 | Search | Invalid search query |
| SEARCH_FILTER_INVALID | 400 | Search | Invalid filter |
| RATE_LIMIT_EXCEEDED | 429 | Rate Limit | Rate limit exceeded |
| STORAGE_UNAVAILABLE | 503 | Storage | Storage unavailable |
| SERVICE_INTERNAL_ERROR | 500 | Service | Internal service error |

For the complete list of error codes, see the [Error Codes API](../api/http/errors.md).