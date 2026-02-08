from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Token(BaseModel):
    """
    Token response schema.
    Returned after successful login.
    """

    access_token: str = Field(
        description="JWT access token for API authentication",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    refresh_token: str = Field(
        description="JWT refresh token for obtaining new access token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Type of token (always 'bearer' for JWT)",
        examples=["bearer"],
    )
    expires_in: int = Field(
        description="Time in seconds until the access token expires"
    )
    expires_at: Optional[datetime] = Field(
        None, description="Exact datetime when the access token expires"
    )


class TokenPayload(BaseModel):
    """
    Decoded JWT token payload schema.class
    Represents the data stored inside the JWT token.
    """

    sub: Optional[str] = Field(
        ...,
        description="Subject (usually user email or ID)",
        examples=["user@example.com"],
    )
    exp: Optional[int] = Field(
        ..., description="Expiration timestamp (Unix timestamp)", examples=[1672531199]
    )
    iat: Optional[int] = Field(
        ..., description="Issued at timestamp (Unix timestamp)", examples=[1672527599]
    )
    type: Optional[str] = Field(
        ...,
        description="Token type ('access', 'refresh', or 'reset')",
        examples=["access"],
    )
    role: Optional[str] = Field(
        None, description="User role (if included in token)", examples=["user"]
    )
    is_superuser: Optional[bool] = Field(
        None,
        description="Whether user is superuser (if included in token)",
        examples=[False],
    )
    user_id: Optional[int] = Field(
        None, description="User ID (if included in token)", examples=[1]
    )
    username: Optional[str] = Field(
        None, description="Username (if included in token)", examples=["john_doe"]
    )


class TokenCreate(BaseModel):
    """
    Schema for creating tokens.
    Used internally by authentication functions.
    """

    email: str = Field(..., description="User email address")
    user_id: int = Field(..., description="User ID")
    role: str = Field(..., description="User role")
    is_superuser: bool = Field(default=False, description="Whether user is superuser")
    expires_delta: Optional[int] = Field(
        None, description="Optional custom expiration time in seconds"
    )


class TokenRefresh(BaseModel):
    """
    Schema for token refresh request.
    """

    refresh_token: str = Field(
        ...,
        description="Valid refresh token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )


class TokenRefreshResponse(BaseModel):
    """
    Response schema for token refresh endpoint.
    """

    access_token: str = Field(
        ...,
        description="New access token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    refresh_token: str = Field(
        ...,
        description="New refresh token (rotated)",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(default="bearer")
    expires_in: int = Field(
        ...,
        description="Time in seconds until the new access token expires",
        examples=[3600],
    )


class TokenVerify(BaseModel):
    """
    Schema for token verification request.
    """

    token: str = Field(
        ...,
        description="Token to verify",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )


class TokenVerifyResponse(BaseModel):
    """
    Response schema for token verification endpoint.
    """

    valid: bool = Field(..., description="Whether the token is valid", examples=[True])
    payload: Optional[TokenPayload] = Field(
        None, description="Decoded token payload if valid"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if token is invalid",
        examples=["Token has expired"],
    )


class PasswordResetRequest(BaseModel):
    """
    Schema for password reset request.
    """

    email: str = Field(
        ..., description="User email address", examples=["user@example.com"]
    )


class PasswordReset(BaseModel):
    """
    Schema for password reset.
    """

    token: str = Field(
        ...,
        description="Password reset token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password",
        examples=["NewStrongPassword123!"],
    )
    confirm_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Confirmation of new password",
        examples=["NewStrongPassword123!"],
    )

    def model_post_init(self, __context):
        """Validate that passwords match."""
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
