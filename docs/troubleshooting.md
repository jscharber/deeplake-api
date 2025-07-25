# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Tributary AI Service for DeepLake.

## 🔍 Quick Diagnosis

### Service Health Check

First, check if the service is running:

```bash
# Check service health
curl http://localhost:8000/api/v1/health

# Expected response
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

### Check Logs

```bash
# Docker logs
docker logs deeplake-api

# Kubernetes logs
kubectl logs -f deployment/deeplake-api -n deeplake

# Local logs
tail -f logs/app.log
```

### Check Resource Usage

```bash
# Docker stats
docker stats deeplake-api

# Kubernetes resource usage
kubectl top pods -n deeplake

# System resources
htop
```

## 🚨 Common Issues

### 1. Service Won't Start

#### Symptoms
- Health check returns connection refused
- Container/pod keeps restarting
- Port binding errors

#### Possible Causes & Solutions

**Port Already in Use**
```bash
# Check what's using port 8000
lsof -i :8000
netstat -tulpn | grep 8000

# Kill process using port
kill -9 <PID>

# Or use different port
export PORT=8001
```

**Missing Environment Variables**
```bash
# Check environment variables
printenv | grep -E "(DEEPLAKE|REDIS|OPENAI)"

# Set required variables
export DEEPLAKE_TOKEN=your-token
export REDIS_URL=redis://localhost:6379
export OPENAI_API_KEY=your-key
```

**Permission Issues**
```bash
# Fix file permissions
chmod +x app/main.py
chown -R $(whoami) .

# Docker permission issues
docker run --user $(id -u):$(id -g) ...
```

### 2. Redis Connection Issues

#### Symptoms
- "Connection refused" errors
- Cache-related failures
- Session issues

#### Solutions

**Check Redis Status**
```bash
# Test Redis connection
redis-cli ping
# Expected: PONG

# Check Redis logs
docker logs redis
kubectl logs redis-0
```

**Redis Authentication**
```bash
# If Redis requires password
redis-cli -a your-password ping

# Update connection string
export REDIS_URL=redis://:password@localhost:6379
```

**Redis Memory Issues**
```bash
# Check Redis memory
redis-cli info memory

# Clear Redis cache
redis-cli flushall
```

### 3. DeepLake Connection Issues

#### Symptoms
- "Authentication failed" errors
- "Dataset not found" errors
- Slow vector operations

#### Solutions

**Check DeepLake Token**
```python
# Test token validity
import deeplake

try:
    ds = deeplake.empty("hub://tributary-ai-services/test-dataset")
    print("Token valid")
except Exception as e:
    print(f"Token invalid: {e}")
```

**Check DeepLake Status**
```bash
# Check DeepLake service status
curl -s https://status.activeloop.ai/

# Test connection
python -c "
import deeplake
print('DeepLake version:', deeplake.__version__)
try:
    deeplake.exists('hub://tributary-ai-services/test')
    print('Connection successful')
except Exception as e:
    print('Connection failed:', e)
"
```

### 4. API Response Issues

#### Symptoms
- Slow response times
- 500 Internal Server Error
- Timeout errors

#### Solutions

**Check API Performance**
```bash
# Test API response time
time curl -X GET "http://localhost:8000/api/v1/health"

# Load test
ab -n 100 -c 10 http://localhost:8000/api/v1/health
```

**Check Resource Limits**
```bash
# Check memory usage
free -h
docker stats

# Check CPU usage
top
htop
```

**Increase Resources**
```yaml
# Docker Compose
services:
  deeplake-api:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'
        reservations:
          memory: 2G
          cpus: '1'
```

### 5. Search/Vector Issues

#### Symptoms
- "Vector dimension mismatch" errors
- Slow search queries
- Inconsistent results

#### Solutions

**Check Vector Dimensions**
```python
# Verify vector dimensions
import numpy as np

vector = np.random.rand(1536)  # Ensure correct dimension
print(f"Vector shape: {vector.shape}")
print(f"Vector type: {type(vector)}")
```

**Check Dataset Configuration**
```bash
# Get dataset info
curl -X GET "http://localhost:8000/api/v1/datasets/my-dataset" \
  -H "Authorization: ApiKey your-api-key"
```

**Optimize Search Parameters**
```python
# Optimize search parameters
search_params = {
    "query_vector": vector.tolist(),
    "k": 10,  # Don't request too many results
    "distance_metric": "cosine",
    "filter": {"category": "specific"}  # Use specific filters
}
```

### 6. Rate Limiting Issues

#### Symptoms
- 429 Too Many Requests errors
- Requests being blocked
- Slow API responses

#### Solutions

**Check Rate Limit Status**
```bash
# Check current usage
curl -X GET "http://localhost:8000/api/v1/rate-limits/usage" \
  -H "Authorization: ApiKey your-api-key"
```

**Implement Exponential Backoff**
```python
import asyncio
import random

async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            
            # Wait with exponential backoff
            wait_time = min(2 ** attempt + random.uniform(0, 1), 60)
            await asyncio.sleep(wait_time)
