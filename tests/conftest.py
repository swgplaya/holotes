from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from src import models  # noqa: F401
from src.database import Base


@pytest.fixture
def sqlite_session_factory(
    tmp_path: Path,
) -> Iterator[sessionmaker]:
    """Создаёт отдельную временную SQLite для каждого теста."""

    database_path = tmp_path / "test.db"

    engine = create_engine(
        URL.create(
            "sqlite",
            database=str(database_path),
        ),
        connect_args={
            "check_same_thread": False,
        },
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(
        dbapi_connection,
        connection_record,
    ) -> None:
        """Включает внешние ключи во временной SQLite."""

        del connection_record

        cursor = dbapi_connection.cursor()
        cursor.execute(
            "PRAGMA foreign_keys=ON"
        )
        cursor.close()

    Base.metadata.create_all(
        bind=engine
    )

    factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    try:
        yield factory
    finally:
        engine.dispose()