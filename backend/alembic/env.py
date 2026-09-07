import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.assistant import models as assistant_models  # noqa: F401
from app.calendar import models  # noqa: F401
from app.core.config import get_settings
from app.course_calendars import models as course_calendar_models  # noqa: F401
from app.course_sources import models as course_source_models  # noqa: F401
from app.courses import models as course_models  # noqa: F401
from app.database.base import Base
from app.diagnostics import models as diagnostic_models  # noqa: F401
from app.inbox import models as inbox_models  # noqa: F401
from app.integrations import models as integration_models  # noqa: F401
from app.notes import models as note_models  # noqa: F401
from app.notes import summary_models as note_summary_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
