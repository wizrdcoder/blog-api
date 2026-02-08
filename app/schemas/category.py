from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from .post import Post, PostWithCategories, PostWithComments

PostWithCategories.model_rebuild()
PostWithComments.model_rebuild()


class CategoryBase(BaseModel):
    """Base category schema"""

    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    is_featured: bool = False


class CategoryCreate(CategoryBase):
    """Schema for creating a category"""

    pass


class CategoryUpdate(BaseModel):
    """Schema for updating a category"""

    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None
    is_featured: Optional[bool] = None


class Category(CategoryBase):
    """Category schema for API responses"""

    id: UUID
    slug: str
    post_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CategoryWithPosts(Category):
    """Category schema with posts"""

    posts: List[Post] = []
