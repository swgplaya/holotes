from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory
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


def get_head_revision() -> str:
    """Возвращает актуальную head-ревизию Alembic."""

    config = Config(
        str(
            PROJECT_ROOT
            / "alembic.ini"
        )
    )

    config.set_main_option(
        "script_location",
        str(
            PROJECT_ROOT
            / "migrations"
        ),
    )

    revision = (
        ScriptDirectory
        .from_config(config)
        .get_current_head()
    )

    assert revision is not None

    return revision


def run_alembic_upgrade(
    *,
    database_url: str,
    revision: str,
) -> subprocess.CompletedProcess[str]:
    """Выполняет Alembic upgrade для временной базы."""

    environment = os.environ.copy()
    environment[
        "DATABASE_URL"
    ] = database_url

    return subprocess.run(
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

        classification_indexes = {
            index["name"]
            for index in inspector.get_indexes(
                "classification_rules"
            )
        }

        payment_indexes = {
            index["name"]
            for index in inspector.get_indexes(
                "planned_cash_flows"
            )
        }

        assert (
            "ix_classification_rules_active_priority"
            in classification_indexes
        )

        assert (
            "ix_classification_rules_is_active"
            not in classification_indexes
        )

        assert (
            "ix_planned_cash_flows_active_start_date"
            in payment_indexes
        )

        assert (
            "ix_planned_cash_flows_is_active"
            not in payment_indexes
        )

        with test_engine.connect() as connection:
            revision = connection.scalar(
                text(
                    "SELECT version_num "
                    "FROM alembic_version"
                )
            )

        assert revision == get_head_revision()
    finally:
        test_engine.dispose()


def test_database_upgrades_from_initial_revision(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "migration-upgrade-test.db"
    )

    database_url = (
        f"sqlite:///{database_path.as_posix()}"
    )

    initial_result = run_alembic_upgrade(
        database_url=database_url,
        revision="0001_initial",
    )

    assert initial_result.returncode == 0, (
        initial_result.stdout
        + "\n"
        + initial_result.stderr
    )

    initial_engine = create_engine(
        database_url
    )

    try:
        inspector = inspect(
            initial_engine
        )

        initial_rule_indexes = {
            index["name"]
            for index in inspector.get_indexes(
                "classification_rules"
            )
        }

        initial_payment_indexes = {
            index["name"]
            for index in inspector.get_indexes(
                "planned_cash_flows"
            )
        }

        assert (
            "ix_classification_rules_is_active"
            in initial_rule_indexes
        )

        assert (
            "ix_classification_rules_active_priority"
            not in initial_rule_indexes
        )

        assert (
            "ix_planned_cash_flows_is_active"
            in initial_payment_indexes
        )

        assert (
            "ix_planned_cash_flows_active_start_date"
            not in initial_payment_indexes
        )
    finally:
        initial_engine.dispose()

    upgrade_result = run_alembic_upgrade(
        database_url=database_url,
        revision="head",
    )

    assert upgrade_result.returncode == 0, (
        upgrade_result.stdout
        + "\n"
        + upgrade_result.stderr
    )

    upgraded_engine = create_engine(
        database_url
    )

    try:
        inspector = inspect(
            upgraded_engine
        )

        upgraded_rule_indexes = {
            index["name"]
            for index in inspector.get_indexes(
                "classification_rules"
            )
        }

        upgraded_payment_indexes = {
            index["name"]
            for index in inspector.get_indexes(
                "planned_cash_flows"
            )
        }

        assert (
            "ix_classification_rules_active_priority"
            in upgraded_rule_indexes
        )

        assert (
            "ix_classification_rules_is_active"
            not in upgraded_rule_indexes
        )

        assert (
            "ix_planned_cash_flows_active_start_date"
            in upgraded_payment_indexes
        )

        assert (
            "ix_planned_cash_flows_is_active"
            not in upgraded_payment_indexes
        )

        with upgraded_engine.connect() as connection:
            revision = connection.scalar(
                text(
                    "SELECT version_num "
                    "FROM alembic_version"
                )
            )

        assert revision == get_head_revision()
    finally:
        upgraded_engine.dispose()
