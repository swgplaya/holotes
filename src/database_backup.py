from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
import tempfile
from threading import Lock

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from src.data_revision import (
    bump_database_revision,
)
from src.database import (
    BASE_DIR,
    DATABASE_URL,
    engine,
)


REQUIRED_OPEN_MAS_TABLES = frozenset(
    {
        "alembic_version",
        "bank_transactions",
        "classification_rules",
        "import_batches",
        "import_batch_transactions",
        "planned_cash_flows",
        "unit_economics_products",
        "unit_economics_cost_items",
    }
)


class DatabaseBackupError(Exception):
    """Ошибка резервного копирования или проверки базы."""


@dataclass(frozen=True)
class DatabaseInspection:
    """Результат проверки базы Open MAS."""

    path: Path
    revision: str
    head_revision: str
    is_head: bool
    size_bytes: int
    tables: tuple[str, ...]


def get_alembic_script_directory() -> ScriptDirectory:
    """Возвращает историю миграций проекта."""

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

    return ScriptDirectory.from_config(
        config
    )


def get_head_revision() -> str:
    """Возвращает единственную head-ревизию Alembic."""

    script_directory = (
        get_alembic_script_directory()
    )

    heads = script_directory.get_heads()

    if len(heads) != 1:
        raise DatabaseBackupError(
            "История миграций должна содержать "
            "ровно одну head-ревизию."
        )

    return heads[0]


def resolve_sqlite_database_path(
    database_url: str = DATABASE_URL,
    *,
    base_directory: Path = BASE_DIR,
) -> Path:
    """Преобразует SQLite URL в абсолютный путь."""

    url = make_url(database_url)

    if url.get_backend_name() != "sqlite":
        raise DatabaseBackupError(
            "Резервное копирование пока "
            "поддерживает только SQLite."
        )

    database_name = url.database

    if not database_name:
        raise DatabaseBackupError(
            "В DATABASE_URL не указан файл базы."
        )

    if database_name == ":memory:":
        raise DatabaseBackupError(
            "Базу SQLite в памяти нельзя "
            "сохранить как резервную копию."
        )

    database_path = Path(
        database_name
    )

    if not database_path.is_absolute():
        database_path = (
            base_directory
            / database_path
        )

    return database_path.resolve()


@contextmanager
def _connect_read_only(
    database_path: Path,
) -> Iterator[sqlite3.Connection]:
    """Opens a read-only SQLite connection and closes it."""

    database_uri = (
        database_path.resolve().as_uri()
        + "?mode=ro"
    )

    connection = sqlite3.connect(
        database_uri,
        uri=True,
    )

    try:
        yield connection
    finally:
        connection.close()


def _read_database_revision(
    connection: sqlite3.Connection,
) -> str:
    """Читает единственную ревизию Alembic."""

    revision_rows = connection.execute(
        "SELECT version_num "
        "FROM alembic_version"
    ).fetchall()

    if len(revision_rows) != 1:
        raise DatabaseBackupError(
            "Таблица alembic_version должна "
            "содержать ровно одну ревизию."
        )

    revision = str(
        revision_rows[0][0]
    ).strip()

    if not revision:
        raise DatabaseBackupError(
            "В базе не указана ревизия Alembic."
        )

    return revision


