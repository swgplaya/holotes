from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


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
    def enable_sqlite_foreign_keys(
        dbapi_connection,
        connection_record,
    ) -> None:
        """Включает поддержку внешних ключей в SQLite."""

        del connection_record

        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def init_db() -> None:
    """Создаёт отсутствующие таблицы."""

    # Импорт нужен здесь, чтобы SQLAlchemy увидел модели.
    from src import models  # noqa: F401

    Base.metadata.create_all(bind=engine)