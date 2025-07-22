# Observability Strategy

This document outlines the comprehensive observability strategy for the Tributary AI Service for DeepLake, including monitoring, alerting, logging, and tracing best practices.

## 🎯 Observability Pillars

### The Three Pillars of Observability

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Observability Stack                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │    METRICS      │  │     LOGS        │  │     TRACES      │            │
│  │                 │  │                 │  │                 │            │
│  │ • Prometheus    │  │ • Structured    │  │ • Distributed   │            │
│  │ • Grafana       │  │ • Centralized   │  │ • OpenTelemetry │            │
│  │ • Alerting      │  │ • Searchable    │  │ • Jaeger        │            │
│  │ • Dashboards    │  │ • Retention     │  │ • Correlation   │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Unified Observability                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Correlation across signals                                              │
│  • Root cause analysis                                                     │
│  • Performance optimization                                                │
│  • Incident response                                                       │
│  • Capacity planning                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📊 Metrics Strategy

### Golden Signals Implementation

```python
# app/observability/golden_signals.py
from typing import Dict, Any, Optional
from dataclasses import dataclass
from prometheus_client import Counter, Histogram, Gauge
import time

@dataclass
class GoldenSignals:
    """The Four Golden Signals of Monitoring"""
    
    # 1. Latency
    latency_histogram: Histogram
    
    # 2. Traffic
    traffic_counter: Counter
    
    # 3. Errors
    error_counter: Counter
    
    # 4. Saturation
    saturation_gauge: Gauge

class GoldenSignalsCollector:
    """Collector for golden signals metrics"""
    
    def __init__(self):
        self.signals = GoldenSignals(
            latency_histogram=Histogram(
                'request_duration_seconds',
                'Request duration in seconds',
                ['method', 'endpoint', 'status_code', 'tenant_id'],
                buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
            ),
            traffic_counter=Counter(
                'requests_total',
                'Total number of requests',
                ['method', 'endpoint', 'status_code', 'tenant_id']
            ),
            error_counter=Counter(
                'errors_total',
                'Total number of errors',
                ['error_type', 'error_code', 'method', 'endpoint', 'tenant_id']
            ),
            saturation_gauge=Gauge(
                'resource_utilization_percent',
                'Resource utilization percentage',
                ['resource_type', 'instance']
            )
        )
    
    def record_request(self, method: str, endpoint: str, status_code: int, 
                      duration: float, tenant_id: str):
        """Record request metrics"""
        labels = {
            'method': method,
            'endpoint': endpoint,
            'status_code': str(status_code),
            'tenant_id': tenant_id
        }
        
        # Latency
        self.signals.latency_histogram.labels(**labels).observe(duration)
        
        # Traffic
        self.signals.traffic_counter.labels(**labels).inc()
        
        # Errors (if applicable)
        if status_code >= 400:
            self.signals.error_counter.labels(
                error_type='http_error',
                error_code=str(status_code),
                **labels
            ).inc()
    
    def record_saturation(self, resource_type: str, instance: str, utilization: float):
        """Record resource saturation"""
        self.signals.saturation_gauge.labels(
            resource_type=resource_type,
            instance=instance
        ).set(utilization)

# Global collector
golden_signals = GoldenSignalsCollector()
```

### Custom Business Metrics

```python
# app/observability/business_metrics.py
from prometheus_client import Counter, Histogram, Gauge, Summary
from typing import Dict, Any
import time

class BusinessMetricsCollector:
    """Collector for business-specific metrics"""
    
    def __init__(self):
        # Dataset metrics
        self.datasets_created = Counter(
            'datasets_created_total',
            'Total datasets created',
            ['tenant_id', 'dataset_type']
        )
        
        self.datasets_active = Gauge(
            'datasets_active_total',
            'Total active datasets',
            ['tenant_id', 'dataset_type']
        )
        
        # Vector metrics
        self.vectors_added = Counter(
            'vectors_added_total',
            'Total vectors added',
            ['dataset_id', 'tenant_id', 'operation_type']
        )
        
        self.vectors_total = Gauge(
            'vectors_stored_total',
            'Total vectors stored',
            ['dataset_id', 'tenant_id']
        )
        
        # Search metrics
        self.searches_performed = Counter(
            'searches_performed_total',
            'Total searches performed',
            ['search_type', 'dataset_id', 'tenant_id']
        )
        
        self.search_accuracy = Histogram(
            'search_accuracy_score',
            'Search accuracy score',
            ['search_type', 'dataset_id', 'tenant_id'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
        
        # Performance metrics
        self.index_build_time = Histogram(
            'index_build_duration_seconds',
            'Time to build index',
            ['index_type', 'dataset_size_bucket', 'tenant_id'],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600]
        )
        
        self.query_complexity = Histogram(
            'query_complexity_score',
            'Query complexity score',
            ['query_type', 'dataset_id', 'tenant_id'],
            buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        )
        
        # Usage metrics
        self.api_key_usage = Counter(
            'api_key_usage_total',
            'API key usage count',
            ['api_key_id', 'tenant_id', 'operation_type']
        )
        
        self.tenant_activity = Gauge(
            'tenant_activity_score',
            'Tenant activity score',
            ['tenant_id', 'activity_type']
        )
    
    def record_dataset_creation(self, tenant_id: str, dataset_type: str):
        """Record dataset creation"""
        self.datasets_created.labels(
            tenant_id=tenant_id,
            dataset_type=dataset_type
        ).inc()
    
    def record_vector_operation(self, dataset_id: str, tenant_id: str, 
                              operation_type: str, vector_count: int):
        """Record vector operation"""
        self.vectors_added.labels(
            dataset_id=dataset_id,
            tenant_id=tenant_id,
            operation_type=operation_type
        ).inc(vector_count)
    
    def record_search(self, search_type: str, dataset_id: str, tenant_id: str, 
                     accuracy_score: float = None, complexity_score: float = None):
        """Record search operation"""
        self.searches_performed.labels(
            search_type=search_type,
            dataset_id=dataset_id,
            tenant_id=tenant_id
        ).inc()
        
        if accuracy_score is not None:
            self.search_accuracy.labels(
                search_type=search_type,
                dataset_id=dataset_id,
                tenant_id=tenant_id
            ).observe(accuracy_score)
        
        if complexity_score is not None:
            self.query_complexity.labels(
                query_type=search_type,
                dataset_id=dataset_id,
                tenant_id=tenant_id
            ).observe(complexity_score)
    
    def record_index_build(self, index_type: str, dataset_size_bucket: str, 
                          tenant_id: str, duration: float):
        """Record index build time"""
        self.index_build_time.labels(
            index_type=index_type,
            dataset_size_bucket=dataset_size_bucket,
            tenant_id=tenant_id
        ).observe(duration)
    
    def update_tenant_activity(self, tenant_id: str, activity_type: str, score: float):
        """Update tenant activity score"""
        self.tenant_activity.labels(
            tenant_id=tenant_id,
            activity_type=activity_type
        ).set(score)

# Global business metrics
business_metrics = BusinessMetricsCollector()
```

