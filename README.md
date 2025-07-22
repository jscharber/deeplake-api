# Tributary AI services for DeepLake

A production-ready, universal vector database service built with Deep Lake, providing both HTTP REST and gRPC APIs for vector storage, search, and management.

## 🚀 Features

- **Dual API Support**: Both HTTP REST and gRPC APIs
- **Production Ready**: Authentication, rate limiting, monitoring, and metrics
- **Multi-tenant**: Secure tenant isolation and resource management
- **High Performance**: Optimized for large-scale vector operations
- **Cloud Native**: Docker, Kubernetes, and monitoring ready
- **Comprehensive**: Full CRUD operations for datasets and vectors
- **Flexible Search**: Vector similarity search with advanced filtering options

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Authentication](#authentication)
- [Deployment](#deployment)
- [Examples](#examples)
- [Monitoring](#monitoring)
- [Development](#development)
- [Contributing](#contributing)

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/deeplake-vector-service.git
   cd deeplake-vector-service
   ```

2. **Start all services (including monitoring)**
   ```bash
   docker-compose up -d
   ```

3. **Access the Monitoring Dashboard**
   ```bash
   # Open in your browser:
   http://localhost:8080
   
   # The dashboard provides access to:
   # - Service health monitoring
   # - Grafana dashboards (localhost:3000)
   # - Prometheus metrics (localhost:9090) 
   # - AlertManager (localhost:9093)
   # - API documentation (localhost:8000/docs)
   ```

4. **Verify the service is running**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

5. **Generate and configure API key**
   ```bash
   # Generate JWT secret
   export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   
   # Generate API key
   python scripts/generate_api_key_quick.py
   export API_KEY="your-generated-api-key"
   ```

6. **Create your first dataset**
   ```bash
   curl -X POST http://localhost:8000/api/v1/datasets/ \
     -H "Authorization: ApiKey $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "my-first-dataset",
       "dimensions": 128,
       "metric_type": "cosine",
       "description": "My first vector dataset"
     }'
   ```

### Manual Installation

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run the service**
   ```bash
   python -m app.main
   ```

## 📦 Installation

### Requirements

- Python 3.9+
- Redis (for caching)
- Deep Lake library
- Docker (optional)
- Kubernetes (for production deployment)

### Dependencies

The service uses the following key dependencies:

- **FastAPI**: Modern, fast web framework for building APIs
- **Deep Lake**: Vector database and data lake for AI
- **gRPC**: High-performance RPC framework
- **Redis**: In-memory cache for improved performance
- **Prometheus**: Metrics and monitoring
- **Pydantic**: Data validation and settings management
- **Structlog**: Structured logging

Install all dependencies:

```bash
pip install -r requirements.txt
```

For development dependencies:

```bash
pip install -r requirements-dev.txt
```

## 📖 API Documentation

### HTTP REST API

The service provides a comprehensive REST API at `/api/v1`:

#### Datasets
- `POST /datasets` - Create a new dataset
- `GET /datasets` - List all datasets
- `GET /datasets/{id}` - Get dataset information
- `PUT /datasets/{id}` - Update dataset
- `DELETE /datasets/{id}` - Delete dataset
- `GET /datasets/{id}/stats` - Get dataset statistics

#### Vectors
- `POST /datasets/{id}/vectors` - Insert single vector
- `POST /datasets/{id}/vectors/batch` - Insert multiple vectors
- `GET /datasets/{id}/vectors` - List vectors (paginated)
- `GET /datasets/{id}/vectors/{vector_id}` - Get specific vector
- `PUT /datasets/{id}/vectors/{vector_id}` - Update vector
- `DELETE /datasets/{id}/vectors/{vector_id}` - Delete vector

#### Search
- `POST /datasets/{id}/search` - Vector similarity search
- `POST /datasets/{id}/search/text` - Text-based search
- `POST /datasets/{id}/search/hybrid` - Hybrid search
- `POST /search/multi-dataset` - Multi-dataset search

#### Health & Monitoring
- `GET /health` - Health check
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe
- `GET /metrics` - Prometheus metrics
- `GET /stats` - Service statistics

### gRPC API

The service also provides a gRPC API with the following services:

- **DatasetService**: Dataset management operations
- **VectorService**: Vector CRUD operations
- **SearchService**: Vector search operations
- **HealthService**: Health checks and metrics

See `proto/deeplake_service.proto` for the complete protocol buffer definition.

### Interactive Documentation

Interactive API documentation is always available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

**Note**: In v1.0.1+, documentation endpoints are always accessible regardless of environment mode.

## ⚙️ Configuration

The service uses environment variables for configuration. Copy `.env.example` to `.env` and customize:

### Core Configuration

```bash
# Deep Lake Configuration
DEEPLAKE_STORAGE_LOCATION=./data/vectors
DEEPLAKE_TOKEN=your_deeplake_token
DEEPLAKE_ORG_ID=your_org_id

# Server Configuration
HTTP_HOST=0.0.0.0
HTTP_PORT=8000
GRPC_HOST=0.0.0.0
GRPC_PORT=50051

# Authentication
JWT_SECRET_KEY=your-secret-key-change-in-production
```

### Advanced Configuration

```bash
# Redis Cache
REDIS_URL=redis://localhost:6379/0
REDIS_TTL_SECONDS=3600

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_BURST=100

# Performance
PERFORMANCE_MAX_VECTOR_BATCH_SIZE=1000
PERFORMANCE_DEFAULT_SEARCH_TIMEOUT=30
PERFORMANCE_MAX_CONCURRENT_SEARCHES=50

# Monitoring
MONITORING_LOG_LEVEL=INFO
MONITORING_ENABLE_METRICS=true
```

## 🔐 Authentication

The service supports two authentication methods:

### 🚨 Security Update (v1.0.1)

**BREAKING CHANGE**: Hardcoded API keys have been removed for security. You must now generate API keys using the provided tools.

### API Key Authentication

1. **Generate JWT Secret**:
   ```bash
   export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

2. **Generate an API key**:
   ```bash
   python scripts/generate_api_key_quick.py
   export API_KEY="your-generated-api-key"
   ```

3. **Include in requests**:
   ```bash
   curl -H "Authorization: ApiKey $API_KEY" ...
   ```

### Environment Setup

For convenient development, add to your `~/.bashrc`:
```bash
# See bashrc_exports.sh for complete template
export JWT_SECRET_KEY="your-jwt-secret-key"
export API_KEY="your-api-key"
```

### JWT Token Authentication

1. **Obtain a JWT token** from your authentication service
2. **Include in requests**:
   ```bash
   curl -H "Authorization: Bearer your-jwt-token" ...
   ```

### Permissions

The service supports role-based access control with the following permissions:

- `read`: Read datasets and vectors, perform searches
- `write`: Create and modify datasets and vectors
- `admin`: Full access including metrics and system operations

## 🚀 Deployment

### Development

```bash
# Start with auto-reload
python -m app.main

# Or with Docker
docker-compose up --build
```

### Production

#### Docker

```bash
# Build image
docker build -t deeplake-service:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -p 50051:50051 \
  -e DEEPLAKE_STORAGE_LOCATION=/data \
  -v $(pwd)/data:/data \
  deeplake-service:latest
```

#### Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f deployment/kubernetes/

# Check deployment status
kubectl get pods -n deeplake
kubectl get services -n deeplake
```

#### Monitoring Stack

The service includes a complete monitoring stack:

```bash
# Start with monitoring
docker-compose -f docker-compose.yml up -d

# Access monitoring
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

## 💡 Examples

### Python Client

```python
import asyncio
from docs.examples.python_client import DeepLakeClient

async def main():
    async with DeepLakeClient(api_key="your-api-key") as client:
        # Create dataset
        dataset = await client.create_dataset(
            name="example-dataset",
            dimensions=128,
            description="Example dataset"
        )
        
        # Insert vectors
        vectors = [{
            "id": "vec1",
            "document_id": "doc1",
            "values": [0.1] * 128,
            "content": "Example content"
        }]
        
        result = await client.insert_vectors_batch(
            dataset["id"], vectors
        )
        
        # Search
        search_result = await client.search_vectors(
            dataset_id=dataset["id"],
            query_vector=[0.1] * 128,
            top_k=10
        )
        
        print(f"Found {len(search_result['results'])} results")

asyncio.run(main())
```

### cURL Examples

```bash
# Run the interactive cURL examples
./docs/examples/curl_examples.sh
```

### Go Client

See `docs/examples/go_client.go` for a complete Go client implementation.

## 📊 Monitoring

### Metrics

The service exposes Prometheus metrics at `/api/v1/metrics/prometheus`:

- Request rates and latencies
- Vector operation metrics
- Dataset statistics
- Cache performance
- Error rates
- System resource usage

### Health Checks

- **Liveness**: `/api/v1/health/live` - Basic service health
- **Readiness**: `/api/v1/health/ready` - Service ready to accept traffic
- **Deep Health**: `/api/v1/health` - Comprehensive health with dependencies

### Logging

Structured logging with configurable levels and formats:

```bash
# JSON format (production)
MONITORING_LOG_FORMAT=json

# Human-readable format (development)
MONITORING_LOG_FORMAT=console
```

## 🚨 Alerting System

The DeepLake API includes a comprehensive alerting system for proactive monitoring and incident response.

### 🔧 Quick Setup

1. **Start the monitoring stack**:
   ```bash
   docker-compose up -d
   ```

2. **Configure notifications**:
   ```bash
   # Run the alerting setup script
   ./scripts/setup-alerting.sh
   ```

3. **Test the system**:
   ```bash
   # Run alerting tests
   ./scripts/test-alerting.sh
   ```

### 📊 Monitoring Components

- **Prometheus** (`:9090`): Metrics collection and alert evaluation
- **Alertmanager** (`:9093`): Alert routing and notifications
- **Grafana** (`:3000`): Dashboards and visualization
- **Redis**: Cache monitoring and health checks

### 🔔 Alert Types

**Service Health**:
- Service downtime detection (DeepLakeAPIDown)
- Cache service monitoring (RedisCacheDown)
- High error rates (>5% warning, >10% critical)

**Performance**:
- Response latency (>2s warning, >5s critical)
- Search query performance (>10s warning, >30s critical)
- Vector insertion speed monitoring

**Resource Usage**:
- Memory consumption (>2GB warning, >4GB critical)
- Storage growth monitoring (>1GB/hour warning)
- Cache hit rate monitoring (<50% warning)

**Data Operations**:
- Vector insertion activity monitoring
- Dataset size alerts (>10GB warning)
- Tenant-specific performance monitoring

### 📞 Notification Channels

Configure multiple notification channels in `deployment/alertmanager.yml`:

**Slack**:
```yaml
slack_configs:
- api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK'
  channel: '#alerts-critical'
  title: 'DeepLake API Alert'
  send_resolved: true
```

**PagerDuty**:
```yaml
pagerduty_configs:
- routing_key: 'YOUR_PAGERDUTY_INTEGRATION_KEY'
  description: 'DeepLake API Critical Alert'
  severity: 'critical'
```

**Email**:
```yaml
email_configs:
- to: 'oncall@yourcompany.com'
  subject: 'DeepLake API Alert'
  body: 'Alert details...'
```

### 🧪 Testing Alerts

```bash
# Basic alert system test
./scripts/test-alerting.sh

# Simulate high error rate
./scripts/test-alerting.sh error-rate

# Simulate service downtime
./scripts/test-alerting.sh service-down

# Run stress test
./scripts/test-alerting.sh stress
```

### 📋 Service URLs

- **Grafana Dashboard**: http://localhost:3000
- **Prometheus Metrics**: http://localhost:9090
- **Alertmanager Console**: http://localhost:9093
- **DeepLake API Health**: http://localhost:8000/api/v1/health
- **Prometheus Metrics Endpoint**: http://localhost:8000/api/v1/metrics/prometheus

### 📚 Documentation

- **Setup Guide**: `deployment/alerting-setup.md`
- **Configuration Templates**: `deployment/alertmanager-templates.yml`
- **Alert Rules**: `deployment/prometheus-alerts.yml`

## 📦 Bulk Import/Export

Efficiently transfer large amounts of vector data with comprehensive import/export functionality.

### 🔧 Supported Formats

- **CSV**: Simple tabular format for vectors and metadata
- **JSON**: Structured format with full metadata support  
- **JSONL**: Line-delimited JSON for streaming large datasets

### 📊 Features

- **Asynchronous Processing**: Large operations run in background
- **Progress Tracking**: Real-time status monitoring
- **Error Handling**: Detailed error reporting and partial success handling
- **Filtering**: Export subsets based on metadata filters
- **Batch Processing**: Configurable batch sizes for optimal performance

### 🚀 Quick Usage

**Import vectors**:
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/import" \
  -H "Authorization: ApiKey your-api-key" \
  -F "file=@vectors.csv" \
  -F "format=csv"
```

**Export vectors**:
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/export" \
  -H "Authorization: ApiKey your-api-key" \
  -d '{"format": "json", "limit": 1000}'
```

**Monitor progress**:
```bash
curl "http://localhost:8000/api/v1/import/{job_id}" \
  -H "Authorization: ApiKey your-api-key"
```

### 🧪 Testing

```bash
# Test import/export functionality
./test_import_export.py
```

### 📚 Documentation

- **Complete Guide**: `docs/import-export.md`
- **API Reference**: Available in `/docs` endpoint
- **Sample Files**: Various format examples included

## 🔍 Hybrid Search

Advanced search combining vector similarity and text search for superior results.

### 🧠 Fusion Methods

- **Weighted Sum**: Simple weighted combination (default)
- **Reciprocal Rank Fusion**: Advanced rank-based fusion
- **CombSUM/CombMNZ**: Score aggregation methods
- **Borda Count**: Democratic voting approach

### ⚡ Features

- **Configurable Weighting**: Balance semantic vs keyword search
- **Intelligent Caching**: Optimized performance for repeated queries
- **Multiple Algorithms**: 5 different fusion methods available
- **Metadata Integration**: Works with advanced metadata filtering

### 🚀 Quick Usage

**Balanced hybrid search**:
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/search/hybrid" \
  -H "Authorization: ApiKey your-api-key" \
  -d '{
    "query_text": "machine learning tutorial",
    "vector_weight": 0.6,
    "text_weight": 0.4,
    "fusion_method": "weighted_sum"
  }'
```

**Semantic-heavy search**:
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/my-dataset/search/hybrid" \
  -H "Authorization: ApiKey your-api-key" \
  -d '{
    "query_text": "natural language understanding",
    "vector_weight": 0.8,
    "text_weight": 0.2,
    "fusion_method": "reciprocal_rank_fusion"
  }'
```

### 🧪 Testing

```bash
# Test all fusion methods and configurations
./test_hybrid_search.py
```

### 📚 Documentation

- **Complete Guide**: `docs/hybrid-search.md`
- **Fusion Method Details**: Comprehensive algorithm explanations
- **Performance Tuning**: Weight optimization guidelines

## 🛠️ Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/deeplake-vector-service.git
cd deeplake-vector-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
./scripts/test.sh

# Run specific test categories
pytest tests/unit/
pytest tests/integration/ -m integration
pytest tests/ -m "not slow"

# Run with coverage
pytest --cov=app --cov-report=html
```

### Code Quality

```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint code
flake8 app/ tests/
mypy app/

# Run all quality checks
./scripts/build.sh
```

### Generate Protocol Buffers

```bash
# Generate Python gRPC code
./scripts/generate_proto.sh
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run quality checks: `./scripts/build.sh`
5. Run tests: `./scripts/test.sh`
6. Commit your changes: `git commit -m 'Add amazing feature'`
7. Push to the branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: See the `docs/` directory
- **Examples**: Check `docs/examples/` for client examples
- **Issues**: Report bugs and request features on GitHub Issues
- **Discussions**: Join community discussions on GitHub Discussions

## 🗺️ Roadmap

### ✅ Recently Completed (v1.0.2)
- [x] **Security Hardening**: Removed hardcoded API keys and JWT secrets
- [x] **Documentation Access**: Always-available API documentation
- [x] **Service Configuration**: Enhanced environment variable support
- [x] **Cosine Similarity**: Implementation of cosine distance metric
- [x] **Metadata Filtering**: Advanced search filtering capabilities
- [x] **Alerting System**: Comprehensive monitoring and alerting infrastructure
- [x] **Grafana Dashboards**: Operational monitoring dashboards
- [x] **Bulk Import/Export**: CSV, JSON, and JSONL import/export with progress tracking
- [x] **Hybrid Search**: Vector + text search with multiple fusion algorithms

### 🎯 Upcoming Features
- [ ] **Text embedding integration**: Direct embedding service integration
- [ ] **Advanced indexing options**: HNSW and IVF index support
- [ ] **Horizontal scaling support**: Multi-instance deployment
- [ ] **GraphQL API**: Alternative query interface
- [ ] **Real-time search updates**: Live search result updates
- [ ] **Machine Learning Ops**: Model versioning and A/B testing
- [ ] **Data Pipeline Integration**: ETL connectors and streaming support

See [ROADMAP.md](ROADMAP.md) for detailed planning and timelines.

## 📈 Performance

### Benchmarks

- **Search latency**: < 100ms for datasets with 1M+ vectors
- **Insertion rate**: > 10k vectors/second
- **Concurrent requests**: Supports 1000+ concurrent connections
- **Memory usage**: < 2GB for typical workloads

### Optimization Tips

1. Use batch operations for inserting multiple vectors
2. Enable caching for frequently accessed data
3. Choose appropriate vector dimensions for your use case
4. Use filtering to reduce search space
5. Monitor metrics to identify bottlenecks

---

**Made with ❤️ by the Tributary AI services for DeepLake Team**
