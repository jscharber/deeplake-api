# Vector Indexing Guide

The Tributary AI Service for DeepLake supports multiple vector indexing algorithms to optimize search performance for different use cases and dataset sizes.

## Overview

Vector indexing dramatically improves search performance by creating specialized data structures that enable approximate nearest neighbor (ANN) search instead of brute-force comparison against every vector.

## Supported Index Types

### 1. Default
Let DeepLake automatically choose the best index type based on dataset characteristics.

### 2. Flat (Brute-Force)
- **Description**: No index, performs exact brute-force search
- **When to use**: Small datasets (<1,000 vectors) or when 100% recall is required
- **Pros**: 100% accurate, no index build time
- **Cons**: Slow for large datasets (O(n) complexity)

### 3. HNSW (Hierarchical Navigable Small World)
- **Description**: Graph-based index providing excellent speed/accuracy trade-off
- **When to use**: Medium to large datasets (>1,000 vectors)
- **Pros**: Fast search, high recall, good for high-dimensional data
- **Cons**: Higher memory usage, index build time

### 4. IVF (Inverted File Index)
- **Description**: Clustering-based index that partitions vectors into cells
- **When to use**: Very large datasets (>100,000 vectors)
- **Pros**: Memory efficient, fast for very large datasets
- **Cons**: Requires training, lower recall than HNSW

## Creating Datasets with Indexing

### Specify Index Type at Creation

```bash
curl -X POST http://localhost:8000/api/v1/datasets/ \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "indexed-dataset",
    "dimensions": 128,
    "metric_type": "cosine",
    "index_type": "hnsw",
    "description": "Dataset with HNSW indexing"
  }'
```

### Available Index Types
- `default` - Let DeepLake decide
- `flat` - No index (brute-force)
- `hnsw` - HNSW graph index
- `ivf` - IVF clustering index

## HNSW Indexing

HNSW creates a multi-layer graph structure for efficient approximate nearest neighbor search.

### Key Parameters

- **M** (default: 16): Number of bi-directional links per node
  - Higher M = better recall but more memory
  - Recommended: 12-48

- **ef_construction** (default: 200): Size of dynamic candidate list during construction
  - Higher = better index quality but slower build
  - Recommended: 100-500

- **ef_search** (default: 50): Size of dynamic candidate list during search
  - Higher = better recall but slower search
  - Can be tuned per query

### Creating HNSW Index

```bash
curl -X POST http://localhost:8000/api/v1/datasets/my-dataset/index \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "index_type": "hnsw",
    "hnsw_m": 32,
    "hnsw_ef_construction": 400,
    "hnsw_ef_search": 100,
    "force_rebuild": false
  }'
```

### Search with HNSW Parameters

```bash
curl -X POST http://localhost:8000/api/v1/datasets/my-dataset/search \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query_vector": [0.1, 0.2, ...],
    "options": {
      "top_k": 10,
      "ef_search": 150
    }
  }'
```

## IVF Indexing

IVF partitions vectors into clusters for efficient search in very large datasets.

### Key Parameters

- **nlist** (default: 100): Number of clusters
  - More clusters = better search quality but slower
  - Recommended: sqrt(n) where n is number of vectors

- **nprobe** (default: 10): Number of clusters to search
  - Higher = better recall but slower
  - Can be tuned per query

### Creating IVF Index

```bash
curl -X POST http://localhost:8000/api/v1/datasets/my-dataset/index \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "index_type": "ivf",
    "ivf_nlist": 256,
    "ivf_nprobe": 20,
    "force_rebuild": false
  }'
```

### Search with IVF Parameters

```bash
curl -X POST http://localhost:8000/api/v1/datasets/my-dataset/search \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query_vector": [0.1, 0.2, ...],
    "options": {
      "top_k": 10,
      "nprobe": 30
    }
  }'
```

## Index Management

### Get Index Statistics

```bash
curl http://localhost:8000/api/v1/datasets/my-dataset/index \
  -H "Authorization: ApiKey your-api-key"
```

Response:
```json
{
  "index_type": "hnsw",
  "total_vectors": 100000,
  "index_size_bytes": 52428800,
  "build_time_seconds": 45.2,
  "last_updated": "2024-01-15 10:30:00",
  "parameters": {
    "m": 32,
    "ef_construction": 400,
    "ef": 100
  },
  "is_trained": true
}
```

### Rebuild Index

Force rebuild with new parameters:

```bash
curl -X POST http://localhost:8000/api/v1/datasets/my-dataset/index \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "index_type": "hnsw",
    "force_rebuild": true,
    "hnsw_m": 48,
    "hnsw_ef_construction": 500
  }'
```

### Delete Index

Revert to flat (brute-force) search:

```bash
curl -X DELETE http://localhost:8000/api/v1/datasets/my-dataset/index \
  -H "Authorization: ApiKey your-api-key"
```

## Performance Optimization

### Choosing the Right Index

