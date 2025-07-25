# HTTP API Reference

The Tributary AI Service for DeepLake provides a comprehensive REST API for managing vector databases, performing similarity searches, and handling metadata operations.

## 🌐 Base URL

- **Production**: `https://api.yourcompany.com`
- **Staging**: `https://staging-api.yourcompany.com`
- **Local Development**: `http://localhost:8000`

## 🔐 Authentication

All API requests require authentication using API keys. Include your API key in the `Authorization` header:

```http
Authorization: ApiKey your-api-key-here
```

## 📊 API Endpoints Overview

| Category | Endpoint | Description |
|----------|----------|-------------|
| **Health** | `GET /api/v1/health` | Service health check |
| **Datasets** | `GET /api/v1/datasets` | List datasets |
| **Datasets** | `POST /api/v1/datasets` | Create dataset |
| **Datasets** | `GET /api/v1/datasets/{id}` | Get dataset details |
| **Datasets** | `DELETE /api/v1/datasets/{id}` | Delete dataset |
| **Vectors** | `POST /api/v1/datasets/{id}/vectors` | Add vectors |
| **Vectors** | `POST /api/v1/datasets/{id}/vectors/batch` | Batch add vectors |
| **Vectors** | `GET /api/v1/datasets/{id}/vectors` | List vectors |
| **Vectors** | `DELETE /api/v1/datasets/{id}/vectors/{vector_id}` | Delete vector |
| **Search** | `POST /api/v1/datasets/{id}/search` | Vector similarity search |
| **Search** | `POST /api/v1/datasets/{id}/search/text` | Text search |
| **Search** | `POST /api/v1/datasets/{id}/search/hybrid` | Hybrid search |
| **Import/Export** | `POST /api/v1/datasets/{id}/export` | Export dataset |
| **Import/Export** | `POST /api/v1/datasets/{id}/import` | Import dataset |
| **Indexes** | `POST /api/v1/datasets/{id}/index` | Create/update index |
| **Indexes** | `GET /api/v1/datasets/{id}/index` | Get index status |
| **Backup** | `POST /api/v1/backups` | Create backup |
| **Backup** | `GET /api/v1/backups` | List backups |
| **Rate Limits** | `GET /api/v1/rate-limits` | Get rate limit info |

## 🏥 Health Check

### Get Service Health

```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "services": {
    "deeplake": "healthy",
    "redis": "healthy",
    "embedding": "healthy"
  },
  "version": "1.0.0",
  "uptime": 86400
}
```

## 📁 Dataset Management

### List Datasets

```http
GET /api/v1/datasets
```

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `page_size` (int, optional): Items per page (default: 50, max: 1000)
- `search` (string, optional): Search term for dataset names

**Response:**
```json
{
  "datasets": [
    {
      "id": "my-dataset",
      "name": "My Dataset",
      "description": "A sample dataset",
      "embedding_dimension": 1536,
      "vector_count": 1000,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "metadata": {
        "category": "documents",
        "version": "1.0"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 5,
    "total_pages": 1
  }
}
```

### Create Dataset

```http
POST /api/v1/datasets
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "my-dataset",
  "description": "A sample dataset for documents",
  "embedding_dimension": 1536,
  "distance_metric": "cosine",
  "metadata": {
    "category": "documents",
    "version": "1.0"
  }
}
```

**Response:**
```json
{
  "id": "my-dataset",
  "name": "My Dataset",
  "description": "A sample dataset for documents",
  "embedding_dimension": 1536,
  "distance_metric": "cosine",
  "vector_count": 0,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "metadata": {
    "category": "documents",
    "version": "1.0"
  }
}
```

### Get Dataset Details

```http
GET /api/v1/datasets/{dataset_id}
```

**Response:**
```json
{
  "id": "my-dataset",
  "name": "My Dataset",
  "description": "A sample dataset",
  "embedding_dimension": 1536,
  "distance_metric": "cosine",
  "vector_count": 1000,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "metadata": {
    "category": "documents",
    "version": "1.0"
  },
  "statistics": {
    "size_bytes": 1048576,
    "index_type": "hnsw",
    "index_status": "built"
  }
}
```

### Delete Dataset

```http
DELETE /api/v1/datasets/{dataset_id}
```

**Response:**
```json
{
  "message": "Dataset 'my-dataset' deleted successfully"
}
```

## 🔢 Vector Operations

### Add Vectors

```http
POST /api/v1/datasets/{dataset_id}/vectors
Content-Type: application/json
```

**Request Body:**
```json
{
  "vectors": [
    [0.1, 0.2, 0.3, ...],  // 1536 dimensions
    [0.4, 0.5, 0.6, ...]   // 1536 dimensions
  ],
  "metadata": [
    {
      "id": "doc1",
      "title": "Document 1",
      "category": "tech",
      "url": "https://scharber.com/doc1"
    },
    {
      "id": "doc2",
      "title": "Document 2",
      "category": "science",
      "url": "https://scharber.com/doc2"
    }
  ]
}
```

