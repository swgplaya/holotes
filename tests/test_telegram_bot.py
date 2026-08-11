from __future__ import annotations

from types import SimpleNamespace

import pytest

import src.telegram_bot as telegram_bot
from src.telegram_settings import (
    TelegramSettings,
)


def make_update(
    *,
    text: str,
    user_id: int = 123456789,
    chat_id: int = 123456789,
    chat_type: str = "private",
    language_code: str = "ru",
    message_thread_id: int | None = None,
) -> dict[str, object]:
    message: dict[str, object] = {
        "message_id": 200,
        "text": text,
        "from": {
            "id": user_id,
            "language_code": (
                language_code
            ),
        },
        "chat": {
            "id": chat_id,
            "type": chat_type,
        },
    }

    if message_thread_id is not None:
        message[
            "message_thread_id"
        ] = message_thread_id

    return {
        "update_id": 100,
        "message": message,
    }


def make_settings(
    *,
    is_enabled: bool = True,
) -> TelegramSettings:
    return TelegramSettings(
        is_enabled=is_enabled,
        default_summary_period=(
            "current_month"
        ),
        include_cash_flow=True,
        include_pnl=True,
        include_pending_count=True,
        include_payment_calendar=True,
    )


def test_register_bot_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[
        dict[str, object]
    ] = []

    def fake_api_request(
        **kwargs: object,
    ) -> bool:
        calls.append(
            kwargs
        )

        return True

    monkeypatch.setattr(
        telegram_bot,
        "_telegram_api_request",
        fake_api_request,
    )

    telegram_bot.register_bot_commands(
        token="SECRET"
    )

    assert len(calls) == 3

    assert all(
        call["method"]
        == "setMyCommands"
        for call in calls
    )

    assert [
        call["parameters"].get(
            "language_code"
        )
        for call in calls
    ] == [
        None,
        "ru",
        "zh",
    ]

    for call in calls:
        commands = call[
            "parameters"
        ]["commands"]

        assert [
            command["command"]
            for command in commands
        ] == [
            "start",
            "help",
            "myid",
            "chatid",
            "language",
            "summary",
        ]


def test_fatal_polling_errors() -> None:
    unauthorized = (
        telegram_bot
        .TelegramBotApiError(
            "Unauthorized",
            status_code=401,
        )
    )

    conflict = (
        telegram_bot
        .TelegramBotApiError(
            "Conflict",
            status_code=409,
        )
    )

    temporary = (
        telegram_bot
        .TelegramBotApiError(
            "Temporary network error"
        )
    )

    assert (
        telegram_bot
        ._polling_error_is_fatal(
            unauthorized
        )
        is True
    )

    assert (
        telegram_bot
        ._polling_error_is_fatal(
            conflict
        )
        is True
    )

    assert (
        telegram_bot
        ._polling_error_is_fatal(
            temporary
        )
        is False
    )


def test_parse_command_with_bot_mention() -> None:
    command = telegram_bot.parse_command(
        "/summary@HolotesBot 2026-07",
        bot_username="holotesbot",
    )

    assert command == (
        telegram_bot.ParsedCommand(
            name="summary",
            arguments="2026-07",
        )
    )


def test_command_for_another_bot_is_ignored() -> None:
    assert (
        telegram_bot.parse_command(
            "/summary@another_bot",
            bot_username="holotesbot",
        )
        is None
    )


def test_extract_message_context() -> None:
    context = (
        telegram_bot
        .extract_message_context(
            make_update(
                text="/myid",
                chat_id=-100123,
                chat_type="supergroup",
                message_thread_id=4,
            )
        )
    )

    assert context is not None
    assert context.update_id == 100
    assert context.message_id == 200

    assert (
        context.telegram_user_id
        == 123456789
    )

    assert (
        context.telegram_chat_id
        == -100123
    )

    assert (
        context.chat_type
        == "supergroup"
    )

    assert (
        context.message_thread_id
        == 4
    )


def test_myid_is_available_without_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent_messages: list[
        tuple[int, str]
    ] = []

    monkeypatch.setattr(
        telegram_bot,
        "send_text",
        lambda *, token, chat_id, text, message_thread_id=None: (
            sent_messages.append(
                (
                    chat_id,
                    text,
                )
            )
        ),
    )

    handled = telegram_bot.handle_update(
        update=make_update(
            text="/myid"
        ),
        token="SECRET",
        bot_username="holotesbot",
    )

    assert handled is True

    assert sent_messages == [
        (
            123456789,
            (
                "Ваш Telegram user ID: "
                "123456789"
            ),
        )
    ]