## 🔍 Distributed Tracing Strategy

### Trace Context Propagation

```python
# app/observability/trace_context.py
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from typing import Dict, Any, Optional
import uuid

class TraceContextManager:
    """Manages distributed tracing context"""
    
    def __init__(self):
        self.propagator = TraceContextTextMapPropagator()
    
    def inject_context(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Inject trace context into headers"""
        self.propagator.inject(headers)
        return headers
    
    def extract_context(self, headers: Dict[str, str]) -> Optional[context.Context]:
        """Extract trace context from headers"""
        return self.propagator.extract(headers)
    
    def create_span(self, name: str, context: Optional[context.Context] = None, 
                   attributes: Optional[Dict[str, Any]] = None):
        """Create a new span with optional context"""
        tracer = trace.get_tracer(__name__)
        
        if context:
            with trace.use_span(trace.NonRecordingSpan(context), end_on_exit=False):
                span = tracer.start_span(name)
        else:
            span = tracer.start_span(name)
        
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        return span
    
    def add_span_event(self, span, event_name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add event to span"""
        span.add_event(event_name, attributes or {})
    
    def set_span_status(self, span, status_code: str, description: str = None):
        """Set span status"""
        if status_code == "OK":
            span.set_status(trace.Status(trace.StatusCode.OK))
        elif status_code == "ERROR":
            span.set_status(trace.Status(trace.StatusCode.ERROR, description))
        else:
            span.set_status(trace.Status(trace.StatusCode.UNSET))

# Global trace context manager
trace_context = TraceContextManager()
```

### Tracing Decorators

```python
# app/observability/tracing_decorators.py
from functools import wraps
from typing import Callable, Any, Dict, Optional
from opentelemetry import trace
import time
import asyncio

def trace_async(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """Decorator for tracing async operations"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(operation_name) as span:
                # Set basic attributes
                span.set_attribute("operation.name", operation_name)
                span.set_attribute("operation.type", "async")
                
                # Set custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Set function metadata
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    start_time = time.time()
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Set success attributes
                    span.set_attribute("operation.duration", duration)
                    span.set_attribute("operation.success", True)
                    
                    # Add completion event
                    span.add_event("operation.completed", {
                        "duration": duration,
                        "result_type": type(result).__name__
                    })
                    
                    return result
                
                except Exception as e:
                    # Record exception
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    
                    # Set error attributes
                    span.set_attribute("operation.success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    
                    raise
        
        return wrapper
    return decorator

def trace_sync(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """Decorator for tracing sync operations"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(operation_name) as span:
                # Set basic attributes
                span.set_attribute("operation.name", operation_name)
                span.set_attribute("operation.type", "sync")
                
                # Set custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Set function metadata
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Set success attributes
                    span.set_attribute("operation.duration", duration)
                    span.set_attribute("operation.success", True)
                    
                    return result
                
                except Exception as e:
                    # Record exception
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    
                    # Set error attributes
                    span.set_attribute("operation.success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    
                    raise
        
        return wrapper
    return decorator

# Auto-detect function type decorator
def trace_operation(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """Auto-detecting decorator for tracing operations"""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            return trace_async(operation_name, attributes)(func)
        else:
            return trace_sync(operation_name, attributes)(func)
    
    return decorator
```

## 📝 Structured Logging Strategy

### Log Correlation

