# Production Deployment Guide

This guide covers deploying the Tributary AI Service for DeepLake to production environments with best practices for security, performance, and reliability.

## 🎯 Production Readiness Checklist

### Security
- [ ] Enable HTTPS/TLS encryption
- [ ] Configure secure API key management
- [ ] Set up proper authentication and authorization
- [ ] Enable audit logging
- [ ] Configure network security (VPC, security groups)
- [ ] Set up secrets management
- [ ] Enable CORS policies
- [ ] Configure rate limiting

### Performance
- [ ] Configure horizontal scaling
- [ ] Set up load balancing
- [ ] Enable caching (Redis)
- [ ] Configure database optimization
- [ ] Set up CDN for static assets
- [ ] Configure connection pooling
- [ ] Optimize container resources

### Reliability
- [ ] Configure health checks
- [ ] Set up monitoring and alerting
- [ ] Configure backup and disaster recovery
- [ ] Set up log aggregation
- [ ] Configure auto-scaling
- [ ] Set up multi-region deployment
- [ ] Test failover procedures

### Compliance
- [ ] Configure data encryption
- [ ] Set up audit logging
- [ ] Configure data retention policies
- [ ] Set up compliance monitoring
- [ ] Configure access controls
- [ ] Set up vulnerability scanning

## 🏗️ Infrastructure Architecture

### High-Level Production Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                  Internet                                │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              CDN / WAF                                   │
│                           (CloudFlare / AWS)                             │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Load Balancer                                 │
│                         (ALB / NGINX / HAProxy)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
    ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
    │ Tributary AI Service│ │ Tributary AI Service│ │ Tributary AI Service│
    │     Instance 1      │ │     Instance 2      │ │     Instance 3      │
    └─────────────────────┘ └─────────────────────┘ └─────────────────────┘
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                          Shared Services                             │
    ├─────────────────────────────────────────────────────────────────────┤
    │  Redis Cluster      │  DeepLake Hub     │  Monitoring Stack          │
    │  (Cache/Session)    │  (Vector Storage) │  (Prometheus/Grafana)      │
    └─────────────────────────────────────────────────────────────────────┘
```

## ☸️ Kubernetes Deployment

### Production Kubernetes Manifests

#### Namespace and Configuration

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: deeplake-prod
  labels:
    name: deeplake-prod
    environment: production

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: deeplake-config
  namespace: deeplake-prod
data:
  HOST: "0.0.0.0"
  PORT: "8000"
  WORKERS: "8"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "structured"
  ENVIRONMENT: "production"
  DEBUG: "false"
  CORS_ORIGINS: '["https://app.yourcompany.com", "https://admin.yourcompany.com"]'
  RATE_LIMIT_REQUESTS_PER_MINUTE: "5000"
  RATE_LIMIT_BURST: "500"
  PROMETHEUS_ENABLED: "true"
  BACKUP_ENABLED: "true"
  BACKUP_SCHEDULE: "0 2 * * *"

---
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: deeplake-secrets
  namespace: deeplake-prod
type: Opaque
data:
  DEEPLAKE_TOKEN: <base64-encoded-token>
  OPENAI_API_KEY: <base64-encoded-key>
  REDIS_PASSWORD: <base64-encoded-password>
  JWT_SECRET: <base64-encoded-secret>
  BACKUP_S3_ACCESS_KEY: <base64-encoded-key>
  BACKUP_S3_SECRET_KEY: <base64-encoded-secret>
```

#### Redis Cluster

```yaml
# redis-cluster.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cluster
  namespace: deeplake-prod
spec:
  serviceName: redis-cluster
  replicas: 3
  selector:
    matchLabels:
      app: redis-cluster
  template:
    metadata:
      labels:
        app: redis-cluster
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        - containerPort: 16379
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: deeplake-secrets
              key: REDIS_PASSWORD
        command:
        - redis-server
        - /etc/redis/redis.conf
        volumeMounts:
        - name: redis-config
          mountPath: /etc/redis
        - name: redis-data
          mountPath: /data
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
      volumes:
      - name: redis-config
        configMap:
          name: redis-config
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 20Gi

---
# redis-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: redis-cluster
  namespace: deeplake-prod
spec:
  selector:
    app: redis-cluster
  ports:
  - port: 6379
    targetPort: 6379
  clusterIP: None
```

