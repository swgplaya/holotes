from __future__ import annotations

from threading import Lock


_revision_lock = Lock()
_database_revision = 0


def get_database_revision() -> int:
    """Возвращает текущую ревизию данных приложения."""

    with _revision_lock:
        return _database_revision


def bump_database_revision() -> int:
    """Увеличивает ревизию после успешного изменения базы."""

    global _database_revision

    with _revision_lock:
        _database_revision += 1

        return _database_revision
