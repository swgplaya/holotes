from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

import pytest


PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)


def find_free_port() -> int:
    """Возвращает свободный локальный TCP-порт."""

    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as server_socket:
        server_socket.bind(
            ("127.0.0.1", 0)
        )

        return int(
            server_socket
            .getsockname()[1]
        )


@pytest.fixture(scope="session")
def streamlit_base_url(
    tmp_path_factory: pytest.TempPathFactory,
) -> str:
    """Запускает Holotes с изолированной временной БД."""

    temporary_directory = (
        tmp_path_factory.mktemp(
            "browser-smoke"
        )
    )

    database_path = (
        temporary_directory
        / "browser-smoke.db"
    )

    log_path = (
        temporary_directory
        / "streamlit.log"
    )

    port = find_free_port()

    base_url = (
        f"http://127.0.0.1:{port}"
    )

    environment = os.environ.copy()

    environment["DATABASE_URL"] = (
        f"sqlite:///{database_path.as_posix()}"
    )

    environment[
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS"
    ] = "false"

    seed_script = """
from datetime import date, datetime, time, timedelta

from src.database import SessionLocal, init_db
from src.models import BankTransaction


init_db()

today = date.today()
first_current_month = today.replace(day=1)
previous_month_date = (
    first_current_month
    - timedelta(days=1)
)

posted_at = datetime.combine(
    previous_month_date,
    time(12, 0),
)

with SessionLocal() as session:
    session.add(
        BankTransaction(
            source_hash="b" * 64,
            direction="income",
            posted_at=posted_at,
            amount_kopecks=100_00,
            signed_amount_kopecks=100_00,
            currency="RUB",
            description=(
                "Browser smoke report transaction"
            ),
            include_in_pnl=True,
            pnl_category="Продажи",
            include_in_cf=True,
            cf_category="Операционная деятельность",
            classification_status="classified",
        )
    )
    session.commit()
"""

    seed_result = subprocess.run(
        [
            sys.executable,
            "-c",
            seed_script,
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    if seed_result.returncode != 0:
        raise RuntimeError(
            "Could not seed browser smoke database.\n\n"
            + seed_result.stdout
            + "\n"
            + seed_result.stderr
        )

    with log_path.open(
        "w+",
        encoding="utf-8",
    ) as log_file:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.headless=true",
                "--server.address=127.0.0.1",
                f"--server.port={port}",
                "--browser.gatherUsageStats=false",
            ],
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

        deadline = (
            time.monotonic()
            + 45
        )

        try:
            while (
                time.monotonic()
                < deadline
            ):
                if (
                    process.poll()
                    is not None
                ):
                    break

                try:
                    with urlopen(
                        base_url,
                        timeout=1,
                    ) as response:
                        if response.status == 200:
                            yield base_url
                            return
                except (
                    URLError,
                    TimeoutError,
                ):
                    time.sleep(0.25)

            log_file.flush()
            log_file.seek(0)

            output = log_file.read()

            raise RuntimeError(
                "Streamlit did not start.\n\n"
                + output
            )
        finally:
            if process.poll() is None:
                process.terminate()

                try:
                    process.wait(
                        timeout=10
                    )
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(
                        timeout=5
                    )
