"""
Vector indexing service for optimized search performance.

Supports multiple indexing algorithms:
- HNSW (Hierarchical Navigable Small World)
- IVF (Inverted File Index)
- Flat (brute-force search)
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from app.config.logging import get_logger, LoggingMixin
from app.config.settings import settings
from app.models.exceptions import IndexingException, ValidationException


class IndexType(Enum):
    """Supported index types."""
    FLAT = "flat"
    HNSW = "hnsw"
    IVF = "ivf"
    DEFAULT = "default"  # Let DeepLake decide


@dataclass
class HNSWParameters:
    """HNSW index parameters."""
    m: int = 16  # Number of bi-directional links created for each node
    ef_construction: int = 200  # Size of the dynamic candidate list
    ef_search: int = 50  # Size of the dynamic list for search
    max_elements: int = 1000000  # Maximum number of elements in the index
    seed: int = 42  # Random seed for reproducibility
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DeepLake."""
        return {
            "m": self.m,
            "ef_construction": self.ef_construction,
            "ef": self.ef_search,
            "max_elements": self.max_elements,
            "seed": self.seed
        }


@dataclass
class IVFParameters:
    """IVF index parameters."""
    nlist: int = 100  # Number of clusters
    nprobe: int = 10  # Number of clusters to search
    quantizer_type: str = "flat"  # Type of quantizer
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DeepLake."""
        return {
            "nlist": self.nlist,
            "nprobe": self.nprobe,
            "quantizer": self.quantizer_type
        }


@dataclass
class IndexConfig:
    """Index configuration."""
    index_type: IndexType
    metric_type: str
    dimensions: int
    hnsw_params: Optional[HNSWParameters] = None
    ivf_params: Optional[IVFParameters] = None
    
    def get_index_params(self) -> Dict[str, Any]:
        """Get index parameters based on type."""
        if self.index_type == IndexType.HNSW and self.hnsw_params:
            return self.hnsw_params.to_dict()
        elif self.index_type == IndexType.IVF and self.ivf_params:
            return self.ivf_params.to_dict()
        return {}


@dataclass
class IndexStats:
    """Index statistics."""
    index_type: str
    total_vectors: int
    index_size_bytes: int
    build_time_seconds: float
    last_updated: str
    parameters: Dict[str, Any]
    is_trained: bool = True
    training_vectors: int = 0


class IndexService(LoggingMixin):
    """Service for managing vector indexes."""
    
    def __init__(self):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=settings.performance.deeplake_thread_pool_workers)
        self.indexes: Dict[str, Any] = {}
        
    async def create_index(
        self,
        dataset: Any,
        index_config: IndexConfig,
        force_rebuild: bool = False
    ) -> IndexStats:
        """
        Create or update an index for a dataset.
        
        Args:
            dataset: DeepLake dataset object
            index_config: Index configuration
            force_rebuild: Force rebuild even if index exists
            
        Returns:
            Index statistics
        """
        start_time = time.time()
        
        try:
            # Check if index already exists and if rebuild is needed
            if not force_rebuild and self._has_valid_index(dataset, index_config):
                self.logger.info("Using existing index", index_type=index_config.index_type.value)
                return await self.get_index_stats(dataset)
            
            # Build index based on type
            if index_config.index_type == IndexType.HNSW:
                stats = await self._build_hnsw_index(dataset, index_config)
            elif index_config.index_type == IndexType.IVF:
                stats = await self._build_ivf_index(dataset, index_config)
            elif index_config.index_type == IndexType.FLAT:
                stats = await self._build_flat_index(dataset, index_config)
            else:
                # Default - let DeepLake handle it
                stats = await self._build_default_index(dataset, index_config)
            
            build_time = time.time() - start_time
            stats.build_time_seconds = build_time
            
            self.logger.info(
                "Index created successfully",
                index_type=index_config.index_type.value,
                build_time=build_time,
                vectors=stats.total_vectors
            )
            
            return stats
            
        except Exception as e:
            self.logger.error("Failed to create index", error=str(e))
            raise IndexingException(f"Failed to create index: {str(e)}")
    
    async def _build_hnsw_index(
        self,
        dataset: Any,
        index_config: IndexConfig
    ) -> IndexStats:
        """Build HNSW index."""
        loop = asyncio.get_event_loop()
        
        # Get HNSW parameters
        params = index_config.hnsw_params or HNSWParameters()
        
        # Check if we have enough vectors
        num_vectors = len(dataset)
        if num_vectors < 100:
            self.logger.warning(
                "Not enough vectors for HNSW index, falling back to flat index",
                num_vectors=num_vectors
            )
            return await self._build_flat_index(dataset, index_config)
        
        # Adjust parameters based on dataset size
        if num_vectors < 10000:
            params.m = min(params.m, 8)
            params.ef_construction = min(params.ef_construction, 100)
        elif num_vectors > 1000000:
            params.m = max(params.m, 32)
            params.ef_construction = max(params.ef_construction, 400)
        
        self.logger.info(
            "Building HNSW index",
            num_vectors=num_vectors,
            m=params.m,
            ef_construction=params.ef_construction
        )
        
        # Build index using DeepLake's HNSW support
        # Note: DeepLake 4.0 might have different API, adjust as needed
        try:
            # Create index configuration
            index_params = {
                "type": "hnsw",
                "distance": index_config.metric_type,
                "hnsw_m": params.m,
                "hnsw_ef_construction": params.ef_construction,
                "hnsw_ef": params.ef_search,
                "hnsw_max_elements": params.max_elements,
            }
            
            # Apply index to embedding column
            await loop.run_in_executor(
                self.executor,
                lambda: dataset.embedding.create_index(index_params)
            )
            
            # Get index size (approximate)
            index_size = num_vectors * params.m * 8  # Rough estimate
            
            return IndexStats(
                index_type="hnsw",
                total_vectors=num_vectors,
                index_size_bytes=index_size,
                build_time_seconds=0,  # Will be set by caller
                last_updated=time.strftime("%Y-%m-%d %H:%M:%S"),
                parameters=params.to_dict(),
                is_trained=True
            )
            
        except Exception as e:
            # If HNSW is not supported, fall back to flat index
            self.logger.warning(f"HNSW index creation failed: {e}, falling back to flat index")
            return await self._build_flat_index(dataset, index_config)
    
    async def _build_ivf_index(
        self,
        dataset: Any,
        index_config: IndexConfig
    ) -> IndexStats:
        """Build IVF index."""
        loop = asyncio.get_event_loop()
        
        # Get IVF parameters
        params = index_config.ivf_params or IVFParameters()
        
        # Check if we have enough vectors
        num_vectors = len(dataset)
        if num_vectors < params.nlist * 40:
            self.logger.warning(
                "Not enough vectors for IVF index, falling back to flat index",
                num_vectors=num_vectors,
                nlist=params.nlist
            )
            return await self._build_flat_index(dataset, index_config)
        
        self.logger.info(
            "Building IVF index",
            num_vectors=num_vectors,
            nlist=params.nlist,
            nprobe=params.nprobe
        )
        
        try:
            # Create index configuration
            index_params = {
                "type": "ivf",
                "distance": index_config.metric_type,
                "ivf_nlist": params.nlist,
                "ivf_nprobe": params.nprobe,
            }
            
            # Apply index to embedding column
            await loop.run_in_executor(
                self.executor,
                lambda: dataset.embedding.create_index(index_params)
            )
            
            # Get index size (approximate)
            index_size = num_vectors * 4 + params.nlist * index_config.dimensions * 4
            
            return IndexStats(
                index_type="ivf",
                total_vectors=num_vectors,
                index_size_bytes=index_size,
                build_time_seconds=0,
                last_updated=time.strftime("%Y-%m-%d %H:%M:%S"),
                parameters=params.to_dict(),
                is_trained=True,
                training_vectors=min(num_vectors, params.nlist * 256)
            )
            
        except Exception as e:
            self.logger.warning(f"IVF index creation failed: {e}, falling back to flat index")
            return await self._build_flat_index(dataset, index_config)
    
    async def _build_flat_index(
        self,
        dataset: Any,
        index_config: IndexConfig
    ) -> IndexStats:
        """Build flat (brute-force) index."""
        num_vectors = len(dataset)
        
        self.logger.info("Using flat index", num_vectors=num_vectors)
        
        # Flat index doesn't need building, it's brute-force
        index_size = num_vectors * index_config.dimensions * 4  # float32
        
        return IndexStats(
            index_type="flat",
            total_vectors=num_vectors,
            index_size_bytes=index_size,
            build_time_seconds=0,
            last_updated=time.strftime("%Y-%m-%d %H:%M:%S"),
            parameters={},
            is_trained=True
        )
    
    async def _build_default_index(
        self,
        dataset: Any,
        index_config: IndexConfig
    ) -> IndexStats:
        """Let DeepLake choose the best index."""
        num_vectors = len(dataset)
        
        self.logger.info("Using default DeepLake indexing", num_vectors=num_vectors)
        
        # DeepLake will choose based on dataset size and characteristics
        return IndexStats(
            index_type="default",
            total_vectors=num_vectors,
            index_size_bytes=0,  # Unknown
            build_time_seconds=0,
            last_updated=time.strftime("%Y-%m-%d %H:%M:%S"),
            parameters={},
            is_trained=True
        )
    
    def _has_valid_index(self, dataset: Any, index_config: IndexConfig) -> bool:
        """Check if dataset has a valid index of the requested type."""
        # In DeepLake 4.0, we might need to check index metadata
        # For now, assume no index exists
        return False
    
    async def get_index_stats(self, dataset: Any) -> IndexStats:
        """Get statistics for the current index."""
        num_vectors = len(dataset)
        
        # Try to get index info from dataset
        # This is placeholder - adjust based on DeepLake 4.0 API
        return IndexStats(
            index_type="unknown",
            total_vectors=num_vectors,
            index_size_bytes=0,
            build_time_seconds=0,
            last_updated=time.strftime("%Y-%m-%d %H:%M:%S"),
            parameters={},
            is_trained=True
        )
    
    async def optimize_index(
        self,
        dataset: Any,
        target_recall: float = 0.95,
        sample_queries: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Optimize index parameters for target recall.
        
        Args:
            dataset: DeepLake dataset
            target_recall: Target recall rate (0-1)
            sample_queries: Sample query vectors for testing
            
        Returns:
            Optimized parameters and performance metrics
        """
        self.logger.info("Optimizing index parameters", target_recall=target_recall)
        
        # This would involve testing different parameter combinations
        # and measuring recall vs speed trade-offs
        
        # Placeholder for now
        return {
            "optimized_params": {},
            "achieved_recall": target_recall,
            "queries_per_second": 1000
        }
    
    def get_search_params(
        self,
        index_type: IndexType,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get optimized search parameters for index type.
        
        Args:
            index_type: Type of index
            options: Search options
            
        Returns:
            Search parameters
        """
        params = {}
        
        if index_type == IndexType.HNSW:
            # Use ef_search from options or default
            ef_search = options.get("ef_search", 50) if options else 50
            params["hnsw_ef"] = ef_search
            
        elif index_type == IndexType.IVF:
            # Use nprobe from options or default
            nprobe = options.get("nprobe", 10) if options else 10
            params["ivf_nprobe"] = nprobe
        
        return params
    
    async def close(self):
        """Close the index service."""
        self.executor.shutdown(wait=True)
        self.indexes.clear()