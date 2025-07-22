# Monitoring and Observability Guide

This guide covers comprehensive monitoring, observability, and alerting for the Tributary AI Service for DeepLake.

## 🎯 Overview

The Tributary AI Service for DeepLake implements a comprehensive observability stack with:
- **Metrics Collection**: Prometheus with custom business metrics
- **Distributed Tracing**: OpenTelemetry with Jaeger
- **Centralized Logging**: Structured logging with ELK stack
- **Dashboards**: Grafana with pre-built dashboards
- **Alerting**: Prometheus AlertManager with multiple channels
- **Health Checks**: Deep health monitoring
- **Performance Monitoring**: APM with detailed insights

## 📊 Metrics Architecture

### Core Metrics Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Metrics Collection                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Application  │   Custom      │   System      │   Business   │   External   │
│  Metrics      │   Metrics     │   Metrics     │   Metrics    │   Metrics    │
│               │               │               │              │              │
│  • Requests   │  • Search     │  • CPU        │  • Datasets  │  • DeepLake  │
│  • Latency    │  • Vectors    │  • Memory     │  • Tenants   │  • Redis     │
│  • Errors     │  • Cache      │  • Disk       │  • API Keys  │  • OpenAI    │
│  • Throughput │  • Indexing   │  • Network    │  • Usage     │  • S3        │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Prometheus (Metrics Storage)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Time-series database                                                    │
│  • PromQL query language                                                   │
│  • Service discovery                                                       │
│  • Scraping configuration                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Grafana (Visualization)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Pre-built dashboards                                                    │
│  • Custom visualizations                                                   │
│  • Alerting rules                                                          │
│  • Data source management                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"
  - "recording_rules.yml"

scrape_configs:
  - job_name: 'deeplake-api'
    static_configs:
      - targets: ['deeplake-api:9090']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    metrics_path: '/metrics'

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

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

### Custom Metrics Implementation

```python
# app/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Summary, Info
from typing import Dict, Optional
import time

class DeepLakeMetrics:
    """Comprehensive metrics for Tributary AI Service for DeepLake"""
    
    def __init__(self):
        # HTTP Metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code', 'tenant_id']
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint', 'tenant_id'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        # Business Metrics
        self.datasets_total = Gauge(
            'datasets_total',
            'Total number of datasets',
            ['tenant_id']
        )
        
        self.vectors_total = Gauge(
            'vectors_total',
            'Total number of vectors',
            ['dataset_id', 'tenant_id']
        )
        
        self.search_operations_total = Counter(
            'search_operations_total',
            'Total search operations',
            ['search_type', 'dataset_id', 'tenant_id']
        )
        
        self.search_latency = Histogram(
            'search_latency_seconds',
            'Search operation latency',
            ['search_type', 'dataset_id', 'tenant_id'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        # Vector Operations
        self.vector_operations_total = Counter(
            'vector_operations_total',
            'Total vector operations',
            ['operation', 'dataset_id', 'tenant_id']
        )
        
        self.vector_batch_size = Histogram(
            'vector_batch_size',
            'Vector batch operation size',
            ['operation', 'dataset_id', 'tenant_id'],
            buckets=[1, 10, 50, 100, 500, 1000, 5000]
        )
        
        # Cache Metrics
        self.cache_operations_total = Counter(
            'cache_operations_total',
            'Total cache operations',
            ['operation', 'cache_type', 'tenant_id']
        )
        
        self.cache_hit_ratio = Gauge(
            'cache_hit_ratio',
            'Cache hit ratio',
            ['cache_type', 'tenant_id']
        )
        
        # Rate Limiting
        self.rate_limit_hits_total = Counter(
            'rate_limit_hits_total',
            'Total rate limit hits',
            ['tenant_id', 'limit_type']
        )
        
        self.rate_limit_remaining = Gauge(
            'rate_limit_remaining',
            'Remaining rate limit capacity',
            ['tenant_id', 'limit_type']
        )
        
        # System Metrics
        self.active_connections = Gauge(
            'active_connections',
            'Active database connections'
        )
        
        self.memory_usage_bytes = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            ['memory_type']
        )
        
        # Error Metrics
        self.errors_total = Counter(
            'errors_total',
            'Total errors',
            ['error_type', 'error_code', 'tenant_id']
        )
        
        # Performance Metrics
        self.index_build_duration = Histogram(
            'index_build_duration_seconds',
            'Index build duration',
            ['index_type', 'dataset_id', 'tenant_id'],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800]
        )
        
        self.backup_duration = Histogram(
            'backup_duration_seconds',
            'Backup operation duration',
            ['backup_type', 'tenant_id'],
            buckets=[10, 30, 60, 300, 600, 1800, 3600]
        )
        
        # Service Info
        self.service_info = Info(
            'deeplake_api_info',
            'Tributary AI Service for DeepLake service information'
        )
    
    def record_request(self, method: str, endpoint: str, status_code: int, 
                      duration: float, tenant_id: Optional[str] = None):
        """Record HTTP request metrics"""
        labels = {
            'method': method,
            'endpoint': endpoint,
            'status_code': str(status_code),
            'tenant_id': tenant_id or 'unknown'
        }
        
        self.http_requests_total.labels(**labels).inc()
        self.http_request_duration.labels(
            method=method, 
            endpoint=endpoint, 
            tenant_id=tenant_id or 'unknown'
        ).observe(duration)
    
    def record_search(self, search_type: str, dataset_id: str, tenant_id: str, 
                     duration: float, results_count: int):
        """Record search operation metrics"""
        self.search_operations_total.labels(
            search_type=search_type,
            dataset_id=dataset_id,
            tenant_id=tenant_id
        ).inc()
        
        self.search_latency.labels(
            search_type=search_type,
            dataset_id=dataset_id,
            tenant_id=tenant_id
        ).observe(duration)
    
    def record_vector_operation(self, operation: str, dataset_id: str, 
                              tenant_id: str, batch_size: int):
        """Record vector operation metrics"""
        self.vector_operations_total.labels(
            operation=operation,
            dataset_id=dataset_id,
            tenant_id=tenant_id
        ).inc()
        
        self.vector_batch_size.labels(
            operation=operation,
            dataset_id=dataset_id,
            tenant_id=tenant_id
        ).observe(batch_size)
    
    def record_cache_operation(self, operation: str, cache_type: str, 
                             tenant_id: str, hit: bool):
        """Record cache operation metrics"""
        self.cache_operations_total.labels(
            operation=operation,
            cache_type=cache_type,
            tenant_id=tenant_id
        ).inc()
        
        # Update hit ratio (simplified - use more sophisticated calculation in production)
        if hit:
            self.cache_hit_ratio.labels(
                cache_type=cache_type,
                tenant_id=tenant_id
            ).set(1)
    
    def record_error(self, error_type: str, error_code: str, tenant_id: str):
        """Record error metrics"""
        self.errors_total.labels(
            error_type=error_type,
            error_code=error_code,
            tenant_id=tenant_id
        ).inc()

# Global metrics instance
metrics = DeepLakeMetrics()
```

