# Configuration Guide

The Tributary AI Service for DeepLake is fully configurable through environment variables. This document provides a comprehensive guide to all available configuration options.

## Configuration Overview

All configuration is managed through environment variables using Pydantic Settings. Each configuration section has a specific prefix for easy organization.

## Environment File Setup

Create a `.env` file in the project root with your configuration:

```bash
# Copy the example file
cp .env.example .env

# Edit with your settings
vim .env
```

## Configuration Sections

### Deep Lake Configuration (`DEEPLAKE_`)

Core Deep Lake storage and connection settings.

```bash
# Storage location for Deep Lake datasets
DEEPLAKE_STORAGE_LOCATION=./data/vectors

# Deep Lake authentication token (optional)
DEEPLAKE_TOKEN=your_deeplake_token

# Deep Lake organization ID (optional)
DEEPLAKE_ORG_ID=your_org_id
```

### HTTP Server Configuration (`HTTP_`)

HTTP server and connection settings.

```bash
# HTTP server host
HTTP_HOST=0.0.0.0

# HTTP server port
HTTP_PORT=8000

# Number of worker processes
HTTP_WORKERS=4
```

### gRPC Server Configuration (`GRPC_`)

gRPC server settings for high-performance API access.

```bash
# gRPC server host
GRPC_HOST=0.0.0.0

# gRPC server port
GRPC_PORT=50051

# Maximum number of gRPC workers
GRPC_MAX_WORKERS=10
```

### Authentication Configuration

JWT and API key authentication settings.

```bash
# JWT secret key (REQUIRED - generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=your-secret-key-change-in-production

# JWT algorithm
JWT_ALGORITHM=HS256

# JWT expiration in hours (default: 1 year)
JWT_EXPIRATION_HOURS=8760
```

### Redis Cache Configuration (`REDIS_`)

Redis caching settings for improved performance.

```bash
# Redis connection URL
REDIS_URL=redis://localhost:6379/0

# TTL configurations for different cache types (seconds)
REDIS_DEFAULT_TTL_SECONDS=3600      # 1 hour default
REDIS_SEARCH_CACHE_TTL=300          # 5 minutes for search results
REDIS_METADATA_CACHE_TTL=1800       # 30 minutes for metadata
REDIS_DATASET_CACHE_TTL=900         # 15 minutes for dataset info
REDIS_EMBEDDING_CACHE_TTL=3600      # 1 hour for embeddings

# Connection configuration
REDIS_MAX_CONNECTIONS=20
REDIS_CONNECTION_TIMEOUT=5
REDIS_RETRY_ATTEMPTS=3

# Memory optimization
REDIS_COMPRESS_CACHE=true
REDIS_MAX_CACHE_SIZE_MB=512
```

### Performance Configuration (`PERFORMANCE_`)

Performance tuning and timeout settings.

```bash
# Vector operations
PERFORMANCE_MAX_VECTOR_BATCH_SIZE=1000
PERFORMANCE_DEFAULT_SEARCH_TIMEOUT=30
PERFORMANCE_MAX_CONCURRENT_SEARCHES=50

# Thread pool configuration
PERFORMANCE_DEEPLAKE_THREAD_POOL_WORKERS=10

# HTTP timeouts (seconds)
PERFORMANCE_HTTP_REQUEST_TIMEOUT=300
PERFORMANCE_HTTP_KEEP_ALIVE_TIMEOUT=5

# Search operation timeouts (seconds)
PERFORMANCE_VECTOR_SEARCH_TIMEOUT=30
PERFORMANCE_TEXT_SEARCH_TIMEOUT=15
PERFORMANCE_HYBRID_SEARCH_TIMEOUT=45

# Import/export settings
PERFORMANCE_IMPORT_BATCH_SIZE=100
PERFORMANCE_EXPORT_BATCH_SIZE=100
PERFORMANCE_IMPORT_TIMEOUT=3600      # 1 hour
PERFORMANCE_EXPORT_TIMEOUT=1800      # 30 minutes

# Database timeouts (seconds)
PERFORMANCE_DATABASE_CONNECTION_TIMEOUT=30
PERFORMANCE_DATABASE_QUERY_TIMEOUT=60

# Pagination and limits
PERFORMANCE_DEFAULT_PAGE_SIZE=100
PERFORMANCE_MAX_PAGE_SIZE=1000
PERFORMANCE_MAX_SEARCH_RESULTS=10000
```