```python
# app/observability/log_correlation.py
import logging
import json
import uuid
from typing import Dict, Any, Optional
from contextvars import ContextVar
from opentelemetry import trace

# Context variables for correlation
request_id_var: ContextVar[str] = ContextVar('request_id', default=None)
tenant_id_var: ContextVar[str] = ContextVar('tenant_id', default=None)
user_id_var: ContextVar[str] = ContextVar('user_id', default=None)

class CorrelatedLogger:
    """Logger that automatically includes correlation IDs"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.setup_logger()
    
    def setup_logger(self):
        """Setup structured logging with correlation"""
        handler = logging.StreamHandler()
        formatter = CorrelatedFormatter()
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
    
    def _get_correlation_context(self) -> Dict[str, Any]:
        """Get correlation context"""
        context = {}
        
        # Request ID
        request_id = request_id_var.get()
        if request_id:
            context['request_id'] = request_id
        
        # Tenant ID
        tenant_id = tenant_id_var.get()
        if tenant_id:
            context['tenant_id'] = tenant_id
        
        # User ID
        user_id = user_id_var.get()
        if user_id:
            context['user_id'] = user_id
        
        # Trace context
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            trace_context = current_span.get_span_context()
            context['trace_id'] = format(trace_context.trace_id, '032x')
            context['span_id'] = format(trace_context.span_id, '016x')
        
        return context
    
    def log(self, level: str, message: str, **kwargs):
        """Log with correlation context"""
        # Get correlation context
        context = self._get_correlation_context()
        
        # Merge with provided kwargs
        log_data = {**context, **kwargs}
        
        # Log message
        getattr(self.logger, level.lower())(message, extra=log_data)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.log('ERROR', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.log('DEBUG', message, **kwargs)

class CorrelatedFormatter(logging.Formatter):
    """Custom formatter that includes correlation context"""
    
    def format(self, record):
        # Build log entry
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add correlation context from record
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'tenant_id'):
            log_entry['tenant_id'] = record.tenant_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'trace_id'):
            log_entry['trace_id'] = record.trace_id
        if hasattr(record, 'span_id'):
            log_entry['span_id'] = record.span_id
        
        # Add any additional fields from extra
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'message']:
                log_entry[key] = value
        
        return json.dumps(log_entry)

# Context managers for correlation
class CorrelationContext:
    """Context manager for setting correlation context"""
    
    def __init__(self, request_id: str = None, tenant_id: str = None, 
                 user_id: str = None):
        self.request_id = request_id or str(uuid.uuid4())
        self.tenant_id = tenant_id
        self.user_id = user_id
        
        self.request_id_token = None
        self.tenant_id_token = None
        self.user_id_token = None
    
    def __enter__(self):
        self.request_id_token = request_id_var.set(self.request_id)
        if self.tenant_id:
            self.tenant_id_token = tenant_id_var.set(self.tenant_id)
        if self.user_id:
            self.user_id_token = user_id_var.set(self.user_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.request_id_token:
            request_id_var.reset(self.request_id_token)
        if self.tenant_id_token:
            tenant_id_var.reset(self.tenant_id_token)
        if self.user_id_token:
            user_id_var.reset(self.user_id_token)

# Global logger instance
correlated_logger = CorrelatedLogger('deeplake-api')
```

## 🚨 Advanced Alerting Strategy

### Intelligent Alerting

