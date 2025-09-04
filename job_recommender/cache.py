"""Redis caching configuration and utilities."""

import os
import json
import logging
from typing import Any, Optional, Union
from datetime import timedelta
import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_URL = os.getenv("REDIS_URL")

# Cache settings
DEFAULT_CACHE_TTL = int(os.getenv("DEFAULT_CACHE_TTL", "3600"))  # 1 hour
LONG_CACHE_TTL = int(os.getenv("LONG_CACHE_TTL", "86400"))  # 1 day
SHORT_CACHE_TTL = int(os.getenv("SHORT_CACHE_TTL", "300"))  # 5 minutes


class RedisCache:
    """Redis cache manager with advanced features."""
    
    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection."""
        try:
            if REDIS_URL:
                self.redis_client = redis.from_url(
                    REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            else:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self.redis_client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "app"
    ) -> bool:
        """Set a value in cache with optional TTL."""
        if not self.is_available():
            return False
        
        try:
            full_key = f"{namespace}:{key}"
            
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = str(value)
            
            # Set with TTL
            if ttl:
                success = self.redis_client.setex(full_key, ttl, serialized_value)
            else:
                success = self.redis_client.set(full_key, serialized_value)
            
            return bool(success)
            
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    def get(
        self,
        key: str,
        namespace: str = "app",
        deserialize: bool = True
    ) -> Optional[Any]:
        """Get a value from cache."""
        if not self.is_available():
            return None
        
        try:
            full_key = f"{namespace}:{key}"
            value = self.redis_client.get(full_key)
            
            if value is None:
                return None
            
            # Try to deserialize as JSON
            if deserialize:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            else:
                return value
            
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    def delete(self, key: str, namespace: str = "app") -> bool:
        """Delete a key from cache."""
        if not self.is_available():
            return False
        
        try:
            full_key = f"{namespace}:{key}"
            result = self.redis_client.delete(full_key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    def exists(self, key: str, namespace: str = "app") -> bool:
        """Check if a key exists in cache."""
        if not self.is_available():
            return False
        
        try:
            full_key = f"{namespace}:{key}"
            return bool(self.redis_client.exists(full_key))
            
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    def get_ttl(self, key: str, namespace: str = "app") -> int:
        """Get TTL for a key."""
        if not self.is_available():
            return -1
        
        try:
            full_key = f"{namespace}:{key}"
            return self.redis_client.ttl(full_key)
            
        except Exception as e:
            logger.error(f"Error getting TTL for key {key}: {e}")
            return -1
    
    def extend_ttl(self, key: str, ttl: int, namespace: str = "app") -> bool:
        """Extend TTL for a key."""
        if not self.is_available():
            return False
        
        try:
            full_key = f"{namespace}:{key}"
            return bool(self.redis_client.expire(full_key, ttl))
            
        except Exception as e:
            logger.error(f"Error extending TTL for key {key}: {e}")
            return False
    
    def flush_namespace(self, namespace: str) -> int:
        """Delete all keys in a namespace."""
        if not self.is_available():
            return 0
        
        try:
            pattern = f"{namespace}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                return self.redis_client.delete(*keys)
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Error flushing namespace {namespace}: {e}")
            return 0
    
    def get_all_keys(self, namespace: str = "*") -> list:
        """Get all keys matching a namespace pattern."""
        if not self.is_available():
            return []
        
        try:
            pattern = f"{namespace}:*" if namespace != "*" else "*"
            return self.redis_client.keys(pattern)
            
        except Exception as e:
            logger.error(f"Error getting keys for namespace {namespace}: {e}")
            return []
    
    def increment(self, key: str, amount: int = 1, namespace: str = "counters") -> Optional[int]:
        """Increment a counter in cache."""
        if not self.is_available():
            return None
        
        try:
            full_key = f"{namespace}:{key}"
            return self.redis_client.incr(full_key, amount)
            
        except Exception as e:
            logger.error(f"Error incrementing counter {key}: {e}")
            return None
    
    def decrement(self, key: str, amount: int = 1, namespace: str = "counters") -> Optional[int]:
        """Decrement a counter in cache."""
        if not self.is_available():
            return None
        
        try:
            full_key = f"{namespace}:{key}"
            return self.redis_client.decr(full_key, amount)
            
        except Exception as e:
            logger.error(f"Error decrementing counter {key}: {e}")
            return None
    
    def set_hash(self, key: str, field: str, value: Any, namespace: str = "hashes") -> bool:
        """Set a field in a hash."""
        if not self.is_available():
            return False
        
        try:
            full_key = f"{namespace}:{key}"
            
            # Serialize value if needed
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = str(value)
            
            return bool(self.redis_client.hset(full_key, field, serialized_value))
            
        except Exception as e:
            logger.error(f"Error setting hash field {key}.{field}: {e}")
            return False
    
    def get_hash(
        self,
        key: str,
        field: str,
        namespace: str = "hashes",
        deserialize: bool = True
    ) -> Optional[Any]:
        """Get a field from a hash."""
        if not self.is_available():
            return None
        
        try:
            full_key = f"{namespace}:{key}"
            value = self.redis_client.hget(full_key, field)
            
            if value is None:
                return None
            
            # Try to deserialize as JSON
            if deserialize:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            else:
                return value
                
        except Exception as e:
            logger.error(f"Error getting hash field {key}.{field}: {e}")
            return None
    
    def get_all_hash(self, key: str, namespace: str = "hashes") -> dict:
        """Get all fields from a hash."""
        if not self.is_available():
            return {}
        
        try:
            full_key = f"{namespace}:{key}"
            return self.redis_client.hgetall(full_key)
            
        except Exception as e:
            logger.error(f"Error getting all hash fields for {key}: {e}")
            return {}


# Global cache instance
cache = RedisCache()

# Alias for backward compatibility
JobCache = RedisCache


# Cache decorators
def cached(
    ttl: int = DEFAULT_CACHE_TTL,
    namespace: str = "app",
    key_prefix: str = None
):
    """Decorator for caching function results."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_prefix:
                cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key, namespace)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl, namespace)
            logger.debug(f"Cached result for {func.__name__}")
            
            return result
        return wrapper
    return decorator