#### Tributary AI Service Deployment

```yaml
# deeplake-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deeplake-api
  namespace: deeplake-prod
  labels:
    app: deeplake-api
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: deeplake-api
  template:
    metadata:
      labels:
        app: deeplake-api
        version: v1
    spec:
      serviceAccountName: deeplake-api
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: deeplake-api
        image: your-registry/deeplake-api:v1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: REDIS_URL
          value: "redis://redis-cluster:6379"
        envFrom:
        - configMapRef:
            name: deeplake-config
        - secretRef:
            name: deeplake-secrets
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 5
          failureThreshold: 3
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        volumeMounts:
        - name: data
          mountPath: /data
        - name: logs
          mountPath: /app/logs
        - name: tmp
          mountPath: /tmp
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: deeplake-data
      - name: logs
        persistentVolumeClaim:
          claimName: deeplake-logs
      - name: tmp
        emptyDir: {}
      imagePullSecrets:
      - name: registry-credentials
      nodeSelector:
        node-type: api
      tolerations:
      - key: "api-nodes"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"

---
# deeplake-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: deeplake-api
  namespace: deeplake-prod
  labels:
    app: deeplake-api
spec:
  selector:
    app: deeplake-api
  ports:
  - port: 80
    targetPort: 8000
    name: http
  - port: 9090
    targetPort: 9090
    name: metrics
  type: ClusterIP
```

#### Horizontal Pod Autoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: deeplake-api-hpa
  namespace: deeplake-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: deeplake-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

#### Ingress Configuration

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: deeplake-api-ingress
  namespace: deeplake-prod
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    nginx.ingress.kubernetes.io/rate-limit: "1000"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    external-dns.alpha.kubernetes.io/hostname: "api.yourcompany.com"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.yourcompany.com
    secretName: deeplake-api-tls
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

## 🐳 Docker Production Configuration

### Optimized Dockerfile

```dockerfile
# Multi-stage production Dockerfile
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
WORKDIR /app
COPY . .

# Set ownership and permissions
RUN chown -R appuser:appuser /app
RUN chmod -R 755 /app

# Create directories for data and logs
RUN mkdir -p /data /app/logs && \
    chown -R appuser:appuser /data /app/logs

# Switch to non-root user
USER appuser

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Docker Compose for Production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  deeplake-api:
    image: your-registry/deeplake-api:v1.0.0
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 4G
          cpus: '2'
        reservations:
          memory: 1G
          cpus: '0.5'
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
        order: start-first
    environment:
      - ENVIRONMENT=production
      - WORKERS=4
      - LOG_LEVEL=INFO
      - REDIS_URL=redis://redis-cluster:6379
      - DEEPLAKE_TOKEN=${DEEPLAKE_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis-cluster
    networks:
      - deeplake-network
    volumes:
      - deeplake-data:/data
      - deeplake-logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis-cluster:
    image: redis:7-alpine
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: '1'
        reservations:
          memory: 512M
          cpus: '0.25'
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    networks:
      - deeplake-network
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - deeplake-api
    networks:
      - deeplake-network
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    networks:
      - deeplake-network
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_SECURITY_ADMIN_USER=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    networks:
      - deeplake-network
    restart: unless-stopped

networks:
  deeplake-network:
    driver: overlay
    attachable: true

volumes:
  deeplake-data:
    driver: local
  deeplake-logs:
    driver: local
  redis-data:
    driver: local
  prometheus-data:
    driver: local
  grafana-data:
    driver: local
```

## 🔒 Security Configuration

### SSL/TLS Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream deeplake-api {
        server deeplake-api:8000;
        keepalive 32;
    }

    server {
        listen 80;
        server_name api.yourcompany.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name api.yourcompany.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # Rate limiting
        limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
        limit_req zone=api burst=200 nodelay;

        # Proxy configuration
        location / {
            proxy_pass http://deeplake-api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Connection "";
            proxy_http_version 1.1;
            proxy_buffering off;
            proxy_read_timeout 300s;
            proxy_send_timeout 300s;
        }

        # Health check endpoint
        location /health {
            access_log off;
            proxy_pass http://deeplake-api/api/v1/health;
        }
    }
}
```

### Security Policy

```yaml
# security-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deeplake-api-network-policy
  namespace: deeplake-prod
