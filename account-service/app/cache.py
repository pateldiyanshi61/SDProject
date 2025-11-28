"""
Redis Cache Helper for Banking Microservices
Place this file in each service's app/ directory
"""
import json
import os
from typing import Optional, Any
from functools import wraps
import redis
from redis.exceptions import RedisError

class CacheManager:
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "redis")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            print(f"✓ Redis connected: {self.redis_host}:{self.redis_port}")
        except RedisError as e:
            print(f"⚠ Redis connection failed: {e}")
            self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            print(f"Cache get error for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL (default 5 minutes)"""
        if not self.redis_client:
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            self.redis_client.setex(key, ttl, serialized)
            return True
        except (RedisError, TypeError) as e:
            print(f"Cache set error for {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except RedisError as e:
            print(f"Cache delete error for {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> bool:
        """Delete all keys matching pattern"""
        if not self.redis_client:
            return False
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            return True
        except RedisError as e:
            print(f"Cache delete pattern error for {pattern}: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except RedisError:
            return False


# Global cache instance
cache = CacheManager()


def cached(key_prefix: str, ttl: int = 300):
    """
    Decorator for caching function results
    
    Usage:
        @cached(key_prefix="user", ttl=600)
        async def get_user(user_id: str):
            # function logic
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            cache_key = f"{key_prefix}:{':'.join(map(str, args))}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    """
    Helper function to invalidate cache by pattern
    
    Usage:
        invalidate_cache("user:123:*")
    """
    return cache.delete_pattern(pattern)