| Dataset Size | Recommended Index | Rationale |
|-------------|------------------|-----------|
| < 1K vectors | Flat | Index overhead not worth it |
| 1K - 10K | HNSW (M=16) | Good balance of speed/accuracy |
| 10K - 100K | HNSW (M=32) | Scales well with size |
| 100K - 1M | IVF or HNSW | Depends on memory constraints |
| > 1M | IVF | Memory efficient for large scale |

### HNSW Tuning Guide

**For Speed** (lower quality):
- M = 12-16
- ef_construction = 100-200
- ef_search = 10-50

**For Quality** (slower):
- M = 32-48
- ef_construction = 400-500
- ef_search = 100-200

**Balanced**:
- M = 16-24
- ef_construction = 200-300
- ef_search = 50-100

### IVF Tuning Guide

**Number of Clusters**:
- nlist = sqrt(n) is a good starting point
- For 1M vectors: nlist = 1000
- For 10M vectors: nlist = 3000-5000

**Search Quality**:
- nprobe = 1: Very fast but low recall
- nprobe = 10: Good balance
- nprobe = 50: High quality but slower
- nprobe = nlist: Exact search (defeats purpose)

## Automatic Index Building

Indexes are automatically built/updated when:

1. **Vector count threshold**: Dataset reaches 1,000 vectors
2. **Batch insertions**: After inserting large batches
3. **Manual trigger**: Via the index API

The system will:
- Skip index building for datasets with `index_type: "flat"`
- Use default parameters unless specified
- Log index build progress and statistics

## Monitoring Index Performance

### Prometheus Metrics

Monitor index performance with these metrics:

```
# Index operations
deeplake_index_operations_total{dataset_id="...", operation="create"}

# Build duration
deeplake_index_build_duration_seconds{dataset_id="...", index_type="hnsw"}

# Index size
deeplake_index_size_bytes{dataset_id="...", index_type="hnsw"}
```

### Grafana Dashboard

The indexing dashboard shows:
- Index build times by dataset
- Search performance comparison (indexed vs flat)
- Memory usage by index type
- Parameter effectiveness (recall vs speed)

## Best Practices

1. **Start Simple**: Begin with default indexing and optimize based on actual performance

2. **Test Parameters**: Use a representative sample to test different parameters:
   ```python
   # Test different ef_search values
   for ef in [10, 50, 100, 200]:
       measure_search_performance(ef_search=ef)
   ```

3. **Monitor Recall**: Periodically check search quality:
   - Compare indexed results with exact (flat) search
   - Aim for >95% recall for most applications

4. **Index Maintenance**:
   - Rebuild indexes periodically as data distribution changes
   - Monitor index size growth
   - Consider re-tuning parameters as dataset grows

5. **Memory Management**:
   - HNSW uses ~(M * 2 * sizeof(int) * N) bytes
   - IVF uses less memory but requires training vectors
   - Plan capacity accordingly

## Python Client Example

```python
import httpx
import asyncio

async def create_indexed_dataset():
    async with httpx.AsyncClient() as client:
        # Create dataset with HNSW
        response = await client.post(
            "http://localhost:8000/api/v1/datasets/",
            json={
                "name": "my-indexed-dataset",
                "dimensions": 768,
                "metric_type": "cosine",
                "index_type": "hnsw"
            },
            headers={"Authorization": "ApiKey your-key"}
        )
        
        dataset = response.json()
        dataset_id = dataset["id"]
        
        # Insert vectors (index builds automatically after 1000)
        # ... insert vectors ...
        
        # Optimize index for better recall
        response = await client.post(
            f"http://localhost:8000/api/v1/datasets/{dataset_id}/index",
            json={
                "index_type": "hnsw",
                "force_rebuild": True,
                "hnsw_m": 48,
                "hnsw_ef_construction": 500
            },
            headers={"Authorization": "ApiKey your-key"}
        )
        
        # Search with custom parameters
        response = await client.post(
            f"http://localhost:8000/api/v1/datasets/{dataset_id}/search",
            json={
                "query_vector": query_embedding,
                "options": {
                    "top_k": 20,
                    "ef_search": 200  # Higher for better quality
                }
            },
            headers={"Authorization": "ApiKey your-key"}
        )
```

## Troubleshooting

### Index Not Building
- Check vector count (needs >1000 for auto-build)
- Verify index_type is not "flat"
- Check logs for build errors

### Poor Search Quality
- Increase ef_search (HNSW) or nprobe (IVF)
- Rebuild index with higher quality parameters
- Verify correct distance metric

### High Memory Usage
- Reduce M parameter for HNSW
- Use IVF for very large datasets
- Monitor with Prometheus metrics

### Slow Index Build
- Normal for large datasets
- Use background jobs for rebuilds
- Consider IVF for faster builds

## Conclusion

Vector indexing is essential for production deployments with large datasets. Start with HNSW for most use cases, and consider IVF for very large scale. Always monitor performance and tune parameters based on your specific requirements for speed, accuracy, and resource usage.