spec:
  podSelector:
    matchLabels:
      app: deeplake-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: deeplake-prod
    ports:
    - protocol: TCP
      port: 6379
  - to: []
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
    - protocol: UDP
      port: 53

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: deeplake-api
  namespace: deeplake-prod
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT-ID:role/deeplake-api-role

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deeplake-api-role
  namespace: deeplake-prod
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: deeplake-api-binding
  namespace: deeplake-prod
subjects:
- kind: ServiceAccount
  name: deeplake-api
  namespace: deeplake-prod
roleRef:
  kind: Role
  name: deeplake-api-role
  apiGroup: rbac.authorization.k8s.io
```

## 📊 Monitoring and Logging

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'deeplake-api'
    static_configs:
      - targets: ['deeplake-api:9090']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-cluster:6379']
    metrics_path: '/metrics'

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboards

```yaml
# grafana-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: deeplake-dashboard
  namespace: monitoring
data:
  dashboard.json: |
    {
      "dashboard": {
        "title": "Tributary AI Service for DeepLake Dashboard",
        "panels": [
          {
            "title": "Request Rate",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(http_requests_total[5m])",
                "legendFormat": "{{method}} {{endpoint}}"
              }
            ]
          },
          {
            "title": "Response Time",
            "type": "graph",
            "targets": [
              {
                "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                "legendFormat": "95th percentile"
              }
            ]
          },
          {
            "title": "Error Rate",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
                "legendFormat": "5xx errors"
              }
            ]
          }
        ]
      }
    }
```

## 🚀 CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/production.yml
name: Production Deployment

on:
  push:
    branches: [main]
    tags: ['v*']

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        python -m pytest tests/ -v --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Run security scan
      uses: securecodewarrior/github-action-add-sarif@v1
      with:
        sarif-file: security-scan.sarif

  build-and-push:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    outputs:
      image: ${{ steps.image.outputs.image }}
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
    
    - name: Output image
      id: image
      run: echo "image=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}" >> $GITHUB_OUTPUT

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    environment: production
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'v1.28.0'
    
    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig
    
    - name: Deploy to production
      run: |
        export KUBECONFIG=kubeconfig
        sed -i 's|IMAGE_PLACEHOLDER|${{ needs.build-and-push.outputs.image }}|g' k8s/production/deployment.yaml
        kubectl apply -f k8s/production/
    
    - name: Verify deployment
      run: |
        export KUBECONFIG=kubeconfig
        kubectl rollout status deployment/deeplake-api -n deeplake-prod --timeout=300s
```

### ArgoCD Configuration

```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: deeplake-api-prod
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/Tributary-ai-services/deeplake-api
    targetRevision: HEAD
    path: k8s/production
  destination:
    server: https://kubernetes.default.svc
    namespace: deeplake-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

## 📈 Performance Optimization

### Database Optimization

```python
# Production database configuration
DATABASE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "connect_args": {
        "connect_timeout": 10,
        "read_timeout": 30,
        "write_timeout": 30
    }
}

# Connection pooling
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    **DATABASE_CONFIG
)
```

### Caching Strategy

```python
# Production caching configuration
CACHE_CONFIG = {
    "default_ttl": 3600,
    "query_cache_ttl": 1800,
    "metadata_cache_ttl": 7200,
    "max_connections": 100,
    "retry_on_timeout": True,
    "socket_keepalive": True,
    "socket_keepalive_options": {
        "TCP_KEEPINTVL": 1,
        "TCP_KEEPCNT": 3,
        "TCP_KEEPIDLE": 1,
    }
}
```

### Load Testing

```python
# load_test.py
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

