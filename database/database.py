"""
Database engine and session setup.

Important for Railway / hosted Postgres:
- Railway often provides DATABASE_URL as "postgresql://..." (sync URL).
- SQLAlchemy async engine requires an async driver in the URL, e.g. "postgresql+asyncpg://...".

We normalize the URL automatically so the app works out-of-the-box on Railway.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from logger_config import logger
from .models import Base


def _to_async_database_url(url: str) -> str:
    """Convert common Postgres URLs to SQLAlchemy asyncpg URLs.

    Examples:
      - postgresql://... -> postgresql+asyncpg://...
      - postgres://...   -> postgresql+asyncpg://...

    Other schemes (sqlite+aiosqlite, etc.) are returned as-is.
    """

    if not url:
        return url

    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Some platforms still emit the deprecated postgres:// scheme
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)

    return url


# Priority for DB URL:
# 1) environment variable DATABASE_URL
# 2) config.database_url (if defined)
# 3) fallback to local sqlite file for dev
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    try:
        from config import config
        DATABASE_URL = getattr(config, "database_url", None)
    except Exception:
        DATABASE_URL = None

if not DATABASE_URL:
    DATABASE_URL = "sqlite+aiosqlite:///./ai_content_bot.db"
    logger.info("No DATABASE_URL provided — using local SQLite for dev: ./ai_content_bot.db")

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
