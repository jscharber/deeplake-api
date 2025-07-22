# Quick Start Guide

Get up and running with the Tributary AI Service for DeepLake in just 5 minutes! This guide will walk you through the essential steps to start using the vector database service.

## 🚀 Installation

### Option 1: Docker (Recommended)

```bash
# Pull and run the latest image
docker run -d \
  --name deeplake-api \
  -p 8000:8000 \
  -e DEEPLAKE_TOKEN=your-token-here \
  -e REDIS_URL=redis://localhost:6379 \
  deeplake-api:latest
```

### Option 2: Local Development

```bash
# Clone the repository
git clone https://github.com/your-org/deeplake-api.git
cd deeplake-api

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DEEPLAKE_TOKEN=your-token-here
export REDIS_URL=redis://localhost:6379

# Start the service
python -m app.main
```

### Option 3: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  deeplake-api:
    image: deeplake-api:latest
    ports:
      - "8000:8000"
    environment:
      - DEEPLAKE_TOKEN=your-token-here
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

```bash
docker-compose up -d
```

## 🔑 Authentication

First, obtain your API key:

```bash
# Get your API key (replace with your actual process)
export API_KEY="your-api-key-here"
```

## 📊 Basic Usage

### 1. Create a Dataset

```bash
curl -X POST "http://localhost:8000/api/v1/datasets" \
  -H "Authorization: ApiKey $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-first-dataset",
    "description": "My first vector dataset",
    "embedding_dimension": 1536
  }'
```

### 2. Add Vectors

```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-first-dataset/vectors" \
  -H "Authorization: ApiKey $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [
      [0.1, 0.2, 0.3, ...],  # 1536 dimensions
      [0.4, 0.5, 0.6, ...]   # 1536 dimensions
    ],
    "metadata": [
      {"title": "Document 1", "category": "tech"},
      {"title": "Document 2", "category": "science"}
    ]
  }'
```

### 3. Search for Similar Vectors

```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-first-dataset/search" \
  -H "Authorization: ApiKey $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query_vector": [0.1, 0.2, 0.3, ...],  # 1536 dimensions
    "k": 5,
    "distance_metric": "cosine"
  }'
```

## 🐍 Python SDK Example

```python
import asyncio
from deeplake_api import DeepLakeClient

async def main():
    # Initialize client
    client = DeepLakeClient(
        base_url="http://localhost:8000",
        api_key="your-api-key-here"
    )
    
    # Create dataset
    dataset = await client.create_dataset(
        name="my-dataset",
        description="Example dataset",
        embedding_dimension=1536
    )
    
    # Add vectors
    vectors = [
        [0.1] * 1536,  # Sample vector
        [0.2] * 1536,  # Sample vector
    ]
    
    metadata = [
        {"title": "Document 1", "category": "tech"},
        {"title": "Document 2", "category": "science"}
    ]
    
    await client.add_vectors(
        dataset_id="my-dataset",
        vectors=vectors,
        metadata=metadata
    )
    
    # Search
    results = await client.search(
        dataset_id="my-dataset",
        query_vector=[0.15] * 1536,
        k=5
    )
    
    print(f"Found {len(results)} similar vectors")
    for result in results:
        print(f"Score: {result.score}, Metadata: {result.metadata}")

# Run the example
asyncio.run(main())
```

## 📝 JavaScript/TypeScript Example

```typescript
import { DeepLakeClient } from '@deeplake/api-client';

const client = new DeepLakeClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key-here'
});

async function example() {
  // Create dataset
  const dataset = await client.createDataset({
    name: 'my-dataset',
    description: 'Example dataset',
    embeddingDimension: 1536
  });

  // Add vectors
  await client.addVectors({
    datasetId: 'my-dataset',
    vectors: [
      new Array(1536).fill(0.1),
      new Array(1536).fill(0.2)
    ],
    metadata: [
      { title: 'Document 1', category: 'tech' },
      { title: 'Document 2', category: 'science' }
    ]
  });

  // Search
  const results = await client.search({
    datasetId: 'my-dataset',
    queryVector: new Array(1536).fill(0.15),
    k: 5
  });

  console.log(`Found ${results.length} similar vectors`);
  results.forEach(result => {
    console.log(`Score: ${result.score}, Metadata:`, result.metadata);
  });
}

example().catch(console.error);
```

## 🔍 Advanced Search Examples

### Hybrid Search (Vector + Text)

```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/search/hybrid" \
  -H "Authorization: ApiKey $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query_vector": [0.1, 0.2, 0.3, ...],
    "query_text": "machine learning artificial intelligence",
    "k": 10,
    "alpha": 0.7,
    "filter": {
      "category": {"$in": ["tech", "ai"]}
    }
  }'
```

### Metadata Filtering

