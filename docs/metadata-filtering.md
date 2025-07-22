# Advanced Metadata Filtering

The Tributary AI Service for DeepLake supports sophisticated metadata filtering capabilities that allow you to filter search results based on complex criteria. This document describes the available filtering options and provides examples.

## Overview

Metadata filtering allows you to:
- Filter search results based on vector metadata
- Use complex boolean expressions (AND, OR, NOT)
- Apply comparison operators (=, !=, <, >, <=, >=, IN, LIKE)
- Support multiple data types (string, numeric, boolean, date, array)
- Use nested metadata filtering with dot notation
- Write filters in multiple formats (JSON, MongoDB-style, SQL-like)

## Filter Formats

### 1. Simple Dictionary Format

The simplest format uses key-value pairs for exact matching:

```json
{
  "category": "programming",
  "level": "beginner",
  "published": true
}
```

This is equivalent to: `category = 'programming' AND level = 'beginner' AND published = true`

### 2. MongoDB-Style Format

Use MongoDB-style operators for complex queries:

```json
{
  "$and": [
    {"category": "programming"},
    {"$or": [
      {"level": "beginner"},
      {"level": "intermediate"}
    ]},
    {"rating": {"$gt": 4.0}}
  ]
}
```

### 3. SQL-Like String Format

Write filters using SQL-like syntax:

```sql
category = 'programming' AND (level = 'beginner' OR level = 'intermediate') AND rating > 4.0
```

## Supported Operators

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equal | `{"category": "tech"}` |
| `!=` | Not equal | `{"category": {"$ne": "tech"}}` |
| `<` | Less than | `{"rating": {"$lt": 4.0}}` |
| `<=` | Less than or equal | `{"rating": {"$lte": 4.0}}` |
| `>` | Greater than | `{"rating": {"$gt": 4.0}}` |
| `>=` | Greater than or equal | `{"rating": {"$gte": 4.0}}` |

### List Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `IN` | Value in list | `{"language": {"$in": ["python", "javascript"]}}` |
| `NOT_IN` | Value not in list | `{"language": {"$nin": ["java", "c++"]}}` |

### Pattern Matching

| Operator | Description | Example |
|----------|-------------|---------|
| `LIKE` | Pattern matching with wildcards | `{"title": {"$like": "Python%"}}` |
| `NOT_LIKE` | Negated pattern matching | `{"title": {"$not_like": "%deprecated%"}}` |

### Existence Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `EXISTS` | Field exists | `{"author": {"$exists": true}}` |
| `NOT_EXISTS` | Field doesn't exist | `{"deprecated": {"$exists": false}}` |
| `IS_NULL` | Field is null | `{"description": {"$null": true}}` |
| `IS_NOT_NULL` | Field is not null | `{"description": {"$null": false}}` |

### Boolean Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `AND` | All conditions must be true | `{"$and": [{"a": 1}, {"b": 2}]}` |
| `OR` | Any condition can be true | `{"$or": [{"a": 1}, {"b": 2}]}` |
| `NOT` | Negates the condition | `{"$not": {"category": "spam"}}` |

## Data Types

The filtering system automatically detects and handles different data types:

### String Values
```json
{"author": "John Doe"}
{"title": {"$like": "Python%"}}
```

### Numeric Values
```json
{"rating": 4.5}
{"price": {"$lt": 100}}
{"views": {"$gte": 1000}}
```

### Boolean Values
```json
{"published": true}
{"featured": false}
```

### Date Values
```json
{"created_at": {"$gt": "2023-01-01"}}
{"updated_at": {"$lt": "2023-12-31T23:59:59"}}
```

### Array Values
```json
{"tags": {"$in": ["python", "tutorial"]}}
{"categories": {"$nin": ["spam", "test"]}}
```

## Nested Metadata

Use dot notation to access nested metadata fields:

```json
{
  "metadata": {
    "content": {
      "type": "article",
      "quality": {
        "score": 8.5,
        "reviewed": true
      }
    },
    "author": {
      "name": "Jane Smith",
      "verified": true
    }
  }
}
```

Filter with:
```json
{
  "content.type": "article",
  "content.quality.score": {"$gt": 8.0},
  "author.verified": true
}
```

## Usage Examples

### Basic Search with Metadata Filter

```python
import httpx

# Simple equality filter
search_data = {
    "query_text": "machine learning",
    "options": {
        "top_k": 10,
        "include_metadata": True,
        "filters": {
            "category": "data-science",
            "level": "intermediate"
        }
    }
}

response = await client.post(
    f"{BASE_URL}/api/v1/datasets/{dataset_id}/search/text",
    json=search_data,
    headers=headers
)
```

