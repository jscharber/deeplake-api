# Rate Limiting

The Tributary AI Service for DeepLake implements comprehensive rate limiting to ensure fair usage and system stability across all tenants.

## Overview

Rate limiting is enforced at multiple levels:

1. **Global rate limits** - Apply to all requests from a tenant
2. **Operation-specific limits** - Apply to specific operations (search, insert, etc.)
3. **Cost-based limiting** - Expensive operations consume more quota
4. **Tenant-specific overrides** - Custom limits for premium/enterprise tenants

## Configuration

### Default Limits

```python
# Default rate limits (per tenant)
requests_per_minute: 1000
requests_per_hour: 50000
requests_per_day: 1000000
burst_size: 100
```

### Operation-Specific Limits

```python
operation_limits = {
    "search": 100,          # per minute
    "insert": 1000,         # per minute
    "create_dataset": 10,   # per minute
    "delete": 50,           # per minute
    "import": 5,            # per minute
    "export": 10,           # per minute
}
```

### Tenant Tiers

Premium and enterprise tenants receive higher limits:

```python
# Premium tier
requests_per_minute: 5000
requests_per_hour: 200000
burst_size: 500

# Enterprise tier
requests_per_minute: 10000
requests_per_hour: 500000
burst_size: 1000
```

## Rate Limiting Strategies

The system supports multiple rate limiting algorithms:

### 1. Sliding Window (Default)
- Tracks requests over a rolling 60-second window
- Provides smooth rate limiting without burst issues
- Most accurate for sustained load

### 2. Token Bucket
- Allows bursts up to the bucket capacity
- Tokens are refilled at a constant rate
- Good for handling traffic spikes

### 3. Fixed Window
- Simple counter that resets every minute
- Can allow bursts at window boundaries
- Lightweight implementation

### 4. Leaky Bucket
- Processes requests at a constant rate
- Smooths out traffic spikes
- Similar to token bucket but with continuous processing

## Request Costs

Different operations have different costs:

```python
request_costs = {
    "batch_insert": 10,     # High cost for batch operations
    "import": 50,           # Very high cost for bulk import
    "export": 20,           # High cost for bulk export
    "create_dataset": 5,    # Medium cost for dataset creation
    "index_operation": 20,  # High cost for index building
    "hybrid_search": 3,     # Medium cost for complex search
    "search": 1,            # Standard cost
    "insert": 1,            # Standard cost
}
```

## API Endpoints

### Get Current Rate Limits

```http
GET /api/v1/rate-limits
Authorization: ApiKey your-api-key
```

Response:
```json
{
    "tenant_id": "your-tenant-id",
    "requests_per_minute": 1000,
    "requests_per_hour": 50000,
    "requests_per_day": 1000000,
    "burst_size": 100,
    "strategy": "sliding_window",
    "operation_limits": {
        "search": 100,
        "insert": 1000,
        "create_dataset": 10
    }
}
```

### Get Usage Statistics

```http
GET /api/v1/rate-limits/usage
Authorization: ApiKey your-api-key
```

Response:
```json
{
    "tenant_id": "your-tenant-id",
    "current_minute": 45,
    "current_hour": 1250,
    "current_day": 15000,
    "total_requests": 15000,
    "operations": {
        "search": 800,
        "insert": 500,
        "create_dataset": 2
    },
    "limits": {
        "requests_per_minute": 1000,
        "requests_per_hour": 50000,
        "requests_per_day": 1000000,
        "burst_size": 100,
        "strategy": "sliding_window",
        "operation_limits": {
            "search": 100,
            "insert": 1000
        }
    }
}
```

### Test Rate Limiting

```http
POST /api/v1/test-rate-limit?operation=search&cost=1
Authorization: ApiKey your-api-key
```

Response:
```json
{
    "tenant_id": "your-tenant-id",
    "operation": "search",
    "cost": 1,
    "allowed": true,
    "limit": 100,
    "remaining": 99,
    "reset_at": "2024-01-01T12:01:00Z",
    "retry_after": null
}
```

## Admin Endpoints

### Update Tenant Rate Limits

```http
POST /api/v1/admin/rate-limits/{tenant_id}
Authorization: ApiKey admin-api-key
Content-Type: application/json

{
    "requests_per_minute": 2000,
    "requests_per_hour": 100000,
    "burst_size": 200
}
```

### Reset Tenant Rate Limits

```http
POST /api/v1/admin/rate-limits/{tenant_id}/reset
Authorization: ApiKey admin-api-key
```

### Get Rate Limit Health

```http
GET /api/v1/admin/rate-limits/health
Authorization: ApiKey admin-api-key
```

## Rate Limit Headers

All API responses include rate limit headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995260
Retry-After: 60
```

## Error Responses

When rate limit is exceeded:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640995260
Retry-After: 60
Content-Type: application/json

{
    "error": "Rate limit exceeded",
    "message": "Rate limit exceeded: 1000 requests per minute",
    "retry_after": 60
}
```

## Monitoring

Rate limiting metrics are available through:

1. **Prometheus metrics** - Request counts, limit violations, etc.
2. **Application logs** - Rate limit events and violations
3. **Health endpoint** - System status and Redis connectivity

### Key Metrics

- `rate_limit_requests_total{tenant_id, operation, status}`
- `rate_limit_violations_total{tenant_id, operation}`
- `rate_limit_check_duration_seconds{tenant_id, strategy}`

## Best Practices

### For API Consumers

1. **Monitor rate limit headers** - Check remaining quota in responses
2. **Implement exponential backoff** - When rate limited, back off exponentially
3. **Batch operations** - Use batch endpoints for multiple operations
4. **Cache results** - Avoid repeated identical requests

### For Administrators

1. **Monitor tenant usage** - Track which tenants are hitting limits
2. **Adjust limits based on usage** - Increase limits for legitimate high-usage tenants
3. **Set up alerts** - Get notified when tenants consistently hit limits
4. **Review operation costs** - Adjust costs based on actual system impact

## Configuration

Rate limiting can be configured through environment variables:

```bash
# Redis connection (required for distributed rate limiting)
REDIS_URL=redis://localhost:6379

# Default rate limits
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_BURST=100

# Rate limiting strategy
RATE_LIMIT_STRATEGY=sliding_window
```

## Troubleshooting

### Common Issues

1. **Rate limits not enforcing**
   - Check Redis connectivity
   - Verify middleware is properly configured
   - Check tenant ID extraction

2. **Inconsistent rate limiting**
   - Ensure all instances use the same Redis
   - Check system clock synchronization
   - Verify rate limit strategy configuration

3. **False rate limit violations**
   - Check for clock skew between systems
   - Verify Redis persistence configuration
   - Review request cost calculations

### Debug Commands

```bash
# Check Redis connectivity
redis-cli ping

# View rate limit keys
redis-cli keys "rate_limit:*"

# Check usage statistics
redis-cli keys "usage:*"

# Monitor rate limit activity
redis-cli monitor | grep rate_limit
```