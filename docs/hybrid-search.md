# Hybrid Search API

The Tributary AI Service for DeepLake provides sophisticated hybrid search capabilities that combine vector similarity search with text-based search to deliver more comprehensive and accurate search results.

## Overview

Hybrid search combines the strengths of two search paradigms:
- **Vector Similarity Search**: Understands semantic meaning and context
- **Text-based Search**: Handles exact keyword matching and traditional search patterns

By intelligently combining these approaches, hybrid search provides superior results for complex queries that benefit from both semantic understanding and precise keyword matching.

## Key Features

- **Multiple Fusion Methods**: Various algorithms for combining search results
- **Configurable Weighting**: Adjust the balance between vector and text search
- **Intelligent Caching**: Optimized performance for repeated queries  
- **Metadata Filtering**: Apply filters to both search types
- **Real-time Processing**: Efficient parallel execution of search types
- **Comprehensive Metrics**: Detailed performance and relevance tracking

## Fusion Methods

### 1. Weighted Sum (Default)
Combines normalized scores using configurable weights:
```
final_score = (vector_weight × vector_score) + (text_weight × text_score)
```

### 2. Reciprocal Rank Fusion (RRF)
Uses rank positions instead of raw scores:
```
rrf_score = Σ(weight / (k + rank))
```
Where `k` is typically 60 (RRF parameter).

### 3. CombSUM
Simple addition of raw scores:
```
combsum_score = (vector_weight × vector_score) + (text_weight × text_score)
```

### 4. CombMNZ  
CombSUM multiplied by the number of non-zero scores:
```
combmnz_score = combsum_score × non_zero_count
```

### 5. Borda Count
Voting-based fusion using rank positions:
```
borda_score = Σ(weight × (total_results - rank))
```

## API Usage

### Basic Hybrid Search

**Endpoint**: `POST /api/v1/datasets/{dataset_id}/search/hybrid`

**Request**:
```json
{
  "query_text": "machine learning algorithms",
  "vector_weight": 0.6,
  "text_weight": 0.4,
  "fusion_method": "weighted_sum",
  "options": {
    "top_k": 10,
    "include_content": true,
    "include_metadata": true
  }
}
```

**Response**:
```json
{
  "results": [
    {
      "vector": {
        "id": "doc123",
        "content": "Advanced machine learning algorithms for data science",
        "metadata": {"category": "ai", "level": "advanced"}
      },
      "score": 0.8542,
      "distance": 0.1458,
      "rank": 1
    }
  ],
  "total_found": 15,
  "has_more": true,
  "query_time_ms": 45.2,
  "stats": {
    "vectors_scanned": 1000,
    "index_hits": 25,
    "filtered_results": 15
  }
}
```

### Advanced Examples

#### Semantic-Heavy Search
For queries requiring deep understanding:
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/search/hybrid" \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "natural language understanding",
    "vector_weight": 0.8,
    "text_weight": 0.2,
    "fusion_method": "weighted_sum",
    "options": {"top_k": 5}
  }'
```

#### Keyword-Heavy Search  
For precise term matching:
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/search/hybrid" \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "Python pandas dataframe",
    "vector_weight": 0.3,
    "text_weight": 0.7,
    "fusion_method": "reciprocal_rank_fusion",
    "options": {"top_k": 10}
  }'
```

#### Balanced Search with Filters
Combining semantic and keyword search with metadata filtering:
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/search/hybrid" \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "tutorial beginner guide",
    "vector_weight": 0.5,
    "text_weight": 0.5,
    "fusion_method": "comb_mnz",
    "options": {
      "top_k": 15,
      "filters": {
        "category": "education",
        "level": "beginner"
      }
    }
  }'