### Rate Limiting Configuration (`RATE_LIMIT_`)

Rate limiting settings for API protection.

```bash
# Requests per minute per client
RATE_LIMIT_REQUESTS_PER_MINUTE=1000

# Burst capacity
RATE_LIMIT_BURST=100
```

### Monitoring Configuration (`MONITORING_`)

Monitoring, metrics, and logging settings.

```bash
# Enable Prometheus metrics
MONITORING_ENABLE_METRICS=true

# Metrics server port
MONITORING_METRICS_PORT=9090

# Logging configuration
MONITORING_LOG_LEVEL=INFO
MONITORING_LOG_FORMAT=json  # or "console" for development
```

### Development Configuration (`DEV_`)

Development and debugging settings.

```bash
# Debug mode
DEV_DEBUG=false

# Auto-reload on changes
DEV_RELOAD=false

# CORS allowed origins (comma-separated)
DEV_CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Development API key (for testing)
DEV_DEFAULT_API_KEY=your-dev-api-key
```

### Embedding Service Configuration (`EMBEDDING_`)

Embedding service and model settings.

```bash
# OpenAI configuration
EMBEDDING_OPENAI_API_KEY=your-openai-api-key
EMBEDDING_OPENAI_MODEL=text-embedding-3-small

# Sentence Transformers configuration
EMBEDDING_SENTENCE_TRANSFORMERS_MODEL=all-MiniLM-L6-v2

# General embedding settings
EMBEDDING_CACHE_TTL=3600
EMBEDDING_MAX_TEXT_LENGTH=10000
EMBEDDING_BATCH_SIZE=32
```

## Configuration Examples

### Production Environment

```bash
# Production .env example
DEEPLAKE_STORAGE_LOCATION=/data/vectors
JWT_SECRET_KEY=your-super-secure-secret-key
REDIS_URL=redis://redis:6379/0
HTTP_HOST=0.0.0.0
HTTP_PORT=8000
MONITORING_LOG_LEVEL=INFO
MONITORING_LOG_FORMAT=json
PERFORMANCE_MAX_CONCURRENT_SEARCHES=100
RATE_LIMIT_REQUESTS_PER_MINUTE=5000
```

### Development Environment

```bash
# Development .env example
DEV_DEBUG=true
DEV_RELOAD=true
MONITORING_LOG_LEVEL=DEBUG
MONITORING_LOG_FORMAT=console
DEV_CORS_ORIGINS=http://localhost:3000,http://localhost:8080
PERFORMANCE_DEEPLAKE_THREAD_POOL_WORKERS=4
```

### High-Performance Environment

```bash
# High-performance configuration
PERFORMANCE_MAX_VECTOR_BATCH_SIZE=2000
PERFORMANCE_MAX_CONCURRENT_SEARCHES=200
PERFORMANCE_DEEPLAKE_THREAD_POOL_WORKERS=20
REDIS_MAX_CONNECTIONS=50
HTTP_WORKERS=8
GRPC_MAX_WORKERS=20
```

## Configuration Validation

The service validates all configuration at startup. Invalid values will prevent the service from starting with clear error messages.

### Required Configuration

The following settings MUST be configured:

- `JWT_SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### Optional Configuration

All other settings have sensible defaults and are optional.

## Environment-Specific Configuration

### Docker Compose

Use environment variables in your `docker-compose.yml`:

```yaml
version: '3.8'
services:
  deeplake-api:
    image: deeplake-api:latest
    environment:
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - REDIS_URL=redis://redis:6379/0
      - DEEPLAKE_STORAGE_LOCATION=/data/vectors
    volumes:
      - ./data:/data
