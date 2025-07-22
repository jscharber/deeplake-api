"""
Rate limiting service for tenant-based API throttling.

Implements multiple rate limiting strategies:
- Fixed window counter
- Sliding window log
- Token bucket
- Leaky bucket
"""

import time
import asyncio
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

import redis.asyncio as redis
from app.config.settings import settings
from app.config.logging import get_logger, LoggingMixin
from app.models.exceptions import RateLimitExceededException


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 1000
    requests_per_hour: int = 50000
    requests_per_day: int = 1000000
    burst_size: int = 100
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    
    # Tenant-specific overrides
    tenant_limits: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Operation-specific limits
    operation_limits: Dict[str, int] = field(default_factory=lambda: {
        "search": 100,  # per minute
        "insert": 1000,  # per minute
        "create_dataset": 10,  # per minute
        "delete": 50,  # per minute
        "import": 5,  # per minute
        "export": 10,  # per minute
    })


@dataclass
class RateLimitStatus:
    """Rate limit status for a tenant."""
    allowed: bool
    limit: int
    remaining: int
    reset_at: datetime
    retry_after: Optional[int] = None  # seconds


@dataclass
class TenantUsageStats:
    """Tenant usage statistics."""
    tenant_id: str
    current_minute: int
    current_hour: int
    current_day: int
    total_requests: int
    total_errors: int
    last_request: datetime
    operations: Dict[str, int]  # operation -> count