### Metrics Middleware

```python
# app/middleware/metrics_middleware.py
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.monitoring.metrics import metrics

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract tenant ID from request
        tenant_id = self.extract_tenant_id(request)
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        metrics.record_request(
            method=request.method,
            endpoint=self.normalize_endpoint(request.url.path),
            status_code=response.status_code,
            duration=duration,
            tenant_id=tenant_id
        )
        
        return response
    
    def extract_tenant_id(self, request: Request) -> str:
        """Extract tenant ID from request"""
        # Check header
        if 'x-tenant-id' in request.headers:
            return request.headers['x-tenant-id']
        
        # Check from auth token (if available)
        if hasattr(request.state, 'tenant_id'):
            return request.state.tenant_id
        
        return 'unknown'
    
    def normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics"""
        # Replace dynamic segments with placeholders
        import re
        
        # Dataset ID pattern
        path = re.sub(r'/datasets/[^/]+', '/datasets/{id}', path)
        
        # Vector ID pattern
        path = re.sub(r'/vectors/[^/]+', '/vectors/{id}', path)
        
        # Backup ID pattern
        path = re.sub(r'/backups/[^/]+', '/backups/{id}', path)
        
        return path
```

## 🔍 Distributed Tracing

### OpenTelemetry Configuration

```python
# app/monitoring/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from typing import Optional, Dict, Any
import os

class TracingService:
    """OpenTelemetry tracing service"""
    
    def __init__(self, service_name: str = "deeplake-api"):
        self.service_name = service_name
        self.tracer = None
        self.setup_tracing()
    
    def setup_tracing(self):
        """Setup OpenTelemetry tracing"""
        # Create resource
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": os.getenv("APP_VERSION", "unknown"),
            "deployment.environment": os.getenv("ENVIRONMENT", "development")
        })
        
        # Create tracer provider
        trace.set_tracer_provider(TracerProvider(resource=resource))
        
        # Create Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
            agent_port=int(os.getenv("JAEGER_AGENT_PORT", "14268")),
        )
        
        # Create span processor
        span_processor = BatchSpanProcessor(jaeger_exporter)
        
        # Add span processor to tracer provider
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        # Get tracer
        self.tracer = trace.get_tracer(__name__)
        
        # Auto-instrument frameworks
        self.setup_auto_instrumentation()
    
    def setup_auto_instrumentation(self):
        """Setup automatic instrumentation"""
        # FastAPI instrumentation
        FastAPIInstrumentor.instrument()
        
        # HTTP client instrumentation
        HTTPXClientInstrumentor().instrument()
        
        # Redis instrumentation
        RedisInstrumentor().instrument()
        
        # SQLAlchemy instrumentation
        SQLAlchemyInstrumentor().instrument()
    
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Start a new span"""
        span = self.tracer.start_span(name)
        
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        return span
    
    def add_event(self, span, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add event to span"""
        span.add_event(name, attributes or {})
    
    def record_exception(self, span, exception: Exception):
        """Record exception in span"""
        span.record_exception(exception)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))

# Global tracing service
tracing_service = TracingService()
```

