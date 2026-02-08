from fastapi import APIRouter
from app.api import auth
from app.api import posts

# Create main API router
api_router = APIRouter()

# Include auth endpoints with prefix
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Include other endpoints
# api_router.include_router(users.router, prefix="/users", tags=["users"])

api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
