# DeepLake API Monitoring with Grafana

This directory contains comprehensive Grafana dashboards and configuration for monitoring the DeepLake API service.

## Dashboard Overview

### 1. Service Overview (`service-overview.json`)
- **Purpose**: High-level service health and performance metrics
- **Key Metrics**:
  - Request rate (HTTP/gRPC)
  - Request duration percentiles (p50, p95, p99)
  - Error rates by type and operation
  - Active connections
  - Memory usage by component
  - Cache hit ratio

### 2. Vector Operations (`vector-operations.json`)
- **Purpose**: Monitor vector storage and manipulation operations
- **Key Metrics**:
  - Total vectors and datasets
  - Vector insertion rate and duration
  - Vector batch size distribution
  - Storage size by dataset
  - Dataset operations by type

### 3. Search Performance (`search-performance.json`)
- **Purpose**: Monitor search query performance and efficiency
- **Key Metrics**:
  - Search query rate by type
  - Search duration percentiles
  - Results returned per search
  - Vectors scanned per search
  - Search efficiency metrics
  - Search type distribution

### 4. Tenant Analytics (`tenant-analytics.json`)
- **Purpose**: Multi-tenant usage patterns and resource consumption
- **Key Metrics**:
  - HTTP request rate by tenant
  - Datasets and vectors per tenant
  - Storage usage by tenant
  - Search activity by tenant
  - Error rates by tenant

### 5. Cache & Error Monitoring (`cache-and-errors.json`)
- **Purpose**: Monitor caching performance and error patterns
- **Key Metrics**:
  - Cache hit ratio and operation rates
  - Error rates by type and operation
  - Top error types
  - Overall error rate percentages
  - Error distribution by tenant

## Setup Instructions

### 1. Using Docker Compose (Recommended)

The monitoring stack is already configured in `docker-compose.yml`:

```bash
# Start all services including Grafana and Prometheus
docker-compose up -d

# Access Grafana at http://localhost:3000
# Default credentials: admin/admin
```

### 2. Manual Setup

If you prefer to set up Grafana manually:

1. **Install Grafana**:
   ```bash
   # Using Docker
   docker run -d --name grafana -p 3000:3000 grafana/grafana:latest
   
   # Using package manager (Ubuntu/Debian)
   sudo apt-get install -y software-properties-common
   sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
   sudo apt-get update
   sudo apt-get install grafana
   ```

2. **Configure Prometheus Data Source**:
   - URL: `http://prometheus:9090` (if using docker-compose) or `http://localhost:9090`
   - Access: Server (default)
   - HTTP Method: GET

3. **Import Dashboards**:
   - Copy JSON files from `dashboards/` directory
   - Import each dashboard in Grafana UI

### 3. Kubernetes Deployment

For Kubernetes deployments, use the Helm charts in `../kubernetes/`:

```bash
# Deploy with monitoring enabled
helm install deeplake-api ./deployment/helm/ \
  --set monitoring.enabled=true \
  --set monitoring.grafana.enabled=true
```

## Dashboard Usage

### Filtering and Variables

Most dashboards include template variables for filtering:

- **Tenant**: Filter by tenant ID (multi-select)
- **Dataset**: Filter by dataset ID
- **Search Type**: Filter by search type (vector, text, hybrid)
- **Error Type**: Filter by error type

### Time Range

- Default: Last 1 hour
- Recommended for production: Last 24 hours
- Auto-refresh: 5 seconds (configurable)

### Key Metrics to Monitor

#### Service Health
- Request rate should be steady without sudden spikes
- P95 latency should be under acceptable thresholds
- Error rate should be minimal (<1%)

#### Vector Operations
- Vector insertion rate indicates usage patterns
- Storage growth should be monitored for capacity planning
- Batch size distribution helps optimize ingestion

#### Search Performance
- Search latency should be consistent
- High vectors scanned vs. results returned may indicate inefficient queries
- Search efficiency helps identify optimization opportunities

#### Tenant Usage
- Monitor tenant resource consumption
- Identify heavy users and usage patterns
- Track tenant-specific error rates

#### Cache Performance
- Cache hit ratio should be >70% for optimal performance
- Monitor cache operations for bottlenecks
- Track cache effectiveness over time

## Alerting

### Recommended Alerts

Create alerts for:

1. **High Error Rate**: `sum(rate(deeplake_errors_total[5m])) / sum(rate(deeplake_http_requests_total[5m])) > 0.05`
2. **High Latency**: `histogram_quantile(0.95, rate(deeplake_http_request_duration_seconds_bucket[5m])) > 2.0`
3. **Low Cache Hit Rate**: `deeplake_cache_hit_ratio < 0.5`
4. **Storage Growth**: `increase(deeplake_storage_size_bytes[1h]) > 1073741824` (1GB/hour)

### Alert Channels

Configure notification channels:
- Slack/Teams for team notifications
- Email for critical alerts
- PagerDuty for production incidents

## Customization

### Adding New Panels

1. Use existing queries as templates
2. Follow naming conventions: `deeplake_*`
3. Include appropriate labels for filtering
4. Use consistent time ranges and refresh rates

### Modifying Dashboards

1. Edit JSON files directly or use Grafana UI
2. Export updated dashboards to maintain version control
3. Test changes in development environment first

### Adding New Metrics

1. Add metrics to `MetricsService` in the application
2. Update Prometheus scraping if needed
3. Create corresponding dashboard panels
4. Document new metrics in this README

## Troubleshooting

### Common Issues

1. **No Data in Dashboards**:
   - Check Prometheus is scraping metrics endpoint
   - Verify service is running and exposing metrics
   - Check network connectivity between services

2. **High Memory Usage**:
   - Increase Prometheus retention settings
   - Optimize query performance
   - Consider using recording rules

3. **Dashboard Loading Slowly**:
   - Reduce time range
   - Optimize queries
   - Use recording rules for complex calculations

### Logs and Debugging

- Grafana logs: `docker logs grafana`
- Prometheus logs: `docker logs prometheus`
- Service metrics endpoint: `http://localhost:8000/api/v1/metrics/prometheus`

## Performance Optimization

### Query Optimization

- Use appropriate time ranges
- Leverage recording rules for complex calculations
- Use `rate()` for counters, `histogram_quantile()` for histograms

### Resource Management

- Monitor Grafana memory usage
- Set appropriate retention policies
- Use dashboard variables to reduce query load

## Maintenance

### Regular Tasks

1. **Monthly**:
   - Review dashboard performance
   - Update alert thresholds based on usage patterns
   - Archive old data if needed

2. **Quarterly**:
   - Review metric collection requirements
   - Optimize queries and dashboards
   - Update documentation

3. **Annually**:
   - Review monitoring strategy
   - Evaluate new Grafana features
   - Update alerting rules

### Backup and Recovery

- Backup Grafana dashboards: Export as JSON
- Backup Prometheus data: Use snapshots
- Document restoration procedures

## Support

For issues with monitoring setup:
1. Check this README for common solutions
2. Review application logs for metric collection issues
3. Consult Grafana documentation for dashboard issues
4. Contact the development team for metric-specific questions