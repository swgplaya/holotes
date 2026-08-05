from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import (
    create_engine,
    inspect,
    text,
)

from src import models  # noqa: F401
from src.database import Base


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)


def test_init_db_applies_migrations_to_empty_database(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "migration-test.db"
    )

    database_url = (
        f"sqlite:///{database_path.as_posix()}"
    )

    environment = os.environ.copy()
    environment[
        "DATABASE_URL"
    ] = database_url

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from src.database "
                "import init_db; "
                "init_db(); "
                "init_db()"
            ),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, (
        result.stdout
        + "\n"
        + result.stderr
    )

    test_engine = create_engine(
        database_url
    )

    try:
        inspector = inspect(
            test_engine
        )

        actual_tables = set(
            inspector.get_table_names()
        )

        expected_tables = (
            set(
                Base.metadata.tables
            )
            | {
                "alembic_version",
            }
        )

        assert actual_tables == expected_tables

        with test_engine.connect() as connection:
            revision = connection.scalar(
                text(
                    "SELECT version_num "
                    "FROM alembic_version"
                )
            )

        assert revision == "0001_initial"
    finally:
        test_engine.dispose()
