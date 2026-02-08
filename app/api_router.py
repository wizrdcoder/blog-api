from fastapi import APIRouter
from app.api import auth
from app.api import posts

# Create main API router
api_router = APIRouter()

# Include auth endpoints with prefix
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
