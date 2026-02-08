from typing import AsyncGenerator, Generator, Any
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from sqlalchemy.orm import DeclarativeBase

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# create async engine for PostgreSQL
async_engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.LOG_LEVEL == "DEBUG",
    poolclass=NullPool,
    future=True,
)

# create async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# create Base class for models
# Base: DeclarativeMeta = declarative_base()


class Base(DeclarativeBase):
    pass


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get async database session.
    Used with FastAPI's Depends for async endpoints.
    """

    session = AsyncSessionLocal()

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


sync_engine = create_engine(
    str(settings.DATABASE_URL).replace("postgresql+asyncpg", "postgresql"),
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


def get_sync_db() -> Generator[Any, Any]:
    """
    Get syncronous database session for background tasks or CLI
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