### Custom Tracing Decorators

```python
# app/monitoring/decorators.py
from functools import wraps
from typing import Callable, Any
from app.monitoring.tracing import tracing_service
import time

def trace_operation(operation_name: str):
    """Decorator to trace operations"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            with tracing_service.start_span(operation_name) as span:
                # Add function details
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                # Add arguments (be careful with sensitive data)
                if args:
                    span.set_attribute("function.args_count", len(args))
                if kwargs:
                    span.set_attribute("function.kwargs_count", len(kwargs))
                
                try:
                    start_time = time.time()
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    span.set_attribute("function.duration", duration)
                    span.set_attribute("function.success", True)
                    
                    return result
                except Exception as e:
                    tracing_service.record_exception(span, e)
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            with tracing_service.start_span(operation_name) as span:
                # Add function details
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    span.set_attribute("function.duration", duration)
                    span.set_attribute("function.success", True)
                    
                    return result
                except Exception as e:
                    tracing_service.record_exception(span, e)
                    raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Usage examples
@trace_operation("search_vectors")
async def search_vectors(dataset_id: str, query_vector: list, k: int):
    """Search vectors with tracing"""
    # Implementation here
    pass

@trace_operation("index_build")
async def build_index(dataset_id: str, index_type: str):
    """Build index with tracing"""
    # Implementation here
    pass
```

## 📝 Structured Logging

### Logging Configuration

```python
# app/monitoring/logging.py
import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pythonjsonlogger import jsonlogger
import os

class StructuredLogger:
    """Structured logging service"""
    
    def __init__(self, service_name: str = "deeplake-api"):
        self.service_name = service_name
        self.logger = None
        self.setup_logging()
    
    def setup_logging(self):
        """Setup structured logging"""
        # Create custom formatter
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
        )
        
        # Create handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        
        # Create logger
        self.logger = logging.getLogger(self.service_name)
        self.logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
        self.logger.addHandler(handler)
        
        # Prevent duplicate logs
        self.logger.propagate = False
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "level": level,
            "message": message,
            "environment": os.getenv("ENVIRONMENT", "development"),
            **kwargs
        }
        
        getattr(self.logger, level.lower())(json.dumps(log_data))
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log("ERROR", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log("DEBUG", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log("CRITICAL", message, **kwargs)
    
    def log_request(self, request_id: str, method: str, path: str, 
                   status_code: int, duration: float, tenant_id: Optional[str] = None):
        """Log HTTP request"""
        self.info(
            "HTTP request processed",
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            duration=duration,
            tenant_id=tenant_id
        )
    
    def log_search(self, search_type: str, dataset_id: str, tenant_id: str,
                  duration: float, results_count: int, query_params: Dict[str, Any]):
        """Log search operation"""
        self.info(
            "Search operation completed",
            search_type=search_type,
            dataset_id=dataset_id,
            tenant_id=tenant_id,
            duration=duration,
            results_count=results_count,
            query_params=query_params
        )
    
    def log_error(self, error_type: str, error_code: str, message: str,
                 tenant_id: Optional[str] = None, **context):
        """Log error with context"""
        self.error(
            message,
            error_type=error_type,
            error_code=error_code,
            tenant_id=tenant_id,
            **context
        )

# Global logger instance
logger = StructuredLogger()
```

### Logging Middleware

```python
# app/middleware/logging_middleware.py
import uuid
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.monitoring.logging import logger

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        # Log request start
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host if request.client else None
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log request completion
        logger.log_request(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration,
            tenant_id=getattr(request.state, 'tenant_id', None)
        )
        
        # Add request ID to response headers
        response.headers["x-request-id"] = request_id
        
        return response
```

## 🚨 Alerting System

### Alert Rules Configuration

