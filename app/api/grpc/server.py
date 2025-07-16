"""gRPC server implementation."""

import asyncio
import grpc
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from app.config.settings import settings
from app.config.logging import get_logger, LoggingMixin
from app.api.grpc.handlers.dataset_handler import DatasetServicer
from app.api.grpc.handlers.vector_handler import VectorServicer
from app.api.grpc.handlers.search_handler import SearchServicer
from app.api.grpc.handlers.health_handler import HealthServicer
from app.services.deeplake_service import DeepLakeService
from app.services.auth_service import AuthService
from app.services.cache_service import CacheService
from app.services.metrics_service import MetricsService


class GRPCServer(LoggingMixin):
    """gRPC server wrapper."""
    
    def __init__(
        self,
        deeplake_service: DeepLakeService,
        auth_service: AuthService,
        cache_service: CacheService,
        metrics_service: MetricsService
    ):
        super().__init__()
        self.deeplake_service = deeplake_service
        self.auth_service = auth_service
        self.cache_service = cache_service
        self.metrics_service = metrics_service
        self.server: Optional[grpc.aio.Server] = None
        
    async def start(self) -> None:
        """Start the gRPC server."""
        try:
            # Create thread pool for blocking operations
            executor = ThreadPoolExecutor(max_workers=settings.grpc.max_workers)
            
            # Create server
            self.server = grpc.aio.server(executor)
            
            # Add servicers
            # Note: We would add the actual proto-generated servicers here
            # For now, we'll create placeholder servicers
            
            # In a full implementation, you would add:
            # deeplake_service_pb2_grpc.add_DatasetServiceServicer_to_server(
            #     DatasetServicer(self.deeplake_service, self.auth_service, self.metrics_service),
            #     self.server
            # )
            # deeplake_service_pb2_grpc.add_VectorServiceServicer_to_server(
            #     VectorServicer(self.deeplake_service, self.auth_service, self.metrics_service),
            #     self.server
            # )
            # deeplake_service_pb2_grpc.add_SearchServiceServicer_to_server(
            #     SearchServicer(self.deeplake_service, self.auth_service, self.metrics_service),
            #     self.server
            # )
            # deeplake_service_pb2_grpc.add_HealthServiceServicer_to_server(
            #     HealthServicer(self.metrics_service),
            #     self.server
            # )
            
            # Add secure port or insecure port
            listen_addr = f"{settings.grpc.host}:{settings.grpc.port}"
            self.server.add_insecure_port(listen_addr)
            
            # Start server
            await self.server.start()
            
            self.logger.info(
                "gRPC server started",
                host=settings.grpc.host,
                port=settings.grpc.port,
                max_workers=settings.grpc.max_workers
            )
            
        except Exception as e:
            self.logger.error("Failed to start gRPC server", error=str(e))
            raise
    
    async def stop(self) -> None:
        """Stop the gRPC server."""
        if self.server:
            try:
                await self.server.stop(grace=30)
                self.logger.info("gRPC server stopped")
            except Exception as e:
                self.logger.error("Error stopping gRPC server", error=str(e))
    
    async def wait_for_termination(self) -> None:
        """Wait for server termination."""
        if self.server:
            await self.server.wait_for_termination()


def create_grpc_server(
    deeplake_service: DeepLakeService,
    auth_service: AuthService,
    cache_service: CacheService,
    metrics_service: MetricsService
) -> GRPCServer:
    """Create and configure a gRPC server."""
    return GRPCServer(
        deeplake_service=deeplake_service,
        auth_service=auth_service,
        cache_service=cache_service,
        metrics_service=metrics_service
    )