def inspect_open_mas_database(
    database_path: Path,
) -> DatabaseInspection:
    """Проверяет целостность и совместимость базы."""

    database_path = (
        Path(database_path).resolve()
    )

    if not database_path.is_file():
        raise DatabaseBackupError(
            "Файл базы данных не найден."
        )

    if database_path.stat().st_size == 0:
        raise DatabaseBackupError(
            "Файл базы данных пуст."
        )

    try:
        with _connect_read_only(
            database_path
        ) as connection:
            integrity_rows = (
                connection.execute(
                    "PRAGMA integrity_check"
                ).fetchall()
            )

            integrity_messages = [
                str(row[0])
                for row in integrity_rows
            ]

            if integrity_messages != ["ok"]:
                raise DatabaseBackupError(
                    "SQLite integrity_check "
                    "обнаружил повреждение базы: "
                    + "; ".join(
                        integrity_messages[:5]
                    )
                )

            table_rows = connection.execute(
                "SELECT name "
                "FROM sqlite_master "
                "WHERE type = 'table'"
            ).fetchall()

            tables = {
                str(row[0])
                for row in table_rows
            }

            missing_tables = (
                REQUIRED_OPEN_MAS_TABLES
                - tables
            )

            if missing_tables:
                raise DatabaseBackupError(
                    "Файл не является совместимой "
                    "базой Open MAS. "
                    "Отсутствуют таблицы: "
                    + ", ".join(
                        sorted(missing_tables)
                    )
                )

            revision = (
                _read_database_revision(
                    connection
                )
            )

            foreign_key_violations = (
                connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall()
            )

            if foreign_key_violations:
                raise DatabaseBackupError(
                    "В базе обнаружены нарушения "
                    "внешних ключей."
                )

    except DatabaseBackupError:
        raise
    except sqlite3.DatabaseError as exc:
        raise DatabaseBackupError(
            "Не удалось прочитать SQLite-базу."
        ) from exc

    script_directory = (
        get_alembic_script_directory()
    )

    known_revisions = {
        revision_item.revision
        for revision_item
        in script_directory.walk_revisions()
    }

    if revision not in known_revisions:
        raise DatabaseBackupError(
            "Версия базы не поддерживается "
            "этой сборкой Open MAS: "
            f"{revision}."
        )

    head_revision = get_head_revision()

    return DatabaseInspection(
        path=database_path,
        revision=revision,
        head_revision=head_revision,
        is_head=(
            revision
            == head_revision
        ),
        size_bytes=(
            database_path.stat().st_size
        ),
        tables=tuple(
            sorted(tables)
        ),
    )


def _build_backup_path(
    backup_directory: Path,
    created_at: datetime,
) -> Path:
    """Создаёт свободное имя backup-файла."""

    timestamp = created_at.strftime(
        "%Y%m%d-%H%M%S"
    )

    base_name = (
        f"open-mas-backup-{timestamp}"
    )

    candidate = (
        backup_directory
        / f"{base_name}.db"
    )

    suffix = 1

    while candidate.exists():
        candidate = (
            backup_directory
            / f"{base_name}-{suffix}.db"
        )

        suffix += 1

    return candidate


def create_database_backup(
    source_path: Path,
    backup_directory: Path,
    *,
    created_at: datetime | None = None,
) -> Path:
    """Создаёт согласованный снимок SQLite-базы."""

    source_path = Path(
        source_path
    ).resolve()

    backup_directory = Path(
        backup_directory
    ).resolve()

    inspect_open_mas_database(
        source_path
    )

    backup_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    backup_path = _build_backup_path(
        backup_directory,
        created_at or datetime.now(),
    )

    try:
        with _connect_read_only(
            source_path
        ) as source_connection:
            backup_connection = (
                sqlite3.connect(
                    backup_path
                )
            )

            try:
                source_connection.backup(
                    backup_connection
                )

                backup_connection.commit()
            finally:
                backup_connection.close()

        inspect_open_mas_database(
            backup_path
        )

    except Exception:
        backup_path.unlink(
            missing_ok=True
        )

        raise

    return backup_path


@dataclass(frozen=True)
class DatabaseRestoreResult:
    """Result of restoring an Open MAS database."""

    database_path: Path
    safety_backup_path: Path
    source_revision: str
    restored_revision: str
    migrated: bool


_database_restore_lock = Lock()