```yaml
# alert_rules.yml
groups:
  - name: deeplake-api-alerts
    rules:
      # High Error Rate
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status_code=~"5.."}[5m])) by (instance) /
            sum(rate(http_requests_total[5m])) by (instance)
          ) > 0.05
        for: 5m
        labels:
          severity: critical
          service: deeplake-api
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for instance {{ $labels.instance }}"
          dashboard: "https://grafana.example.com/d/deeplake-api"
          runbook: "https://docs.example.com/runbooks/high-error-rate"
      
      # High Response Time
      - alert: HighResponseTime
        expr: |
          histogram_quantile(0.95, 
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, instance)
          ) > 2.0
        for: 5m
        labels:
          severity: warning
          service: deeplake-api
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s for instance {{ $labels.instance }}"
      
      # Service Down
      - alert: ServiceDown
        expr: up{job="deeplake-api"} == 0
        for: 1m
        labels:
          severity: critical
          service: deeplake-api
        annotations:
          summary: "Tributary AI Service for DeepLake service is down"
          description: "Service {{ $labels.instance }} has been down for more than 1 minute"
      
      # High Memory Usage
      - alert: HighMemoryUsage
        expr: |
          (
            memory_usage_bytes{memory_type="used"} / 
            memory_usage_bytes{memory_type="total"}
          ) > 0.90
        for: 5m
        labels:
          severity: warning
          service: deeplake-api
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }} on {{ $labels.instance }}"
      
      # Database Connection Issues
      - alert: DatabaseConnectionsHigh
        expr: active_connections > 80
        for: 5m
        labels:
          severity: warning
          service: deeplake-api
        annotations:
          summary: "High database connections"
          description: "Database connections are {{ $value }} on {{ $labels.instance }}"
      
      # Search Performance Degradation
      - alert: SlowSearchQueries
        expr: |
          histogram_quantile(0.95,
            sum(rate(search_latency_seconds_bucket[5m])) by (le, search_type)
          ) > 5.0
        for: 5m
        labels:
          severity: warning
          service: deeplake-api
        annotations:
          summary: "Slow search queries detected"
          description: "95th percentile search latency is {{ $value }}s for {{ $labels.search_type }}"
      
      # Cache Hit Rate Low
      - alert: LowCacheHitRate
        expr: cache_hit_ratio < 0.5
        for: 10m
        labels:
          severity: warning
          service: deeplake-api
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }} for {{ $labels.cache_type }}"
      
      # Rate Limiting Triggered
      - alert: RateLimitingTriggered
        expr: rate(rate_limit_hits_total[5m]) > 10
        for: 2m
        labels:
          severity: warning
          service: deeplake-api
        annotations:
          summary: "Rate limiting frequently triggered"
          description: "Rate limiting hits: {{ $value }}/sec for tenant {{ $labels.tenant_id }}"
      
      # Vector Operations Failing
      - alert: VectorOperationsFailing
        expr: |
          (
            sum(rate(errors_total{error_type="vector"}[5m])) by (tenant_id) /
            sum(rate(vector_operations_total[5m])) by (tenant_id)
          ) > 0.1
        for: 5m
        labels:
          severity: critical
          service: deeplake-api
        annotations:
          summary: "Vector operations failing"
          description: "Vector operation failure rate is {{ $value | humanizePercentage }} for tenant {{ $labels.tenant_id }}"

  - name: deeplake-infrastructure-alerts
    rules:
      # Redis Connection Issues
      - alert: RedisConnectionFailed
        expr: redis_connected_clients == 0
        for: 2m
        labels:
          severity: critical
          service: redis
        annotations:
          summary: "Redis connection failed"
          description: "Redis instance {{ $labels.instance }} has no connected clients"
      
      # Disk Space Low
      - alert: DiskSpaceLow
        expr: |
          (
            disk_free_bytes / disk_total_bytes
          ) < 0.1
        for: 5m
        labels:
          severity: critical
          service: system
        annotations:
          summary: "Disk space low"
          description: "Disk space is {{ $value | humanizePercentage }} full on {{ $labels.instance }}"
      
      # Backup Failures
      - alert: BackupFailed
        expr: |
          increase(backup_duration_seconds_count[24h]) == 0
        for: 1h
        labels:
          severity: warning
          service: backup
        annotations:
          summary: "Backup not completed"
          description: "No successful backups in the last 24 hours"
```

### AlertManager Configuration

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@yourcompany.com'
  smtp_auth_username: 'alerts@yourcompany.com'
  smtp_auth_password: 'your-app-password'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default-receiver'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      continue: true
    - match:
        severity: warning
      receiver: 'warning-alerts'

receivers:
  - name: 'default-receiver'
    email_configs:
      - to: 'devops@yourcompany.com'
        subject: 'Tributary AI Service for DeepLake Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Labels: {{ range .Labels.SortedPairs }}{{ .Name }}={{ .Value }} {{ end }}
          {{ end }}

  - name: 'critical-alerts'
    email_configs:
      - to: 'oncall@yourcompany.com'
        subject: 'CRITICAL: Tributary AI Service for DeepLake Alert'
        body: |
          🚨 CRITICAL ALERT 🚨
          
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Dashboard: {{ .Annotations.dashboard }}
          Runbook: {{ .Annotations.runbook }}
          {{ end }}
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts-critical'
        title: 'Critical Alert: {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          🚨 {{ .Annotations.summary }}
          {{ .Annotations.description }}
          {{ end }}
    pagerduty_configs:
      - service_key: 'your-pagerduty-service-key'
        description: 'Tributary AI Service for DeepLake Critical Alert'

  - name: 'warning-alerts'
    email_configs:
      - to: 'team@yourcompany.com'
        subject: 'WARNING: Tributary AI Service for DeepLake Alert'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts-warning'
        title: 'Warning: {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          ⚠️ {{ .Annotations.summary }}
          {{ .Annotations.description }}
          {{ end }}
