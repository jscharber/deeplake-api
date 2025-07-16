"""Cache service for improving performance."""

import json
import pickle
from typing import Any, Optional, Dict, List
import asyncio
from datetime import datetime, timedelta

import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config.settings import settings
from app.config.logging import get_logger, LoggingMixin
from app.models.exceptions import CacheException


class CacheService(LoggingMixin):
    """Redis-based cache service."""
    
    def __init__(self) -> None:
        super().__init__()
        self.redis_url = settings.redis.url
        self.ttl_seconds = settings.redis.ttl_seconds
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = True
        
    async def initialize(self) -> None:
        """Initialize the cache service."""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            if self.redis_client:
                await self.redis_client.ping()
            self.logger.info("Cache service initialized", redis_url=self.redis_url)
        except Exception as e:
            self.logger.warning("Failed to initialize cache service", error=str(e))
            self.enabled = False
    
    async def close(self) -> None:
        """Close the cache service."""
        if self.redis_client:
            await self.redis_client.close()
            self.logger.info("Cache service closed")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            cached_data = await self.redis_client.get(key)
            if cached_data:
                data = pickle.loads(cached_data)
                self.logger.debug("Cache hit", key=key)
                return data
            else:
                self.logger.debug("Cache miss", key=key)
                return None
        except Exception as e:
            self.logger.error("Failed to get from cache", key=key, error=str(e))
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache."""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            ttl = ttl or self.ttl_seconds
            serialized_data = pickle.dumps(value)
            await self.redis_client.setex(key, ttl, serialized_data)
            self.logger.debug("Cache set", key=key, ttl=ttl)
            return True
        except Exception as e:
            self.logger.error("Failed to set cache", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            result = await self.redis_client.delete(key)
            self.logger.debug("Cache delete", key=key, deleted=bool(result))
            return bool(result)
        except Exception as e:
            self.logger.error("Failed to delete from cache", key=key, error=str(e))
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern."""
        if not self.enabled or not self.redis_client:
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted_count = await self.redis_client.delete(*keys)
                self.logger.info("Cache pattern cleared", pattern=pattern, deleted=deleted_count)
                return int(deleted_count)
            return 0
        except Exception as e:
            self.logger.error("Failed to clear cache pattern", pattern=pattern, error=str(e))
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            result = await self.redis_client.exists(key)
            return bool(result)
        except Exception as e:
            self.logger.error("Failed to check cache existence", key=key, error=str(e))
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled or not self.redis_client:
            return {"enabled": False}
        
        try:
            info = await self.redis_client.info()
            return {
                "enabled": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                ),
            }
        except Exception as e:
            self.logger.error("Failed to get cache stats", error=str(e))
            return {"enabled": False, "error": str(e)}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate."""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100.0
    
    def get_cache_key(self, prefix: str, *args: Any, **kwargs: Any) -> str:
        """Generate a cache key from prefix and arguments."""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                key_parts.append(str(hash(str(arg))))
        
        # Add keyword arguments
        for key, value in sorted(kwargs.items()):
            if isinstance(value, (str, int, float, bool)):
                key_parts.append(f"{key}:{value}")
            else:
                key_parts.append(f"{key}:{hash(str(value))}")
        
        return ":".join(key_parts)


class CacheManager:
    """High-level cache manager with typed methods."""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.logger = get_logger(self.__class__.__name__)
    
    async def get_dataset_info(self, dataset_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached dataset information."""
        key = self.cache.get_cache_key("dataset_info", dataset_id, tenant_id=tenant_id)
        return await self.cache.get(key)
    
    async def cache_dataset_info(self, dataset_id: str, dataset_info: Dict[str, Any], tenant_id: Optional[str] = None) -> bool:
        """Cache dataset information."""
        key = self.cache.get_cache_key("dataset_info", dataset_id, tenant_id=tenant_id)
        return await self.cache.set(key, dataset_info, ttl=3600)  # 1 hour
    
    async def get_search_results(self, dataset_id: str, query_hash: str, options_hash: str, tenant_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results."""
        key = self.cache.get_cache_key("search_results", dataset_id, query_hash, options_hash, tenant_id=tenant_id)
        return await self.cache.get(key)
    
    async def cache_search_results(self, dataset_id: str, query_hash: str, options_hash: str, results: List[Dict[str, Any]], tenant_id: Optional[str] = None) -> bool:
        """Cache search results."""
        key = self.cache.get_cache_key("search_results", dataset_id, query_hash, options_hash, tenant_id=tenant_id)
        return await self.cache.set(key, results, ttl=300)  # 5 minutes
    
    async def invalidate_dataset_cache(self, dataset_id: str, tenant_id: Optional[str] = None) -> None:
        """Invalidate all cache entries for a dataset."""
        patterns = [
            f"dataset_info:{dataset_id}:*",
            f"search_results:{dataset_id}:*",
        ]
        
        for pattern in patterns:
            await self.cache.clear_pattern(pattern)
        
        self.logger.info("Dataset cache invalidated", dataset_id=dataset_id, tenant_id=tenant_id)
    
    async def get_vector_info(self, dataset_id: str, vector_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached vector information."""
        key = self.cache.get_cache_key("vector_info", dataset_id, vector_id, tenant_id=tenant_id)
        return await self.cache.get(key)
    
    async def cache_vector_info(self, dataset_id: str, vector_id: str, vector_info: Dict[str, Any], tenant_id: Optional[str] = None) -> bool:
        """Cache vector information."""
        key = self.cache.get_cache_key("vector_info", dataset_id, vector_id, tenant_id=tenant_id)
        return await self.cache.set(key, vector_info, ttl=1800)  # 30 minutes
    
    async def invalidate_vector_cache(self, dataset_id: str, vector_id: str, tenant_id: Optional[str] = None) -> None:
        """Invalidate cached vector information."""
        key = self.cache.get_cache_key("vector_info", dataset_id, vector_id, tenant_id=tenant_id)
        await self.cache.delete(key)
        self.logger.info("Vector cache invalidated", dataset_id=dataset_id, vector_id=vector_id, tenant_id=tenant_id)