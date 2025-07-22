# Installation & Setup

This guide provides comprehensive instructions for installing and setting up the Tributary AI Service for DeepLake across different environments.

## 📋 Prerequisites

### System Requirements

**Minimum Requirements:**
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 10GB available space
- **Network**: 1Gbps connection
- **OS**: Linux, macOS, or Windows (with WSL2)

**Recommended Requirements:**
- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Storage**: 100GB+ SSD
- **Network**: 10Gbps connection
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+)

### Software Dependencies

- **Python**: 3.9+ (for local development)
- **Docker**: 20.10+ (for containerized deployment)
- **Redis**: 6.0+ (for caching)
- **DeepLake**: 4.0+ (vector database)

## 🐳 Docker Installation (Recommended)

### Quick Start

```bash
# Pull the latest image
docker pull deeplake-api:latest

# Run with basic configuration
docker run -d \
  --name deeplake-api \
  -p 8000:8000 \
  -e DEEPLAKE_TOKEN=your-token-here \
  -e REDIS_URL=redis://localhost:6379 \
  deeplake-api:latest
```

### Production Docker Setup

```bash
# Create a network for the services
docker network create deeplake-network

# Run Redis
docker run -d \
  --name redis \
  --network deeplake-network \
  -p 6379:6379 \
  redis:7-alpine

# Run Tributary AI Service
docker run -d \
  --name deeplake-api \
  --network deeplake-network \
  -p 8000:8000 \
  -e DEEPLAKE_TOKEN=your-token-here \
  -e REDIS_URL=redis://redis:6379 \
  -e LOG_LEVEL=INFO \
  -e WORKERS=4 \
  -v /path/to/data:/data \
  deeplake-api:latest
```

### Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  deeplake-api:
    image: deeplake-api:latest
    container_name: deeplake-api
    ports:
      - "8000:8000"
    environment:
      - DEEPLAKE_TOKEN=${DEEPLAKE_TOKEN}
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
      - WORKERS=4
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis
    volumes:
      - deeplake_data:/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    restart: unless-stopped

volumes:
  deeplake_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    name: deeplake-network
```

Start the services:

```bash
# Create environment file
cat > .env << EOF
DEEPLAKE_TOKEN=your-token-here
OPENAI_API_KEY=your-openai-key
EOF

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f deeplake-api
```

## 🐍 Local Development Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/deeplake-api.git
cd deeplake-api
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### 4. Set Up Environment Variables

```bash
# Create environment file
cp .env.example .env

# Edit environment file
nano .env
```

Example `.env` file:

```bash
# DeepLake Configuration
DEEPLAKE_TOKEN=your-token-here
DEEPLAKE_ORG=your-org-name

# Service Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4
DEBUG=false

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Embedding Service
OPENAI_API_KEY=your-openai-key
EMBEDDING_MODEL=text-embedding-ada-002

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_BURST=100

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=structured

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=9090
```

### 5. Set Up Redis

**Option A: Docker**
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

**Option B: Local Installation**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install redis-server

# macOS
brew install redis
brew services start redis

# CentOS/RHEL
sudo yum install redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 6. Initialize the Database

```bash
# Run initialization script
python scripts/init_db.py

# Or manually create required directories
mkdir -p data/datasets
mkdir -p logs
```

### 7. Start the Service

```bash
# Development mode with auto-reload
python -m app.main

# Or using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## ☸️ Kubernetes Installation

### 1. Prepare Kubernetes Manifests

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: deeplake
  labels:
    name: deeplake

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: deeplake-config
  namespace: deeplake
data:
  HOST: "0.0.0.0"
  PORT: "8000"
  WORKERS: "4"
  LOG_LEVEL: "INFO"
  REDIS_URL: "redis://redis:6379"

---
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: deeplake-secrets
  namespace: deeplake
type: Opaque
data:
  DEEPLAKE_TOKEN: <base64-encoded-token>
  OPENAI_API_KEY: <base64-encoded-key>

---
# redis-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: deeplake
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command: ["redis-server", "--appendonly", "yes"]
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-pvc

---
# redis-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: deeplake
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379

---
# deeplake-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deeplake-api
  namespace: deeplake
spec:
  replicas: 3
  selector:
    matchLabels:
      app: deeplake-api
  template:
    metadata:
      labels:
        app: deeplake-api
    spec:
      containers:
      - name: deeplake-api
        image: deeplake-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: HOST
          valueFrom:
            configMapKeyRef:
              name: deeplake-config
              key: HOST
        - name: PORT
          valueFrom:
            configMapKeyRef:
              name: deeplake-config
              key: PORT
        - name: WORKERS
          valueFrom:
            configMapKeyRef:
              name: deeplake-config
              key: WORKERS
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: deeplake-config
              key: REDIS_URL
        - name: DEEPLAKE_TOKEN
          valueFrom:
            secretKeyRef:
              name: deeplake-secrets
              key: DEEPLAKE_TOKEN
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: deeplake-secrets
              key: OPENAI_API_KEY
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"

---
# deeplake-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: deeplake-api
  namespace: deeplake
spec:
  selector:
    app: deeplake-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer

---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: deeplake-ingress
  namespace: deeplake
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.yourcompany.com
    secretName: deeplake-tls
  rules:
  - host: api.yourcompany.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: deeplake-api
            port:
              number: 80
```

### 2. Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f k8s/

# Or apply individually
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/redis-service.yaml
kubectl apply -f k8s/deeplake-deployment.yaml
kubectl apply -f k8s/deeplake-service.yaml
kubectl apply -f k8s/ingress.yaml

# Check deployment status
kubectl get pods -n deeplake
kubectl get services -n deeplake
```

### 3. Verify Installation

