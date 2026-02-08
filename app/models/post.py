from sqlalchemy import (
    Column,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Table,
    ARRAY,
    CheckConstraint,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base
from sqlalchemy.dialects.postgresql import JSONB

# Association table for many-to-many relationship
# post_categories = Table(
#     "post_categories",
#     Base.metadata,
#     Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE")),
#     Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE")),
#     # Composite primary key
#     PrimaryKeyConstraint("post_id", "category_id"),
# )
post_categories = Table(
    "post_categories",
    Base.metadata,
    Column("post_id", UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE")),
    Column(
        "category_id",
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
    ),
    PrimaryKeyConstraint("post_id", "category_id"),
)


class Post(Base):
    """
    Blog post model with PostgreSQL advanced features.
    """

    __tablename__ = "posts"

    # Using UUID for distributed systems
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, index=True, nullable=False)
    content = Column(Text, nullable=False)
    excerpt = Column(String(500))

    # Status
    published = Column(Boolean, default=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # SEO
    meta_title = Column(String(200))
    meta_description = Column(String(500))

    # Statistics
    view_count = Column(Integer, default=0, index=True)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)

    # Foreign keys
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # PostgreSQL arrays for tags
    # tags = Column(ARRAY(String(50)), nullable=False, server_default=text("'{}'"))
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        nullable=False,
        server_default=text("'{}'"),
    )
    # tags = Column(
    #     ARRAY(String(50)),
    #     nullable=False,
    #     server_default=text("'{}'"),
    # )

    # JSONB for flexible metadata
    post_metadata = Column(JSONB, default=dict, nullable=False)

    # Full-text search vector (PostgreSQL specific)
    search_vector = Column(TSVECTOR)

    # Relationships with explicit cascade rules
    author = relationship("User", back_populates="posts")
    categories = relationship(
        "Category",
        secondary=post_categories,
        back_populates="posts",
        lazy="selectin",  # Eager loading strategy
    )
    comments = relationship(
        "Comment",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="Comment.created_at.desc()",
    )
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")

    # PostgreSQL-specific constraints and indexes
    __table_args__ = (
        # Check constraints
        CheckConstraint("char_length(title) >= 5", name="title_length_check"),
        CheckConstraint("view_count >= 0", name="view_count_positive"),
        # Partial index for performance
        # Index("idx_posts_published", "published", postgresql_where=(published == True)),
        # Full-text search index
        Index("idx_posts_search", "search_vector", postgresql_using="gin"),
        # Index on array column (PostgreSQL specific)
        Index("idx_posts_tags", "tags", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Post(id={self.id}, title={self.title}, author_id={self.author_id})>"


class Comment(Base):
    """Comment model with hierarchical replies support."""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)

    # Hierarchical comments (self-referential foreign key)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)

    # Foreign keys
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Status
    is_approved = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], backref="replies")

    __table_args__ = (
        Index("idx_comments_post", "post_id", "created_at"),
        Index("idx_comments_user", "user_id", "created_at"),
    )


class Like(Base):
    """Like model for posts."""

    __tablename__ = "likes"

    id = Column(Integer, primary_key=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Unique constraint to prevent duplicate likes
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_post_user_like"),)

    # Relationships
    post = relationship("Post", back_populates="likes")
    user = relationship("User", back_populates="likes")


class Category(Base):
    """Category model for organizing posts."""

    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    slug = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text)

    # SEO
    meta_title = Column(String(200))
    meta_description = Column(String(500))

    # Display
    is_featured = Column(Boolean, default=False)
    display_order = Column(Integer, default=0, index=True)

    # Relationships
    posts = relationship(
        "Post",
        secondary="post_categories",
        back_populates="categories",
        lazy="dynamic",  # Returns query instead of list
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name})>"
