# DeepLake API Alerting System Setup

This document describes how to configure and deploy the comprehensive alerting system for the DeepLake API service.

## Overview

The alerting system consists of:
- **Prometheus**: Metrics collection and alert rule evaluation
- **Alertmanager**: Alert routing and notification delivery
- **Grafana**: Visualization and dashboards
- **Multiple notification channels**: Slack, PagerDuty, Email

## Components

### 1. Prometheus (Port 9090)
- Scrapes metrics from DeepLake API service
- Evaluates alert rules defined in `prometheus-alerts.yml`
- Sends alerts to Alertmanager

### 2. Alertmanager (Port 9093)
- Receives alerts from Prometheus
- Routes alerts based on severity and conditions
- Sends notifications to configured channels
- Handles alert grouping, inhibition, and silencing

### 3. Grafana (Port 3000)
- Visualizes metrics and alerts
- Provides dashboards for monitoring
- Admin interface for alert management

## Quick Start

### 1. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Required for DeepLake API
JWT_SECRET_KEY=your-secret-key-here
GRAFANA_PASSWORD=admin

# Optional - DeepLake Cloud
DEEPLAKE_TOKEN=your-deeplake-token
DEEPLAKE_ORG_ID=your-org-id

# Alerting Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
PAGERDUTY_INTEGRATION_KEY=your-pagerduty-integration-key
ALERT_EMAIL_TO=tas-deeplake@scharber.com
ALERT_EMAIL_FROM=tas-deeplake@scharber.com
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=tas-deeplake@scharber.com
SMTP_PASSWORD=your-smtp-password
```

### 2. Configure Notification Channels

Edit `deployment/alertmanager.yml` to configure your notification channels:

#### Slack Configuration
```yaml
slack_configs:
- api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
  channel: '#alerts-critical'
  title: 'DeepLake API Critical Alert'
  text: 'Alert: {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
  send_resolved: true
```

#### PagerDuty Configuration
```yaml
pagerduty_configs:
- routing_key: 'YOUR_PAGERDUTY_INTEGRATION_KEY'
  description: 'DeepLake API Critical Alert: {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
  severity: 'critical'
```

#### Email Configuration
```yaml
email_configs:
- to: 'tas-deeplake@scharber.com'
  subject: 'DeepLake API Critical Alert'
  body: |
    Alert Details:
    {{ range .Alerts }}
    - Alert: {{ .Annotations.summary }}
    - Description: {{ .Annotations.description }}
    - Severity: {{ .Labels.severity }}
    - Instance: {{ .Labels.instance }}
    {{ end }}
```

### 3. Deploy the Stack

```bash
# Start all services including alerting
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f alertmanager
docker-compose logs -f prometheus
```

### 4. Verify Setup

1. **Prometheus**: Visit http://localhost:9090
   - Check Status > Targets to ensure all targets are up
   - Check Alerts to see configured rules

2. **Alertmanager**: Visit http://localhost:9093
   - Check Status to verify configuration
   - View active alerts

3. **Grafana**: Visit http://localhost:3000
   - Login with admin/admin (or your configured password)
   - Import dashboards from `deployment/grafana/dashboards/`

## Alert Rules

The system includes comprehensive alert rules covering:

### Service Health
- **DeepLakeAPIDown**: Service unavailable
- **RedisCacheDown**: Cache service unavailable
- **HighErrorRate**: >5% error rate (warning), >10% (critical)

### Performance
- **HighLatency**: >2s 95th percentile (warning), >5s (critical)
- **SlowSearchQueries**: >10s search time (warning), >30s (critical)
- **SlowVectorInsertion**: >5s insertion time

### Resource Usage
- **HighMemoryUsage**: >2GB (warning), >4GB (critical)
- **HighStorageGrowth**: >1GB/hour (warning), >5GB/hour (critical)
- **LowCacheHitRate**: <50% (warning), <20% (critical)

### Data Operations
- **NoVectorInsertion**: No activity for 2 hours
- **TooManyVectors**: >10M vectors per dataset
- **LargeDatasetSize**: >10GB per dataset

### Tenant-Specific
- **HighTenantErrorRate**: >10% error rate per tenant
- **HighTenantLatency**: >3s 95th percentile per tenant

## Notification Routing

Alerts are routed based on severity:

### Critical Alerts
- **Channels**: Slack (#alerts-critical), PagerDuty, Email (oncall)
- **Repeat Interval**: 5 minutes for service down alerts
- **Examples**: DeepLakeAPIDown, RedisCacheDown, VeryHighErrorRate

### Warning Alerts
- **Channels**: Slack (#alerts-warning), Email (team)
- **Repeat Interval**: 1 hour
- **Examples**: HighLatency, LowCacheHitRate, SlowSearchQueries

### Alert Grouping
- Alerts are grouped by `alertname`
- Group wait: 10 seconds
- Group interval: 10 seconds

## Customization

### Adding New Alert Rules

1. Edit `deployment/prometheus-alerts.yml`
2. Add your alert rule following the existing pattern:

```yaml
- alert: YourAlertName
  expr: your_metric_expression > threshold
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Alert description"
    description: "Detailed description with {{ $value }}"