### Complex Boolean Logic

```python
# MongoDB-style complex filter
search_data = {
    "query_text": "python",
    "options": {
        "top_k": 5,
        "filters": {
            "$and": [
                {"published": True},
                {"$or": [
                    {"category": "programming"},
                    {"category": "data-science"}
                ]},
                {"rating": {"$gte": 4.0}},
                {"language": {"$in": ["python", "jupyter"]}}
            ]
        }
    }
}
```

### SQL-Like String Filter

```python
# SQL-like string filter
search_data = {
    "query_text": "tutorial",
    "options": {
        "top_k": 10,
        "filters": "category = 'programming' AND level IN ('beginner', 'intermediate') AND rating > 4.0"
    }
}
```

### Date Range Filtering

```python
# Date range filter
search_data = {
    "query_text": "recent updates",
    "options": {
        "top_k": 20,
        "filters": {
            "updated_at": {"$gte": "2023-01-01"},
            "created_at": {"$lte": "2023-12-31"}
        }
    }
}
```

### Pattern Matching

```python
# Pattern matching with LIKE
search_data = {
    "query_text": "documentation",
    "options": {
        "top_k": 15,
        "filters": {
            "title": {"$like": "Python%"},
            "author": {"$not_like": "%test%"}
        }
    }
}
```

## Performance Considerations

### Indexing
- Metadata filtering is performed post-search on the vector results
- For better performance, consider using metadata filters that are selective
- Common filter fields should be indexed at the application level

### Query Optimization
- Use specific filters early in the query to reduce processing
- Combine vector similarity with metadata filtering for optimal results
- Consider using `top_k` limits to reduce the number of results to filter

### Memory Usage
- Complex nested filters may require more memory
- Very large metadata objects should be avoided
- Consider pagination for large result sets

## Error Handling

### Invalid Filter Expressions
```json
{
  "error": "Invalid metadata filter: Unable to parse SQL condition: invalid syntax"
}
```

### Data Type Mismatches
```json
{
  "error": "Invalid metadata filter: Cannot compare string 'abc' with number 123"
}
```

### Missing Fields
Filters on non-existent fields return empty results by default. Use `EXISTS` operator to check for field presence.

## Best Practices

1. **Start Simple**: Begin with basic equality filters before moving to complex expressions
2. **Use Appropriate Data Types**: Ensure metadata values are stored with correct types
3. **Test Filters**: Use the test script to validate your filter expressions
4. **Performance Testing**: Test filter performance with your actual data volumes
5. **Error Handling**: Always handle potential filter parsing errors in your application
6. **Documentation**: Document your metadata schema and common filter patterns

## API Reference

### Search Endpoints

All search endpoints support metadata filtering:

- `POST /api/v1/datasets/{dataset_id}/search` - Vector search with metadata filtering
- `POST /api/v1/datasets/{dataset_id}/search/text` - Text search with metadata filtering  
- `POST /api/v1/datasets/{dataset_id}/search/hybrid` - Hybrid search with metadata filtering

### Filter Parameter

The `filters` parameter in `SearchOptions` accepts:
- `Dict[str, Any]` - Dictionary format (simple or MongoDB-style)
- `str` - SQL-like string format
- `null` - No filtering (default)

### Response Format

Filtered results maintain the same response format with additional metadata:

```json
{
  "results": [
    {
      "vector": {
        "id": "doc1",
        "content": "Python programming tutorial",
        "metadata": {
          "category": "programming",
          "level": "beginner",
          "rating": 4.5,
          "published": true
        }
      },
      "score": 0.8542,
      "distance": 0.1458,
      "rank": 1
    }
  ],
  "total_found": 1,
  "query_time_ms": 45.2
}
```

## Troubleshooting

### Common Issues

1. **Empty Results**: Check if metadata fields exist and match expected values
2. **Syntax Errors**: Validate filter syntax using the test script
3. **Type Mismatches**: Ensure data types match between filter and metadata
4. **Performance Issues**: Optimize filters and consider indexing strategies

### Debug Mode

Enable debug logging to see filter parsing and application:

```python
import logging
logging.getLogger("metadata_filter").setLevel(logging.DEBUG)
```

### Testing

Use the provided test script to validate your filtering setup:

```bash
python test_metadata_filtering.py
```

This comprehensive metadata filtering system provides powerful capabilities for precise search result filtering while maintaining performance and usability.