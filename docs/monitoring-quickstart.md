# Monitoring Quick Start Guide

This guide provides the fastest way to get Prometheus and Grafana running with the Tributary AI Service for DeepLake.

## 🚀 Quick Setup with Docker Compose

### 1. Create docker-compose.monitoring.yml

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    networks:
      - deeplake-network

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    networks:
      - deeplake-network

  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    networks:
      - deeplake-network

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    ports:
      - "9100:9100"
    networks:
      - deeplake-network

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:

networks:
  deeplake-network:
    external: true
```

### 2. Create Monitoring Configuration

```bash
# Create directory structure
mkdir -p monitoring/grafana/provisioning/{dashboards,datasources}

# Create Prometheus configuration
cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'deeplake-api'
    static_configs:
      - targets: ['deeplake-api:9090']
    metrics_path: '/metrics'

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
EOF

# Create AlertManager configuration
cat > monitoring/alertmanager.yml << 'EOF'
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://127.0.0.1:5001/'
        send_resolved: true
EOF

# Create Grafana datasource
cat > monitoring/grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

# Create Grafana dashboard provisioning
cat > monitoring/grafana/provisioning/dashboards/dashboard.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /etc/grafana/provisioning/dashboards
EOF
```

### 3. Start Monitoring Stack

```bash
# Start all services
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Check services are running
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml ps

# View logs
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml logs -f
```

## 🔍 Quick Verification

### 1. Check Service Status

```bash
# Check all endpoints
curl -s http://localhost:8000/api/v1/health | jq .
curl -s http://localhost:9090/-/healthy
curl -s http://localhost:3000/api/health
curl -s http://localhost:9093/-/healthy
```

### 2. Access Web UIs

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **AlertManager**: http://localhost:9093
- **API Metrics**: http://localhost:8000/metrics

### 3. Quick Metrics Test

In Prometheus UI, run these queries:

```promql
# Check if API is being scraped
up{job="deeplake-api"}

# See all available metrics
{__name__=~"http_.*"}

# Check request rate
rate(http_requests_total[1m])
```

## 📊 Import Pre-built Dashboard

### 1. Download Dashboard

```bash
# Download the comprehensive dashboard
curl -o deeplake-dashboard.json \
  https://raw.githubusercontent.com/Tributary-ai-services/deeplake-api/main/monitoring/dashboards/overview.json
```

### 2. Import to Grafana

1. Login to Grafana (http://localhost:3000)
2. Click "+" → "Import"
3. Upload `deeplake-dashboard.json`
4. Select "Prometheus" as data source
5. Click "Import"

## 🚦 Generate Test Metrics

```bash
# Quick test to generate metrics
API_KEY="your-api-key"

# Create a test dataset
curl -X POST http://localhost:8000/api/v1/datasets \
  -H "Authorization: ApiKey $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "test-metrics",
    "name": "Test Metrics",
    "embedding_dimension": 128
  }'

# Generate some traffic
for i in {1..100}; do
  curl -s http://localhost:8000/api/v1/health > /dev/null
  sleep 0.1
done

# Check metrics in Prometheus
# Should see increased http_requests_total
```

## 🎯 Key Metrics to Monitor

### Essential Metrics

| Metric | Query | What it Shows |
|--------|-------|---------------|
| Request Rate | `rate(http_requests_total[5m])` | Requests per second |
| Error Rate | `rate(http_requests_total{status_code=~"5.."}[5m])` | Errors per second |
| Latency P95 | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` | 95th percentile response time |
| Active Datasets | `datasets_active_total` | Total number of datasets |
| Vector Operations | `rate(vector_operations_total[5m])` | Vector ops per second |

### Quick Grafana Panels

Create a new dashboard with these panels:

```json
{
  "panels": [
    {
      "title": "Request Rate",
      "targets": [{
        "expr": "sum(rate(http_requests_total[5m]))"
      }]
    },
    {
      "title": "Error Rate %",
      "targets": [{
        "expr": "sum(rate(http_requests_total{status_code=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m])) * 100"
      }]
    },
    {
      "title": "Response Time",
      "targets": [{
        "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))"
      }]
    }
  ]
}
```

## 🔧 Troubleshooting

### No Metrics Showing

```bash
# Check if API is exposing metrics
curl http://localhost:8000/metrics | grep http_requests_total

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job:.labels.job, health:.health}'

# Check API logs
docker logs deeplake-api | grep metrics
```

### Grafana Connection Issues

```bash
# Test Prometheus from Grafana container
docker exec grafana curl http://prometheus:9090/api/v1/query?query=up

# Check network connectivity
docker network inspect deeplake-network
```

## 📚 Next Steps

1. **Custom Alerts**: Add alert rules in `monitoring/alert_rules.yml`
2. **Custom Dashboards**: Create dashboards for your specific use cases
3. **External Storage**: Configure long-term metrics storage
4. **Security**: Add authentication to Prometheus and AlertManager

For detailed configuration and troubleshooting, see:
- [Monitoring Guide](./monitoring.md)
- [Monitoring Verification](./monitoring-verification.md)
- [Observability Strategy](./observability.md)