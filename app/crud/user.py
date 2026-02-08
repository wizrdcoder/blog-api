from typing import Optional, Any, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, or_
from sqlalchemy.orm import selectinload
from app.models.post import Comment, Post
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from datetime import datetime, timezone


class UserCRUD:
    """
    CRUD opeerations for User mode with async support.
    Uses SQLAlachemy 2.0 ASYNC API
    """

    @staticmethod
    async def get_by_id(
        db: AsyncSession, user_id: int, include_profile: bool = False
    ) -> Optional[User]:
        query = select(User).where(User.id == user_id)

        if include_profile:
            query = query.options(selectinload(User.profile))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(
        db: AsyncSession, username: str, include_profile: bool = False
    ) -> Optional[User]:
        query = select(User).where(User.username == username)

        if include_profile:
            query = query.options(selectinload(User.profile))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(
        db: AsyncSession, email: str, include_profile: bool = False
    ) -> Optional[User]:
        query = select(User).where(User.email == email)

        if include_profile:
            query = query.options(selectinload(User.profile))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_multi(
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> list[User] | Sequence[User]:
        """Get multiple users with filtering"""
        query = select(User)

        # Apply filters
        if search:
            search_filter = or_(
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)

        if role:
            query = query.where(User.role == role)

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_count(db: AsyncSession, **filters) -> Any:
        """Get count of users matching filters"""
        query = select(func.count(User.id))

        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(User, key):
                    query = query.where(getattr(User, key) == value)

        result = await db.execute(query)
        return result.scalar()

    @staticmethod
    async def create(db: AsyncSession, obj_in: UserCreate) -> User:
        from app.core.security import get_password_hash

        """Create new user"""
        # Hash password
        hashed_password = get_password_hash(obj_in.password)

        # Create user instance
        db_obj = User(
            email=obj_in.email,
            username=obj_in.username,
            full_name=obj_in.full_name,
            hashed_password=hashed_password,
            role=UserRole.USER,
            created_at=datetime.now(timezone.utc),
        )

        # Add to session
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        return db_obj

    @staticmethod
    async def update(db: AsyncSession, *, db_obj: User, obj_in: UserUpdate) -> User:
        from app.core.security import get_password_hash, verify_password

        """Update user"""
        update_data = obj_in.model_dump(exclude_unset=True)

        # Handle password update
        if "password" in update_data:
            hashed_password = get_password_hash(update_data["password"])
            update_data["hashed_password"] = hashed_password
            del update_data["password"]

        # Update fields
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        return db_obj

    @staticmethod
    async def authenticate(
        db: AsyncSession, *, email: str, password: str
    ) -> Optional[User]:
        from app.core.security import verify_password

        """Authenticate user by email and password"""
        user = await UserCRUD.get_user_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, str(user.hashed_password)):
            return None
        return user

    @staticmethod
    async def delete_user(db: AsyncSession, *, user_id: int) -> bool:
        """Delete user (soft delete by marking as inactive)"""
        query = (
            update(User)
            .where(User.id == user_id)
            .values(is_active=False)
            .returning(User.id)
        )

        result = await db.execute(query)
        await db.commit()

        return result.scalar() is not None

    @staticmethod
    async def update_last_login(db: AsyncSession, *, user_id: int) -> None:
        """Update user's last login timestamp"""
        from datetime import datetime, timezone

        query = (
            update(User)
            .where(User.id == user_id)
            .values(last_login=datetime.now(timezone.utc))
        )
        await db.execute(query)
        await db.commit()

    @staticmethod
    async def get_with_stats(db: AsyncSession, user_id: int) -> dict[str, Any] | None:
        """Get user with statistics (post count, comment count, etc.)"""
        from sqlalchemy import func

        # Subquery for post count
        post_count_subq = (
            select(func.count()).where(Post.author_id == user_id).scalar_subquery()
        )

        # Subquery for comment count
        comment_count_subq = (
            select(func.count()).where(Comment.user_id == user_id).scalar_subquery()
        )

        # Main query
        query = select(
            User,
            post_count_subq.label("post_count"),
            comment_count_subq.label("comment_count"),
        ).where(User.id == user_id)

        result = await db.execute(query)
        row = result.first()

        if not row:
            return None

        user, post_count, comment_count = row
        user_dict = {
            **user.__dict__,
            "post_count": post_count,
            "comment_count": comment_count,
        }

        return user_dict

    @staticmethod
    async def update_password(
        db: AsyncSession, user_id: int, new_password: str
    ) -> None:
        from app.core.security import get_password_hash

        password_hashed = get_password_hash(new_password)
        query = (
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=password_hashed)
        )
        await db.execute(query)
        await db.commit()


user_crud = UserCRUD()