# Pre-defined cache namespaces
class CacheNamespaces:
    """Predefined cache namespaces for different data types."""
    
    JOBS = "jobs"
    USERS = "users"
    RESUMES = "resumes"
    ANALYSES = "analyses"
    RECOMMENDATIONS = "recommendations"
    SKILLS = "skills"
    RATE_LIMITS = "rate_limits"
    SESSIONS = "sessions"
    SEARCH_RESULTS = "search"
    API_RESPONSES = "api"


# Cache helper functions
def cache_job_search_results(
    search_params: dict,
    results: list,
    ttl: int = SHORT_CACHE_TTL
) -> bool:
    """Cache job search results."""
    cache_key = f"search:{hash(str(sorted(search_params.items())))}"
    return cache.set(cache_key, results, ttl, CacheNamespaces.SEARCH_RESULTS)


def get_cached_job_search_results(search_params: dict) -> Optional[list]:
    """Get cached job search results."""
    cache_key = f"search:{hash(str(sorted(search_params.items())))}"
    return cache.get(cache_key, CacheNamespaces.SEARCH_RESULTS)


def cache_user_recommendations(
    user_id: int,
    recommendations: list,
    ttl: int = DEFAULT_CACHE_TTL
) -> bool:
    """Cache user recommendations."""
    cache_key = f"user_{user_id}_recommendations"
    return cache.set(cache_key, recommendations, ttl, CacheNamespaces.RECOMMENDATIONS)


def get_cached_user_recommendations(user_id: int) -> Optional[list]:
    """Get cached user recommendations."""
    cache_key = f"user_{user_id}_recommendations"
    return cache.get(cache_key, CacheNamespaces.RECOMMENDATIONS)


def invalidate_user_cache(user_id: int):
    """Invalidate all cached data for a user."""
    patterns = [
        f"{CacheNamespaces.RECOMMENDATIONS}:*user_{user_id}*",
        f"{CacheNamespaces.ANALYSES}:*user_{user_id}*",
        f"{CacheNamespaces.USERS}:*{user_id}*"
    ]
    
    for pattern in patterns:
        if cache.is_available():
            try:
                keys = cache.redis_client.keys(pattern)
                if keys:
                    cache.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Error invalidating user cache: {e}")


def cache_analysis_result(
    user_id: int,
    job_id: int,
    resume_id: int,
    analysis: dict,
    ttl: int = LONG_CACHE_TTL
) -> bool:
    """Cache analysis result."""
    cache_key = f"analysis_u{user_id}_j{job_id}_r{resume_id}"
    return cache.set(cache_key, analysis, ttl, CacheNamespaces.ANALYSES)


def get_cached_analysis_result(
    user_id: int,
    job_id: int,
    resume_id: int
) -> Optional[dict]:
    """Get cached analysis result."""
    cache_key = f"analysis_u{user_id}_j{job_id}_r{resume_id}"
    return cache.get(cache_key, CacheNamespaces.ANALYSES)