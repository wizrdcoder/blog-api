from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy import Column
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from app.core.config import settings
from app.crud.user import user_crud
from app.database import get_async_db
from app.models.user import User
import bcrypt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,  # Allow optional authentication
)

# redis connection pool
redis_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global redis_pool
    if redis_pool is None:
        redis_pool = await redis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    return redis_pool


# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password, hashed_password)


# def get_password_hash(password: str) -> str:
#     return pwd_context.hash(password)


def verify_password(
    plain_password: Union[str, bytes], hashed_password: Union[str, bytes]
) -> bool:
    """
    Verify password using direct bcrypt.
    """
    # Convert to bytes if strings
    if isinstance(plain_password, str):
        plain_password = plain_password.encode("utf-8")
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode("utf-8")

    try:
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception as e:
        print(f"Verification error: {e}")
        return False


def get_password_hash(password: Union[str, bytes]) -> str:
    """
    Generate password hash using direct bcrypt.
    """
    if isinstance(password, str):
        password = password.encode("utf-8")

    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password, salt)

    # Return as string
    return hashed.decode("utf-8")


def create_access_token(
    data: dict[str, Any], expires_delta: Optional[timedelta] = None
):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=30)  # 30 days expiry

    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def verify_token(token: str) -> Optional[dict[str, Any]]:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> Optional[User]:
    if token is None:
        return None

    is_blacklisted = await redis_client.get(f"blacklist:{token}")
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
        )
    print("token ==================", token)
    payload = await verify_token(token)
    print("payload ==================", payload)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credential",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: str | None = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credential",
        )

    user = await user_crud.get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive User"
        )
    return user


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Dependency to get current active user"""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return current_user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any] | User:
    """Dependency to get current superuser"""
    if not current_user or not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


def require_role(required_role: str):
    """
    Factory function to create role-based dependency.
    Returns a sync function that FastAPI can use.
    """

    async def role_checker(current_user: Any = Depends(get_current_user)) -> Any:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Check if user has required role or is admin
        if not hasattr(current_user, "role"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User role not defined"
            )

        if current_user.role not in [required_role, "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role or higher",
            )

        return current_user

    return role_checker


# Create role-specific dependencies
require_moderator = require_role("moderator")
require_admin = require_role("admin")


async def blacklist_token(token: str) -> None:
    """Add token to blacklist (for logout)"""
    redis_client = await get_redis()
    payload = await verify_token(token)
    if payload and "exp" in payload:
        expire_at = payload["exp"]
        # ttl = expire_at - int(datetime.now(timezone.utc))
        time_diff = expire_at - datetime.now(timezone.utc)
        ttl = int(time_diff.total_seconds())
        if ttl > 0:
            await redis_client.setex(f"blacklist:{token}", ttl, "1")