```

## Fusion Method Selection Guide

### When to Use Each Method

| Method | Best For | Characteristics |
|--------|----------|-----------------|
| **Weighted Sum** | General purpose, balanced results | Normalizes scores, predictable weighting |
| **RRF** | Rank-based importance | Good for combining diverse ranking signals |
| **CombSUM** | Raw score preservation | Maintains original score magnitudes |
| **CombMNZ** | Consensus emphasis | Favors documents found by multiple methods |
| **Borda Count** | Democratic voting | Position-based, reduces score variance |

### Performance Characteristics

| Method | Computation | Memory | Ranking Quality |
|--------|-------------|--------|-----------------|
| Weighted Sum | Fast | Low | High |
| RRF | Fast | Low | Very High |
| CombSUM | Fastest | Lowest | Medium |
| CombMNZ | Fast | Low | High |
| Borda Count | Medium | Medium | High |

## Optimal Weight Configuration

### Content Type Guidelines

**Technical Documentation**: 
- Vector: 0.4, Text: 0.6 (keyword precision important)

**Creative Content**:
- Vector: 0.7, Text: 0.3 (semantic understanding crucial)

**News Articles**:
- Vector: 0.5, Text: 0.5 (balanced approach)

**Code/API Documentation**:
- Vector: 0.3, Text: 0.7 (exact term matching critical)

**Academic Papers**:
- Vector: 0.6, Text: 0.4 (concept understanding important)

### Dynamic Weight Adjustment

Consider adjusting weights based on:
- **Query Length**: Longer queries → higher vector weight
- **Query Type**: Questions → higher vector weight, keywords → higher text weight
- **Domain**: Technical domains → higher text weight, conceptual domains → higher vector weight

## Performance Optimization

### Caching Strategy
Hybrid search results are cached for 5 minutes by default:
```python
# Cache key includes query text, weights, and filters
cache_key = f"{dataset_id}:{query_text}:{vector_weight}:{text_weight}:{filters}"
```

### Query Optimization Tips

1. **Batch Similar Queries**: Group related searches for better cache utilization
2. **Use Appropriate Top-K**: Don't request more results than needed
3. **Apply Filters Early**: Use metadata filters to reduce search space
4. **Choose Efficient Fusion**: RRF and Weighted Sum are fastest

### Index Management

The system automatically builds and maintains text indexes:
- **Inverted Index**: For fast keyword lookup
- **Document Cache**: For snippet generation
- **Auto-Refresh**: Indexes update when new vectors are added

## Advanced Features

### Custom Vector Input
Provide pre-computed vectors for hybrid search:
```json
{
  "query_vector": [0.1, 0.2, 0.3, ...],
  "query_text": "machine learning",
  "vector_weight": 0.7,
  "text_weight": 0.3
}
```

### Result Reranking
Enable additional reranking for improved relevance:
```json
{
  "query_text": "deep learning tutorial",
  "options": {
    "rerank": true,
    "top_k": 20
  }
}
```

### Snippet Generation
Get highlighted text snippets in results:
- Automatically generated around query terms
- Configurable snippet length
- Context-aware extraction

## Error Handling

### Common Error Scenarios

**Missing Query**:
```json
{
  "error": "Either query_text or query_vector must be provided",
  "status_code": 400
}
```

**Invalid Weights**:
```json
{
  "error": "Vector weight and text weight must sum to 1.0",
  "status_code": 422
}
```

**Invalid Fusion Method**:
```json
{
  "error": "Invalid fusion method: invalid_method",
  "status_code": 400
}
```

### Error Recovery

1. **Auto-normalization**: Weights are automatically normalized if they don't sum to 1.0
2. **Fallback to Vector Search**: If text search fails, falls back to vector-only
3. **Graceful Degradation**: Partial results returned if one search type fails

## Monitoring and Analytics

### Key Metrics

**Performance Metrics**:
- Query latency (vector vs text vs fusion)
- Cache hit ratios
- Index build times

**Quality Metrics**:
- Result diversity
- Fusion effectiveness
- User engagement patterns

**Usage Metrics**:
- Popular fusion methods
- Weight distribution patterns
- Query complexity analysis

### Prometheus Metrics

Monitor hybrid search performance:
```
# Query duration by fusion method
deeplake_search_query_duration_seconds{search_type="hybrid",fusion_method="weighted_sum"}

# Fusion method usage
deeplake_search_queries_total{search_type="hybrid",fusion_method="rrf"}

# Text index statistics
deeplake_text_index_size{dataset_id="my-dataset"}
```

## Best Practices

### Query Design

1. **Use Natural Language**: Hybrid search works best with natural queries
2. **Include Context**: Provide enough context for semantic understanding
3. **Balance Specificity**: Mix general concepts with specific terms

### Weight Tuning

1. **Start with 50/50**: Begin with equal weights and adjust based on results
2. **Test with Real Data**: Use actual user queries for weight optimization
3. **Domain-Specific Tuning**: Adjust weights based on content domain

### Performance

1. **Monitor Cache Performance**: High cache hit rates indicate good performance
2. **Optimize Text Indexes**: Regular index maintenance for large datasets
3. **Use Appropriate Timeouts**: Set reasonable timeouts for complex queries

### Result Quality

1. **Validate Fusion Methods**: Test different methods with ground truth data
2. **Monitor User Feedback**: Track user interactions with search results
3. **A/B Testing**: Compare hybrid vs. single-mode search performance

## Integration Examples

### Python Client
```python
import httpx

async def hybrid_search(dataset_id, query, vector_weight=0.5):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8000/api/v1/datasets/{dataset_id}/search/hybrid",
            json={
                "query_text": query,
                "vector_weight": vector_weight,
                "text_weight": 1.0 - vector_weight,
                "fusion_method": "weighted_sum",
                "options": {"top_k": 10}
            },
            headers={"Authorization": "ApiKey your-key"}
        )
        return response.json()
```

### JavaScript Client
```javascript
async function hybridSearch(datasetId, query, vectorWeight = 0.5) {
  const response = await fetch(
    `http://localhost:8000/api/v1/datasets/${datasetId}/search/hybrid`,
    {
      method: 'POST',
      headers: {
        'Authorization': 'ApiKey your-key',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query_text: query,
        vector_weight: vectorWeight,
        text_weight: 1.0 - vectorWeight,
        fusion_method: 'reciprocal_rank_fusion',
        options: { top_k: 10 }
      })
    }
  );
  return response.json();
}
```

## Testing

Run comprehensive hybrid search tests:
```bash
# Test all fusion methods and weight combinations
./test_hybrid_search.py
```

The test script validates:
- ✅ Basic hybrid search functionality
- ✅ All fusion method implementations  
- ✅ Weight configuration handling
- ✅ Metadata filter integration
- ✅ Performance comparison with pure vector search
- ✅ Error handling and edge cases

## Conclusion

Hybrid search represents the next evolution in search technology, combining the semantic understanding of vector search with the precision of traditional text search. By leveraging multiple fusion methods and configurable weighting, applications can deliver search experiences that are both comprehensive and highly relevant to user intent.

The Tributary AI Service for DeepLake's hybrid search implementation provides production-ready performance with comprehensive monitoring, intelligent caching, and extensive customization options to meet diverse application requirements.