**Response:**
```json
{
  "message": "Added 2 vectors successfully",
  "vector_ids": ["vec-001", "vec-002"],
  "dataset_id": "my-dataset",
  "total_vectors": 1002
}
```

### Batch Add Vectors

```http
POST /api/v1/datasets/{dataset_id}/vectors/batch
Content-Type: application/json
```

**Request Body:**
```json
{
  "vectors": [
    [0.1, 0.2, 0.3, ...],
    [0.4, 0.5, 0.6, ...],
    // ... up to 1000 vectors
  ],
  "metadata": [
    {"id": "doc1", "title": "Document 1"},
    {"id": "doc2", "title": "Document 2"},
    // ... corresponding metadata
  ],
  "batch_size": 100
}
```

**Response:**
```json
{
  "message": "Added 1000 vectors successfully",
  "vector_ids": ["vec-001", "vec-002", ...],
  "dataset_id": "my-dataset",
  "total_vectors": 2000,
  "processing_time": 2.5
}
```

### List Vectors

```http
GET /api/v1/datasets/{dataset_id}/vectors
```

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `page_size` (int, optional): Items per page (default: 50, max: 1000)
- `include_vectors` (bool, optional): Include vector embeddings (default: false)

**Response:**
```json
{
  "vectors": [
    {
      "id": "vec-001",
      "vector": [0.1, 0.2, 0.3, ...],  // Only if include_vectors=true
      "metadata": {
        "id": "doc1",
        "title": "Document 1",
        "category": "tech"
      },
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 1000,
    "total_pages": 20
  }
}
```

### Delete Vector

```http
DELETE /api/v1/datasets/{dataset_id}/vectors/{vector_id}
```

**Response:**
```json
{
  "message": "Vector 'vec-001' deleted successfully"
}
```

## 🔍 Search Operations

### Vector Similarity Search

```http
POST /api/v1/datasets/{dataset_id}/search
Content-Type: application/json
```

**Request Body:**
```json
{
  "query_vector": [0.1, 0.2, 0.3, ...],  // 1536 dimensions
  "k": 10,
  "distance_metric": "cosine",
  "filter": {
    "category": "tech",
    "date": {"$gte": "2024-01-01"}
  },
  "include_vectors": false,
  "include_metadata": true
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "vec-001",
      "score": 0.95,
      "distance": 0.05,
      "vector": [0.1, 0.2, 0.3, ...],  // Only if include_vectors=true
      "metadata": {
        "id": "doc1",
        "title": "Document 1",
        "category": "tech",
        "url": "https://scharber.com/doc1"
      }
    }
  ],
  "query_time": 0.025,
  "total_results": 10
}
```

### Text Search

```http
POST /api/v1/datasets/{dataset_id}/search/text
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "artificial intelligence machine learning",
  "k": 10,
  "filter": {
    "category": "tech"
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "vec-001",
      "score": 0.92,
      "metadata": {
        "id": "doc1",
        "title": "Introduction to AI",
        "category": "tech",
        "content": "This document covers artificial intelligence..."
      }
    }
  ],
  "query_time": 0.035,
  "total_results": 10
}
```

### Hybrid Search

```http
POST /api/v1/datasets/{dataset_id}/search/hybrid
Content-Type: application/json
```

**Request Body:**
```json
{
  "query_vector": [0.1, 0.2, 0.3, ...],
  "query_text": "artificial intelligence",
  "k": 10,
  "alpha": 0.7,  // Vector weight (0.0 = text only, 1.0 = vector only)
  "filter": {
    "category": {"$in": ["tech", "ai"]}
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "vec-001",
      "combined_score": 0.89,
      "vector_score": 0.92,
      "text_score": 0.85,
      "metadata": {
        "id": "doc1",
        "title": "AI in Practice",
        "category": "tech"
      }
    }
  ],
  "query_time": 0.045,
  "total_results": 10
}
```

## 📤 Import/Export

### Export Dataset

```http
POST /api/v1/datasets/{dataset_id}/export
Content-Type: application/json
```

**Request Body:**
```json
{
  "format": "json",
  "include_vectors": true,
  "include_metadata": true,
  "filter": {
    "category": "tech"
  }
}
```

**Response:**
```json
{
  "export_id": "export-123",
  "status": "processing",
  "download_url": "/api/v1/exports/export-123/download",
  "estimated_completion": "2024-01-01T12:05:00Z"
}
```

### Import Dataset

```http
POST /api/v1/datasets/{dataset_id}/import
Content-Type: multipart/form-data
```

**Request Body:**
```
file: <binary data>
format: json
batch_size: 100
```

**Response:**
```json
{
  "import_id": "import-123",
  "status": "processing",
  "progress": {
    "processed": 0,
    "total": 1000,
    "percentage": 0
  },
  "estimated_completion": "2024-01-01T12:10:00Z"
}
```

## 🔗 Vector Indexing

### Create/Update Index

```http
POST /api/v1/datasets/{dataset_id}/index
Content-Type: application/json
```

**Request Body:**
```json
{
  "index_type": "hnsw",
  "parameters": {
    "m": 16,
    "ef_construction": 200,
    "ef_search": 100
  },
  "force_rebuild": false
}
```