def upgrade_open_mas_database(
    database_path: Path,
) -> DatabaseInspection:
    """Upgrades a separate SQLite database to head."""

    database_path = Path(
        database_path
    ).resolve()

    inspection_before = (
        inspect_open_mas_database(
            database_path
        )
    )

    if inspection_before.is_head:
        return inspection_before

    migration_engine = create_engine(
        (
            "sqlite:///"
            + database_path.as_posix()
        ),
        connect_args={
            "check_same_thread": False,
        },
    )

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

    try:
        with migration_engine.begin() as connection:
            config.attributes[
                "connection"
            ] = connection

            command.upgrade(
                config,
                "head",
            )
    except Exception as exc:
        raise DatabaseBackupError(
            "Could not upgrade the restored "
            "database to the current schema."
        ) from exc
    finally:
        migration_engine.dispose()

    inspection_after = (
        inspect_open_mas_database(
            database_path
        )
    )

    if not inspection_after.is_head:
        raise DatabaseBackupError(
            "The restored database did not "
            "reach the current schema revision."
        )

    return inspection_after


def _copy_sqlite_database(
    source_path: Path,
    target_path: Path,
) -> None:
    """Copies one SQLite database into another."""

    source_path = Path(
        source_path
    ).resolve()

    target_path = Path(
        target_path
    ).resolve()

    target_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with _connect_read_only(
        source_path
    ) as source_connection:
        target_connection = (
            sqlite3.connect(
                target_path,
                timeout=30,
            )
        )

        try:
            source_connection.backup(
                target_connection
            )

            target_connection.commit()
        finally:
            target_connection.close()


def restore_database(
    uploaded_database_path: Path,
    current_database_path: Path,
    backup_directory: Path,
) -> DatabaseRestoreResult:
    """
    Restores the working database safely.

    The uploaded file is validated and upgraded in
    a temporary copy. A safety backup is created
    before the current database is overwritten.
    """

    uploaded_database_path = Path(
        uploaded_database_path
    ).resolve()

    current_database_path = Path(
        current_database_path
    ).resolve()

    backup_directory = Path(
        backup_directory
    ).resolve()

    if (
        uploaded_database_path
        == current_database_path
    ):
        raise DatabaseBackupError(
            "A database cannot be restored "
            "from itself."
        )

    with _database_restore_lock:
        inspect_open_mas_database(
            current_database_path
        )

        with tempfile.TemporaryDirectory(
            prefix="open-mas-restore-",
            dir=current_database_path.parent,
        ) as temporary_directory:
            staging_path = (
                Path(temporary_directory)
                / "staging.db"
            )

            try:
                shutil.copy2(
                    uploaded_database_path,
                    staging_path,
                )
            except OSError as exc:
                raise DatabaseBackupError(
                    "Could not prepare the uploaded "
                    "database for restoration."
                ) from exc

            source_inspection = (
                inspect_open_mas_database(
                    staging_path
                )
            )

            migrated = (
                not source_inspection.is_head
            )

            restored_inspection = (
                upgrade_open_mas_database(
                    staging_path
                )
            )

            safety_backup_path = (
                create_database_backup(
                    current_database_path,
                    backup_directory,
                )
            )

            engine.dispose()

            try:
                _copy_sqlite_database(
                    staging_path,
                    current_database_path,
                )

                final_inspection = (
                    inspect_open_mas_database(
                        current_database_path
                    )
                )

                if not final_inspection.is_head:
                    raise DatabaseBackupError(
                        "The restored database does "
                        "not use the current schema."
                    )

            except Exception as restore_error:
                engine.dispose()

                try:
                    _copy_sqlite_database(
                        safety_backup_path,
                        current_database_path,
                    )

                    inspect_open_mas_database(
                        current_database_path
                    )

                    bump_database_revision()

                except Exception as rollback_error:
                    raise DatabaseBackupError(
                        "Database restoration and "
                        "automatic rollback both "
                        "failed. Safety backup: "
                        f"{safety_backup_path}"
                    ) from rollback_error

                raise DatabaseBackupError(
                    "Database restoration failed. "
                    "The previous state was "
                    "restored automatically."
                ) from restore_error

            bump_database_revision()

            return DatabaseRestoreResult(
                database_path=(
                    current_database_path
                ),
                safety_backup_path=(
                    safety_backup_path
                ),
                source_revision=(
                    source_inspection.revision
                ),
                restored_revision=(
                    restored_inspection.revision
                ),
                migrated=migrated,
            )
