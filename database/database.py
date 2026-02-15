"""
Database engine and session setup.
"""
import os
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from logger_config import logger

# Import Base from models (ensure models.py defines Base)
from .models import Base

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