```python
# app/observability/intelligent_alerting.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import time
import statistics
from collections import deque

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Alert:
    name: str
    severity: AlertSeverity
    message: str
    timestamp: float
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[float] = None

class AlertCondition:
    """Base class for alert conditions"""
    
    def __init__(self, name: str, severity: AlertSeverity):
        self.name = name
        self.severity = severity
        self.history = deque(maxlen=100)
        self.last_alert_time = 0
        self.cooldown_period = 300  # 5 minutes
    
    def evaluate(self, value: float, timestamp: float) -> Optional[Alert]:
        """Evaluate condition and return alert if triggered"""
        self.history.append((timestamp, value))
        
        if self.should_alert(value, timestamp):
            # Check cooldown
            if timestamp - self.last_alert_time < self.cooldown_period:
                return None
            
            self.last_alert_time = timestamp
            return Alert(
                name=self.name,
                severity=self.severity,
                message=self.get_alert_message(value),
                timestamp=timestamp,
                metadata=self.get_alert_metadata(value)
            )
        
        return None
    
    def should_alert(self, value: float, timestamp: float) -> bool:
        """Override in subclasses"""
        raise NotImplementedError
    
    def get_alert_message(self, value: float) -> str:
        """Override in subclasses"""
        return f"Alert condition {self.name} triggered with value {value}"
    
    def get_alert_metadata(self, value: float) -> Dict[str, Any]:
        """Override in subclasses"""
        return {"current_value": value}

class ThresholdCondition(AlertCondition):
    """Simple threshold-based alert condition"""
    
    def __init__(self, name: str, severity: AlertSeverity, threshold: float, 
                 operator: str = "greater"):
        super().__init__(name, severity)
        self.threshold = threshold
        self.operator = operator
    
    def should_alert(self, value: float, timestamp: float) -> bool:
        if self.operator == "greater":
            return value > self.threshold
        elif self.operator == "less":
            return value < self.threshold
        elif self.operator == "equal":
            return value == self.threshold
        else:
            return False
    
    def get_alert_message(self, value: float) -> str:
        return f"{self.name}: {value} {self.operator} {self.threshold}"

class AnomalyCondition(AlertCondition):
    """Anomaly detection based alert condition"""
    
    def __init__(self, name: str, severity: AlertSeverity, 
                 window_size: int = 20, threshold_std: float = 2.0):
        super().__init__(name, severity)
        self.window_size = window_size
        self.threshold_std = threshold_std
    
    def should_alert(self, value: float, timestamp: float) -> bool:
        if len(self.history) < self.window_size:
            return False
        
        # Get recent values
        recent_values = [v for _, v in list(self.history)[-self.window_size:]]
        
        # Calculate mean and std
        mean = statistics.mean(recent_values)
        std = statistics.stdev(recent_values) if len(recent_values) > 1 else 0
        
        # Check for anomaly
        if std == 0:
            return False
        
        z_score = abs(value - mean) / std
        return z_score > self.threshold_std
    
    def get_alert_message(self, value: float) -> str:
        if len(self.history) >= self.window_size:
            recent_values = [v for _, v in list(self.history)[-self.window_size:]]
            mean = statistics.mean(recent_values)
            std = statistics.stdev(recent_values) if len(recent_values) > 1 else 0
            z_score = abs(value - mean) / std if std > 0 else 0
            
            return f"{self.name}: Anomaly detected - value: {value}, mean: {mean:.2f}, z-score: {z_score:.2f}"
        
        return f"{self.name}: Anomaly detected - value: {value}"

class TrendCondition(AlertCondition):
    """Trend-based alert condition"""
    
    def __init__(self, name: str, severity: AlertSeverity, 
                 window_size: int = 10, trend_threshold: float = 0.1):
        super().__init__(name, severity)
        self.window_size = window_size
        self.trend_threshold = trend_threshold
    
    def should_alert(self, value: float, timestamp: float) -> bool:
        if len(self.history) < self.window_size:
            return False
        
        # Get recent values
        recent_values = [v for _, v in list(self.history)[-self.window_size:]]
        
        # Calculate trend (simple linear regression slope)
        n = len(recent_values)
        x = list(range(n))
        
        # Calculate slope
        sum_x = sum(x)
        sum_y = sum(recent_values)
        sum_xy = sum(x[i] * recent_values[i] for i in range(n))
        sum_x_squared = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x * sum_x)
        
        # Check if trend exceeds threshold
        return abs(slope) > self.trend_threshold
    
    def get_alert_message(self, value: float) -> str:
        return f"{self.name}: Trend alert - current value: {value}"

class IntelligentAlertManager:
    """Manager for intelligent alerting"""
    
    def __init__(self):
        self.conditions: Dict[str, AlertCondition] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
    
    def add_condition(self, condition: AlertCondition):
        """Add alert condition"""
        self.conditions[condition.name] = condition
    
    def evaluate_metric(self, metric_name: str, value: float, timestamp: float = None):
        """Evaluate metric against all conditions"""
        if timestamp is None:
            timestamp = time.time()
        
        alerts = []
        
        for condition_name, condition in self.conditions.items():
            if metric_name in condition_name or condition_name in metric_name:
                alert = condition.evaluate(value, timestamp)
                if alert:
                    alerts.append(alert)
                    self.active_alerts[condition_name] = alert
                    self.alert_history.append(alert)
        
        return alerts
    
    def resolve_alert(self, condition_name: str):
        """Resolve alert"""
        if condition_name in self.active_alerts:
            alert = self.active_alerts[condition_name]
            alert.resolved = True
            alert.resolved_at = time.time()
            del self.active_alerts[condition_name]
    
    def get_active_alerts(self) -> List[Alert]:
        """Get active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary"""
        active_count = len(self.active_alerts)
        total_count = len(self.alert_history)
        
        # Count by severity
        severity_counts = {}
        for alert in self.active_alerts.values():
            severity = alert.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "active_alerts": active_count,
            "total_alerts": total_count,
            "severity_breakdown": severity_counts,
            "most_recent_alert": max(self.alert_history, key=lambda a: a.timestamp) if self.alert_history else None
        }

# Global alert manager
alert_manager = IntelligentAlertManager()

# Pre-configured conditions
alert_manager.add_condition(
    ThresholdCondition("high_error_rate", AlertSeverity.HIGH, 0.05, "greater")
)
alert_manager.add_condition(
    ThresholdCondition("high_latency", AlertSeverity.MEDIUM, 2.0, "greater")
)
alert_manager.add_condition(
    AnomalyCondition("response_time_anomaly", AlertSeverity.MEDIUM)
)
alert_manager.add_condition(
    TrendCondition("memory_usage_trend", AlertSeverity.LOW, trend_threshold=0.1)
)
```

## 📊 Observability Dashboard Strategy

### Custom Dashboard Configuration

