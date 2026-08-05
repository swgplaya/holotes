from __future__ import annotations

import run_open_mas


def test_build_service_commands() -> None:
    services = (
        run_open_mas
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
