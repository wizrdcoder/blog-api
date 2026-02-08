from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Enum,
    Text,
)
from sqlalchemy.orm import relationship
import enum
from app.database import Base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import backref
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text


class UserRole(str, enum.Enum):
    """Enum for user roles"""

    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class User(Base):
    """
    User model with PostgreSQL-specific features.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(100))
    last_login = Column(DateTime(timezone=True), nullable=True)
    hashed_password = Column(String(255), nullable=False)

    # profile fields
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # status fields
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)

    # role based asccess control
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"),
        nullable=False,
        default=UserRole.USER,
        # server_default=UserRole.USER.value,
    )
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # timestamps with timezone support
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship(
        "Comment", back_populates="user", cascade="all, delete-orphan"
    )
    likes = relationship("Like", back_populates="user")

    # def __repr__(self) -> str:
    #     return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class UserProfile(Base):
    """
    Extended user profile information.
    """

    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    website = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)

    # JSON field for additional metadata
    user_metadata = Column(JSONB, default={}, nullable=True)

    # PostgreSQL-specific: Use check connection
    # __table_args__ = CheckConstraint(
    #     "char_length(website) <= 500", name="website_length_check"
    # )

    # Relationship
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile",
    )
    # user = relationship("User", backref=backref("profile", uselist=False))
