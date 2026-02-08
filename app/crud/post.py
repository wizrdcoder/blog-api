from typing import Optional, List, Dict, Any, Sequence
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Row, select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.dialects.postgresql import array_agg
from app.models.post import Category, Post, Comment, Like
from app.models.user import User
from app.schemas.post import PostCreate, PostUpdate
import slugify


class PostCRUD:
    """
    CRUD operations for Post model with PostgreSQL-specific features.
    """

    @staticmethod
    async def get(
        db: AsyncSession,
        post_id: UUID,
        include_author: bool = True,
        include_categories: bool = False,
        include_comments: bool = False,
    ) -> Optional[Post]:
        """Get post by ID with optional relationships"""
        query = select(Post).where(Post.id == post_id)

        # Eager loading based on options
        if include_author:
            query = query.options(selectinload(Post.author))
        if include_categories:
            query = query.options(selectinload(Post.categories))
        if include_comments:
            query = query.options(
                selectinload(Post.comments).selectinload(Comment.user)
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_slug(db: AsyncSession, slug: str) -> Optional[Post]:
        """Get post by slug"""
        query = select(Post).where(Post.slug == slug).options(selectinload(Post.author))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_multi(
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        published_only: bool = True,
        author_id: Optional[int] = None,
        category_id: Optional[int] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> List[Post] | Sequence[Post]:
        """Get multiple posts with advanced filtering"""
        query = select(Post).options(selectinload(Post.author))

        # Apply filters
        if published_only:
            query = query.where(Post.published.is_(True))

        if author_id:
            query = query.where(Post.author_id == author_id)

        if category_id:
            query = query.join(Post.categories).where(Category.id == category_id)

        if tag:
            query = query.where(Post.tags.contains([tag]))

        if search:
            search_conditions = or_(
                Post.title.ilike(f"%{search}%"),
                Post.content.ilike(f"%{search}%"),
                Post.excerpt.ilike(f"%{search}%"),
            )
            query = query.where(search_conditions)

        # Apply ordering
        order_column = getattr(Post, order_by, Post.created_at)
        if order_desc:
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create(db: AsyncSession, *, obj_in: PostCreate, author_id: int) -> Post:
        """Create new post"""

        # Generate slug from title
        slug = slugify.slugify(obj_in.title)

        # Check for duplicate slug
        counter = 1
        original_slug = slug
        while await PostCRUD.get_by_slug(db, slug):
            slug = f"{original_slug}-{counter}"
            counter += 1

        # Create post instance
        db_obj = Post(
            title=obj_in.title,
            slug=slug,
            content=obj_in.content,
            excerpt=obj_in.excerpt,
            published=obj_in.published,
            tags=obj_in.tags,
            author_id=author_id,
        )

        # Add categories if provided
        if obj_in.category_ids:
            categories = await db.execute(
                select(Category).where(Category.id.in_(obj_in.category_ids))
            )
            db_obj.categories = categories.scalars().all()

        # Set published_at if publishing
        if obj_in.published:
            from datetime import datetime, timezone

            db_obj.published_at = datetime.now(timezone.utc)  # type: ignore[assignment]

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        return db_obj

    @staticmethod
    async def update(db: AsyncSession, *, db_obj: Post, obj_in: PostUpdate) -> Post:
        """Update post"""
        update_data = obj_in.model_dump(exclude_unset=True)

        # Update slug if title changed
        if "title" in update_data:
            new_slug = slugify.slugify(update_data["title"])

            # Check for duplicate slug
            counter = 1
            original_slug = new_slug
            while await PostCRUD.get_by_slug(db, new_slug):
                new_slug = f"{original_slug}-{counter}"
                counter += 1

            update_data["slug"] = new_slug

        # Handle categories update
        if "category_ids" in update_data:
            categories = await db.execute(
                select(Category).where(Category.id.in_(update_data["category_ids"]))
            )
            db_obj.categories = categories.scalars().all()
            del update_data["category_ids"]

        # Set published_at if publishing for the first time
        if (
            "published" in update_data
            and update_data["published"]
            and not db_obj.published
        ):
            from datetime import datetime, timezone

            update_data["published_at"] = datetime.now(timezone.utc)

        # Update fields
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        return db_obj

    @staticmethod
    async def increment_view_count(db: AsyncSession, post_id: UUID) -> None:
        """Increment post view count atomically"""
        query = (
            update(Post)
            .where(Post.id == post_id)
            .values(view_count=Post.view_count + 1)
        )
        await db.execute(query)
        await db.commit()

    @staticmethod
    async def search_full_text(
        db: AsyncSession, search_query: str, limit: int = 20
    ) -> List[Post] | Sequence[Row[Any]]:
        """Full-text search using PostgreSQL tsvector"""
        from sqlalchemy import text

        # Using PostgreSQL full-text search
        query = text("""
            SELECT id, title, excerpt, slug, author_id,
                   ts_rank(search_vector, plainto_tsquery(:query)) as rank
            FROM posts
            WHERE search_vector @@ plainto_tsquery(:query)
            AND published = true
            ORDER BY rank DESC
            LIMIT :limit
        """)

        result = await db.execute(query, {"query": search_query, "limit": limit})

        return result.fetchall()

    @staticmethod
    async def get_popular(
        db: AsyncSession, days: int = 7, limit: int = 10
    ) -> List[Post] | Sequence[Post]:
        """Get popular posts based on views in last N days"""
        from datetime import datetime, timedelta, timezone

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(Post)
            .where(Post.published.is_(True))
            .where(Post.created_at >= cutoff_date)
            .order_by(Post.view_count.desc())
            .limit(limit)
            .options(selectinload(Post.author))
        )

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_statistics(
        db: AsyncSession, author_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get post statistics"""
        query = select(
            func.count(Post.id).label("total_posts"),
            func.sum(Post.view_count).label("total_views"),
            func.avg(Post.view_count).label("avg_views"),
            func.max(Post.view_count).label("max_views"),
        ).where(Post.published.is_(True))

        if author_id:
            query = query.where(Post.author_id == author_id)

        result = await db.execute(query)
        stats = result.one()

        return {
            "total_posts": stats.total_posts or 0,
            "total_views": stats.total_views or 0,
            "avg_views": float(stats.avg_views or 0),
            "max_views": stats.max_views or 0,
        }


# Create singleton instance
post_crud = PostCRUD()
