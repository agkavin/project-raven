"""
Database connection and session management for PostgreSQL.
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv(dotenv_path="../.env")

logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/project_raven"
)

# Create async engine
# NullPool is used with asyncpg to prevent connection reuse across event loops
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI endpoints to get database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

async def init_db():
    """
    Initialize database tables.
    This is called on application startup.
    """
    from .models import Base
    
    try:
        async with engine.begin() as conn:
            # Create all tables (fresh DB, no Alembic)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def close_db():
    """
    Close database connections.
    """
    await engine.dispose()
    logger.info("Database connections closed")