```

### Kubernetes

Use ConfigMaps and Secrets for configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: deeplake-config
data:
  REDIS_URL: "redis://redis-service:6379/0"
  MONITORING_LOG_LEVEL: "INFO"
  PERFORMANCE_MAX_CONCURRENT_SEARCHES: "100"
---
apiVersion: v1
kind: Secret
metadata:
  name: deeplake-secrets
type: Opaque
stringData:
  JWT_SECRET_KEY: "your-secret-key"
```

## Configuration Override Priority

Configuration is loaded in the following order (later values override earlier ones):

1. Default values (in code)
2. `.env` file
3. Environment variables
4. Command-line arguments (where applicable)

## Troubleshooting Configuration

### Common Issues

**Service won't start**:
- Check that `JWT_SECRET_KEY` is set
- Verify Redis connection with `REDIS_URL`
- Ensure storage directory exists and is writable

**Performance issues**:
- Increase `PERFORMANCE_DEEPLAKE_THREAD_POOL_WORKERS`
- Adjust `PERFORMANCE_MAX_CONCURRENT_SEARCHES`
- Tune cache TTL values
- Check `REDIS_MAX_CONNECTIONS`

**Memory issues**:
- Reduce `PERFORMANCE_MAX_VECTOR_BATCH_SIZE`
- Lower `REDIS_MAX_CACHE_SIZE_MB`
- Decrease cache TTL values

### Configuration Validation Errors

The service provides detailed error messages for configuration issues:

```bash
# Example validation error
ValidationError: JWT_SECRET_KEY is required but not set
ValidationError: REDIS_MAX_CONNECTIONS must be between 1 and 1000
```

## Security Considerations

### Sensitive Configuration

Never commit sensitive values to version control:

- `JWT_SECRET_KEY`
- `DEEPLAKE_TOKEN`
- `EMBEDDING_OPENAI_API_KEY`
- `DEV_DEFAULT_API_KEY`

Use environment-specific methods:
- Environment variables
- Secret management systems
- Encrypted configuration files

### Production Security

For production deployments:

1. Generate strong `JWT_SECRET_KEY`
2. Use least-privilege Redis access
3. Set appropriate timeout values
4. Enable monitoring and alerting
5. Regular security updates

## Performance Tuning

### High-Throughput Scenarios

```bash
# Optimize for high throughput
PERFORMANCE_MAX_VECTOR_BATCH_SIZE=2000
PERFORMANCE_MAX_CONCURRENT_SEARCHES=500
PERFORMANCE_DEEPLAKE_THREAD_POOL_WORKERS=32
HTTP_WORKERS=16
REDIS_MAX_CONNECTIONS=100
```

### Low-Latency Scenarios

```bash
# Optimize for low latency
REDIS_SEARCH_CACHE_TTL=60         # Short cache TTL
PERFORMANCE_VECTOR_SEARCH_TIMEOUT=10
PERFORMANCE_MAX_CONCURRENT_SEARCHES=50
REDIS_CONNECTION_TIMEOUT=2
```

### Memory-Constrained Environments

```bash
# Optimize for memory usage
PERFORMANCE_MAX_VECTOR_BATCH_SIZE=100
REDIS_MAX_CACHE_SIZE_MB=128
REDIS_DEFAULT_TTL_SECONDS=1800    # Shorter cache TTL
PERFORMANCE_DEEPLAKE_THREAD_POOL_WORKERS=4
```

## Monitoring Configuration

Monitor these key configuration-related metrics:

- Cache hit ratios (adjust TTL values)
- Request timeouts (tune timeout settings)
- Memory usage (adjust batch sizes and cache limits)
- Thread pool utilization (tune worker counts)

## Configuration Best Practices

1. **Start with defaults**: Use default values initially, then tune based on monitoring
2. **Environment-specific**: Use different configurations for dev/staging/production
3. **Document changes**: Keep track of configuration changes and their impact
4. **Test configuration**: Validate configuration changes in staging first
5. **Monitor impact**: Watch metrics after configuration changes
6. **Version control**: Keep configuration templates in version control
7. **Security first**: Never expose sensitive configuration values

This comprehensive configuration system allows fine-tuning of all system parameters while maintaining security and ease of management.