```

### 7. Authentication Issues

#### Symptoms
- 401 Unauthorized errors
- "Invalid API key" messages
- Permission denied errors

#### Solutions

**Check API Key Format**
```bash
# Correct format
curl -H "Authorization: ApiKey your-api-key-here" \
     http://localhost:8000/api/v1/datasets

# Alternative formats
curl -H "Authorization: Bearer your-jwt-token" \
     http://localhost:8000/api/v1/datasets
```

**Verify API Key**
```python
# Test API key
import requests

headers = {"Authorization": "ApiKey your-api-key"}
response = requests.get("http://localhost:8000/api/v1/health", headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

### 8. Database/Storage Issues

#### Symptoms
- "Storage unavailable" errors
- Data corruption
- Slow queries

#### Solutions

**Check Storage Space**
```bash
# Check disk space
df -h

# Check DeepLake storage
du -sh ~/.deeplake/

# Clean up old data
rm -rf ~/.deeplake/cache/*
```

**Check Database Connections**
```bash
# Check active connections
netstat -an | grep :5432

# Test database connection
psql -h localhost -U postgres -c "SELECT 1"
```

## 🔧 Debug Mode

### Enable Debug Logging

```bash
# Environment variable
export LOG_LEVEL=DEBUG

# Docker
docker run -e LOG_LEVEL=DEBUG deeplake-api

# Kubernetes
kubectl set env deployment/deeplake-api LOG_LEVEL=DEBUG
```

### Debug Configuration

```python
# Debug configuration
DEBUG_CONFIG = {
    "log_level": "DEBUG",
    "log_format": "detailed",
    "enable_profiling": True,
    "slow_query_threshold": 1.0,
    "debug_headers": True
}
```

### Performance Profiling

```python
# Profile slow functions
import cProfile
import pstats

def profile_function(func):
    """Profile a function"""
    pr = cProfile.Profile()
    pr.enable()
    
    result = func()
    
    pr.disable()
    stats = pstats.Stats(pr)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
    
    return result
```

## 📊 Monitoring and Alerting

### Key Metrics to Monitor

**Service Metrics**
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Memory usage
process_resident_memory_bytes
```

**Business Metrics**
```promql
# Vector operations
rate(vector_operations_total[5m])

# Search queries
rate(search_queries_total[5m])

# Dataset operations
rate(dataset_operations_total[5m])
```

### Alert Rules

```yaml
# alerts.yml
groups:
- name: deeplake-api
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} requests per second"

  - alert: HighMemoryUsage
    expr: process_resident_memory_bytes > 2e9
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is {{ $value | humanize }}B"

  - alert: SlowResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Slow response time"
      description: "95th percentile response time is {{ $value }}s"
```

## 🛠️ Diagnostic Tools

### Health Check Script

```python
#!/usr/bin/env python3
"""
Comprehensive health check script
"""

import asyncio
import aiohttp
import time
import psutil
import redis
import deeplake

async def health_check():
    """Run comprehensive health check"""
    checks = {
        "api": False,
        "redis": False,
        "deeplake": False,
        "disk_space": False,
        "memory": False,
        "cpu": False
    }
    
    # Check API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/v1/health") as response:
                if response.status == 200:
                    checks["api"] = True
    except Exception as e:
        print(f"API check failed: {e}")
    
    # Check Redis
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        if r.ping():
            checks["redis"] = True
    except Exception as e:
        print(f"Redis check failed: {e}")
    
    # Check DeepLake
    try:
        deeplake.exists("hub://test/test")
        checks["deeplake"] = True
    except Exception as e:
        print(f"DeepLake check failed: {e}")
    
    # Check disk space
    disk_usage = psutil.disk_usage('/')
    if disk_usage.free > 1e9:  # 1GB free
        checks["disk_space"] = True
    
    # Check memory
    memory = psutil.virtual_memory()
    if memory.percent < 90:
        checks["memory"] = True
    
    # Check CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent < 90:
        checks["cpu"] = True
    
    # Print results
    print("Health Check Results:")
    print("=" * 30)
    for check, status in checks.items():
        status_str = "✅ PASS" if status else "❌ FAIL"
        print(f"{check:<15} {status_str}")
    
    # Overall status
    overall = all(checks.values())
    print(f"\nOverall: {'✅ HEALTHY' if overall else '❌ UNHEALTHY'}")
    
    return overall

if __name__ == "__main__":
    asyncio.run(health_check())
```

### Log Analysis Script

```python
#!/usr/bin/env python3
"""
Log analysis script
"""

import re
import json
from collections import defaultdict, Counter
from datetime import datetime

