"""Core Deep Lake service implementation."""

import os
import hashlib
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor

import deeplake
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config.settings import settings
from app.config.logging import get_logger, LoggingMixin
from app.models.schemas import (
    DatasetCreate, DatasetUpdate, DatasetResponse, DatasetStats,
    VectorCreate, VectorUpdate, VectorResponse, VectorBatchInsert, VectorBatchResponse,
    SearchRequest, SearchResponse, SearchResultItem, SearchStats, SearchOptions
)
from app.models.exceptions import (
    DatasetNotFoundException, DatasetAlreadyExistsException,
    VectorNotFoundException, InvalidVectorDimensionsException,
    InvalidSearchParametersException, StorageException
)
from app.services.index_service import IndexService, IndexType, IndexConfig, HNSWParameters, IVFParameters


class DeepLakeService(LoggingMixin):
    """Core service for Deep Lake operations."""
    
    def __init__(self) -> None:
        super().__init__()
        self.storage_location = settings.deeplake.storage_location
        self.token = settings.deeplake.token
        self.org_id = settings.deeplake.org_id
        self.datasets: Dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=settings.performance.deeplake_thread_pool_workers)
        self.index_service = IndexService()
        
        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_location, exist_ok=True)
        
        self.logger.info("DeepLakeService initialized", storage_location=self.storage_location)
    
    async def close(self) -> None:
        """Close the service and clean up resources."""
        self.executor.shutdown(wait=True)
        await self.index_service.close()
        for dataset in self.datasets.values():
            try:
                if hasattr(dataset, 'close'):
                    dataset.close()
            except Exception as e:
                self.logger.error("Error closing dataset", error=str(e))
        self.logger.info("DeepLakeService closed")
    
    def _get_dataset_path(self, dataset_name: str, tenant_id: Optional[str] = None) -> str:
        """Get the full path for a dataset."""
        if tenant_id:
            return os.path.join(self.storage_location, tenant_id, dataset_name)
        return os.path.join(self.storage_location, dataset_name)
    
    def _get_dataset_key(self, dataset_name: str, tenant_id: Optional[str] = None) -> str:
        """Get the cache key for a dataset."""
        if tenant_id:
            return f"{tenant_id}:{dataset_name}"
        return dataset_name
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _load_dataset(self, dataset_path: str, read_only: bool = False) -> Any:
        """Load a Deep Lake dataset with retry logic."""
        try:
            loop = asyncio.get_event_loop()
            # Deep Lake 4.0 only supports token parameter, not read_only
            load_kwargs: Dict[str, Any] = {}
            if self.token:
                load_kwargs["token"] = self.token
            
            return await loop.run_in_executor(
                self.executor,
                lambda: deeplake.open(dataset_path, **load_kwargs)
            )
        except Exception as e:
            self.logger.error("Failed to load dataset", path=dataset_path, error=str(e))
            raise StorageException(f"Failed to load dataset: {str(e)}", "load_dataset")
    
    async def create_dataset(
        self,
        dataset_create: DatasetCreate,
        tenant_id: Optional[str] = None
    ) -> DatasetResponse:
        """Create a new Deep Lake dataset."""
        dataset_key = self._get_dataset_key(dataset_create.name, tenant_id)
        dataset_path = self._get_dataset_path(dataset_create.name, tenant_id)
        
        self.logger.info(
            "Creating dataset",
            name=dataset_create.name,
            tenant_id=tenant_id,
            path=dataset_path
        )
        
        # Check if dataset already exists
        if os.path.exists(dataset_path) and not dataset_create.overwrite:
            raise DatasetAlreadyExistsException(dataset_create.name, tenant_id)
        
        # Always clean up existing dataset to avoid corruption
        if os.path.exists(dataset_path):
            import shutil
            shutil.rmtree(dataset_path, ignore_errors=True)
            self.logger.info(f"Cleaned up existing dataset: {dataset_path}")
        
        try:
            # Create dataset directory if needed
            os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
            
            # Dataset cleanup already handled above
            
            # Create Deep Lake dataset with 4.0 API using schema
            loop = asyncio.get_event_loop()
            # Only pass token if it's not None or empty
            create_kwargs: Dict[str, Any] = {}
            if self.token:
                create_kwargs["token"] = self.token
            
            # Define comprehensive schema for Deep Lake 4.0 compatibility
            import deeplake
            # Schema matching the corrected payload format with metadata support
            schema = {
                'id': deeplake.types.Text(),
                'document_id': deeplake.types.Text(), 
                'embedding': deeplake.types.Array(deeplake.types.Float32(), shape=[dataset_create.dimensions]),
                'content': deeplake.types.Text(),
                'chunk_count': deeplake.types.Int32(),
                'metadata': deeplake.types.Text(),  # JSON string for metadata
                'chunk_id': deeplake.types.Text(),
                'content_hash': deeplake.types.Text(),
                'content_type': deeplake.types.Text(),
                'language': deeplake.types.Text(),
                'chunk_index': deeplake.types.Int32(),
                'model': deeplake.types.Text(),
                'created_at': deeplake.types.Text(),
                'updated_at': deeplake.types.Text()
            }
            
            create_kwargs["schema"] = schema
            
            dataset = await loop.run_in_executor(
                self.executor,
                lambda: deeplake.create(dataset_path, **create_kwargs)
            )
            
            # Store dataset metadata in our own tracking (Deep Lake 4.0 doesn't use .info)
            dataset_metadata = {
                'name': dataset_create.name,
                'description': dataset_create.description or '',
                'dimensions': dataset_create.dimensions,
                'metric_type': dataset_create.metric_type,
                'index_type': dataset_create.index_type,
                'tenant_id': tenant_id or '',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }
            
            # Add custom metadata
            if dataset_create.metadata:
                dataset_metadata.update(dataset_create.metadata)
            
            # Store metadata in a JSON file alongside the dataset
            metadata_path = os.path.join(dataset_path, 'dataset_metadata.json')
            with open(metadata_path, 'w') as f:
                import json
                json.dump(dataset_metadata, f, indent=2)
            
            # Cache the dataset
            self.datasets[dataset_key] = dataset
            
            self.logger.info("Dataset created successfully", name=dataset_create.name)
            
            return DatasetResponse(
                id=dataset_create.name,
                name=dataset_create.name,
                description=dataset_create.description,
                dimensions=dataset_create.dimensions,
                metric_type=dataset_create.metric_type,
                index_type=dataset_create.index_type,
                metadata=dataset_create.metadata or {},
                storage_location=dataset_path,
                vector_count=0,
                storage_size=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                tenant_id=tenant_id
            )
            
        except Exception as e:
            self.logger.error("Failed to create dataset", name=dataset_create.name, error=str(e))
            raise StorageException(f"Failed to create dataset: {str(e)}", "create_dataset")
    
    async def get_dataset(
        self,
        dataset_id: str,
        tenant_id: Optional[str] = None
    ) -> DatasetResponse:
        """Get dataset information."""
        dataset_key = self._get_dataset_key(dataset_id, tenant_id)
        dataset_path = self._get_dataset_path(dataset_id, tenant_id)
        
        if not os.path.exists(dataset_path):
            raise DatasetNotFoundException(dataset_id, tenant_id)
        
        try:
            # Load dataset if not cached
            if dataset_key not in self.datasets:
                self.datasets[dataset_key] = await self._load_dataset(dataset_path, read_only=True)
            
            dataset = self.datasets[dataset_key]
            
            # Load metadata from our JSON file instead of dataset.info
            info = await self._load_dataset_metadata(dataset_path)
            
            return DatasetResponse(
                id=dataset_id,
                name=info.get('name', dataset_id),
                description=info.get('description', ''),
                dimensions=info.get('dimensions', 0),
                metric_type=info.get('metric_type', 'cosine'),
                index_type=info.get('index_type', 'default'),
                metadata={k: v for k, v in info.items() if k not in ['name', 'description', 'dimensions', 'metric_type', 'index_type', 'tenant_id', 'created_at', 'updated_at']},
                storage_location=dataset_path,
                vector_count=len(dataset),
                storage_size=self._get_directory_size(dataset_path),
                created_at=datetime.fromisoformat(info.get('created_at', datetime.now(timezone.utc).isoformat())),
                updated_at=datetime.fromisoformat(info.get('updated_at', datetime.now(timezone.utc).isoformat())),
                tenant_id=tenant_id
            )
            
        except DatasetNotFoundException:
            # Re-raise DatasetNotFoundException as-is
            raise
        except Exception as e:
            self.logger.error("Failed to get dataset", dataset_id=dataset_id, error=str(e))
            raise StorageException(f"Failed to get dataset: {str(e)}", "get_dataset")
    
    async def list_datasets(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DatasetResponse]:
        """List all datasets for a tenant."""
        datasets: List[DatasetResponse] = []
        
        try:
            base_path = os.path.join(self.storage_location, tenant_id) if tenant_id else self.storage_location
            
            if not os.path.exists(base_path):
                return datasets
            
            # Get all dataset directories
            dataset_dirs = []
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                if os.path.isdir(item_path) and self._is_deeplake_dataset(item_path):
                    dataset_dirs.append(item)
            
            # Sort and paginate
            dataset_dirs.sort()
            dataset_dirs = dataset_dirs[offset:offset + limit]
            
            # Load dataset info
            for dataset_name in dataset_dirs:
                try:
                    dataset_response = await self.get_dataset(dataset_name, tenant_id)
                    datasets.append(dataset_response)
                except Exception as e:
                    self.logger.warning("Failed to load dataset", dataset_name=dataset_name, error=str(e))
                    continue
            
            return datasets
            
        except Exception as e:
            self.logger.error("Failed to list datasets", error=str(e))
            raise StorageException(f"Failed to list datasets: {str(e)}", "list_datasets")
    
    async def delete_dataset(
        self,
        dataset_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """Delete a dataset."""
        dataset_key = self._get_dataset_key(dataset_id, tenant_id)
        dataset_path = self._get_dataset_path(dataset_id, tenant_id)
        
        if not os.path.exists(dataset_path):
            raise DatasetNotFoundException(dataset_id, tenant_id)
        
        try:
            # Remove from cache
            if dataset_key in self.datasets:
                dataset = self.datasets[dataset_key]
                if hasattr(dataset, 'close'):
                    dataset.close()
                del self.datasets[dataset_key]
            
            # Delete dataset directory
            import shutil
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: shutil.rmtree(dataset_path)
            )
            
            self.logger.info("Dataset deleted", dataset_id=dataset_id)
            
        except Exception as e:
            self.logger.error("Failed to delete dataset", dataset_id=dataset_id, error=str(e))
            raise StorageException(f"Failed to delete dataset: {str(e)}", "delete_dataset")
    
    async def insert_vectors(
        self,
        dataset_id: str,
        vectors: List[VectorCreate],
        tenant_id: Optional[str] = None,
        skip_existing: bool = False,
        overwrite: bool = False
    ) -> VectorBatchResponse:
        """Insert vectors into a dataset."""
        start_time = time.time()
        dataset_key = self._get_dataset_key(dataset_id, tenant_id)
        dataset_path = self._get_dataset_path(dataset_id, tenant_id)
        
        if not os.path.exists(dataset_path):
            raise DatasetNotFoundException(dataset_id, tenant_id)
        
        try:
            # Load dataset
            self.logger.info("Loading dataset for vector insertion", dataset_id=dataset_id, dataset_key=dataset_key, dataset_path=dataset_path)
            if dataset_key not in self.datasets:
                self.datasets[dataset_key] = await self._load_dataset(dataset_path, read_only=False)
            
            dataset = self.datasets[dataset_key]
            self.logger.info("Dataset loaded successfully", dataset_id=dataset_id, dataset_length=len(dataset))
            
            # Get dataset dimensions from our metadata
            dataset_info = await self._load_dataset_metadata(dataset_path)
            expected_dimensions = dataset_info.get('dimensions', 0)
            self.logger.info("Dataset metadata loaded", dataset_id=dataset_id, expected_dimensions=expected_dimensions)
            
            inserted_count = 0
            skipped_count = 0
            failed_count = 0
            error_messages = []
            
            # Process vectors
            for vector in vectors:
                try:
                    # Validate dimensions
                    if len(vector.values) != expected_dimensions:
                        raise InvalidVectorDimensionsException(expected_dimensions, len(vector.values))
                    
                    # Generate ID if not provided
                    vector_id = vector.id or str(uuid.uuid4())
                    
                    # Check if vector exists
                    if skip_existing and self._vector_exists(dataset, vector_id):
                        skipped_count += 1
                        continue
                    
                    # Create vector data
                    now = datetime.now(timezone.utc).isoformat()
                    content_hash = hashlib.sha256((vector.content or '').encode()).hexdigest()
                    
                    # Serialize metadata as JSON string
                    import json
                    metadata_json = json.dumps(vector.metadata or {})
                    
                    # Data matching the comprehensive payload format with metadata
                    vector_data = {
                        'id': str(vector_id),
                        'document_id': str(vector.document_id),
                        'embedding': np.array(vector.values, dtype=np.float32),
                        'content': str(vector.content or ''),
                        'chunk_count': int(vector.chunk_count or 1),
                        'metadata': metadata_json,
                        'chunk_id': str(vector.chunk_id or ''),
                        'content_hash': content_hash,
                        'content_type': str(vector.content_type or ''),
                        'language': str(vector.language or ''),
                        'chunk_index': int(vector.chunk_index or 0),
                        'model': str(vector.model or ''),
                        'created_at': now,
                        'updated_at': now
                    }
                    
                    self.logger.debug("Appending vector to dataset", vector_id=vector_id, data_keys=list(vector_data.keys()))
                    
                    # Append to dataset with correct Deep Lake v4 format
                    # For single samples, Deep Lake v4 expects a list containing a dictionary: [{...}]
                    try:
                        dataset.append([vector_data])  # Wrap in list for single sample
                        inserted_count += 1
                    except Exception as append_error:
                        # Handle specific Deep Lake 4.0 append errors
                        if "FileNotFoundError" in str(append_error) or "chunks" in str(append_error):
                            self.logger.error("Dataset corruption detected during append", error=str(append_error))
                            # Try to recreate the dataset
                            raise StorageException(f"Dataset corruption detected: {str(append_error)}", "dataset_append")
                        else:
                            raise append_error
                    
                except Exception as e:
                    failed_count += 1
                    error_messages.append(f"Vector {vector.id or 'unknown'}: {str(e)}")
                    self.logger.warning("Failed to insert vector", vector_id=vector.id, error=str(e))
            
            # Commit changes (with retry for concurrent access)
            loop = asyncio.get_event_loop()
            max_retries = 5
            for retry in range(max_retries):
                try:
                    await loop.run_in_executor(self.executor, dataset.commit)
                    break
                except RuntimeError as e:
                    # Check for lock file errors (including the specific pattern seen in logs)
                    error_str = str(e).lower()
                    if ("index.lock" in error_str or "lock" in error_str) and retry < max_retries - 1:
                        # Wait longer for heavily contended operations
                        wait_time = 0.2 * (2 ** retry)  # Exponential backoff: 0.2, 0.4, 0.8, 1.6 seconds
                        await asyncio.sleep(wait_time)
                        self.logger.warning(f"Dataset commit retry {retry + 1} after {wait_time}s", dataset_id=dataset_id, error=str(e))
                        continue
                    else:
                        raise
            
            # Check if we need to build/update index
            dataset_info = await self._load_dataset_metadata(dataset_path)
            index_type_str = dataset_info.get('index_type', 'default')
            
            # Build index if we have enough vectors and index type is specified
            vector_count = len(dataset)
            if vector_count >= 1000 and index_type_str != 'flat':
                try:
                    await self._build_or_update_index(dataset, dataset_info, dataset_id)
                except Exception as e:
                    self.logger.warning(f"Failed to build index: {e}, continuing without index")
            
            processing_time = (time.time() - start_time) * 1000
            
            # Check if we need to build/rebuild index for large datasets
            current_vector_count = len(dataset)
            index_type = dataset_info.get('index_type', 'default')
            
            # Auto-create IVF index for datasets with many vectors
            if (inserted_count > 0 and current_vector_count >= 10000 and 
                index_type in ['default', 'ivf']):
                
                try:
                    self.logger.info("Auto-creating IVF index for large dataset", 
                                   dataset_id=dataset_id, vector_count=current_vector_count)
                    
                    # Create IVF index configuration
                    ivf_params = IVFParameters(
                        nlist=min(max(int(current_vector_count / 100), 100), 4096),
                        nprobe=min(max(int(current_vector_count / 1000), 10), 128)
                    )
                    
                    index_config = IndexConfig(
                        index_type=IndexType.IVF,
                        metric_type=dataset_info.get('metric_type', 'cosine'),
                        dimensions=expected_dimensions,
                        ivf_params=ivf_params
                    )
                    
                    # Build index asynchronously
                    index_stats = await self.index_service.create_index(
                        dataset, index_config, force_rebuild=False
                    )
                    
                    self.logger.info("IVF index created successfully", 
                                   dataset_id=dataset_id, 
                                   build_time=index_stats.build_time_seconds,
                                   nlist=ivf_params.nlist)
                                   
                except Exception as e:
                    # Index creation failure shouldn't fail the entire operation
                    self.logger.warning("Failed to create IVF index", 
                                      dataset_id=dataset_id, error=str(e))
            
            self.logger.info(
                "Vectors inserted",
                dataset_id=dataset_id,
                inserted=inserted_count,
                skipped=skipped_count,
                failed=failed_count,
                processing_time_ms=processing_time
            )
            
            return VectorBatchResponse(
                inserted_count=inserted_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
                error_messages=error_messages,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            self.logger.error("Failed to insert vectors", dataset_id=dataset_id, error=str(e), exc_info=True)
            raise StorageException(f"Failed to insert vectors: {str(e)}", "insert_vectors")
    
    async def create_index(
        self,
        dataset_id: str,
        index_type: str = "ivf",
        parameters: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create an index for a dataset."""
        dataset_key = self._get_dataset_key(dataset_id, tenant_id)
        dataset_path = self._get_dataset_path(dataset_id, tenant_id)
        
        if not os.path.exists(dataset_path):
            raise DatasetNotFoundException(dataset_id, tenant_id)
        
        try:
            # Load dataset
            if dataset_key not in self.datasets:
                self.datasets[dataset_key] = await self._load_dataset(dataset_path, read_only=False)
            
            dataset = self.datasets[dataset_key]
            dataset_info = await self._load_dataset_metadata(dataset_path)
            
            # Create index configuration
            if index_type.lower() == "ivf":
                ivf_params = IVFParameters()
                if parameters:
                    if "nlist" in parameters:
                        ivf_params.nlist = int(parameters["nlist"])
                    if "nprobe" in parameters:
                        ivf_params.nprobe = int(parameters["nprobe"])
                
                index_config = IndexConfig(
                    index_type=IndexType.IVF,
                    metric_type=dataset_info.get('metric_type', 'cosine'),
                    dimensions=dataset_info.get('dimensions', 0),
                    ivf_params=ivf_params
                )
            elif index_type.lower() == "hnsw":
                hnsw_params = HNSWParameters()
                if parameters:
                    if "m" in parameters:
                        hnsw_params.m = int(parameters["m"])
                    if "ef_construction" in parameters:
                        hnsw_params.ef_construction = int(parameters["ef_construction"])
                    if "ef_search" in parameters:
                        hnsw_params.ef_search = int(parameters["ef_search"])
                
                index_config = IndexConfig(
                    index_type=IndexType.HNSW,
                    metric_type=dataset_info.get('metric_type', 'cosine'),
                    dimensions=dataset_info.get('dimensions', 0),
                    hnsw_params=hnsw_params
                )
            elif index_type.lower() == "flat":
                index_config = IndexConfig(
                    index_type=IndexType.FLAT,
                    metric_type=dataset_info.get('metric_type', 'cosine'),
                    dimensions=dataset_info.get('dimensions', 0)
                )
            else:
                raise ValidationException(f"Unsupported index type: {index_type}")
            
            # Create the index
            self.logger.info("Creating index", dataset_id=dataset_id, index_type=index_type)
            index_stats = await self.index_service.create_index(
                dataset, index_config, force_rebuild=True
            )
            
            self.logger.info("Index created successfully", 
                           dataset_id=dataset_id,
                           index_type=index_type,
                           build_time=index_stats.build_time_seconds,
                           vector_count=index_stats.total_vectors)
            
            return {
                "index_type": index_stats.index_type,
                "total_vectors": index_stats.total_vectors,
                "index_size_bytes": index_stats.index_size_bytes,
                "build_time_seconds": index_stats.build_time_seconds,
                "parameters": index_stats.parameters,
                "is_trained": index_stats.is_trained,
                "created_at": index_stats.last_updated
            }
            
        except Exception as e:
            self.logger.error("Failed to create index", dataset_id=dataset_id, error=str(e))
            raise StorageException(f"Failed to create index: {str(e)}", "create_index")
    
    async def get_index_info(
        self,
        dataset_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get information about dataset's current index."""
        dataset_key = self._get_dataset_key(dataset_id, tenant_id)
        dataset_path = self._get_dataset_path(dataset_id, tenant_id)
        
        if not os.path.exists(dataset_path):
            raise DatasetNotFoundException(dataset_id, tenant_id)
        
        try:
            # Load dataset
            if dataset_key not in self.datasets:
                self.datasets[dataset_key] = await self._load_dataset(dataset_path, read_only=True)
            
            dataset = self.datasets[dataset_key]
            
            # Get index statistics
            index_stats = await self.index_service.get_index_stats(dataset)
            
            return {
                "index_type": index_stats.index_type,
                "total_vectors": index_stats.total_vectors,
                "index_size_bytes": index_stats.index_size_bytes,
                "build_time_seconds": index_stats.build_time_seconds,
                "parameters": index_stats.parameters,
                "is_trained": index_stats.is_trained,
                "last_updated": index_stats.last_updated
            }
            
        except Exception as e:
            self.logger.error("Failed to get index info", dataset_id=dataset_id, error=str(e))
            return None
    
    async def search_vectors(
        self,
        dataset_id: str,
        query_vector: List[float],
        options: SearchOptions,
        tenant_id: Optional[str] = None
    ) -> SearchResponse:
        """Search for similar vectors."""
        start_time = time.time()
        dataset_key = self._get_dataset_key(dataset_id, tenant_id)
        dataset_path = self._get_dataset_path(dataset_id, tenant_id)
        
        if not os.path.exists(dataset_path):
            raise DatasetNotFoundException(dataset_id, tenant_id)
        
        try:
            # Load dataset
            if dataset_key not in self.datasets:
                self.datasets[dataset_key] = await self._load_dataset(dataset_path, read_only=True)
            
            dataset = self.datasets[dataset_key]
            
            # Validate query vector dimensions using our metadata
            dataset_info = await self._load_dataset_metadata(dataset_path)
            expected_dimensions = dataset_info.get('dimensions', 0)
            if len(query_vector) != expected_dimensions:
                raise InvalidVectorDimensionsException(expected_dimensions, len(query_vector))
            
            # Perform search
            query_embedding = np.array(query_vector, dtype=np.float32)
            
            # Get dataset metric type from metadata
            dataset_info = await self._load_dataset_metadata(dataset_path)
            dataset_metric = dataset_info.get('metric_type', 'cosine')
            
            # Use search options metric override if provided
            metric_type = options.metric_type or dataset_metric
            
            # Get index type and search parameters
            index_type_str = dataset_info.get('index_type', 'default')
            try:
                index_type = IndexType(index_type_str)
            except ValueError:
                index_type = IndexType.DEFAULT
            
            # Get search parameters based on index type
            search_params = self.index_service.get_search_params(
                index_type,
                {
                    "ef_search": options.ef_search,
                    "nprobe": options.nprobe
                } if options.ef_search or options.nprobe else None
            )
            
            # Build search query based on metric type
            # Note: Deep Lake may not support all distance functions in SQL queries
            # We'll use a simple approach that gets all results and then sort/filter in Python
            search_query = f"SELECT * LIMIT {options.top_k * 10}"  # Get more results to sort later
            
            # Use Deep Lake's search functionality (4.0 API)
            self.logger.info(f"Executing search query: {search_query}")
            loop = asyncio.get_event_loop()
            search_results = await loop.run_in_executor(
                self.executor,
                lambda: dataset.query(search_query)
            )
            self.logger.info(f"Search returned {len(search_results)} raw results")
            
            # Process results and calculate similarities
            candidates = []
            self.logger.info(f"Processing {len(search_results)} search results")
            for i, result in enumerate(search_results):
                try:
                    self.logger.debug(f"Processing result {i}: {result}")
                    # DeepLake 4.0 returns RowView objects, not dictionaries
                    # Extract embedding values
                    embedding_values = []
                    try:
                        embedding_data = result['embedding']
                        if hasattr(embedding_data, 'tolist'):
                            embedding_values = embedding_data.tolist()
                        elif hasattr(embedding_data, '__iter__'):
                            embedding_values = list(embedding_data)
                        else:
                            embedding_values = []
                    except Exception as e:
                        self.logger.warning(f"Failed to extract embedding: {e}")
                        embedding_values = []
                    
                    # Extract fields using string keys for RowView
                    try:
                        result_id = result['id']
                    except:
                        result_id = ''
                    
                    try:
                        result_document_id = result['document_id']
                    except:
                        result_document_id = ''
                    
                    try:
                        result_content = result['content']
                    except:
                        result_content = ''
                    
                    try:
                        result_chunk_id = result['chunk_id']
                    except:
                        result_chunk_id = ''
                    
                    try:
                        result_metadata_json = result['metadata']
                        # Parse JSON metadata
                        import json
                        result_metadata = json.loads(result_metadata_json) if result_metadata_json else {}
                    except:
                        result_metadata = {}
                    
                    try:
                        result_content_hash = result['content_hash']
                    except:
                        result_content_hash = ''
                    
                    try:
                        result_content_type = result['content_type']
                    except:
                        result_content_type = ''
                    
                    try:
                        result_language = result['language']
                    except:
                        result_language = ''
                    
                    try:
                        result_chunk_index = result['chunk_index']
                    except:
                        result_chunk_index = 0
                    
                    try:
                        result_model = result['model']
                    except:
                        result_model = ''
                    
                    try:
                        result_created_at = result['created_at']
                    except:
                        result_created_at = datetime.now(timezone.utc).isoformat()
                    
                    try:
                        result_updated_at = result['updated_at']
                    except:
                        result_updated_at = datetime.now(timezone.utc).isoformat()
                    
                    try:
                        result_chunk_count = result['chunk_count']
                    except:
                        result_chunk_count = 1
                    
                    vector_data = {
                        'id': result_id,
                        'document_id': result_document_id,
                        'chunk_id': result_chunk_id,
                        'values': embedding_values,
                        'content': result_content,
                        'metadata': result_metadata,
                        'content_hash': result_content_hash,
                        'content_type': result_content_type,
                        'language': result_language,
                        'chunk_index': result_chunk_index,
                        'chunk_count': result_chunk_count,
                        'model': result_model,
                        'created_at': result_created_at,
                        'updated_at': result_updated_at,
                    }
                    
                    
                    # Calculate similarity score based on metric type
                    vector_values = np.array(vector_data['values'])
                    
                    # Implement all supported distance metrics
                    if metric_type.lower() == 'cosine':
                        # Calculate cosine similarity
                        dot_product = np.dot(query_embedding, vector_values)
                        query_norm = np.linalg.norm(query_embedding)
                        vector_norm = np.linalg.norm(vector_values)
                        
                        if query_norm == 0 or vector_norm == 0:
                            score = 0.0
                            distance = 1.0
                        else:
                            score = dot_product / (query_norm * vector_norm)
                            distance = 1.0 - score  # Convert similarity to distance
                    
                    elif metric_type.lower() == 'dot_product':
                        # Calculate dot product similarity (higher is better)
                        dot_product = np.dot(query_embedding, vector_values)
                        score = dot_product
                        # Convert to distance (lower is better) by inverting
                        distance = -dot_product if dot_product != 0 else float('inf')
                    
                    elif metric_type.lower() == 'manhattan':
                        # Calculate Manhattan (L1) distance
                        distance = np.sum(np.abs(query_embedding - vector_values))
                        score = 1.0 / (1.0 + distance) if distance > 0 else 1.0
                    
                    elif metric_type.lower() == 'hamming':
                        # Calculate Hamming distance (for binary/categorical data)
                        # Convert continuous vectors to binary for Hamming distance
                        query_binary = (query_embedding > 0.5).astype(int)
                        vector_binary = (vector_values > 0.5).astype(int)
                        distance = np.sum(query_binary != vector_binary) / len(query_binary)
                        score = 1.0 - distance  # Convert distance to similarity
                    
                    else:  # euclidean (L2) - default
                        # Calculate L2 (Euclidean) distance
                        distance = np.linalg.norm(query_embedding - vector_values)
                        score = 1.0 / (1.0 + distance) if distance > 0 else 1.0
                    
                    vector_response = VectorResponse(
                        id=vector_data['id'],
                        dataset_id=dataset_id,
                        document_id=vector_data['document_id'],
                        chunk_id=vector_data['chunk_id'],
                        values=vector_data['values'],
                        content=vector_data['content'] if options.include_content else None,
                        content_hash=vector_data['content_hash'],
                        metadata=vector_data['metadata'] if options.include_metadata else {},
                        content_type=vector_data['content_type'],
                        language=vector_data['language'],
                        chunk_index=vector_data['chunk_index'],
                        chunk_count=vector_data['chunk_count'],
                        model=vector_data['model'],
                        dimensions=len(vector_data['values']),
                        created_at=vector_data['created_at'],
                        updated_at=vector_data['updated_at'],
                        tenant_id=tenant_id
                    )
                    
                    # Store candidate with score for sorting
                    candidates.append({
                        'vector_response': vector_response,
                        'score': float(score),
                        'distance': float(distance),
                        'original_index': i
                    })
                    
                except Exception as e:
                    self.logger.warning("Failed to process search result", index=i, error=str(e))
                    continue
            
            # Sort candidates by score - different metrics require different sorting
            if metric_type.lower() in ['cosine', 'hamming']:
                # For similarity metrics, higher scores are better
                candidates.sort(key=lambda x: x['score'], reverse=True)
            elif metric_type.lower() == 'dot_product':
                # For dot product, higher values are better (more similar)
                candidates.sort(key=lambda x: x['score'], reverse=True)
            else:  # euclidean, manhattan - distance metrics
                # For distance metrics, lower distances are better
                candidates.sort(key=lambda x: x['distance'], reverse=False)
            
            # Apply filtering and create final results
            results = []
            
            # Parse metadata filters if provided
            metadata_filter_expr = None
            if options.filters:
                from app.services.metadata_filter import metadata_filter_service
                try:
                    metadata_filter_expr = metadata_filter_service.parse_filter_expression(options.filters)
                    self.logger.debug("Parsed metadata filter expression", filter_expr=metadata_filter_expr)
                except Exception as e:
                    self.logger.error("Failed to parse metadata filter", error=str(e))
                    raise InvalidSearchParametersException(f"Invalid metadata filter: {e}")
            
            for i, candidate in enumerate(candidates):
                score = candidate['score']
                distance = candidate['distance']
                vector_response = candidate['vector_response']
                
                # Apply threshold filtering if specified
                if options.threshold is not None:
                    if score < options.threshold:
                        continue
                
                # Apply min_score filtering if specified
                if options.min_score is not None and score < options.min_score:
                    continue
                
                # Apply max_distance filtering if specified  
                if options.max_distance is not None and distance > options.max_distance:
                    continue
                
                # Apply metadata filtering if specified
                if metadata_filter_expr:
                    try:
                        if not metadata_filter_service.apply_filter(vector_response.metadata, metadata_filter_expr):
                            continue
                    except Exception as e:
                        self.logger.warning("Failed to apply metadata filter", error=str(e), metadata=vector_response.metadata)
                        continue
                
                # Stop if we have enough results
                if len(results) >= options.top_k:
                    break
                
                results.append(SearchResultItem(
                    vector=vector_response,
                    score=score,
                    distance=distance,
                    rank=len(results) + 1
                ))
            
            self.logger.info(f"Filtered to {len(results)} final results from {len(candidates)} candidates")
            
            query_time = (time.time() - start_time) * 1000
            
            stats = SearchStats(
                vectors_scanned=len(dataset),
                index_hits=len(results),
                filtered_results=len(results),
                database_time_ms=query_time,
                post_processing_time_ms=0.0
            )
            
            self.logger.info(
                "Vector search completed",
                dataset_id=dataset_id,
                results_count=len(results),
                query_time_ms=query_time
            )
            
            return SearchResponse(
                results=results,
                total_found=len(results),
                has_more=False,
                query_time_ms=query_time,
                stats=stats
            )
            
        except Exception as e:
            self.logger.error("Failed to search vectors", dataset_id=dataset_id, error=str(e))
            raise StorageException(f"Failed to search vectors: {str(e)}", "search_vectors")
    
    async def get_vector(
        self,
        dataset_id: str,
        vector_id: str,
        tenant_id: Optional[str] = None
    ) -> VectorResponse:
        """Get a specific vector by ID."""
        dataset_key = self._get_dataset_key(dataset_id, tenant_id)
        dataset_path = self._get_dataset_path(dataset_id, tenant_id)
        
        if not os.path.exists(dataset_path):
            raise DatasetNotFoundException(dataset_id, tenant_id)
        
        try:
            # Load dataset
            if dataset_key not in self.datasets:
                self.datasets[dataset_key] = await self._load_dataset(dataset_path, read_only=True)
            
            dataset = self.datasets[dataset_key]
            
            # Search for vector by ID
            loop = asyncio.get_event_loop()
            vector_index = await loop.run_in_executor(
                self.executor,
                lambda: self._find_vector_index_by_id(dataset, vector_id)
            )
            
            if vector_index is None:
                raise VectorNotFoundException(vector_id, dataset_id)
            
            # Get vector data
            vector_data = await loop.run_in_executor(
                self.executor,
                lambda: self._get_vector_data_by_index(dataset, vector_index)
            )
            
            return VectorResponse(
                id=vector_data['id'],
                dataset_id=dataset_id,
                document_id=vector_data['document_id'],
                chunk_id=vector_data['chunk_id'],
                values=vector_data['values'],
                content=vector_data['content'],
                metadata=vector_data['metadata'],
                content_type=vector_data.get('content_type', 'text/plain'),
                language=vector_data.get('language', 'en'),
                chunk_index=vector_data.get('chunk_index', 0),
                chunk_count=vector_data.get('chunk_count', 1),
                model=vector_data.get('model', ''),
                dimensions=len(vector_data['values']),
                created_at=vector_data['created_at'],
                updated_at=vector_data['updated_at'],
                tenant_id=tenant_id
            )
        
        except VectorNotFoundException:
            raise
        except Exception as e:
            self.logger.error("Failed to get vector", dataset_id=dataset_id, vector_id=vector_id, error=str(e))
            raise StorageException(f"Failed to get vector: {str(e)}", "get_vector")
    
    async def update_vector(
        self,
        dataset_id: str,
        vector_id: str,
        vector_update: VectorUpdate,
        tenant_id: Optional[str] = None
    ) -> VectorResponse:
        """Update a specific vector."""
        dataset_key = self._get_dataset_key(dataset_id, tenant_id)
        dataset_path = self._get_dataset_path(dataset_id, tenant_id)
        
        if not os.path.exists(dataset_path):
            raise DatasetNotFoundException(dataset_id, tenant_id)
        
        try:
            # Load dataset (read-write mode)
            if dataset_key not in self.datasets:
                self.datasets[dataset_key] = await self._load_dataset(dataset_path, read_only=False)
            
            dataset = self.datasets[dataset_key]
            
            # Find vector index
            loop = asyncio.get_event_loop()
            vector_index = await loop.run_in_executor(
                self.executor,
                lambda: self._find_vector_index_by_id(dataset, vector_id)
            )
            
            if vector_index is None:
                raise VectorNotFoundException(vector_id, dataset_id)
            
            # Update vector data
            current_time = datetime.now(timezone.utc).isoformat()
            
            await loop.run_in_executor(
                self.executor,
                lambda: self._update_vector_at_index(dataset, vector_index, vector_update, current_time)
            )
            
            # Return updated vector
            return await self.get_vector(dataset_id, vector_id, tenant_id)
        
        except VectorNotFoundException:
            raise
        except Exception as e:
            self.logger.error("Failed to update vector", dataset_id=dataset_id, vector_id=vector_id, error=str(e))
            raise StorageException(f"Failed to update vector: {str(e)}", "update_vector")
    
    async def delete_vector(
        self,
        dataset_id: str,
        vector_id: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Delete a specific vector."""
        dataset_key = self._get_dataset_key(dataset_id, tenant_id)
        dataset_path = self._get_dataset_path(dataset_id, tenant_id)
        
        if not os.path.exists(dataset_path):
            raise DatasetNotFoundException(dataset_id, tenant_id)
        
        try:
            # Load dataset (read-write mode)
            if dataset_key not in self.datasets:
                self.datasets[dataset_key] = await self._load_dataset(dataset_path, read_only=False)
            
            dataset = self.datasets[dataset_key]
            
            # Find vector index
            loop = asyncio.get_event_loop()
            vector_index = await loop.run_in_executor(
                self.executor,
                lambda: self._find_vector_index_by_id(dataset, vector_id)
            )
            
            if vector_index is None:
                raise VectorNotFoundException(vector_id, dataset_id)
            
            # Delete vector
            await loop.run_in_executor(
                self.executor,
                lambda: self._delete_vector_at_index(dataset, vector_index)
            )
            
            self.logger.info("Vector deleted", dataset_id=dataset_id, vector_id=vector_id)
            return True
        
        except VectorNotFoundException:
            raise
        except Exception as e:
            self.logger.error("Failed to delete vector", dataset_id=dataset_id, vector_id=vector_id, error=str(e))
            raise StorageException(f"Failed to delete vector: {str(e)}", "delete_vector")
    
    async def list_vectors(
        self,
        dataset_id: str,
        limit: int = 50,
        offset: int = 0,
        tenant_id: Optional[str] = None
    ) -> List[VectorResponse]:
        """List vectors in a dataset with pagination."""
        dataset_key = self._get_dataset_key(dataset_id, tenant_id)
        dataset_path = self._get_dataset_path(dataset_id, tenant_id)
        
        if not os.path.exists(dataset_path):
            raise DatasetNotFoundException(dataset_id, tenant_id)
        
        try:
            # Load dataset
            if dataset_key not in self.datasets:
                self.datasets[dataset_key] = await self._load_dataset(dataset_path, read_only=True)
            
            dataset = self.datasets[dataset_key]
            
            # Get total length
            total_vectors = len(dataset)
            
            if offset >= total_vectors:
                return []
            
            # Calculate actual limit
            end_index = min(offset + limit, total_vectors)
            
            # Get vectors
            vectors = []
            loop = asyncio.get_event_loop()
            
            for i in range(offset, end_index):
                try:
                    vector_data = await loop.run_in_executor(
                        self.executor,
                        lambda idx=i: self._get_vector_data_by_index(dataset, idx)
                    )
                    
                    vectors.append(VectorResponse(
                        id=vector_data['id'],
                        dataset_id=dataset_id,
                        document_id=vector_data['document_id'],
                        chunk_id=vector_data['chunk_id'],
                        values=vector_data['values'],
                        content=vector_data['content'],
                        metadata=vector_data['metadata'],
                        content_type=vector_data.get('content_type', 'text/plain'),
                        language=vector_data.get('language', 'en'),
                        chunk_index=vector_data.get('chunk_index', 0),
                        chunk_count=vector_data.get('chunk_count', 1),
                        model=vector_data.get('model', ''),
                        dimensions=len(vector_data['values']),
                        created_at=vector_data['created_at'],
                        updated_at=vector_data['updated_at'],
                        tenant_id=tenant_id
                    ))
                except Exception as e:
                    self.logger.warning("Failed to process vector at index", index=i, error=str(e))
                    continue
            
            return vectors
        
        except Exception as e:
            self.logger.error("Failed to list vectors", dataset_id=dataset_id, error=str(e))
            raise StorageException(f"Failed to list vectors: {str(e)}", "list_vectors")
    
    def _find_vector_index_by_id(self, dataset: Any, vector_id: str) -> Optional[int]:
        """Find the index of a vector by its ID."""
        try:
            for i in range(len(dataset)):
                if dataset.id[i].data()[0] == vector_id:
                    return i
            return None
        except Exception:
            return None
    
    def _get_vector_data_by_index(self, dataset: Any, index: int) -> Dict[str, Any]:
        """Get vector data by index."""
        try:
            import json
            
            # Get metadata and deserialize from JSON
            metadata_json = dataset.metadata[index].data()[0] if dataset.metadata[index].data() else '{}'
            try:
                metadata = json.loads(metadata_json)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
            
            return {
                'id': dataset.id[index].data()[0] if dataset.id[index].data() else '',
                'document_id': dataset.document_id[index].data()[0] if dataset.document_id[index].data() else '',
                'chunk_id': dataset.chunk_id[index].data()[0] if dataset.chunk_id[index].data() else '',
                'values': dataset.embedding[index].data()[0].tolist() if dataset.embedding[index].data() else [],
                'content': dataset.content[index].data()[0] if dataset.content[index].data() else '',
                'metadata': metadata,
                'content_type': dataset.content_type[index].data()[0] if dataset.content_type[index].data() else 'text/plain',
                'language': dataset.language[index].data()[0] if dataset.language[index].data() else 'en',
                'chunk_index': int(dataset.chunk_index[index].data()[0]) if dataset.chunk_index[index].data() else 0,
                'chunk_count': int(dataset.chunk_count[index].data()[0]) if dataset.chunk_count[index].data() else 1,
                'model': dataset.model[index].data()[0] if dataset.model[index].data() else '',
                'created_at': datetime.fromisoformat(dataset.created_at[index].data()[0]) if dataset.created_at[index].data() else datetime.now(timezone.utc),
                'updated_at': datetime.fromisoformat(dataset.updated_at[index].data()[0]) if dataset.updated_at[index].data() else datetime.now(timezone.utc),
            }
        except Exception as e:
            self.logger.error("Failed to get vector data by index", index=index, error=str(e))
            raise
    
    def _update_vector_at_index(self, dataset: Any, index: int, vector_update: VectorUpdate, current_time: str) -> None:
        """Update vector data at specific index."""
        try:
            # Update only provided fields
            if vector_update.values is not None:
                dataset.embedding[index] = np.array(vector_update.values, dtype=np.float32)
            
            if vector_update.content is not None:
                dataset.content[index] = vector_update.content
                # Update content hash
                content_hash = hashlib.sha256(vector_update.content.encode()).hexdigest()
                dataset.content_hash[index] = content_hash
            
            if vector_update.metadata is not None:
                import json
                metadata_json = json.dumps(vector_update.metadata)
                dataset.metadata[index] = metadata_json
            
            if vector_update.content_type is not None:
                dataset.content_type[index] = vector_update.content_type
            
            if vector_update.language is not None:
                dataset.language[index] = vector_update.language
            
            # Always update the timestamp
            dataset.updated_at[index] = current_time
            
            # Commit changes
            dataset.commit(f"Updated vector at index {index}")
            
        except Exception as e:
            self.logger.error("Failed to update vector at index", index=index, error=str(e))
            raise
    
    def _delete_vector_at_index(self, dataset: Any, index: int) -> None:
        """Delete vector at specific index."""
        try:
            # Deep Lake doesn't have a direct delete operation
            # We need to remove the item from all tensors
            dataset.id.pop(index)
            dataset.document_id.pop(index)
            dataset.chunk_id.pop(index)
            dataset.embedding.pop(index)
            dataset.content.pop(index)
            dataset.content_hash.pop(index)
            dataset.metadata.pop(index)
            dataset.content_type.pop(index)
            dataset.language.pop(index)
            dataset.chunk_index.pop(index)
            dataset.chunk_count.pop(index)
            dataset.model.pop(index)
            dataset.created_at.pop(index)
            dataset.updated_at.pop(index)
            
            # Commit changes
            dataset.commit(f"Deleted vector at index {index}")
            
        except Exception as e:
            self.logger.error("Failed to delete vector at index", index=index, error=str(e))
            raise
    
    def _vector_exists(self, dataset: Any, vector_id: str) -> bool:
        """Check if a vector exists in the dataset."""
        try:
            # Simple implementation - in production you'd want a more efficient index
            for i in range(len(dataset)):
                if dataset.id[i].data()[0] == vector_id:
                    return True
            return False
        except Exception:
            return False
    
    async def get_dataset_stats(
        self,
        dataset_id: str,
        tenant_id: Optional[str] = None
    ) -> "DatasetStats":
        """Get dataset statistics."""
        try:
            # Get dataset info
            dataset_response = await self.get_dataset(dataset_id, tenant_id)
            
            # Load dataset to get actual stats
            dataset_key = self._get_dataset_key(dataset_id, tenant_id)
            dataset_path = self._get_dataset_path(dataset_id, tenant_id)
            
            if dataset_key not in self.datasets:
                self.datasets[dataset_key] = await self._load_dataset(dataset_path, read_only=True)
            
            dataset = self.datasets[dataset_key]
            
            # Get vector count
            loop = asyncio.get_event_loop()
            vector_count = await loop.run_in_executor(
                self.executor,
                lambda: len(dataset) if dataset else 0
            )
            
            # Get storage size
            storage_size = self._get_directory_size(dataset_path)
            
            # Create metadata stats (simplified)
            metadata_stats = {"total_vectors": vector_count}
            
            # Import here to avoid circular imports
            from app.models.schemas import DatasetStats
            
            return DatasetStats(
                dataset=dataset_response,
                vector_count=vector_count,
                storage_size=storage_size,
                metadata_stats=metadata_stats,
                index_stats=None
            )
            
        except Exception as e:
            self.logger.error("Failed to get dataset stats", dataset_id=dataset_id, error=str(e))
            raise StorageException(f"Failed to get dataset statistics: {str(e)}", "get_dataset_stats")
    
    def _is_deeplake_dataset(self, path: str) -> bool:
        """Check if a directory is a Deep Lake dataset."""
        try:
            return os.path.exists(os.path.join(path, 'dataset_metadata.json'))
        except Exception:
            return False
    
    async def _load_dataset_metadata(self, dataset_path: str) -> Dict[str, Any]:
        """Load dataset metadata from JSON file."""
        metadata_path = os.path.join(dataset_path, 'dataset_metadata.json')
        try:
            if os.path.exists(metadata_path):
                import json
                with open(metadata_path, 'r') as f:
                    result = json.load(f)
                    return dict(result) if isinstance(result, dict) else {}
            else:
                # Return default metadata if file doesn't exist
                return {
                    'name': os.path.basename(dataset_path),
                    'description': '',
                    'dimensions': 0,
                    'metric_type': 'cosine',
                    'index_type': 'default',
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            self.logger.warning("Failed to load dataset metadata", path=metadata_path, error=str(e))
            return {
                'name': os.path.basename(dataset_path),
                'description': '',
                'dimensions': 0,
                'metric_type': 'cosine',
                'index_type': 'default',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
    
    def _get_directory_size(self, path: str) -> int:
        """Get the total size of a directory."""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except OSError:
                        pass
            return total_size
        except Exception:
            return 0
    
    async def _build_or_update_index(self, dataset: Any, dataset_info: Dict[str, Any], dataset_id: str) -> None:
        """Build or update index for the dataset."""
        index_type_str = dataset_info.get('index_type', 'default')
        
        # Map string to enum
        try:
            index_type = IndexType(index_type_str)
        except ValueError:
            index_type = IndexType.DEFAULT
        
        # Get index parameters based on type
        if index_type == IndexType.HNSW:
            hnsw_params = HNSWParameters(
                m=16,
                ef_construction=200,
                ef_search=50
            )
            index_config = IndexConfig(
                index_type=index_type,
                metric_type=dataset_info.get('metric_type', 'cosine'),
                dimensions=dataset_info.get('dimensions', 0),
                hnsw_params=hnsw_params
            )
        elif index_type == IndexType.IVF:
            ivf_params = IVFParameters(
                nlist=100,
                nprobe=10
            )
            index_config = IndexConfig(
                index_type=index_type,
                metric_type=dataset_info.get('metric_type', 'cosine'),
                dimensions=dataset_info.get('dimensions', 0),
                ivf_params=ivf_params
            )
        else:
            index_config = IndexConfig(
                index_type=index_type,
                metric_type=dataset_info.get('metric_type', 'cosine'),
                dimensions=dataset_info.get('dimensions', 0)
            )
        
        # Build the index
        stats = await self.index_service.create_index(dataset, index_config, force_rebuild=False)
        
        self.logger.info(
            "Index built/updated",
            dataset_id=dataset_id,
            index_type=stats.index_type,
            vectors=stats.total_vectors,
            build_time=stats.build_time_seconds
        )