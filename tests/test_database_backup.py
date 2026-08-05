from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from src.database_backup import (
    DatabaseBackupError,
    create_database_backup,
    get_head_revision,
    inspect_open_mas_database,
    resolve_sqlite_database_path,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)


def create_database_at_revision(
    database_path: Path,
    revision: str,
) -> None:
    """Создаёт временную базу через Alembic."""

    database_url = (
        f"sqlite:///"
        f"{database_path.as_posix()}"
    )

    environment = os.environ.copy()

    environment[
        "DATABASE_URL"
    ] = database_url

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            revision,
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


def test_resolve_sqlite_database_path(
    tmp_path: Path,
) -> None:
    resolved = resolve_sqlite_database_path(
        "sqlite:///custom/database.db",
        base_directory=tmp_path,
    )

    assert resolved == (
        tmp_path
        / "custom"
        / "database.db"
    ).resolve()


def test_inspect_open_mas_database(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "finance.db"
    )

    create_database_at_revision(
        database_path,
        "head",
    )

    inspection = inspect_open_mas_database(
        database_path
    )

    assert inspection.revision == (
        get_head_revision()
    )

    assert inspection.is_head is True
    assert inspection.size_bytes > 0

    assert (
        "bank_transactions"
        in inspection.tables
    )

    assert (
        "alembic_version"
        in inspection.tables
    )


def test_inspection_accepts_known_old_revision(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "old-finance.db"
    )

    create_database_at_revision(
        database_path,
        "0001_initial",
    )

    inspection = inspect_open_mas_database(
        database_path
    )

    assert (
        inspection.revision
        == "0001_initial"
    )

    assert inspection.is_head is False


def test_database_backup_is_independent_snapshot(
    tmp_path: Path,
) -> None:
    source_path = (
        tmp_path
        / "source.db"
    )

    backup_directory = (
        tmp_path
        / "backups"
    )

    create_database_at_revision(
        source_path,
        "head",
    )

    with sqlite3.connect(
        source_path
    ) as connection:
        connection.execute(
            "CREATE TABLE backup_test_marker "
            "(value TEXT NOT NULL)"
        )

        connection.execute(
            "INSERT INTO backup_test_marker "
            "(value) VALUES (?)",
            ("before backup",),
        )

    backup_path = create_database_backup(
        source_path,
        backup_directory,
        created_at=datetime(
            2026,
            8,
            5,
            22,
            50,
            0,
        ),
    )

    assert backup_path.name == (
        "open-mas-backup-"
        "20260805-225000.db"
    )

    with sqlite3.connect(
        source_path
    ) as connection:
        connection.execute(
            "UPDATE backup_test_marker "
            "SET value = ?",
            ("after backup",),
        )

    with sqlite3.connect(
        backup_path
    ) as connection:
        backup_value = (
            connection.execute(
                "SELECT value "
                "FROM backup_test_marker"
            ).fetchone()
        )

    assert backup_value == (
        "before backup",
    )

    backup_inspection = (
        inspect_open_mas_database(
            backup_path
        )
    )

    assert backup_inspection.is_head


def test_corrupted_database_is_rejected(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "corrupted.db"
    )

    database_path.write_bytes(
        b"this is not sqlite"
    )

    with pytest.raises(
        DatabaseBackupError
    ):
        inspect_open_mas_database(
            database_path
        )


def test_foreign_sqlite_database_is_rejected(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "foreign.db"
    )

    with sqlite3.connect(
        database_path
    ) as connection:
        connection.execute(
            "CREATE TABLE unrelated "
            "(id INTEGER PRIMARY KEY)"
        )

    with pytest.raises(
        DatabaseBackupError
    ):
        inspect_open_mas_database(
            database_path
        )