**Response:**
```json
{
  "index_id": "idx-001",
  "index_type": "hnsw",
  "status": "building",
  "progress": {
    "processed": 0,
    "total": 1000,
    "percentage": 0
  },
  "estimated_completion": "2024-01-01T12:15:00Z"
}
```

### Get Index Status

```http
GET /api/v1/datasets/{dataset_id}/index
```

**Response:**
```json
{
  "index_id": "idx-001",
  "index_type": "hnsw",
  "status": "built",
  "parameters": {
    "m": 16,
    "ef_construction": 200,
    "ef_search": 100
  },
  "statistics": {
    "build_time": 45.2,
    "memory_usage": 1048576,
    "search_performance": {
      "avg_latency": 0.025,
      "throughput": 1000
    }
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:15:00Z"
}
```

## 💾 Backup Operations

### Create Backup

```http
POST /api/v1/backups
Content-Type: application/json
```

**Request Body:**
```json
{
  "type": "full",
  "dataset_ids": ["my-dataset"],
  "description": "Daily backup"
}
```

**Response:**
```json
{
  "backup_id": "backup-123",
  "status": "completed",
  "message": "Backup created successfully"
}
```

### List Backups

```http
GET /api/v1/backups
```

**Query Parameters:**
- `limit` (int, optional): Maximum number of backups (default: 50)

**Response:**
```json
{
  "backups": [
    {
      "backup_id": "backup-123",
      "timestamp": "2024-01-01T12:00:00Z",
      "type": "full",
      "status": "completed",
      "size_bytes": 1048576,
      "duration_seconds": 30.5
    }
  ]
}
```

## 🚦 Rate Limiting

### Get Rate Limit Info

```http
GET /api/v1/rate-limits
```

**Response:**
```json
{
  "tenant_id": "your-tenant",
  "requests_per_minute": 1000,
  "requests_per_hour": 50000,
  "requests_per_day": 1000000,
  "burst_size": 100,
  "strategy": "sliding_window"
}
```

### Get Usage Statistics

```http
GET /api/v1/rate-limits/usage
```

**Response:**
```json
{
  "tenant_id": "your-tenant",
  "current_minute": 45,
  "current_hour": 1250,
  "current_day": 15000,
  "total_requests": 15000,
  "operations": {
    "search": 800,
    "insert": 500,
    "create_dataset": 2
  }
}
```

## 🔍 Advanced Filtering

### Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `$eq` | Equal to | `{"category": {"$eq": "tech"}}` |
| `$ne` | Not equal to | `{"category": {"$ne": "tech"}}` |
| `$in` | In array | `{"category": {"$in": ["tech", "ai"]}}` |
| `$nin` | Not in array | `{"category": {"$nin": ["spam"]}}` |
| `$gt` | Greater than | `{"score": {"$gt": 0.8}}` |
| `$gte` | Greater than or equal | `{"date": {"$gte": "2024-01-01"}}` |
| `$lt` | Less than | `{"score": {"$lt": 0.5}}` |
| `$lte` | Less than or equal | `{"date": {"$lte": "2024-12-31"}}` |
| `$exists` | Field exists | `{"url": {"$exists": true}}` |
| `$regex` | Regular expression | `{"title": {"$regex": "^AI.*"}}` |
| `$and` | Logical AND | `{"$and": [{"category": "tech"}, {"score": {"$gt": 0.8}}]}` |
| `$or` | Logical OR | `{"$or": [{"category": "tech"}, {"category": "ai"}]}` |

### Complex Filter Examples

```json
{
  "filter": {
    "$and": [
      {"category": {"$in": ["tech", "ai"]}},
      {"score": {"$gte": 0.8}},
      {"$or": [
        {"date": {"$gte": "2024-01-01"}},
        {"priority": "high"}
      ]}
    ]
  }
}
```

## 📊 Response Format

### Success Response

```json
{
  "success": true,
  "data": {
    // Response data
  },
  "message": "Operation completed successfully",
  "request_id": "req-123-456"
}
```

### Error Response

```json
{
  "success": false,
  "error": "DATASET_NOT_FOUND",
  "message": "Dataset 'my-dataset' not found",
  "details": {
    "dataset_id": "my-dataset",
    "tenant_id": "your-tenant"
  },
  "request_id": "req-123-456"
}
```

## 🚨 HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Invalid request parameters |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 409 | Conflict - Resource already exists |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - Service temporarily unavailable |

## 📄 OpenAPI Specification

The complete OpenAPI specification is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## 🔗 Related Documentation

- [Authentication Guide](../authentication.md)
- [Python SDK](../sdk/python.md)
- [Examples & Tutorials](../examples/README.md)
- [Error Handling](../troubleshooting.md)
- [Rate Limiting](../features/rate-limiting.md)

## 📞 Support

For API support and questions:
- **Documentation**: [Full API Documentation](./README.md)
- **GitHub Issues**: [Report Issues](https://github.com/your-org/deeplake-api/issues)
- **Community**: [Join Discord](https://discord.gg/your-discord)
- **Enterprise**: [support@yourcompany.com](mailto:support@yourcompany.com)