def test_summary_rejects_unauthorized_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []

    monkeypatch.setattr(
        telegram_bot,
        "get_telegram_settings",
        lambda: make_settings(),
    )

    monkeypatch.setattr(
        telegram_bot,
        "is_telegram_request_allowed",
        lambda **kwargs: False,
    )

    monkeypatch.setattr(
        telegram_bot,
        "send_text",
        lambda *, token, chat_id, text, message_thread_id=None: (
            messages.append(
                text
            )
        ),
    )

    monkeypatch.setattr(
        telegram_bot,
        "build_telegram_summary",
        lambda **kwargs: (
            pytest.fail(
                "Summary must not be built."
            )
        ),
    )

    telegram_bot.handle_update(
        update=make_update(
            text="/summary"
        ),
        token="SECRET",
        bot_username="holotesbot",
    )

    assert len(messages) == 1

    assert (
        "Доступ к финансовым данным запрещён"
        in messages[0]
    )


def test_disabled_bot_rejects_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []

    monkeypatch.setattr(
        telegram_bot,
        "get_telegram_settings",
        lambda: make_settings(
            is_enabled=False
        ),
    )

    monkeypatch.setattr(
        telegram_bot,
        "send_text",
        lambda *, token, chat_id, text, message_thread_id=None: (
            messages.append(
                text
            )
        ),
    )

    telegram_bot.handle_update(
        update=make_update(
            text="/summary"
        ),
        token="SECRET",
        bot_username="holotesbot",
    )

    assert len(messages) == 1

    assert (
        "сейчас отключены"
        in messages[0]
    )


def test_authorized_summary_uses_period(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}
    messages: list[str] = []

    settings = make_settings()

    monkeypatch.setattr(
        telegram_bot,
        "get_telegram_settings",
        lambda: settings,
    )

    monkeypatch.setattr(
        telegram_bot,
        "is_telegram_request_allowed",
        lambda **kwargs: True,
    )

    def fake_build(
        *,
        period: str | None,
        settings: TelegramSettings,
    ) -> object:
        calls["period"] = period
        calls["settings"] = settings

        return SimpleNamespace()

    monkeypatch.setattr(
        telegram_bot,
        "build_telegram_summary",
        fake_build,
    )

    def fake_format(
        summary: object,
        *,
        language: str,
    ) -> str:
        del summary

        calls["language"] = language

        return "FINANCIAL SUMMARY"

    monkeypatch.setattr(
        telegram_bot,
        "format_telegram_summary",
        fake_format,
    )

    monkeypatch.setattr(
        telegram_bot,
        "send_text",
        lambda *, token, chat_id, text, message_thread_id=None: (
            messages.append(
                text
            )
        ),
    )

    telegram_bot.handle_update(
        update=make_update(
            text="/summary 2026-07"
        ),
        token="SECRET",
        bot_username="holotesbot",
    )

    assert calls == {
        "period": "2026-07",
        "settings": settings,
        "language": "ru",
    }

    assert messages == [
        "FINANCIAL SUMMARY"
    ]


def test_invalid_summary_arguments_show_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []

    monkeypatch.setattr(
        telegram_bot,
        "get_telegram_settings",
        lambda: make_settings(),
    )

    monkeypatch.setattr(
        telegram_bot,
        "is_telegram_request_allowed",
        lambda **kwargs: True,
    )

    monkeypatch.setattr(
        telegram_bot,
        "send_text",
        lambda *, token, chat_id, text, message_thread_id=None: (
            messages.append(
                text
            )
        ),
    )

    telegram_bot.handle_update(
        update=make_update(
            text=(
                "/summary 2026-07 extra"
            )
        ),
        token="SECRET",
        bot_username="holotesbot",
    )

    assert len(messages) == 1

    assert (
        "/summary 2026-07"
        in messages[0]
    )


def test_send_text_targets_forum_topic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[
        dict[str, object]
    ] = []

    def fake_api_request(
        **kwargs: object,
    ) -> dict[str, object]:
        calls.append(
            kwargs
        )

        return {
            "message_id": 1,
        }

    monkeypatch.setattr(
        telegram_bot,
        "_telegram_api_request",
        fake_api_request,
    )

    telegram_bot.send_text(
        token="SECRET",
        chat_id=-100123,
        message_thread_id=4,
        text="Summary",
    )

    assert len(calls) == 1

    assert calls[0][
        "parameters"
    ] == {
        "chat_id": -100123,
        "message_thread_id": 4,
        "text": "Summary",
    }


def test_split_message_respects_limit() -> None:
    chunks = telegram_bot._split_message(
        "12345\n67890\nabcde",
        limit=11,
    )

    assert chunks == (
        "12345\n67890",
        "abcde",
    )

    assert all(
        len(chunk) <= 11
        for chunk in chunks
    )


def test_main_initializes_database_before_bot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        telegram_bot,
        "init_db",
        lambda: calls.append(
            "init_db"
        ),
    )

    monkeypatch.setattr(
        telegram_bot,
        "run_bot",
        lambda: calls.append(
            "run_bot"
        ),
    )

    telegram_bot.main()

    assert calls == [
        "init_db",
        "run_bot",
    ]