```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/search" \
  -H "Authorization: ApiKey $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query_vector": [0.1, 0.2, 0.3, ...],
    "k": 5,
    "filter": {
      "category": "tech",
      "date": {"$gte": "2024-01-01"},
      "score": {"$gt": 0.8}
    }
  }'
```

### Text-Only Search

```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/search/text" \
  -H "Authorization: ApiKey $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence machine learning",
    "k": 10,
    "filter": {
      "category": "tech"
    }
  }'
```

## 📊 Monitoring Your Service

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "services": {
    "deeplake": "healthy",
    "redis": "healthy",
    "embedding": "healthy"
  }
}
```

### Metrics

```bash
curl http://localhost:8000/metrics
```

### API Documentation

Visit the interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🛠️ Common Operations

### List Datasets

```bash
curl -X GET "http://localhost:8000/api/v1/datasets" \
  -H "Authorization: ApiKey $API_KEY"
```

### Get Dataset Info

```bash
curl -X GET "http://localhost:8000/api/v1/datasets/my-dataset" \
  -H "Authorization: ApiKey $API_KEY"
```

### Delete Dataset

```bash
curl -X DELETE "http://localhost:8000/api/v1/datasets/my-dataset" \
  -H "Authorization: ApiKey $API_KEY"
```

### Batch Vector Operations

```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/vectors/batch" \
  -H "Authorization: ApiKey $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [
      [0.1, 0.2, ...],
      [0.3, 0.4, ...],
      ...
    ],
    "metadata": [
      {"id": "doc1", "title": "Document 1"},
      {"id": "doc2", "title": "Document 2"},
      ...
    ]
  }'
```

## 🚨 Error Handling

The API uses standard HTTP status codes:

- **200**: Success
- **201**: Created
- **400**: Bad Request
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **429**: Rate Limited
- **500**: Internal Server Error

Error responses include detailed information:

```json
{
  "error": "DATASET_NOT_FOUND",
  "message": "Dataset 'my-dataset' not found",
  "details": {
    "dataset_id": "my-dataset",
    "tenant_id": "your-tenant"
  },
  "request_id": "req-123-456"
}
```

## 🔧 Environment Variables

Key environment variables for configuration:

```bash
# DeepLake Configuration
export DEEPLAKE_TOKEN=your-token-here
export DEEPLAKE_ORG=your-org

# Service Configuration
export HOST=0.0.0.0
export PORT=8000
export WORKERS=4

# Redis Configuration
export REDIS_URL=redis://localhost:6379

# Embedding Service
export OPENAI_API_KEY=your-openai-key
export EMBEDDING_MODEL=text-embedding-ada-002

# Rate Limiting
export RATE_LIMIT_REQUESTS_PER_MINUTE=1000
export RATE_LIMIT_BURST=100

# Logging
export LOG_LEVEL=INFO
export LOG_FORMAT=structured
```

## 📈 Performance Tips

### 1. Batch Operations
Use batch endpoints for better performance:
```bash
# Instead of multiple single inserts
curl -X POST ".../vectors/batch" -d '{"vectors": [...], "metadata": [...]}'
```

### 2. Appropriate Vector Dimensions
- Use 1536 dimensions for OpenAI embeddings
- Use 768 dimensions for sentence transformers
- Higher dimensions = more storage and compute

### 3. Indexing Strategy
- HNSW for fast approximate search
- Flat for exact search on small datasets
- IVF for large datasets (millions of vectors)

### 4. Caching
- Enable Redis caching for better performance
- Cache frequently accessed metadata
- Use appropriate TTL values

## 🔄 Next Steps

1. **[Read the API Documentation](./api/http/README.md)** - Complete API reference
2. **[Set up Production Deployment](./deployment/production.md)** - Production-ready configuration
3. **[Configure Monitoring](./monitoring.md)** - Set up metrics and alerts
4. **[Implement Security](./security.md)** - Security best practices
5. **[Optimize Performance](./performance.md)** - Performance tuning guide

## 🆘 Need Help?

- **Documentation**: Browse the [full documentation](./README.md)
- **Examples**: Check out [more examples](./examples/README.md)
- **Issues**: Report bugs on [GitHub](https://github.com/your-org/deeplake-api/issues)
- **Community**: Join our [Discord](https://discord.gg/your-discord)
- **Support**: Email [support@your-company.com](mailto:support@your-company.com)

## 📝 What's Next?

Now that you have the basics working, explore these advanced features:

- **[Hybrid Search](./features/hybrid-search.md)** - Combine vector and text search
- **[Advanced Filtering](./features/metadata.md)** - Complex metadata queries
- **[Backup & Recovery](./disaster_recovery.md)** - Data protection
- **[Multi-tenancy](./features/multi-tenancy.md)** - Tenant isolation
- **[Monitoring](./monitoring.md)** - Observability and alerting

Happy vector searching! 🎉