class RateLimitService(LoggingMixin):
    """Service for managing rate limits per tenant."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        super().__init__()
        self.redis_client = redis_client
        self.config = self._load_config()
        self.local_cache: Dict[str, Any] = {}
        self._initialized = False
        
    async def initialize(self):
        """Initialize the rate limit service."""
        if self._initialized:
            return
            
        try:
            if not self.redis_client:
                self.redis_client = redis.from_url(settings.redis.url)
            
            # Test connection
            await self.redis_client.ping()
            self._initialized = True
            self.logger.info("Rate limit service initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize rate limit service: {e}")
            # Fall back to local in-memory rate limiting
            self.redis_client = None
            self._initialized = True
    
    def _load_config(self) -> RateLimitConfig:
        """Load rate limit configuration."""
        config = RateLimitConfig(
            requests_per_minute=settings.rate_limit.requests_per_minute,
            burst_size=settings.rate_limit.burst
        )
        
        # Load tenant-specific limits from configuration
        # This could come from a database or config file
        config.tenant_limits = {
            "premium": {
                "requests_per_minute": 5000,
                "requests_per_hour": 200000,
                "burst_size": 500
            },
            "enterprise": {
                "requests_per_minute": 10000,
                "requests_per_hour": 500000,
                "burst_size": 1000
            }
        }
        
        return config
    
    async def check_rate_limit(
        self,
        tenant_id: str,
        operation: Optional[str] = None,
        cost: int = 1
    ) -> RateLimitStatus:
        """
        Check if request is allowed under rate limits.
        
        Args:
            tenant_id: Tenant identifier
            operation: Optional operation type for operation-specific limits
            cost: Request cost (default 1, can be higher for expensive operations)
            
        Returns:
            RateLimitStatus indicating if request is allowed
            
        Raises:
            RateLimitExceededException if limit is exceeded
        """
        if not self._initialized:
            await self.initialize()
        
        # Get tenant-specific limits
        limits = self._get_tenant_limits(tenant_id)
        
        # Check operation-specific limit first if specified
        if operation and operation in self.config.operation_limits:
            op_status = await self._check_operation_limit(tenant_id, operation, cost)
            if not op_status.allowed:
                raise RateLimitExceededException(
                    f"Rate limit exceeded for operation '{operation}': "
                    f"{op_status.limit} requests per minute"
                )
        
        # Check general rate limits based on strategy
        if self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            status = await self._check_sliding_window(tenant_id, limits, cost)
        elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            status = await self._check_token_bucket(tenant_id, limits, cost)
        elif self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            status = await self._check_fixed_window(tenant_id, limits, cost)
        else:
            status = await self._check_leaky_bucket(tenant_id, limits, cost)
        
        if not status.allowed:
            raise RateLimitExceededException(
                f"Rate limit exceeded: {status.limit} requests per minute"
            )
        
        # Record usage
        await self._record_usage(tenant_id, operation, cost)
        
        return status
    
    async def _check_sliding_window(
        self,
        tenant_id: str,
        limits: Dict[str, int],
        cost: int
    ) -> RateLimitStatus:
        """Sliding window rate limiting."""
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        key = f"rate_limit:sliding:{tenant_id}"
        
        if self.redis_client:
            # Remove old entries
            await self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            current_count = await self.redis_client.zcard(key)
            
            if current_count + cost > limits["requests_per_minute"]:
                # Get oldest entry to calculate retry_after
                oldest = await self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(60 - (now - oldest[0][1]))
                else:
                    retry_after = 60
                
                return RateLimitStatus(
                    allowed=False,
                    limit=limits["requests_per_minute"],
                    remaining=0,
                    reset_at=datetime.fromtimestamp(window_start + 60),
                    retry_after=retry_after
                )
            
            # Add current request
            await self.redis_client.zadd(key, {str(now): now})
            await self.redis_client.expire(key, 70)  # Expire after window + buffer
            
            remaining = limits["requests_per_minute"] - current_count - cost
            
        else:
            # Fallback to local cache
            if key not in self.local_cache:
                self.local_cache[key] = []
            
            # Clean old entries
            self.local_cache[key] = [
                ts for ts in self.local_cache[key] if ts > window_start
            ]
            
            current_count = len(self.local_cache[key])
            
            if current_count + cost > limits["requests_per_minute"]:
                retry_after = 60 if not self.local_cache[key] else int(
                    60 - (now - self.local_cache[key][0])
                )
                
                return RateLimitStatus(
                    allowed=False,
                    limit=limits["requests_per_minute"],
                    remaining=0,
                    reset_at=datetime.fromtimestamp(window_start + 60),
                    retry_after=retry_after
                )
            
            # Add current request
            self.local_cache[key].append(now)
            remaining = limits["requests_per_minute"] - current_count - cost
        
        return RateLimitStatus(
            allowed=True,
            limit=limits["requests_per_minute"],
            remaining=max(0, remaining),
            reset_at=datetime.fromtimestamp(now + 60)
        )
    
    async def _check_token_bucket(
        self,
        tenant_id: str,
        limits: Dict[str, int],
        cost: int
    ) -> RateLimitStatus:
        """Token bucket rate limiting."""
        now = time.time()
        key = f"rate_limit:token:{tenant_id}"
        
        rate = limits["requests_per_minute"] / 60.0  # tokens per second
        capacity = limits.get("burst_size", limits["requests_per_minute"])
        
        if self.redis_client:
            # Get current bucket state
            bucket_data = await self.redis_client.get(key)
            if bucket_data:
                bucket = json.loads(bucket_data)
                tokens = bucket["tokens"]
                last_update = bucket["last_update"]
            else:
                tokens = capacity
                last_update = now
            
            # Add tokens based on time elapsed
            elapsed = now - last_update
            tokens = min(capacity, tokens + elapsed * rate)
            
            if tokens < cost:
                wait_time = (cost - tokens) / rate
                
                return RateLimitStatus(
                    allowed=False,
                    limit=limits["requests_per_minute"],
                    remaining=0,
                    reset_at=datetime.fromtimestamp(now + wait_time),
                    retry_after=int(wait_time)
                )
            
            # Consume tokens
            tokens -= cost
            
            # Save bucket state
            bucket_data = json.dumps({
                "tokens": tokens,
                "last_update": now
            })
            await self.redis_client.setex(key, 120, bucket_data)
            
        else:
            # Local implementation
            if key not in self.local_cache:
                self.local_cache[key] = {
                    "tokens": capacity,
                    "last_update": now
                }
            
            bucket = self.local_cache[key]
            elapsed = now - bucket["last_update"]
            bucket["tokens"] = min(capacity, bucket["tokens"] + elapsed * rate)
            bucket["last_update"] = now
            
            if bucket["tokens"] < cost:
                wait_time = (cost - bucket["tokens"]) / rate
                
                return RateLimitStatus(
                    allowed=False,
                    limit=limits["requests_per_minute"],
                    remaining=0,
                    reset_at=datetime.fromtimestamp(now + wait_time),
                    retry_after=int(wait_time)
                )
            
            bucket["tokens"] -= cost
            tokens = bucket["tokens"]
        
        return RateLimitStatus(
            allowed=True,
            limit=limits["requests_per_minute"],
            remaining=int(tokens),
            reset_at=datetime.fromtimestamp(now + 60)
        )
    
    async def _check_fixed_window(
        self,
        tenant_id: str,
        limits: Dict[str, int],
        cost: int
    ) -> RateLimitStatus:
        """Fixed window rate limiting."""
        now = time.time()
        window = int(now // 60) * 60  # Current minute
        key = f"rate_limit:fixed:{tenant_id}:{window}"
        
        if self.redis_client:
            current_count = await self.redis_client.incrby(key, cost)
            
            if current_count == cost:  # First request in window
                await self.redis_client.expire(key, 70)
            
            if current_count > limits["requests_per_minute"]:
                return RateLimitStatus(
                    allowed=False,
                    limit=limits["requests_per_minute"],
                    remaining=0,
                    reset_at=datetime.fromtimestamp(window + 60),
                    retry_after=int(window + 60 - now)
                )
            
            remaining = limits["requests_per_minute"] - current_count
            
        else:
            # Local implementation
            if key not in self.local_cache:
                self.local_cache[key] = 0
            
            self.local_cache[key] += cost
            current_count = self.local_cache[key]
            
            if current_count > limits["requests_per_minute"]:
                return RateLimitStatus(
                    allowed=False,
                    limit=limits["requests_per_minute"],
                    remaining=0,
                    reset_at=datetime.fromtimestamp(window + 60),
                    retry_after=int(window + 60 - now)
                )
            
            remaining = limits["requests_per_minute"] - current_count
        
        return RateLimitStatus(
            allowed=True,
            limit=limits["requests_per_minute"],
            remaining=max(0, remaining),
            reset_at=datetime.fromtimestamp(window + 60)
        )
    
    async def _check_leaky_bucket(
        self,
        tenant_id: str,
        limits: Dict[str, int],
        cost: int
    ) -> RateLimitStatus:
        """Leaky bucket rate limiting."""
        # Similar to token bucket but with continuous leak
        return await self._check_token_bucket(tenant_id, limits, cost)
    
    async def _check_operation_limit(
        self,
        tenant_id: str,
        operation: str,
        cost: int
    ) -> RateLimitStatus:
        """Check operation-specific rate limit."""
        limit = self.config.operation_limits.get(operation, 100)
        now = time.time()
        window = int(now // 60) * 60
        key = f"rate_limit:op:{tenant_id}:{operation}:{window}"
        
        if self.redis_client:
            current_count = await self.redis_client.incrby(key, cost)
            
            if current_count == cost:
                await self.redis_client.expire(key, 70)
            
            if current_count > limit:
                return RateLimitStatus(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_at=datetime.fromtimestamp(window + 60),
                    retry_after=int(window + 60 - now)
                )
            
            remaining = limit - current_count
        else:
            if key not in self.local_cache:
                self.local_cache[key] = 0
            
            self.local_cache[key] += cost
            current_count = self.local_cache[key]
            
            if current_count > limit:
                return RateLimitStatus(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_at=datetime.fromtimestamp(window + 60),
                    retry_after=int(window + 60 - now)
                )
            
            remaining = limit - current_count
        
        return RateLimitStatus(
            allowed=True,
            limit=limit,
            remaining=max(0, remaining),
            reset_at=datetime.fromtimestamp(window + 60)
        )
    
    def _get_tenant_limits(self, tenant_id: str) -> Dict[str, int]:
        """Get rate limits for a specific tenant."""
        # Check if tenant has custom limits
        if tenant_id in self.config.tenant_limits:
            custom_limits = self.config.tenant_limits[tenant_id]
            return {
                "requests_per_minute": custom_limits.get(
                    "requests_per_minute",
                    self.config.requests_per_minute
                ),
                "requests_per_hour": custom_limits.get(
                    "requests_per_hour",
                    self.config.requests_per_hour
                ),
                "requests_per_day": custom_limits.get(
                    "requests_per_day",
                    self.config.requests_per_day
                ),
                "burst_size": custom_limits.get(
                    "burst_size",
                    self.config.burst_size
                )
            }
        
        # Check tenant tier (would typically come from database)
        # For now, use default limits
        return {
            "requests_per_minute": self.config.requests_per_minute,
            "requests_per_hour": self.config.requests_per_hour,
            "requests_per_day": self.config.requests_per_day,
            "burst_size": self.config.burst_size
        }
    
    async def _record_usage(
        self,
        tenant_id: str,
        operation: Optional[str],
        cost: int
    ):
        """Record usage statistics."""
        now = datetime.now()
        
        # Update usage counters
        keys = [
            f"usage:{tenant_id}:minute:{now.strftime('%Y%m%d%H%M')}",
            f"usage:{tenant_id}:hour:{now.strftime('%Y%m%d%H')}",
            f"usage:{tenant_id}:day:{now.strftime('%Y%m%d')}"
        ]
        
        if self.redis_client:
            pipe = self.redis_client.pipeline()
            for key in keys:
                pipe.incrby(key, cost)
                pipe.expire(key, 86400)  # Expire after 1 day
            
            if operation:
                op_key = f"usage:{tenant_id}:ops:{now.strftime('%Y%m%d')}"
                pipe.hincrby(op_key, operation, cost)
                pipe.expire(op_key, 86400)
            
            await pipe.execute()
    
    async def get_tenant_usage(
        self,
        tenant_id: str
    ) -> TenantUsageStats:
        """Get current usage statistics for a tenant."""
        now = datetime.now()
        
        if self.redis_client:
            keys = {
                "minute": f"usage:{tenant_id}:minute:{now.strftime('%Y%m%d%H%M')}",
                "hour": f"usage:{tenant_id}:hour:{now.strftime('%Y%m%d%H')}",
                "day": f"usage:{tenant_id}:day:{now.strftime('%Y%m%d')}"
            }
            
            # Get usage counts
            pipe = self.redis_client.pipeline()
            for key in keys.values():
                pipe.get(key)
            
            results = await pipe.execute()
            
            current_minute = int(results[0] or 0)
            current_hour = int(results[1] or 0)
            current_day = int(results[2] or 0)
            
            # Get operation counts
            op_key = f"usage:{tenant_id}:ops:{now.strftime('%Y%m%d')}"
            operations = await self.redis_client.hgetall(op_key)
            operations = {k.decode(): int(v) for k, v in operations.items()}
            
        else:
            # Local cache fallback
            current_minute = 0
            current_hour = 0
            current_day = 0
            operations = {}
        
        return TenantUsageStats(
            tenant_id=tenant_id,
            current_minute=current_minute,
            current_hour=current_hour,
            current_day=current_day,
            total_requests=current_day,
            total_errors=0,  # Would track separately
            last_request=now,
            operations=operations
        )
    
    async def reset_tenant_limits(self, tenant_id: str):
        """Reset rate limits for a tenant (admin operation)."""
        if self.redis_client:
            pattern = f"rate_limit:*:{tenant_id}*"
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self.redis_client.delete(*keys)
        else:
            # Clear local cache for tenant
            keys_to_remove = [
                k for k in self.local_cache.keys()
                if tenant_id in k
            ]
            for key in keys_to_remove:
                del self.local_cache[key]
        
        self.logger.info(f"Reset rate limits for tenant: {tenant_id}")
    
    async def update_tenant_limits(
        self,
        tenant_id: str,
        limits: Dict[str, int]
    ):
        """Update rate limits for a specific tenant."""
        self.config.tenant_limits[tenant_id] = limits
        
        # In production, this would persist to database
        self.logger.info(
            f"Updated limits for tenant {tenant_id}: {limits}"
        )
    
    async def close(self):
        """Close the rate limit service."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
        self._initialized = False