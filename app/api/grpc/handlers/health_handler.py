"""Health service gRPC handler."""

import grpc
from datetime import datetime, timezone
from typing import Any, Dict

from app.config.logging import get_logger, LoggingMixin
from app.services.metrics_service import MetricsService
from app.config.settings import settings


class HealthServicer(LoggingMixin):
    """Health service gRPC handler."""
    
    def __init__(self, metrics_service: MetricsService):
        super().__init__()
        self.metrics_service = metrics_service
    
    async def Check(self, request: Any, context: Any) -> Any:
        """Health check endpoint."""
        import time
        start_time = time.time()
        
        try:
            # Check service health
            dependencies = {}
            
            # Check Deep Lake storage
            import os
            if os.path.exists(settings.deeplake.storage_location):
                dependencies["deeplake_storage"] = "healthy"
            else:
                dependencies["deeplake_storage"] = "unhealthy"
            
            # Determine overall status
            unhealthy_deps = [k for k, v in dependencies.items() if v == "unhealthy"]
            overall_status = "unhealthy" if unhealthy_deps else "healthy"
            
            # Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_grpc_request(
                "HealthService", "Check", "OK", duration, None
            )
            
            return {
                "status": overall_status,
                "service": "Tributary AI services for DeepLake",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dependencies": dependencies
            }
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "HealthService", "Check", "INTERNAL", time.time() - start_time, None
            )
            self.logger.error("Unexpected error in health check", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise
    
    async def GetMetrics(self, request: Any, context: Any) -> Any:
        """Get service metrics."""
        import time
        start_time = time.time()
        
        try:
            # Get metrics summary
            metrics_summary = self.metrics_service.get_metrics_summary()
            
            # Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_grpc_request(
                "HealthService", "GetMetrics", "OK", duration, None
            )
            
            return {
                "metrics": {str(k): float(v) for k, v in metrics_summary.items() if isinstance(v, (int, float))},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.metrics_service.record_grpc_request(
                "HealthService", "GetMetrics", "INTERNAL", time.time() - start_time, None
            )
            self.logger.error("Unexpected error in GetMetrics", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            raise