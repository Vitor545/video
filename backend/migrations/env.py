import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config
fileConfig(config.config_file_name)

# Use sync URL from env for migrations
sync_url = os.getenv(
    "SYNC_DATABASE_URL",
    "postgresql+psycopg2://devops:devops@db:5432/devops_platform"
)
config.set_main_option("sqlalchemy.url", sync_url)

from app.database import Base  # noqa: E402
import app.infrastructure.models  # noqa: F401, E402

target_metadata = Base.metadata


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