```

3. Restart Prometheus: `docker-compose restart prometheus`

### Adding New Notification Channels

1. Edit `deployment/alertmanager.yml`
2. Add receiver configuration
3. Add routing rule
4. Restart Alertmanager: `docker-compose restart alertmanager`

### Customizing Alert Thresholds

Edit the expressions in `deployment/prometheus-alerts.yml`:

```yaml
# Change error rate threshold from 5% to 3%
- alert: HighErrorRate
  expr: (sum(rate(deeplake_errors_total[5m])) / sum(rate(deeplake_http_requests_total[5m]))) * 100 > 3
```

## Testing Alerts

### 1. Test Alert Rules
```bash
# Access Prometheus UI
curl http://localhost:9090/alerts

# Force alert evaluation
curl -X POST http://localhost:9090/-/reload
```

### 2. Test Notifications
```bash
# Send test alert to Alertmanager
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning"
    },
    "annotations": {
      "summary": "Test alert",
      "description": "This is a test alert"
    }
  }]'
```

### 3. Simulate Service Issues
```bash
# Stop DeepLake service to trigger alerts
docker-compose stop deeplake-service

# Check alert status
curl http://localhost:9090/api/v1/alerts
```

## Monitoring Best Practices

### 1. Alert Fatigue Prevention
- Use appropriate thresholds to avoid false positives
- Implement alert grouping and inhibition rules
- Set reasonable repeat intervals

### 2. Runbook Integration
- Include runbook links in alert descriptions
- Document common troubleshooting steps
- Maintain escalation procedures

### 3. Regular Maintenance
- Review and update alert thresholds based on performance data
- Clean up unused or ineffective alerts
- Test notification channels regularly

## Troubleshooting

### Common Issues

1. **Alerts not firing**
   - Check Prometheus targets: http://localhost:9090/targets
   - Verify alert rule syntax
   - Check metric names and labels

2. **Notifications not working**
   - Verify Alertmanager configuration
   - Check webhook URLs and API keys
   - Review Alertmanager logs: `docker-compose logs alertmanager`

3. **Missing metrics**
   - Ensure DeepLake API service is running
   - Check metrics endpoint: http://localhost:8000/api/v1/metrics/prometheus
   - Verify Prometheus scrape configuration

### Useful Commands

```bash
# Check alert manager status
curl http://localhost:9093/api/v1/status

# List active alerts
curl http://localhost:9093/api/v1/alerts

# Silence an alert
curl -X POST http://localhost:9093/api/v1/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [{"name": "alertname", "value": "HighErrorRate"}],
    "startsAt": "2024-01-01T00:00:00Z",
    "endsAt": "2024-01-01T01:00:00Z",
    "comment": "Maintenance window"
  }'

# Reload configurations
docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
docker-compose exec alertmanager amtool config check /etc/alertmanager/alertmanager.yml
```

## Production Deployment

### Security Considerations
1. Use proper authentication for Grafana
2. Secure Prometheus and Alertmanager endpoints
3. Use HTTPS for webhook URLs
4. Rotate API keys and passwords regularly

### Scalability
1. Use external storage for Prometheus (e.g., Thanos)
2. Implement high availability for Alertmanager
3. Use service discovery for dynamic environments

### Backup and Recovery
1. Backup Prometheus data and configuration
2. Backup Grafana dashboards and settings
3. Document recovery procedures

This comprehensive alerting system provides production-ready monitoring and notification capabilities for the DeepLake API service.