```

## 📊 Grafana Dashboards

### Main Dashboard Configuration

```json
{
  "dashboard": {
    "id": null,
    "title": "Tributary AI Service for DeepLake Overview",
    "tags": ["deeplake", "api", "monitoring"],
    "timezone": "UTC",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m]))",
            "legendFormat": "Requests/sec"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "reqps",
            "decimals": 2
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Error Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status_code=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m])) * 100",
            "legendFormat": "Error Rate %"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "decimals": 2,
            "thresholds": {
              "steps": [
                {"color": "green", "value": 0},
                {"color": "yellow", "value": 1},
                {"color": "red", "value": 5}
              ]
            }
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0}
      },
      {
        "id": 3,
        "title": "Response Time (95th percentile)",
        "type": "stat",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))",
            "legendFormat": "95th percentile"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s",
            "decimals": 3
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0}
      },
      {
        "id": 4,
        "title": "Active Connections",
        "type": "stat",
        "targets": [
          {
            "expr": "active_connections",
            "legendFormat": "Connections"
          }
        ],
        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
      },
      {
        "id": 5,
        "title": "Request Rate by Endpoint",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m])) by (endpoint)",
            "legendFormat": "{{ endpoint }}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 6,
        "title": "Search Operations",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(search_operations_total[5m])) by (search_type)",
            "legendFormat": "{{ search_type }}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      },
      {
        "id": 7,
        "title": "Search Latency Distribution",
        "type": "heatmap",
        "targets": [
          {
            "expr": "sum(rate(search_latency_seconds_bucket[5m])) by (le)",
            "legendFormat": "{{ le }}"
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16}
      },
      {
        "id": 8,
        "title": "Vector Operations",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(vector_operations_total[5m])) by (operation)",
            "legendFormat": "{{ operation }}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 24}
      },
      {
        "id": 9,
        "title": "Cache Hit Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "cache_hit_ratio",
            "legendFormat": "{{ cache_type }}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24}
      },
      {
        "id": 10,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "memory_usage_bytes",
            "legendFormat": "{{ memory_type }}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "bytes"
          }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 32}
      },
      {
        "id": 11,
        "title": "Rate Limiting",
        "type": "graph",
        "targets": [
          {
            "expr": "rate_limit_remaining",
            "legendFormat": "{{ tenant_id }} - {{ limit_type }}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 32}
      }
    ],
    "refresh": "5s",
    "time": {
      "from": "now-1h",
      "to": "now"
    }
  }
}
```

### Business Metrics Dashboard

```json
{
  "dashboard": {
    "title": "Tributary AI Service for DeepLake Business Metrics",
    "panels": [
      {
        "title": "Total Datasets",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(datasets_total)",
            "legendFormat": "Total Datasets"
          }
        ]
      },
      {
        "title": "Total Vectors",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(vectors_total)",
            "legendFormat": "Total Vectors"
          }
        ]
      },
      {
        "title": "Datasets by Tenant",
        "type": "piechart",
        "targets": [
          {
            "expr": "sum(datasets_total) by (tenant_id)",
            "legendFormat": "{{ tenant_id }}"
          }
        ]
      },
      {
        "title": "Search Operations by Type",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(search_operations_total[5m])) by (search_type)",
            "legendFormat": "{{ search_type }}"
          }
        ]
      },
      {
        "title": "Top Datasets by Usage",
        "type": "table",
        "targets": [
          {
            "expr": "topk(10, sum(rate(search_operations_total[1h])) by (dataset_id))",
            "legendFormat": "{{ dataset_id }}"
          }
        ]
      }
    ]
  }
}
```

## 🔧 Health Checks

### Comprehensive Health Check System

```python
# app/monitoring/health.py
from typing import Dict, Any, List
from enum import Enum
import asyncio
import time
from dataclasses import dataclass
from app.services.deeplake_service import DeepLakeService
from app.services.cache_service import CacheService
import httpx

class HealthStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"

@dataclass
class HealthCheckResult:
    name: str
    status: HealthStatus
    message: str
    duration: float
    details: Dict[str, Any] = None

