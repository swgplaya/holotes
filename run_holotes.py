from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from dotenv import dotenv_values

from src.database import init_db


PROJECT_ROOT = Path(
    __file__
).resolve().parent

PROCESS_CHECK_INTERVAL_SECONDS = 0.5
PROCESS_STOP_TIMEOUT_SECONDS = 5


def _telegram_token_is_configured() -> bool:
    """Returns whether a Telegram bot token is configured."""

    environment_token = os.getenv(
        "TELEGRAM_BOT_TOKEN"
    )

    if (
        environment_token is not None
        and environment_token.strip()
    ):
        return True

    env_path = PROJECT_ROOT / ".env"

    if not env_path.is_file():
        return False

    values = dotenv_values(
        env_path
    )

    file_token = values.get(
        "TELEGRAM_BOT_TOKEN"
    )

    return bool(
        file_token
        and file_token.strip()
    )


@dataclass(frozen=True)
class ServiceCommand:
    """One Holotes background service."""

    name: str
    arguments: tuple[str, ...]


def build_service_commands(
    *,
    python_executable: str | None = None,
) -> tuple[ServiceCommand, ...]:
    """Builds commands for the web app and bot."""

    executable = (
        python_executable
        or sys.executable
    )

    return (
        ServiceCommand(
            name="Streamlit",
            arguments=(
                executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
            ),
        ),
        ServiceCommand(
            name="Telegram bot",
            arguments=(
                executable,
                "-m",
                "src.telegram_bot",
            ),
        ),
    )


def _stop_processes(
    processes: list[
        tuple[
            ServiceCommand,
            subprocess.Popen,
        ]
    ],
) -> None:
    """Stops all child processes."""

    for service, process in processes:
        del service

        if process.poll() is not None:
            continue

        try:
            process.terminate()

        except OSError:
            pass

    for service, process in processes:
        del service

        if process.poll() is not None:
            continue

        try:
            process.wait(
                timeout=(
                    PROCESS_STOP_TIMEOUT_SECONDS
                )
            )

        except subprocess.TimeoutExpired:
            try:
                process.kill()

            except OSError:
                pass


def run_services() -> int:
    """Runs Streamlit and Telegram together."""

    shutdown_requested = False

    def handle_sigterm(
        signum,
        frame,
    ) -> None:
        """Requests a graceful supervisor shutdown."""

        nonlocal shutdown_requested

        del signum
        del frame

        shutdown_requested = True

    previous_sigterm_handler = (
        signal.getsignal(
            signal.SIGTERM
        )
    )

    signal.signal(
        signal.SIGTERM,
        handle_sigterm,
    )

    processes: list[
        tuple[
            ServiceCommand,
            subprocess.Popen,
        ]
    ] = []

    try:
        init_db()

        services = (
            build_service_commands()
        )

        if not _telegram_token_is_configured():
            services = tuple(
                service
                for service in services
                if service.name != "Telegram bot"
            )

            print(
                "Telegram bot token is not configured. "
                "Starting web interface only."
            )

        print(
            "Starting Holotes services..."
        )

        for service in services:
            print(
                f"Starting {service.name}..."
            )

            process = subprocess.Popen(
                service.arguments,
                cwd=PROJECT_ROOT,
            )

            processes.append(
                (
                    service,
                    process,
                )
            )

        print(
            "\nHolotes is running."
        )

        print(
            "Press Ctrl+C to stop "
            "all services.\n"
        )

        while not shutdown_requested:
            for service, process in processes:
                exit_code = process.poll()

                if exit_code is None:
                    continue

                print(
                    f"\n{service.name} stopped "
                    f"with exit code {exit_code}."
                )

                return int(
                    exit_code
                )

            time.sleep(
                PROCESS_CHECK_INTERVAL_SECONDS
            )

        print(
            "\nStopping Holotes services..."
        )

        return 0

    except KeyboardInterrupt:
        print(
            "\nStopping Holotes services..."
        )

        return 0

    finally:
        signal.signal(
            signal.SIGTERM,
            previous_sigterm_handler,
        )

        _stop_processes(
            processes
        )


def main() -> None:
    """CLI entry point."""

    raise SystemExit(
        run_services()
    )


if __name__ == "__main__":
    main()
