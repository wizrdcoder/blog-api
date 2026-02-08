from functools import wraps
from fastapi import Request, HTTPException, status
import redis.asyncio as redis
from app.core.config import settings
from typing import Callable, Optional


redis_client: Optional[redis.Redis] = None


async def get_redis():
    global redis_client
    if redis_client is None:
        redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_client


def manual_rate_limit(requests_per_minute: int = 5):
    """Simple, reliable manual rate limiting"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            redis_conn = await get_redis()

            # Get client IP
            if request.client:
                client_ip = request.client.host
            else:
                # Fallback for testing
                client_ip = "127.0.0.1"

            # Create Redis key
            key = f"rate_limit:{client_ip}:{request.url.path}"

            # Get current count
            current = await redis_conn.get(key)
            current_count = int(current) if current else 0

            # Check if limit exceeded
            if current_count >= requests_per_minute:
                # Get TTL to show when it resets
                ttl = await redis_conn.ttl(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {requests_per_minute} requests per minute. Try again in {ttl} seconds.",
                    headers={"Retry-After": str(ttl if ttl > 0 else 60)},
                )

            # Use pipeline for atomic operations
            pipeline = redis_conn.pipeline()
            pipeline.incr(key)

            # Set expire only on first increment
            if current_count == 0:
                pipeline.expire(key, 60)  # Reset after 60 seconds

            await pipeline.execute()

            # Call the original function
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


# Specific rate limit decorators
def auth_rate_limit():
    """5 requests per minute for auth endpoints"""
    return manual_rate_limit(5)


def api_rate_limit():
    """60 requests per minute for general API"""
    return manual_rate_limit(60)


def strict_rate_limit():
    """10 requests per minute for sensitive operations"""
    return manual_rate_limit(10)