def analyze_logs(log_file):
    """Analyze log file for patterns"""
    errors = []
    response_times = []
    endpoints = Counter()
    status_codes = Counter()
    
    with open(log_file, 'r') as f:
        for line in f:
            try:
                # Parse structured log
                log_entry = json.loads(line)
                
                # Extract metrics
                if 'response_time' in log_entry:
                    response_times.append(log_entry['response_time'])
                
                if 'endpoint' in log_entry:
                    endpoints[log_entry['endpoint']] += 1
                
                if 'status_code' in log_entry:
                    status_codes[log_entry['status_code']] += 1
                
                # Collect errors
                if log_entry.get('level') == 'ERROR':
                    errors.append(log_entry)
                    
            except json.JSONDecodeError:
                # Parse text log
                if 'ERROR' in line:
                    errors.append(line.strip())
    
    # Analysis results
    print("Log Analysis Results:")
    print("=" * 30)
    print(f"Total errors: {len(errors)}")
    print(f"Average response time: {sum(response_times)/len(response_times):.3f}s")
    print(f"Top endpoints: {endpoints.most_common(5)}")
    print(f"Status codes: {dict(status_codes)}")
    
    # Show recent errors
    print("\nRecent Errors:")
    for error in errors[-10:]:
        print(f"  {error}")

if __name__ == "__main__":
    import sys
    log_file = sys.argv[1] if len(sys.argv) > 1 else "logs/app.log"
    analyze_logs(log_file)
```

## 🔄 Recovery Procedures

### Service Recovery

```bash
#!/bin/bash
# service_recovery.sh

echo "Starting service recovery..."

# 1. Stop service
echo "Stopping service..."
docker stop deeplake-api || true
kubectl delete deployment deeplake-api || true

# 2. Clear cache
echo "Clearing cache..."
redis-cli flushall

# 3. Clean up old data
echo "Cleaning up..."
rm -rf /tmp/deeplake-*
docker system prune -f

# 4. Restart dependencies
echo "Restarting dependencies..."
docker restart redis
kubectl rollout restart deployment/redis

# 5. Wait for dependencies
echo "Waiting for dependencies..."
sleep 30

# 6. Start service
echo "Starting service..."
docker start deeplake-api
kubectl apply -f k8s/deployment.yaml

# 7. Wait for service
echo "Waiting for service..."
sleep 60

# 8. Verify service
echo "Verifying service..."
curl -f http://localhost:8000/api/v1/health || {
    echo "Service failed to start"
    exit 1
}

echo "Service recovery completed successfully!"
```

### Database Recovery

```python
#!/usr/bin/env python3
"""
Database recovery script
"""

import asyncio
import deeplake
from app.services.backup_service import BackupService

async def database_recovery():
    """Recover database from backup"""
    backup_service = BackupService()
    
    # List available backups
    backups = await backup_service.list_backups()
    print(f"Available backups: {len(backups)}")
    
    # Find latest backup
    latest_backup = max(backups, key=lambda b: b.timestamp)
    print(f"Latest backup: {latest_backup.backup_id}")
    
    # Restore from backup
    print("Starting restore...")
    success = await backup_service.restore_backup(latest_backup.backup_id)
    
    if success:
        print("Database recovery completed successfully!")
    else:
        print("Database recovery failed!")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(database_recovery())
```

## 📞 Getting Help

### Self-Service Resources

1. **Documentation**: [docs.yourcompany.com](https://docs.yourcompany.com)
2. **FAQ**: [faq.yourcompany.com](https://faq.yourcompany.com)
3. **Community Forum**: [community.yourcompany.com](https://community.yourcompany.com)
4. **GitHub Issues**: [github.com/Tributary-ai-services/deeplake-api/issues](https://github.com/Tributary-ai-services/deeplake-api/issues)

### Support Channels

1. **Technical Support**: [support@yourcompany.com](mailto:support@yourcompany.com)
2. **Emergency Support**: [emergency@yourcompany.com](mailto:emergency@yourcompany.com)
3. **Slack Channel**: #deeplake-api-support
4. **Phone Support**: +1-800-SUPPORT

### Information to Include

When reporting issues, include:

- **Error messages**: Complete error messages and stack traces
- **Environment**: OS, Python version, Docker version
- **Configuration**: Relevant configuration (sanitized)
- **Steps to reproduce**: Exact steps to reproduce the issue
- **Expected vs actual**: What you expected vs what happened
- **Logs**: Relevant log entries
- **Version**: API version and commit hash

### Support Ticket Template

```
**Problem Summary:**
Brief description of the issue

**Environment:**
- OS: Ubuntu 20.04
- Python: 3.11.5
- Docker: 20.10.23
- API Version: v1.0.0

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. Step 3

**Expected Result:**
What should happen

**Actual Result:**
What actually happened

**Error Messages:**
```
[Paste error messages here]
```

**Logs:**
```
[Paste relevant log entries here]
```

**Additional Context:**
Any other relevant information
```

## 🔗 Related Documentation

- [API Reference](./api/http/README.md)
- [Configuration Guide](./configuration.md)
- [Monitoring Guide](./monitoring.md)
- [Performance Guide](./performance.md)
- [Security Guide](./security.md)

## 📚 Advanced Troubleshooting

For advanced troubleshooting scenarios:

- [Network Troubleshooting](./troubleshooting/network.md)
- [Performance Troubleshooting](./troubleshooting/performance.md)
- [Security Troubleshooting](./troubleshooting/security.md)
- [Database Troubleshooting](./troubleshooting/database.md)