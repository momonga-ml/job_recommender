"""Common dependencies for FastAPI endpoints."""

from typing import Optional, Generator
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import redis
from functools import wraps
import time

from ..models.database import get_db
from ..models.user import User
from .auth import verify_token, get_current_user_from_token


# Security scheme
security = HTTPBearer()

# Redis client for caching and rate limiting
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
except Exception:
    redis_client = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    
    try:
        user = get_current_user_from_token(token, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current verified user."""
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified"
        )
    return current_user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None
    
    try:
        user = get_current_user_from_token(credentials.credentials, db)
        return user if user and user.is_active else None
    except:
        return None


class RateLimiter:
    """Rate limiting dependency."""
    
    def __init__(
        self, 
        max_requests: int = 100,
        window_seconds: int = 3600,
        key_prefix: str = "rate_limit"
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
    
    def __call__(self, request: Request) -> None:
        if not redis_client:
            return  # Skip rate limiting if Redis is not available
        
        # Use IP address as identifier
        client_ip = request.client.host
        key = f"{self.key_prefix}:{client_ip}"
        
        try:
            current = redis_client.get(key)
            if current is None:
                # First request from this IP
                redis_client.setex(key, self.window_seconds, 1)
                return
            
            current_requests = int(current)
            if current_requests >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds} seconds."
                )
            
            # Increment counter
            redis_client.incr(key)
            
        except redis.RedisError:
            # If Redis fails, allow the request
            pass


class UserRateLimiter:
    """User-specific rate limiting dependency."""
    
    def __init__(
        self, 
        max_requests: int = 1000,
        window_seconds: int = 3600,
        key_prefix: str = "user_rate_limit"
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
    
    def __call__(
        self,
        current_user: User = Depends(get_current_user),
        request: Request = None
    ) -> None:
        if not redis_client:
            return
        
        key = f"{self.key_prefix}:{current_user.id}"
        
        try:
            current = redis_client.get(key)
            if current is None:
                redis_client.setex(key, self.window_seconds, 1)
                return
            
            current_requests = int(current)
            if current_requests >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"User rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds} seconds."
                )
            
            redis_client.incr(key)
            
        except redis.RedisError:
            pass


def cache_response(expiration_seconds: int = 3600):
    """Cache endpoint response in Redis."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not redis_client:
                return await func(*args, **kwargs)
            
            # Create cache key from function name and arguments
            cache_key = f"cache:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            try:
                # Try to get cached result
                cached_result = redis_client.get(cache_key)
                if cached_result:
                    import json
                    return json.loads(cached_result)
            except:
                pass
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            try:
                import json
                redis_client.setex(
                    cache_key, 
                    expiration_seconds, 
                    json.dumps(result, default=str)
                )
            except:
                pass
            
            return result
        return wrapper
    return decorator


# Rate limiting instances
api_rate_limit = RateLimiter(max_requests=100, window_seconds=3600)
auth_rate_limit = RateLimiter(max_requests=20, window_seconds=900)  # Stricter for auth
user_rate_limit = UserRateLimiter(max_requests=1000, window_seconds=3600)


# Pagination dependency
class PaginationParams:
    """Pagination parameters."""
    
    def __init__(
        self,
        page: int = 1,
        size: int = 20,
        max_size: int = 100
    ):
        self.page = max(1, page)
        self.size = min(max(1, size), max_size)
        self.offset = (self.page - 1) * self.size
        self.limit = self.size


def get_pagination_params(
    page: int = 1,
    size: int = 20
) -> PaginationParams:
    """Get pagination parameters."""
    return PaginationParams(page=page, size=size)