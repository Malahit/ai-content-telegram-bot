import logging
import os
from logging.config import fileConfig

logger = logging.getLogger("alembic")

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

RAILWAY_POSTGRES_URL = "postgresql://postgres:WrFVnUDQCKOHptbvcWSIlpfuXKCmQHbM@postgres.railway.internal:5432/railway"

_db_url = os.environ.get("DATABASE_URL")
if not _db_url:
    _db_url = RAILWAY_POSTGRES_URL
    logger.info("DATABASE_URL not set — using hardcoded Railway PostgreSQL URL")

if _db_url.startswith("postgres://"):
    _db_url = "postgresql://" + _db_url[len("postgres://"):]

config.set_main_option("sqlalchemy.url", _db_url)

from database.models import Base
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
