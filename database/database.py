"""
Database engine and session setup.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from logger_config import logger
from .models import Base

RAILWAY_POSTGRES_URL = "postgresql+asyncpg://postgres:WrFVnUDQCKOHptbvcWSIlpfuXKCmQHbM@postgres.railway.internal:5432/railway"


def _to_async_database_url(url: str) -> str:
    if not url:
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    try:
        from config import config
        DATABASE_URL = getattr(config, "database_url", None)
    except Exception:
        DATABASE_URL = None

if not DATABASE_URL:
    DATABASE_URL = RAILWAY_POSTGRES_URL
    logger.info("No DATABASE_URL env var — using hardcoded Railway PostgreSQL URL")

DATABASE_URL = _to_async_database_url(DATABASE_URL)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created/verified")
    except SQLAlchemyError as e:
        logger.exception(f"Failed to initialize database: {e}")
        raise


def get_session() -> AsyncSession:
    return AsyncSessionLocal()
