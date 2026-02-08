from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import security
from app.core.config import settings
from app.core.security import get_current_user, get_redis
from app.crud.user import user_crud
from app.middleware.rate_limit import api_rate_limit, auth_rate_limit
from app.schemas.user import User, UserCreate, UserWithProfile
from app.schemas.token import (
    Token,
    TokenPayload,
    TokenRefresh,
    TokenRefreshResponse,
    TokenVerify,
    TokenVerifyResponse,
    PasswordResetRequest,
    PasswordReset,
)
from app.database import get_async_db
import redis.asyncio as redis
from datetime import datetime, timezone

router = APIRouter()


@router.post("/login", response_model=Token)
@auth_rate_limit()
async def login(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    redis_client: redis.Redis = Depends(get_redis),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login.

    Returns:
    - **access_token**: JWT access token
    - **refresh_token**: JWT refresh token
    - **token_type**: Always "bearer"
    - **expires_in**: Token expiration in seconds
    - **expires_at**: Exact expiration datetime
    """
    # Authenticate User
    user = await user_crud.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    # Update last login
    await user_crud.update_last_login(db, user_id=int(user.id))

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={
            "sub": user.email,
            "role": user.role.value,
            "user_id": user.id,
            "username": user.username,
            "is_superuser": user.is_superuser,
        },
        expires_delta=access_token_expires,
    )

    # create refresh token
    refresh_token = security.create_access_token(data={"sub": user.email})

    # calculate expiration datetime
    exxpires_at = datetime.now(timezone.utc) + access_token_expires

    # Store refresh token in Redis
    await redis_client.setex(
        f"refresh_token:{user.id}", timedelta(days=30), refresh_token
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": access_token_expires.total_seconds(),
        "exxpires_at": str(exxpires_at),
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    token: str = Depends(security.oauth2_scheme),
    redis_client: redis.Redis = Depends(get_redis),
) -> Any:
    """
    Logout user by blacklisting the access token
    """
    # Add token to blacklisted
    await security.blacklist_token(token)

    # Remove refresh token
    await redis_client.delete(f"refresh_token:{current_user.id}")
    return {"message": "Successfully logged out"}


@router.post("/register")
@auth_rate_limit()
async def register(
    request: Request,
    data: UserCreate,
    db: AsyncSession = Depends(get_async_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> Any:
    # Check if user email already exists
    user = await user_crud.get_user_by_email(db, email=data.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with the email already exists",
        )

    user = await user_crud.create(db, data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occured. Try again later",
        )
    return {"message": "User created successfully"}


@router.get("/me", response_model=UserWithProfile)
@api_rate_limit()
async def read_current_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Get current user information with profile.
    """
    user = await user_crud.get_by_id(db, user_id=current_user.id, include_profile=True)
    return user


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_async_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> Any:
    """
    Refresh access token using a valid refresh token

    This endpoint:
    1. validates the refresh token
    2. Issues new access and refresh tokens
    3. Invalidates the old refresh token (token rotation)
    """

    # verify refresh token
    payload = await security.verify_token(token_data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalida refresh token"
        )

    email = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalida refresh token"
        )

    # Get user
    user = await user_crud.get_user_by_email(db, email)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # verify refresh token is still valid (not revoked)
    stored_token = await redis_client.get(f"refresh_token:{user.id}")
    if stored_token != token_data.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked"
        )

    # create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = security.create_access_token(
        data={
            "sub": user.email,
            "role": user.role.value,
            "user_id": user.id,
            "username": user.username,
            "is_superuser": user.is_superuser,
        },
        expires_delta=access_token_expires,
    )

    # Create new refresh token (token rotation)
    new_refresh_token = security.create_refresh_token(data={"sub": user.email})

    # Update refresh token in redis (Invalidate old, stored new)
    await redis_client.delete(f"refresh_token:{user.id}")
    await redis_client.setex(
        f"refresh_token:{user.id}", timedelta(days=30), new_refresh_token
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": access_token_expires.total_seconds(),
    }


@router.post("/verify", response_model=TokenVerifyResponse)
async def verify_token(
    token_data: TokenVerify, redis_client: redis.Redis = Depends(get_redis)
) -> Any:
    """
    Verify if a token is valid.

    This endpoint can be used by clients to check token validaty
    without making an actual API call.
    """

    # Check if token is blackislted
    is_blacklisted = await redis_client.get(f"blacklisted:{token_data.token}")
    if is_blacklisted:
        return TokenVerifyResponse(
            payload=None, valid=False, error="Token has been revoked"
        )

    # Verify token
    payload = await security.verify_token(token_data.token)
    if payload is None:
        return TokenVerifyResponse(payload=None, valid=False, error="Invalid token")

    # Check if token has expired
    from datetime import datetime

    exp_timestamp = payload.get("exp")
    if exp_timestamp and datetime.now(timezone.utc).timestamp() > exp_timestamp:
        return TokenVerifyResponse(payload=None, valid=False, error="Token has expired")

    # Parse payload into TokenPayload scheme
    token_payload = TokenPayload(
        sub=payload.get("sub"),
        exp=payload.get("exp"),
        iat=payload.get("iat"),
        type=payload.get("type"),
        role=payload.get("role"),
        is_superuser=payload.get("is_superuser"),
        user_id=payload.get("user_id"),
        username=payload.get("username"),
    )
    return TokenVerifyResponse(valid=True, payload=token_payload, error="")


@router.post("/password/reset-request")
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_async_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> Any:
    """
    Request a password reset email

    This endpoint
    1. Checks if email exists
    2. Generates a reset token
    3. Stores token in Redis with short TTL
    4. (In productuion) send email with reset link
    """

    user = await user_crud.get_user_by_email(db, email=reset_data.email)
    if user:
        reset_token = security.create_access_token(
            data={"sub": user.email, "type": "reset", "user_id": user.id},
            expires_delta=timedelta(hours=1),
        )

        # Store reset token in redis
        await redis_client.setex(
            f"password_reset:{user.id}", timedelta(hours=1), reset_token
        )

        # In production, send email here
        # await send_password_reset_email(user.email, reset_token)

        # for demo. lets return token
        # WARNING: DOnt do this in production
        return {
            "message": "If the email exists, a reset link has been sent",
            "reset_token": reset_token,  # remove this in prod
        }

    return {"message": "If the emauil exists, a reset link has been sent"}


@router.post("/password/reset")
async def reset_password(
    reset_data: PasswordReset,
    db: AsyncSession = Depends(get_async_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> Any:
    """
    Reset password using a valid reset token
    """

    # Verify reset token
    payload = await security.verify_token(reset_data.token)
    if not payload or payload.get("type") != "reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    email = payload.get("email")
    user_id = payload.get("user_id")

    if not email or not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token"
        )

    # verify reset token is still valid in redis
    stored_token = await redis_client.get(f"password_reset:{user_id}")
    if stored_token != reset_data.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has been used or expired",
        )

    # Get user
    user = await user_crud.get_by_id(db, user_id=user_id)
    if not user or user.email != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User not found"
        )

    # Update password
    await user_crud.update_password(
        db, user_id=user_id, new_password=reset_data.new_password
    )

    # Delete used reset token
    await redis_client.delete(f"password_reset:{user_id}")

    # Invalidate all existing tokens for this user
    await redis_client.setex(
        f"token_invalidate:{user.id}",
        timedelta(minutes=5),
        str(datetime.now(timezone.utc)),
    )

    return {"message": "Password updated successfully"}
