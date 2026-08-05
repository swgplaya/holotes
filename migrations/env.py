from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from src import models  # noqa: F401
from src.database import (
    Base,
    DATABASE_URL,
    engine,
)


config = context.config

if config.config_file_name is not None:
    fileConfig(
        config.config_file_name
    )


target_metadata = Base.metadata


def configure_connection(
    connection: Connection,
) -> None:
    """Configure and run online migrations."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=(
            connection.dialect.name
            == "sqlite"
        ),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Run migrations without a live connection."""

    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
        render_as_batch=(
            DATABASE_URL.startswith(
                "sqlite"
            )
        ),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using the application engine."""

    supplied_connection = (
        config.attributes.get(
            "connection"
        )
    )

    if supplied_connection is not None:
        configure_connection(
            supplied_connection
        )
        return

    with engine.connect() as connection:
        configure_connection(
            connection
        )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()