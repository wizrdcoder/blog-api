from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi_pagination import add_pagination
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import redis.asyncio as redis
import uvicorn

# from app.api.v1.api import api_router
# from app import api_router
from app.api import auth
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.database import async_engine, Base
from app.api import posts

from app.middleware.logging import LoggingMiddleware
# from app.middleware.rate_limit import setup_rate_limiting
# from app.core.exceptions import setup_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    print("Starting up...")

    # Create database tables (in production, use Alembic migrations)
    if settings.ENVIRONMENT == "development":
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables created!")

    # Initialize Redis cache
    redis_client = await redis.from_url(settings.REDIS_URL)
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
    print("Redis cache initialized!")

    yield

    # Shutdown
    # print("Shutting down...")
    # if redis_client:
    #     await redis_client.close()


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add custom middleware
# app.add_middleware(LoggingMiddleware)

# Set up rate limiting
# setup_rate_limiting(app)

# Set up exception handlers
setup_exception_handlers(app)

# Include API router
# app.include_router(api_router, prefix=settings.API_V1_STR)

# Add pagination support
add_pagination(app)


app.include_router(
    auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"]
)
app.include_router(posts.router, prefix=f"{settings.API_V1_STR}/posts", tags=["posts"])

# Prometheus metrics endpoint
# @app.get("/metrics")
# async def metrics():
#     """Prometheus metrics endpoint"""
#     from prometheus_client import generate_latest
#     from fastapi.responses import Response

#     return Response(content=generate_latest(), media_type="text/plain")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
