from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from src.data_revision import (
    bump_database_revision,
    get_database_revision,
)


def test_database_revision_can_be_bumped_manually(
) -> None:
    before = get_database_revision()

    after = bump_database_revision()

    assert after == before + 1
    assert get_database_revision() == after


def test_session_commit_bumps_database_revision(
    sqlite_session_factory: sessionmaker,
) -> None:
    before = get_database_revision()

    with sqlite_session_factory() as session:
        session.execute(
            text("SELECT 1")
        )
        session.commit()

    assert (
        get_database_revision()
        == before + 1
    )
