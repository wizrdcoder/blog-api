from typing import Optional, Any, ForwardRef
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
from uuid import UUID

from .user import User


# Forward references
CategoryRef = ForwardRef("Category")
CommentRef = ForwardRef("Comment")


class PostBase(BaseModel):
    """Base post schema"""

    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=10)
    excerpt: Optional[str] = Field(None, max_length=500)
    published: bool = False
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    def validate_tags(cls, v):
        """Validate tags array"""
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        for tag in v:
            if len(tag) > 50:
                raise ValueError("Tag must be 50 characters or less")
        return v


class PostCreate(PostBase):
    """Schema for creating a new post"""

    category_ids: Optional[list[UUID]] = None


class PostUpdate(BaseModel):
    """Schema for updating a post"""

    title: Optional[str] = Field(None, min_length=5, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    excerpt: Optional[str] = Field(None, max_length=500)
    published: Optional[bool] = None
    tags: Optional[list[str]] = None
    category_ids: Optional[list[UUID]] = None

    model_config = ConfigDict(extra="forbid")


class PostInDBBase(PostBase):
    """Base schema for post data in database"""

    id: UUID
    slug: str
    author_id: int
    view_count: int
    like_count: int
    comment_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Post(PostInDBBase):
    """Post schema for API responses"""

    author: Optional[User] = None


class PostWithCategories(Post):
    """Post schema with categories"""

    categories: list[CategoryRef] = []


class PostWithComments(Post):
    """Post schema with comments"""

    comments: list["Comment"] = []


class PostSearchResult(BaseModel):
    """Schema for search results"""

    id: UUID
    title: str
    excerpt: Optional[str]
    slug: str
    author: Optional[User]
    relevance_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class PostsPaginated(BaseModel):
    """Paginated response for posts"""

    items: list[Post]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)