```bash
# Check pods
kubectl get pods -n deeplake

# Check logs
kubectl logs -f deployment/deeplake-api -n deeplake

# Port forward for testing
kubectl port-forward service/deeplake-api 8000:80 -n deeplake
```

## 🎯 Helm Installation

### 1. Add Helm Repository

```bash
helm repo add deeplake https://charts.deeplake.ai
helm repo update
```

### 2. Create Values File

```yaml
# values.yaml
replicaCount: 3

image:
  repository: deeplake-api
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  port: 80

ingress:
  enabled: true
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
  hosts:
    - host: api.yourcompany.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: deeplake-tls
      hosts:
        - api.yourcompany.com

config:
  deeplakeToken: "your-token-here"
  openaiApiKey: "your-openai-key"
  logLevel: "INFO"
  workers: 4

redis:
  enabled: true
  auth:
    enabled: false
  master:
    persistence:
      enabled: true
      size: 8Gi

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80

resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### 3. Install with Helm

```bash
# Install
helm install deeplake-api deeplake/deeplake-api -f values.yaml

# Upgrade
helm upgrade deeplake-api deeplake/deeplake-api -f values.yaml

# Check status
helm status deeplake-api

# Uninstall
helm uninstall deeplake-api
```

## 🔧 Configuration

### Environment Variables

Create a comprehensive `.env` file:

```bash
# ===================
# Core Configuration
# ===================
HOST=0.0.0.0
PORT=8000
WORKERS=4
DEBUG=false
ENVIRONMENT=production

# ===================
# DeepLake Configuration
# ===================
DEEPLAKE_TOKEN=your-token-here
DEEPLAKE_ORG=your-org-name
DEEPLAKE_DATASET_PREFIX=prod

# ===================
# Redis Configuration
# ===================
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-redis-password
REDIS_DB=0
REDIS_MAX_CONNECTIONS=20

# ===================
# Embedding Services
# ===================
OPENAI_API_KEY=your-openai-key
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_BATCH_SIZE=100
EMBEDDING_TIMEOUT=30

# ===================
# Rate Limiting
# ===================
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_BURST=100
RATE_LIMIT_ENABLED=true

# ===================
# Monitoring
# ===================
PROMETHEUS_ENABLED=true
METRICS_PORT=9090
LOG_LEVEL=INFO
LOG_FORMAT=structured
SENTRY_DSN=your-sentry-dsn

# ===================
# Security
# ===================
CORS_ORIGINS=["http://localhost:3000", "https://yourapp.com"]
API_KEY_HEADER=Authorization
JWT_SECRET=your-jwt-secret

# ===================
# Backup Configuration
# ===================
BACKUP_ENABLED=true
BACKUP_STORAGE=s3
BACKUP_S3_BUCKET=your-backup-bucket
BACKUP_RETENTION_DAYS=30
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
```

### Configuration File

Alternative YAML configuration:

```yaml
# config.yaml
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  debug: false

deeplake:
  token: "your-token-here"
  org: "your-org-name"
  dataset_prefix: "prod"

redis:
  url: "redis://localhost:6379"
  password: null
  db: 0
  max_connections: 20

embedding:
  openai_api_key: "your-openai-key"
  model: "text-embedding-ada-002"
  batch_size: 100
  timeout: 30

rate_limiting:
  enabled: true
  requests_per_minute: 1000
  burst: 100

monitoring:
  prometheus_enabled: true
  metrics_port: 9090
  log_level: "INFO"
  log_format: "structured"

security:
  cors_origins:
    - "http://localhost:3000"
    - "https://yourapp.com"
  api_key_header: "Authorization"
  jwt_secret: "your-jwt-secret"

backup:
  enabled: true
  storage: "s3"
  s3_bucket: "your-backup-bucket"
  retention_days: 30
```

## ✅ Verification

### 1. Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
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

### 2. API Documentation

Visit: http://localhost:8000/docs

### 3. Metrics

```bash
curl http://localhost:8000/metrics
```

### 4. Test API

```bash
# Test with a simple request
curl -X POST "http://localhost:8000/api/v1/datasets" \
  -H "Authorization: ApiKey your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-dataset",
    "description": "Test dataset",
    "embedding_dimension": 1536
  }'
```

## 🔍 Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs
   docker logs deeplake-api
   
   # Check environment variables
   docker exec deeplake-api printenv
   ```

2. **Redis connection failed**
   ```bash
   # Test Redis connection
   redis-cli ping
   
   # Check Redis logs
   docker logs redis
   ```

3. **DeepLake authentication failed**
   ```bash
   # Verify token
   python -c "import deeplake; print(deeplake.exists('hub://your-org/test'))"
   ```

4. **Port already in use**
   ```bash
   # Find process using port
   lsof -i :8000
   
   # Kill process
   kill -9 <PID>
   ```

### Debug Mode

Run in debug mode for detailed logging:

```bash
docker run -d \
  --name deeplake-api \
  -p 8000:8000 \
  -e DEBUG=true \
  -e LOG_LEVEL=DEBUG \
  deeplake-api:latest
```

## 📈 Next Steps

1. **[Configure Authentication](./authentication.md)**
2. **[Set up Monitoring](./monitoring.md)**
3. **[Deploy to Production](./deployment/production.md)**
4. **[Configure Backups](./disaster_recovery.md)**
5. **[Set up SSL/TLS](./security.md)**

## 🆘 Support

- **Documentation**: [Full Documentation](./README.md)
- **Issues**: [GitHub Issues](https://github.com/your-org/deeplake-api/issues)
- **Community**: [Discord](https://discord.gg/your-discord)
- **Enterprise**: [support@yourcompany.com](mailto:support@yourcompany.com)