```python
# app/observability/dashboard_config.py
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class DashboardPanel:
    title: str
    panel_type: str
    query: str
    description: str
    thresholds: Dict[str, Any] = None
    position: Dict[str, int] = None

@dataclass
class Dashboard:
    title: str
    description: str
    panels: List[DashboardPanel]
    refresh_interval: str = "5s"
    time_range: str = "1h"

class DashboardBuilder:
    """Builder for creating observability dashboards"""
    
    def __init__(self):
        self.dashboards = {}
    
    def create_overview_dashboard(self) -> Dashboard:
        """Create overview dashboard"""
        panels = [
            DashboardPanel(
                title="Request Rate",
                panel_type="stat",
                query="sum(rate(requests_total[5m]))",
                description="Total requests per second",
                thresholds={"green": 0, "yellow": 100, "red": 1000}
            ),
            DashboardPanel(
                title="Error Rate",
                panel_type="stat",
                query="sum(rate(errors_total[5m])) / sum(rate(requests_total[5m])) * 100",
                description="Percentage of requests that failed",
                thresholds={"green": 0, "yellow": 1, "red": 5}
            ),
            DashboardPanel(
                title="Response Time P95",
                panel_type="stat",
                query="histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[5m])) by (le))",
                description="95th percentile response time",
                thresholds={"green": 0, "yellow": 1, "red": 5}
            ),
            DashboardPanel(
                title="Active Datasets",
                panel_type="stat",
                query="sum(datasets_active_total)",
                description="Total number of active datasets"
            ),
            DashboardPanel(
                title="Vector Operations",
                panel_type="graph",
                query="sum(rate(vectors_added_total[5m])) by (operation_type)",
                description="Vector operations per second by type"
            ),
            DashboardPanel(
                title="Search Performance",
                panel_type="graph",
                query="histogram_quantile(0.95, sum(rate(search_duration_seconds_bucket[5m])) by (le, search_type))",
                description="Search performance by type"
            )
        ]
        
        return Dashboard(
            title="Tributary AI Service for DeepLake Overview",
            description="High-level overview of Tributary AI Service for DeepLake performance",
            panels=panels
        )
    
    def create_performance_dashboard(self) -> Dashboard:
        """Create performance dashboard"""
        panels = [
            DashboardPanel(
                title="CPU Usage",
                panel_type="graph",
                query="avg(cpu_usage_percent) by (instance)",
                description="CPU usage by instance"
            ),
            DashboardPanel(
                title="Memory Usage",
                panel_type="graph",
                query="avg(memory_usage_percent) by (instance)",
                description="Memory usage by instance"
            ),
            DashboardPanel(
                title="Database Connections",
                panel_type="graph",
                query="sum(database_connections_active) by (instance)",
                description="Active database connections"
            ),
            DashboardPanel(
                title="Cache Hit Rate",
                panel_type="graph",
                query="avg(cache_hit_rate) by (cache_type)",
                description="Cache hit rate by cache type"
            ),
            DashboardPanel(
                title="Index Build Time",
                panel_type="histogram",
                query="histogram_quantile(0.95, sum(rate(index_build_duration_seconds_bucket[5m])) by (le, index_type))",
                description="Index build time distribution"
            )
        ]
        
        return Dashboard(
            title="Tributary AI Service for DeepLake Performance",
            description="Detailed performance metrics",
            panels=panels
        )
    
    def create_business_dashboard(self) -> Dashboard:
        """Create business metrics dashboard"""
        panels = [
            DashboardPanel(
                title="Total Users",
                panel_type="stat",
                query="sum(users_active_total)",
                description="Total active users"
            ),
            DashboardPanel(
                title="Revenue Impact",
                panel_type="graph",
                query="sum(api_usage_cost) by (tenant_id)",
                description="API usage cost by tenant"
            ),
            DashboardPanel(
                title="Feature Usage",
                panel_type="piechart",
                query="sum(feature_usage_total) by (feature_name)",
                description="Feature usage distribution"
            ),
            DashboardPanel(
                title="Customer Satisfaction",
                panel_type="gauge",
                query="avg(customer_satisfaction_score)",
                description="Average customer satisfaction score"
            )
        ]
        
        return Dashboard(
            title="Tributary AI Service for DeepLake Business Metrics",
            description="Business-focused metrics and KPIs",
            panels=panels
        )
    
    def export_dashboard(self, dashboard: Dashboard) -> Dict[str, Any]:
        """Export dashboard to JSON format"""
        return {
            "dashboard": {
                "title": dashboard.title,
                "description": dashboard.description,
                "refresh": dashboard.refresh_interval,
                "time": {"from": f"now-{dashboard.time_range}", "to": "now"},
                "panels": [
                    {
                        "title": panel.title,
                        "type": panel.panel_type,
                        "targets": [{"expr": panel.query}],
                        "description": panel.description,
                        "thresholds": panel.thresholds or {},
                        "gridPos": panel.position or {}
                    }
                    for panel in dashboard.panels
                ]
            }
        }

# Global dashboard builder
dashboard_builder = DashboardBuilder()
```

## 🔍 Correlation and Root Cause Analysis

### Correlation Engine

