from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    sessionmaker,
)

from src.data_revision import (
    bump_database_revision,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

DEFAULT_DATABASE_PATH = DATA_DIR / "finance.db"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}",
)


class Base(DeclarativeBase):
    """Базовый класс моделей SQLAlchemy."""


connect_args: dict[str, object] = {}

if DATABASE_URL.startswith("sqlite"):
    # Streamlit может выполнять код в разных потоках.
    connect_args["check_same_thread"] = False


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)


if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def configure_sqlite_connection(
        dbapi_connection,
        connection_record,
    ) -> None:
        """Настраивает SQLite для постоянной работы Holotes."""

        del connection_record

        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

@event.listens_for(
    Session,
    "after_commit",
)
def advance_database_revision(
    session: Session,
) -> None:
    """Инвалидирует кэш чтения после успешного commit."""

    del session

    bump_database_revision()

_database_init_lock = Lock()
_database_initialized = False


def _get_alembic_config() -> Config:
    """Создаёт конфигурацию Alembic для текущего проекта."""

    config = Config(
        str(
            BASE_DIR
            / "alembic.ini"
        )
    )

    config.set_main_option(
        "script_location",
        str(
            BASE_DIR
            / "migrations"
        ),
    )

    return config

def init_db() -> None:
    """Обновляет схему базы до последней миграции."""

    global _database_initialized

    if _database_initialized:
        return

    with _database_init_lock:
        if _database_initialized:
            return

        # Импорт регистрирует модели в Base.metadata.
        from src import models  # noqa: F401

        config = _get_alembic_config()

        with engine.begin() as connection:
            config.attributes[
                "connection"
            ] = connection

            command.upgrade(
                config,
                "head",
            )

        _database_initialized = True