async def load_test():
    """Load test the production API"""
    url = "https://api.yourcompany.com/api/v1/datasets"
    headers = {"Authorization": "ApiKey your-api-key"}
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        tasks = []
        
        # Create 1000 concurrent requests
        for _ in range(1000):
            task = session.get(url, headers=headers)
            tasks.append(task)
        
        # Execute all requests
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate results
        duration = time.time() - start_time
        successful_requests = sum(1 for r in responses if hasattr(r, 'status') and r.status == 200)
        
        print(f"Duration: {duration:.2f}s")
        print(f"Successful requests: {successful_requests}/1000")
        print(f"RPS: {successful_requests/duration:.2f}")

asyncio.run(load_test())
```

## 🔄 Backup and Disaster Recovery

### Automated Backup

```yaml
# backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: deeplake-backup
  namespace: deeplake-prod
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: your-registry/deeplake-api:v1.0.0
            command:
            - python
            - scripts/disaster_recovery.py
            - create
            - --type
            - full
            env:
            - name: BACKUP_ENABLED
              value: "true"
            - name: BACKUP_S3_BUCKET
              value: "deeplake-prod-backups"
            envFrom:
            - secretRef:
                name: deeplake-secrets
            resources:
              requests:
                memory: "1Gi"
                cpu: "500m"
              limits:
                memory: "2Gi"
                cpu: "1000m"
          restartPolicy: OnFailure
```

### Disaster Recovery Plan

```bash
#!/bin/bash
# disaster_recovery.sh

# Production disaster recovery script
set -e

BACKUP_ID=$1
TARGET_CLUSTER=$2

if [ -z "$BACKUP_ID" ] || [ -z "$TARGET_CLUSTER" ]; then
    echo "Usage: $0 <backup_id> <target_cluster>"
    exit 1
fi

echo "Starting disaster recovery..."
echo "Backup ID: $BACKUP_ID"
echo "Target cluster: $TARGET_CLUSTER"

# 1. Set up kubectl context
kubectl config use-context $TARGET_CLUSTER

# 2. Create namespace if not exists
kubectl create namespace deeplake-prod --dry-run=client -o yaml | kubectl apply -f -

# 3. Apply secrets and configmaps
kubectl apply -f k8s/production/secrets/
kubectl apply -f k8s/production/configmaps/

# 4. Deploy Redis first
kubectl apply -f k8s/production/redis/
kubectl wait --for=condition=ready pod -l app=redis-cluster --timeout=300s

# 5. Restore from backup
kubectl run backup-restore \
  --image=your-registry/deeplake-api:v1.0.0 \
  --rm -it --restart=Never \
  -- python scripts/disaster_recovery.py restore $BACKUP_ID

# 6. Deploy API
kubectl apply -f k8s/production/api/
kubectl wait --for=condition=ready pod -l app=deeplake-api --timeout=300s

# 7. Verify deployment
kubectl get pods -n deeplake-prod
kubectl get services -n deeplake-prod

echo "Disaster recovery completed successfully!"
```

## 🔗 Related Documentation

- [Kubernetes Deployment](./kubernetes.md)
- [Docker Deployment](./docker.md)
- [Security Guide](../security.md)
- [Monitoring Guide](../monitoring.md)
- [Backup Guide](../disaster_recovery.md)

## 📞 Production Support

### Support Contacts

- **Production Issues**: [production@yourcompany.com](mailto:production@yourcompany.com)
- **Security Issues**: [security@yourcompany.com](mailto:security@yourcompany.com)
- **On-call Engineer**: [oncall@yourcompany.com](mailto:oncall@yourcompany.com)
- **Escalation**: [escalation@yourcompany.com](mailto:escalation@yourcompany.com)

### Emergency Procedures

1. **Service Outage**: Contact on-call engineer immediately
2. **Security Incident**: Follow security incident response plan
3. **Data Loss**: Initiate disaster recovery procedures
4. **Performance Issues**: Check monitoring dashboards and scale if needed

### Production Checklist

Before deploying to production:

- [ ] All tests pass
- [ ] Security scan completed
- [ ] Performance testing completed
- [ ] Backup and recovery tested
- [ ] Monitoring configured
- [ ] Documentation updated
- [ ] Incident response plan reviewed
- [ ] Rollback plan prepared