```python
# app/observability/correlation_engine.py
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import statistics
import numpy as np

@dataclass
class CorrelationEvent:
    timestamp: datetime
    source: str
    event_type: str
    value: float
    metadata: Dict[str, Any]

@dataclass
class CorrelationResult:
    source1: str
    source2: str
    correlation_coefficient: float
    p_value: float
    confidence: float
    time_lag: timedelta

class CorrelationEngine:
    """Engine for finding correlations between observability signals"""
    
    def __init__(self):
        self.events: List[CorrelationEvent] = []
        self.correlation_cache = {}
    
    def add_event(self, event: CorrelationEvent):
        """Add event to correlation analysis"""
        self.events.append(event)
        
        # Keep only recent events (last 24 hours)
        cutoff = datetime.now() - timedelta(days=1)
        self.events = [e for e in self.events if e.timestamp > cutoff]
    
    def find_correlations(self, sources: List[str], 
                         time_window: timedelta = timedelta(hours=1),
                         min_confidence: float = 0.7) -> List[CorrelationResult]:
        """Find correlations between sources"""
        results = []
        
        for i, source1 in enumerate(sources):
            for source2 in sources[i+1:]:
                correlation = self._calculate_correlation(
                    source1, source2, time_window
                )
                
                if correlation and correlation.confidence >= min_confidence:
                    results.append(correlation)
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _calculate_correlation(self, source1: str, source2: str, 
                             time_window: timedelta) -> Optional[CorrelationResult]:
        """Calculate correlation between two sources"""
        # Get events for both sources
        events1 = [e for e in self.events if e.source == source1]
        events2 = [e for e in self.events if e.source == source2]
        
        if len(events1) < 10 or len(events2) < 10:
            return None
        
        # Create time series
        series1 = self._create_time_series(events1, time_window)
        series2 = self._create_time_series(events2, time_window)
        
        # Find common time points
        common_times = set(series1.keys()) & set(series2.keys())
        
        if len(common_times) < 10:
            return None
        
        # Extract values
        values1 = [series1[t] for t in sorted(common_times)]
        values2 = [series2[t] for t in sorted(common_times)]
        
        # Calculate correlation
        correlation_coeff = np.corrcoef(values1, values2)[0, 1]
        
        # Simple p-value calculation (for demonstration)
        p_value = self._calculate_p_value(correlation_coeff, len(values1))
        
        # Calculate confidence
        confidence = (1 - p_value) * abs(correlation_coeff)
        
        return CorrelationResult(
            source1=source1,
            source2=source2,
            correlation_coefficient=correlation_coeff,
            p_value=p_value,
            confidence=confidence,
            time_lag=timedelta(0)  # Simplified - no lag analysis
        )
    
    def _create_time_series(self, events: List[CorrelationEvent], 
                           bucket_size: timedelta) -> Dict[datetime, float]:
        """Create time series from events"""
        series = {}
        
        if not events:
            return series
        
        # Find time range
        start_time = min(e.timestamp for e in events)
        end_time = max(e.timestamp for e in events)
        
        # Create buckets
        current_time = start_time
        while current_time <= end_time:
            bucket_events = [
                e for e in events
                if current_time <= e.timestamp < current_time + bucket_size
            ]
            
            if bucket_events:
                series[current_time] = statistics.mean(e.value for e in bucket_events)
            
            current_time += bucket_size
        
        return series
    
    def _calculate_p_value(self, correlation_coeff: float, sample_size: int) -> float:
        """Calculate p-value for correlation coefficient"""
        # Simplified p-value calculation
        # In practice, you'd use proper statistical methods
        t_stat = abs(correlation_coeff) * np.sqrt((sample_size - 2) / (1 - correlation_coeff**2))
        
        # Rough approximation
        if t_stat > 2.576:  # 99% confidence
            return 0.01
        elif t_stat > 1.96:  # 95% confidence
            return 0.05
        elif t_stat > 1.645:  # 90% confidence
            return 0.10
        else:
            return 0.5
    
    def get_correlation_summary(self) -> Dict[str, Any]:
        """Get correlation analysis summary"""
        sources = list(set(e.source for e in self.events))
        correlations = self.find_correlations(sources)
        
        return {
            "total_events": len(self.events),
            "unique_sources": len(sources),
            "correlations_found": len(correlations),
            "high_confidence_correlations": len([c for c in correlations if c.confidence > 0.8]),
            "top_correlations": correlations[:5] if correlations else []
        }

# Global correlation engine
correlation_engine = CorrelationEngine()
```

## 📈 Observability Maturity Model

### Maturity Levels

