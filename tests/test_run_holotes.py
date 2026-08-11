from __future__ import annotations

import signal

import pytest

import run_holotes


def test_build_service_commands() -> None:
    services = (
        run_holotes
        .build_service_commands(
            python_executable=(
                "test-python"
            )
        )
    )

    assert [
        service.name
        for service in services
    ] == [
        "Streamlit",
        "Telegram bot",
    ]

    assert services[
        0
    ].arguments == (
        "test-python",
        "-m",
        "streamlit",
        "run",
        "app.py",
    )

    assert services[
        1
    ].arguments == (
        "test-python",
        "-m",
        "src.telegram_bot",
    )


class _FakeProcess:
    def __init__(
        self,
        *,
        exit_code: int | None,
    ) -> None:
        self.exit_code = exit_code
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.exit_code

    def terminate(self) -> None:
        self.terminated = True
        self.exit_code = 0

    def wait(
        self,
        timeout: float | None = None,
    ) -> int:
        del timeout

        return int(
            self.exit_code or 0
        )

    def kill(self) -> None:
        self.killed = True
        self.exit_code = -9


def test_run_services_initializes_database_before_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        run_holotes,
        "init_db",
        lambda: calls.append(
            "init_db"
        ),
    )

    monkeypatch.setattr(
        run_holotes.subprocess,
        "Popen",
        lambda *args, **kwargs: (
            calls.append(
                "popen"
            )
            or _FakeProcess(
                exit_code=0
            )
        ),
    )

    result = run_holotes.run_services()

    assert result == 0

    assert calls[:2] == [
        "init_db",
        "popen",
    ]


def test_run_services_handles_sigterm_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess(
        exit_code=None
    )

    captured_handler = None
    previous_handler = object()

    restored_handlers: list[
        object
    ] = []

    monkeypatch.setattr(
        run_holotes,
        "init_db",
        lambda: None,
    )

    monkeypatch.setattr(
        run_holotes.subprocess,
        "Popen",
        lambda *args, **kwargs: process,
    )

    monkeypatch.setattr(
        run_holotes.signal,
        "getsignal",
        lambda signum: previous_handler,
    )

    def fake_signal(
        signum,
        handler,
    ):
        nonlocal captured_handler

        assert signum == signal.SIGTERM

        if handler is previous_handler:
            restored_handlers.append(
                handler
            )

        else:
            captured_handler = handler

        return previous_handler

    monkeypatch.setattr(
        run_holotes.signal,
        "signal",
        fake_signal,
    )

    def request_shutdown(
        seconds: float,
    ) -> None:
        del seconds

        assert captured_handler is not None

        captured_handler(
            signal.SIGTERM,
            None,
        )

    monkeypatch.setattr(
        run_holotes.time,
        "sleep",
        request_shutdown,
    )

    result = run_holotes.run_services()

    assert result == 0
    assert process.terminated is True
    assert process.killed is False

    assert restored_handlers == [
        previous_handler
    ]
