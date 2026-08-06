from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

import src.database_backup as database_backup

from src.database_backup import (
    DatabaseBackupError,
    create_database_backup,
    get_head_revision,
    inspect_holotes_database,
    resolve_sqlite_database_path,
    restore_database,
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


def test_inspect_holotes_database(
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

    inspection = inspect_holotes_database(
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

    inspection = inspect_holotes_database(
        database_path
    )

    assert (
        inspection.revision
        == "0001_initial"
    )

    assert inspection.is_head is False


def test_inspection_accepts_0002_without_telegram_tables(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "revision-0002.db"
    )

    create_database_at_revision(
        database_path,
        "0002_query_indexes",
    )

    inspection = inspect_holotes_database(
        database_path
    )

    assert (
        inspection.revision
        == "0002_query_indexes"
    )

    assert inspection.is_head is False

    assert (
        "telegram_bot_settings"
        not in inspection.tables
    )


def test_head_revision_requires_telegram_tables(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "incomplete-head.db"
    )

    create_database_at_revision(
        database_path,
        "head",
    )

    with sqlite3.connect(
        database_path
    ) as connection:
        connection.execute(
            "DROP TABLE "
            "telegram_allowed_users"
        )

    with pytest.raises(
        DatabaseBackupError,
        match="telegram_allowed_users",
    ):
        inspect_holotes_database(
            database_path
        )


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
        "holotes-backup-"
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
        inspect_holotes_database(
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
        inspect_holotes_database(
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
        inspect_holotes_database(
            database_path
        )


def set_restore_marker(
    database_path: Path,
    value: str,
) -> None:
    """Writes a test marker value to the database."""

    with sqlite3.connect(
        database_path
    ) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS "
            "restore_test_marker "
            "(value TEXT NOT NULL)"
        )

        connection.execute(
            "DELETE FROM "
            "restore_test_marker"
        )

        connection.execute(
            "INSERT INTO "
            "restore_test_marker "
            "(value) VALUES (?)",
            (value,),
        )


def get_restore_marker(
    database_path: Path,
) -> str:
    """Reads a test marker value from the database."""

    with sqlite3.connect(
        database_path
    ) as connection:
        row = connection.execute(
            "SELECT value "
            "FROM restore_test_marker"
        ).fetchone()

    assert row is not None

    return str(row[0])


def test_restore_database_replaces_data_and_keeps_backup(
    tmp_path: Path,
) -> None:
    current_path = (
        tmp_path
        / "current.db"
    )

    uploaded_path = (
        tmp_path
        / "uploaded.db"
    )

    backup_directory = (
        tmp_path
        / "backups"
    )

    create_database_at_revision(
        current_path,
        "head",
    )

    create_database_at_revision(
        uploaded_path,
        "head",
    )

    set_restore_marker(
        current_path,
        "current value",
    )

    set_restore_marker(
        uploaded_path,
        "uploaded value",
    )

    result = restore_database(
        uploaded_path,
        current_path,
        backup_directory,
    )

    assert get_restore_marker(
        current_path
    ) == "uploaded value"

    assert get_restore_marker(
        result.safety_backup_path
    ) == "current value"

    assert result.source_revision == (
        get_head_revision()
    )

    assert result.restored_revision == (
        get_head_revision()
    )

    assert result.migrated is False

    assert (
        result.safety_backup_path
        .is_file()
    )


def test_restore_database_upgrades_old_backup(
    tmp_path: Path,
) -> None:
    current_path = (
        tmp_path
        / "current.db"
    )

    uploaded_path = (
        tmp_path
        / "uploaded-old.db"
    )

    backup_directory = (
        tmp_path
        / "backups"
    )

    create_database_at_revision(
        current_path,
        "head",
    )

    create_database_at_revision(
        uploaded_path,
        "0001_initial",
    )

    set_restore_marker(
        current_path,
        "current value",
    )

    set_restore_marker(
        uploaded_path,
        "old uploaded value",
    )

    result = restore_database(
        uploaded_path,
        current_path,
        backup_directory,
    )

    inspection = (
        inspect_holotes_database(
            current_path
        )
    )

    assert inspection.is_head is True

    assert get_restore_marker(
        current_path
    ) == "old uploaded value"

    assert (
        result.source_revision
        == "0001_initial"
    )

    assert result.restored_revision == (
        get_head_revision()
    )

    assert result.migrated is True


def test_invalid_restore_file_does_not_change_database(
    tmp_path: Path,
) -> None:
    current_path = (
        tmp_path
        / "current.db"
    )

    uploaded_path = (
        tmp_path
        / "invalid.db"
    )

    backup_directory = (
        tmp_path
        / "backups"
    )

    create_database_at_revision(
        current_path,
        "head",
    )

    set_restore_marker(
        current_path,
        "original value",
    )

    uploaded_path.write_bytes(
        b"not a sqlite database"
    )

    with pytest.raises(
        DatabaseBackupError
    ):
        restore_database(
            uploaded_path,
            current_path,
            backup_directory,
        )

    assert get_restore_marker(
        current_path
    ) == "original value"

    assert (
        not backup_directory.exists()
        or not any(
            backup_directory.iterdir()
        )
    )


def test_failed_restore_rolls_back_to_safety_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_path = (
        tmp_path
        / "current.db"
    )

    uploaded_path = (
        tmp_path
        / "uploaded.db"
    )

    backup_directory = (
        tmp_path
        / "backups"
    )

    create_database_at_revision(
        current_path,
        "head",
    )

    create_database_at_revision(
        uploaded_path,
        "head",
    )

    set_restore_marker(
        current_path,
        "original value",
    )

    set_restore_marker(
        uploaded_path,
        "new value",
    )

    original_copy = (
        database_backup
        ._copy_sqlite_database
    )

    call_count = 0

    def failing_first_copy(
        source_path: Path,
        target_path: Path,
    ) -> None:
        nonlocal call_count

        call_count += 1

        if call_count == 1:
            with sqlite3.connect(
                target_path
            ) as connection:
                connection.execute(
                    "UPDATE restore_test_marker "
                    "SET value = ?",
                    ("partially damaged",),
                )

            raise OSError(
                "Simulated restore failure"
            )

        original_copy(
            source_path,
            target_path,
        )

    monkeypatch.setattr(
        database_backup,
        "_copy_sqlite_database",
        failing_first_copy,
    )

    with pytest.raises(
        DatabaseBackupError,
    ):
        restore_database(
            uploaded_path,
            current_path,
            backup_directory,
        )

    assert call_count == 2

    assert get_restore_marker(
        current_path
    ) == "original value"

    backups = list(
        backup_directory.glob(
            "holotes-backup-*.db"
        )
    )

    assert len(backups) == 1

    assert get_restore_marker(
        backups[0]
    ) == "original value"