class HealthCheckService:
    """Comprehensive health check service"""
    
    def __init__(self, deeplake_service: DeepLakeService, cache_service: CacheService):
        self.deeplake_service = deeplake_service
        self.cache_service = cache_service
        self.checks = [
            self._check_api_health,
            self._check_deeplake_health,
            self._check_cache_health,
            self._check_disk_space,
            self._check_memory_usage,
            self._check_database_connections,
            self._check_external_services
        ]
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = []
        start_time = time.time()
        
        # Run all checks concurrently
        tasks = [self._run_check(check) for check in self.checks]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in check_results:
            if isinstance(result, Exception):
                results.append(HealthCheckResult(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=str(result),
                    duration=0.0
                ))
            else:
                results.append(result)
        
        # Determine overall status
        overall_status = self._determine_overall_status(results)
        
        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "duration": time.time() - start_time,
            "checks": [
                {
                    "name": result.name,
                    "status": result.status.value,
                    "message": result.message,
                    "duration": result.duration,
                    "details": result.details or {}
                }
                for result in results
            ]
        }
    
    async def _run_check(self, check_func) -> HealthCheckResult:
        """Run individual health check"""
        start_time = time.time()
        try:
            result = await check_func()
            result.duration = time.time() - start_time
            return result
        except Exception as e:
            return HealthCheckResult(
                name=check_func.__name__,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration=time.time() - start_time
            )
    
    async def _check_api_health(self) -> HealthCheckResult:
        """Check API health"""
        try:
            # Simple API check
            return HealthCheckResult(
                name="api",
                status=HealthStatus.HEALTHY,
                message="API is responding",
                duration=0.0
            )
        except Exception as e:
            return HealthCheckResult(
                name="api",
                status=HealthStatus.UNHEALTHY,
                message=f"API check failed: {str(e)}",
                duration=0.0
            )
    
    async def _check_deeplake_health(self) -> HealthCheckResult:
        """Check DeepLake service health"""
        try:
            # Test DeepLake connection
            test_result = await self.deeplake_service.health_check()
            
            if test_result:
                return HealthCheckResult(
                    name="deeplake",
                    status=HealthStatus.HEALTHY,
                    message="DeepLake service is healthy",
                    duration=0.0
                )
            else:
                return HealthCheckResult(
                    name="deeplake",
                    status=HealthStatus.UNHEALTHY,
                    message="DeepLake service is not responding",
                    duration=0.0
                )
        except Exception as e:
            return HealthCheckResult(
                name="deeplake",
                status=HealthStatus.UNHEALTHY,
                message=f"DeepLake check failed: {str(e)}",
                duration=0.0
            )
    
    async def _check_cache_health(self) -> HealthCheckResult:
        """Check cache service health"""
        try:
            # Test cache connection
            test_key = "health_check_test"
            test_value = "test_value"
            
            # Test set and get
            await self.cache_service.set(test_key, test_value, ttl=60)
            retrieved_value = await self.cache_service.get(test_key)
            
            if retrieved_value == test_value:
                # Clean up test key
                await self.cache_service.delete(test_key)
                
                return HealthCheckResult(
                    name="cache",
                    status=HealthStatus.HEALTHY,
                    message="Cache service is healthy",
                    duration=0.0
                )
            else:
                return HealthCheckResult(
                    name="cache",
                    status=HealthStatus.UNHEALTHY,
                    message="Cache service is not working correctly",
                    duration=0.0
                )
        except Exception as e:
            return HealthCheckResult(
                name="cache",
                status=HealthStatus.UNHEALTHY,
                message=f"Cache check failed: {str(e)}",
                duration=0.0
            )
    
    async def _check_disk_space(self) -> HealthCheckResult:
        """Check disk space"""
        try:
            import shutil
            
            # Check disk space
            total, used, free = shutil.disk_usage("/")
            free_percent = (free / total) * 100
            
            if free_percent > 20:
                status = HealthStatus.HEALTHY
                message = f"Disk space healthy ({free_percent:.1f}% free)"
            elif free_percent > 10:
                status = HealthStatus.DEGRADED
                message = f"Disk space low ({free_percent:.1f}% free)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Disk space critical ({free_percent:.1f}% free)"
            
            return HealthCheckResult(
                name="disk_space",
                status=status,
                message=message,
                duration=0.0,
                details={
                    "total_bytes": total,
                    "used_bytes": used,
                    "free_bytes": free,
                    "free_percent": free_percent
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name="disk_space",
                status=HealthStatus.UNHEALTHY,
                message=f"Disk space check failed: {str(e)}",
                duration=0.0
            )
    
    async def _check_memory_usage(self) -> HealthCheckResult:
        """Check memory usage"""
        try:
            import psutil
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent < 80:
                status = HealthStatus.HEALTHY
                message = f"Memory usage healthy ({memory_percent:.1f}%)"
            elif memory_percent < 90:
                status = HealthStatus.DEGRADED
                message = f"Memory usage high ({memory_percent:.1f}%)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Memory usage critical ({memory_percent:.1f}%)"
            
            return HealthCheckResult(
                name="memory",
                status=status,
                message=message,
                duration=0.0,
                details={
                    "total_bytes": memory.total,
                    "used_bytes": memory.used,
                    "free_bytes": memory.free,
                    "percent": memory_percent
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check failed: {str(e)}",
                duration=0.0
            )
    
    async def _check_database_connections(self) -> HealthCheckResult:
        """Check database connections"""
        try:
            # This would depend on your database setup
            # For now, we'll simulate a check
            connection_count = 25  # Simulate current connections
            max_connections = 100  # Simulate max connections
            
            usage_percent = (connection_count / max_connections) * 100
            
            if usage_percent < 70:
                status = HealthStatus.HEALTHY
                message = f"Database connections healthy ({connection_count}/{max_connections})"
            elif usage_percent < 90:
                status = HealthStatus.DEGRADED
                message = f"Database connections high ({connection_count}/{max_connections})"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Database connections critical ({connection_count}/{max_connections})"
            
            return HealthCheckResult(
                name="database_connections",
                status=status,
                message=message,
                duration=0.0,
                details={
                    "active_connections": connection_count,
                    "max_connections": max_connections,
                    "usage_percent": usage_percent
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name="database_connections",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connections check failed: {str(e)}",
                duration=0.0
            )
    
    async def _check_external_services(self) -> HealthCheckResult:
        """Check external services"""
        try:
            # Check external service connectivity
            external_services = [
                {"name": "OpenAI", "url": "https://api.openai.com/v1/models", "timeout": 5},
                {"name": "DeepLake Hub", "url": "https://api.deeplake.ai/", "timeout": 5}
            ]
            
            service_results = []
            
            async with httpx.AsyncClient() as client:
                for service in external_services:
                    try:
                        response = await client.get(
                            service["url"],
                            timeout=service["timeout"]
                        )
                        service_results.append({
                            "name": service["name"],
                            "status": "healthy" if response.status_code < 400 else "unhealthy",
                            "status_code": response.status_code
                        })
                    except Exception as e:
                        service_results.append({
                            "name": service["name"],
                            "status": "unhealthy",
                            "error": str(e)
                        })
            
            # Determine overall external services status
            unhealthy_count = sum(1 for s in service_results if s["status"] == "unhealthy")
            
            if unhealthy_count == 0:
                status = HealthStatus.HEALTHY
                message = "All external services are healthy"
            elif unhealthy_count < len(service_results):
                status = HealthStatus.DEGRADED
                message = f"{unhealthy_count}/{len(service_results)} external services unhealthy"
            else:
                status = HealthStatus.UNHEALTHY
                message = "All external services are unhealthy"
            
            return HealthCheckResult(
                name="external_services",
                status=status,
                message=message,
                duration=0.0,
                details={"services": service_results}
            )
        except Exception as e:
            return HealthCheckResult(
                name="external_services",
                status=HealthStatus.UNHEALTHY,
                message=f"External services check failed: {str(e)}",
                duration=0.0
            )
    
    def _determine_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Determine overall health status"""
        if any(result.status == HealthStatus.UNHEALTHY for result in results):
            return HealthStatus.UNHEALTHY
        elif any(result.status == HealthStatus.DEGRADED for result in results):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
```

## 🚀 Performance Monitoring

### APM Integration

```python
# app/monitoring/apm.py
from typing import Dict, Any, Optional
import time
import asyncio
from dataclasses import dataclass
from app.monitoring.metrics import metrics
from app.monitoring.logging import logger

@dataclass
class PerformanceMetrics:
    operation_name: str
    duration: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

class APMService:
    """Application Performance Monitoring service"""
    
    def __init__(self):
        self.active_operations = {}
        self.performance_history = []
    
    async def track_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Track operation performance"""
        start_time = time.time()
        operation_id = f"{operation_name}_{start_time}"
        
        # Record operation start
        self.active_operations[operation_id] = {
            "name": operation_name,
            "start_time": start_time,
            "args": args,
            "kwargs": kwargs
        }
        
        try:
            # Execute operation
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func(*args, **kwargs)
            else:
                result = operation_func(*args, **kwargs)
            
            # Record success
            duration = time.time() - start_time
            self._record_performance(
                PerformanceMetrics(
                    operation_name=operation_name,
                    duration=duration,
                    success=True,
                    metadata={"result_type": type(result).__name__}
                )
            )
            
            return result
        
        except Exception as e:
            # Record failure
            duration = time.time() - start_time
            self._record_performance(
                PerformanceMetrics(
                    operation_name=operation_name,
                    duration=duration,
                    success=False,
                    error_message=str(e),
                    metadata={"error_type": type(e).__name__}
                )
            )
            raise
        
        finally:
            # Clean up
            if operation_id in self.active_operations:
                del self.active_operations[operation_id]
    
    def _record_performance(self, perf_metrics: PerformanceMetrics):
        """Record performance metrics"""
        # Add to history
        self.performance_history.append(perf_metrics)
        
        # Keep only recent history
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
        
        # Log performance
        logger.info(
            f"Operation completed: {perf_metrics.operation_name}",
            duration=perf_metrics.duration,
            success=perf_metrics.success,
            error_message=perf_metrics.error_message,
            metadata=perf_metrics.metadata
        )
        
        # Record metrics
        # Note: This would integrate with your metrics system
        # metrics.record_operation_performance(perf_metrics)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.performance_history:
            return {"message": "No performance data available"}
        
        # Calculate statistics
        total_operations = len(self.performance_history)
        successful_operations = sum(1 for m in self.performance_history if m.success)
        failed_operations = total_operations - successful_operations
        
        durations = [m.duration for m in self.performance_history]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        
        # Group by operation
        operation_stats = {}
        for metric in self.performance_history:
            op_name = metric.operation_name
            if op_name not in operation_stats:
                operation_stats[op_name] = {
                    "count": 0,
                    "success_count": 0,
                    "total_duration": 0,
                    "max_duration": 0,
                    "min_duration": float('inf')
                }
            
            stats = operation_stats[op_name]
            stats["count"] += 1
            if metric.success:
                stats["success_count"] += 1
            stats["total_duration"] += metric.duration
            stats["max_duration"] = max(stats["max_duration"], metric.duration)
            stats["min_duration"] = min(stats["min_duration"], metric.duration)
        
        # Calculate averages
        for op_name, stats in operation_stats.items():
            stats["avg_duration"] = stats["total_duration"] / stats["count"]
            stats["success_rate"] = stats["success_count"] / stats["count"]
        
        return {
            "summary": {
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "failed_operations": failed_operations,
                "success_rate": successful_operations / total_operations,
                "avg_duration": avg_duration,
                "max_duration": max_duration,
                "min_duration": min_duration
            },
            "operations": operation_stats,
            "active_operations": len(self.active_operations)
        }

# Global APM service
apm_service = APMService()
```

## 📈 Observability Best Practices

### 1. Golden Signals

Monitor the four golden signals:
- **Latency**: Response time of requests
- **Traffic**: Rate of requests
- **Errors**: Rate of failed requests
- **Saturation**: Resource utilization

### 2. RED Method

For each service, monitor:
- **Rate**: Requests per second
- **Errors**: Number of failed requests
- **Duration**: Time taken to process requests

### 3. USE Method

For each resource, monitor:
- **Utilization**: Percentage of time resource is busy
- **Saturation**: Queue length or wait time
- **Errors**: Error count

### 4. Monitoring Checklist

**Application Metrics:**
- [ ] Request rate and latency
- [ ] Error rates and types
- [ ] Business metrics (datasets, vectors, searches)
- [ ] Cache hit rates
- [ ] Database query performance

**Infrastructure Metrics:**
- [ ] CPU, memory, disk usage
- [ ] Network I/O
- [ ] Database connections
- [ ] Message queue depths

**Business Metrics:**
- [ ] User activity
- [ ] Feature usage
- [ ] Revenue impact
- [ ] Customer satisfaction

## 🔗 Integration with Existing Services

### Service Registration

```python
# app/monitoring/service_registry.py
from app.monitoring.metrics import metrics
from app.monitoring.logging import logger
from app.monitoring.tracing import tracing_service
from app.monitoring.health import HealthCheckService

class MonitoringRegistry:
    """Registry for monitoring services"""
    
    def __init__(self):
        self.metrics = metrics
        self.logger = logger
        self.tracing = tracing_service
        self.health_check = None
    
    def register_health_check(self, health_check_service: HealthCheckService):
        """Register health check service"""
        self.health_check = health_check_service
    
    def initialize_monitoring(self):
        """Initialize all monitoring components"""
        # Set up service info
        self.metrics.service_info.info({
            "version": "1.0.0",
            "environment": "production",
            "build_date": "2024-01-01"
        })
        
        # Log startup
        self.logger.info("Monitoring system initialized")
        
        # Start tracing
        self.tracing.setup_tracing()

# Global registry
monitoring_registry = MonitoringRegistry()
```

## 🔗 Related Documentation

- [Deployment Guide](./deployment/production.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [Performance Guide](./performance.md)
- [Security Guide](./security.md)
- [API Reference](./api/http/README.md)

## 📞 Support

For monitoring and observability questions:
- **Monitoring Team**: [monitoring@yourcompany.com](mailto:monitoring@yourcompany.com)
- **Grafana Dashboards**: [grafana.yourcompany.com](https://grafana.yourcompany.com)
- **Prometheus**: [prometheus.yourcompany.com](https://prometheus.yourcompany.com)
- **Documentation**: [docs.yourcompany.com/monitoring](https://docs.yourcompany.com/monitoring)