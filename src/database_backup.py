from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

from src.database import (
    BASE_DIR,
    DATABASE_URL,
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


def _connect_read_only(
    database_path: Path,
) -> sqlite3.Connection:
    """Открывает SQLite-файл без возможности изменения."""

    database_uri = (
        database_path.resolve().as_uri()
        + "?mode=ro"
    )

    return sqlite3.connect(
        database_uri,
        uri=True,
    )


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
            with sqlite3.connect(
                backup_path
            ) as backup_connection:
                source_connection.backup(
                    backup_connection
                )

        inspect_open_mas_database(
            backup_path
        )

    except Exception:
        backup_path.unlink(
            missing_ok=True
        )

        raise

    return backup_path