```python
# app/observability/maturity_model.py
from enum import Enum
from typing import Dict, Any, List
from dataclasses import dataclass

class MaturityLevel(Enum):
    REACTIVE = 1
    PROACTIVE = 2
    PREDICTIVE = 3
    ADAPTIVE = 4

@dataclass
class MaturityCriterion:
    name: str
    description: str
    current_score: int
    target_score: int
    recommendations: List[str]

class ObservabilityMaturityAssessment:
    """Assessment of observability maturity"""
    
    def __init__(self):
        self.criteria = {
            "monitoring_coverage": MaturityCriterion(
                name="Monitoring Coverage",
                description="Percentage of system components with monitoring",
                current_score=0,
                target_score=4,
                recommendations=[]
            ),
            "alerting_quality": MaturityCriterion(
                name="Alerting Quality",
                description="Quality and actionability of alerts",
                current_score=0,
                target_score=4,
                recommendations=[]
            ),
            "incident_response": MaturityCriterion(
                name="Incident Response",
                description="Effectiveness of incident response process",
                current_score=0,
                target_score=4,
                recommendations=[]
            ),
            "automation_level": MaturityCriterion(
                name="Automation Level",
                description="Degree of automation in observability",
                current_score=0,
                target_score=4,
                recommendations=[]
            ),
            "correlation_analysis": MaturityCriterion(
                name="Correlation Analysis",
                description="Ability to correlate signals across systems",
                current_score=0,
                target_score=4,
                recommendations=[]
            )
        }
    
    def assess_maturity(self) -> Dict[str, Any]:
        """Assess current observability maturity"""
        # Monitoring Coverage Assessment
        self._assess_monitoring_coverage()
        
        # Alerting Quality Assessment
        self._assess_alerting_quality()
        
        # Incident Response Assessment
        self._assess_incident_response()
        
        # Automation Level Assessment
        self._assess_automation_level()
        
        # Correlation Analysis Assessment
        self._assess_correlation_analysis()
        
        # Calculate overall maturity
        overall_score = sum(c.current_score for c in self.criteria.values()) / len(self.criteria)
        maturity_level = self._determine_maturity_level(overall_score)
        
        return {
            "overall_maturity_level": maturity_level.name,
            "overall_score": overall_score,
            "criteria_scores": {
                name: criterion.current_score 
                for name, criterion in self.criteria.items()
            },
            "recommendations": self._get_recommendations(),
            "next_steps": self._get_next_steps()
        }
    
    def _assess_monitoring_coverage(self):
        """Assess monitoring coverage"""
        # Check if we have basic metrics
        has_basic_metrics = True  # Simplified
        has_business_metrics = True  # Simplified
        has_infrastructure_metrics = True  # Simplified
        has_application_metrics = True  # Simplified
        
        score = 0
        recommendations = []
        
        if has_basic_metrics:
            score += 1
        else:
            recommendations.append("Implement basic HTTP metrics")
        
        if has_business_metrics:
            score += 1
        else:
            recommendations.append("Add business-specific metrics")
        
        if has_infrastructure_metrics:
            score += 1
        else:
            recommendations.append("Add infrastructure monitoring")
        
        if has_application_metrics:
            score += 1
        else:
            recommendations.append("Add application performance metrics")
        
        self.criteria["monitoring_coverage"].current_score = score
        self.criteria["monitoring_coverage"].recommendations = recommendations
    
    def _assess_alerting_quality(self):
        """Assess alerting quality"""
        # Simplified assessment
        has_slos = True
        has_actionable_alerts = True
        has_alert_routing = True
        has_alert_suppression = False
        
        score = 0
        recommendations = []
        
        if has_slos:
            score += 1
        else:
            recommendations.append("Define SLOs and SLIs")
        
        if has_actionable_alerts:
            score += 1
        else:
            recommendations.append("Make alerts actionable with runbooks")
        
        if has_alert_routing:
            score += 1
        else:
            recommendations.append("Implement alert routing by severity")
        
        if has_alert_suppression:
            score += 1
        else:
            recommendations.append("Add intelligent alert suppression")
        
        self.criteria["alerting_quality"].current_score = score
        self.criteria["alerting_quality"].recommendations = recommendations
    
    def _assess_incident_response(self):
        """Assess incident response capability"""
        # Simplified assessment
        has_runbooks = True
        has_escalation_procedures = True
        has_post_mortem_process = False
        has_automated_response = False
        
        score = 0
        recommendations = []
        
        if has_runbooks:
            score += 1
        else:
            recommendations.append("Create incident response runbooks")
        
        if has_escalation_procedures:
            score += 1
        else:
            recommendations.append("Define escalation procedures")
        
        if has_post_mortem_process:
            score += 1
        else:
            recommendations.append("Implement post-mortem process")
        
        if has_automated_response:
            score += 1
        else:
            recommendations.append("Add automated incident response")
        
        self.criteria["incident_response"].current_score = score
        self.criteria["incident_response"].recommendations = recommendations
    
    def _assess_automation_level(self):
        """Assess automation level"""
        # Simplified assessment
        has_auto_scaling = True
        has_auto_remediation = False
        has_predictive_scaling = False
        has_chaos_engineering = False
        
        score = 0
        recommendations = []
        
        if has_auto_scaling:
            score += 1
        else:
            recommendations.append("Implement auto-scaling")
        
        if has_auto_remediation:
            score += 1
        else:
            recommendations.append("Add automated remediation")
        
        if has_predictive_scaling:
            score += 1
        else:
            recommendations.append("Implement predictive scaling")
        
        if has_chaos_engineering:
            score += 1
        else:
            recommendations.append("Add chaos engineering practices")
        
        self.criteria["automation_level"].current_score = score
        self.criteria["automation_level"].recommendations = recommendations
    
    def _assess_correlation_analysis(self):
        """Assess correlation analysis capability"""
        # Simplified assessment
        has_trace_correlation = True
        has_log_correlation = True
        has_metric_correlation = False
        has_ml_analysis = False
        
        score = 0
        recommendations = []
        
        if has_trace_correlation:
            score += 1
        else:
            recommendations.append("Implement trace correlation")
        
        if has_log_correlation:
            score += 1
        else:
            recommendations.append("Add log correlation")
        
        if has_metric_correlation:
            score += 1
        else:
            recommendations.append("Implement metric correlation")
        
        if has_ml_analysis:
            score += 1
        else:
            recommendations.append("Add ML-based analysis")
        
        self.criteria["correlation_analysis"].current_score = score
        self.criteria["correlation_analysis"].recommendations = recommendations
    
    def _determine_maturity_level(self, score: float) -> MaturityLevel:
        """Determine maturity level from score"""
        if score >= 3.5:
            return MaturityLevel.ADAPTIVE
        elif score >= 2.5:
            return MaturityLevel.PREDICTIVE
        elif score >= 1.5:
            return MaturityLevel.PROACTIVE
        else:
            return MaturityLevel.REACTIVE
    
    def _get_recommendations(self) -> List[str]:
        """Get all recommendations"""
        recommendations = []
        for criterion in self.criteria.values():
            recommendations.extend(criterion.recommendations)
        return recommendations
    
    def _get_next_steps(self) -> List[str]:
        """Get prioritized next steps"""
        # Find criteria with largest gaps
        gaps = [
            (name, criterion.target_score - criterion.current_score)
            for name, criterion in self.criteria.items()
        ]
        
        # Sort by gap size
        gaps.sort(key=lambda x: x[1], reverse=True)
        
        next_steps = []
        for name, gap in gaps[:3]:  # Top 3 gaps
            if gap > 0:
                next_steps.append(f"Improve {name} (gap: {gap})")
        
        return next_steps

# Global maturity assessment
maturity_assessment = ObservabilityMaturityAssessment()
```

