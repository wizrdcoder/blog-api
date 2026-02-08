from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi_pagination import Page, paginate, add_pagination

# from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user, get_current_active_user, require_role
from app.crud.post import post_crud
from app.models.user import User
from app.schemas.post import Post, PostCreate, PostUpdate, PostWithCategories
from app.database import get_async_db
import redis.asyncio as redis
from app.core.config import settings

router = APIRouter()


@router.get("/", response_model=Page[Post])
# @cache(expire=60)
async def read_posts(
    db: AsyncSession = Depends(get_async_db),
    skip: int = Query(0, gt=0),
    limit: int = Query(100, ge=1, le=1000),
    published_only: bool = Query(True),
    author_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    order_by: str = Query(
        "created_at", pattern="^(created_at|updated_at|view_count|published_at)$"
    ),
    order_desc: bool = Query(True),
) -> Any:
    """
    Retrieve posts with filtering and sorting.

    - **published_only**: Show only published posts (default: True)
    - **author_id**: Filter by author ID
    - **category_id**: Filter by category ID
    - **tag**: Filter by tag
    - **search**: Search in title and content
    - **order_by**: Field to order by (created_at, updated_at, view_count, published_at)
    - **order_desc**: Order descending (default: True)
    """

    posts = await post_crud.get_multi(
        db,
        skip=skip,
        limit=limit,
        published_only=published_only,
        author_id=author_id,
        category_id=category_id,
        tag=tag,
        search=search,
        order_by=order_by,
        order_desc=order_desc,
    )
    return paginate(posts)


@router.get("/search", response_model=list[Post])
async def search_posts(
    q: str = Query(..., min_length=3),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Full-text search posts.

    Uses PostgreSQL full-text search capabilities.
    """
    posts = await post_crud.search_full_text(db, search_query=q, limit=limit)
    return posts


@router.get("/popular", response_model=list[Post])
# @cache(expire=300)
async def read_popular_posts(
    days: int = Query(7, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Get popular posts from last N days.
    """
    posts = await post_crud.get_popular(db, days=days, limit=limit)
    return posts


@router.post("/", response_model=Post, status_code=status.HTTP_201_CREATED)
async def create_post(
    *,
    db: AsyncSession = Depends(get_async_db),
    post_in: PostCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Create new post.

    Requires authentication.
    """
    post = await post_crud.create(db=db, obj_in=post_in, author_id=int(current_user.id))
    return post