## 🔗 Integration Points

### Observability Integration

```python
# app/observability/integration.py
from typing import Dict, Any, Optional
from app.observability.golden_signals import golden_signals
from app.observability.business_metrics import business_metrics
from app.observability.log_correlation import correlated_logger, CorrelationContext
from app.observability.intelligent_alerting import alert_manager
from app.observability.correlation_engine import correlation_engine, CorrelationEvent
from datetime import datetime

class ObservabilityIntegration:
    """Integration layer for all observability components"""
    
    def __init__(self):
        self.golden_signals = golden_signals
        self.business_metrics = business_metrics
        self.logger = correlated_logger
        self.alert_manager = alert_manager
        self.correlation_engine = correlation_engine
    
    async def record_request(self, request_data: Dict[str, Any]):
        """Record request across all observability systems"""
        # Extract request info
        method = request_data['method']
        endpoint = request_data['endpoint']
        status_code = request_data['status_code']
        duration = request_data['duration']
        tenant_id = request_data.get('tenant_id', 'unknown')
        request_id = request_data.get('request_id')
        
        # Set correlation context
        with CorrelationContext(request_id=request_id, tenant_id=tenant_id):
            # Record golden signals
            self.golden_signals.record_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration,
                tenant_id=tenant_id
            )
            
            # Log request
            self.logger.info(
                "Request processed",
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration
            )
            
            # Check for alerts
            self.alert_manager.evaluate_metric('request_duration', duration)
            if status_code >= 500:
                self.alert_manager.evaluate_metric('error_rate', 1.0)
            
            # Add to correlation analysis
            self.correlation_engine.add_event(
                CorrelationEvent(
                    timestamp=datetime.now(),
                    source=f"request_{endpoint}",
                    event_type="response_time",
                    value=duration,
                    metadata={"method": method, "status_code": status_code}
                )
            )
    
    async def record_search_operation(self, search_data: Dict[str, Any]):
        """Record search operation across all systems"""
        search_type = search_data['search_type']
        dataset_id = search_data['dataset_id']
        tenant_id = search_data['tenant_id']
        duration = search_data['duration']
        results_count = search_data['results_count']
        
        # Record business metrics
        self.business_metrics.record_search(
            search_type=search_type,
            dataset_id=dataset_id,
            tenant_id=tenant_id,
            accuracy_score=search_data.get('accuracy_score'),
            complexity_score=search_data.get('complexity_score')
        )
        
        # Log search
        self.logger.info(
            "Search operation completed",
            search_type=search_type,
            dataset_id=dataset_id,
            duration=duration,
            results_count=results_count
        )
        
        # Check for alerts
        self.alert_manager.evaluate_metric('search_duration', duration)
        
        # Add to correlation analysis
        self.correlation_engine.add_event(
            CorrelationEvent(
                timestamp=datetime.now(),
                source=f"search_{search_type}",
                event_type="search_duration",
                value=duration,
                metadata={"dataset_id": dataset_id, "results_count": results_count}
            )
        )
    
    async def record_vector_operation(self, vector_data: Dict[str, Any]):
        """Record vector operation across all systems"""
        operation_type = vector_data['operation_type']
        dataset_id = vector_data['dataset_id']
        tenant_id = vector_data['tenant_id']
        vector_count = vector_data['vector_count']
        
        # Record business metrics
        self.business_metrics.record_vector_operation(
            dataset_id=dataset_id,
            tenant_id=tenant_id,
            operation_type=operation_type,
            vector_count=vector_count
        )
        
        # Log operation
        self.logger.info(
            "Vector operation completed",
            operation_type=operation_type,
            dataset_id=dataset_id,
            vector_count=vector_count
        )
    
    def get_observability_summary(self) -> Dict[str, Any]:
        """Get comprehensive observability summary"""
        return {
            "alerts": self.alert_manager.get_alert_summary(),
            "correlations": self.correlation_engine.get_correlation_summary(),
            "maturity": maturity_assessment.assess_maturity()
        }

# Global integration
observability = ObservabilityIntegration()
```

## 🔗 Related Documentation

- [Monitoring Guide](./monitoring.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [Performance Guide](./performance.md)
- [Security Guide](./security.md)
- [API Reference](./api/http/README.md)

## 📞 Support

For observability questions and support:
- **Observability Team**: [observability@yourcompany.com](mailto:observability@yourcompany.com)
- **Monitoring Documentation**: [docs.yourcompany.com/observability](https://docs.yourcompany.com/observability)
- **Grafana Instance**: [grafana.yourcompany.com](https://grafana.yourcompany.com)
- **Prometheus Instance**: [prometheus.yourcompany.com](https://prometheus.yourcompany.com)
- **Jaeger Instance**: [jaeger.yourcompany.com](https://jaeger.yourcompany.com)