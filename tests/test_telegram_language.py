from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

import src.telegram_bot as telegram_bot
import src.telegram_settings as telegram_settings
from src.telegram_settings import TelegramSettings


def settings() -> TelegramSettings:
    return TelegramSettings(
        is_enabled=True,
        default_summary_period="current_month",
        include_cash_flow=True,
        include_pnl=True,
        include_pending_count=True,
        include_payment_calendar=True,
    )


def update(text: str) -> dict[str, object]:
    return {
        "update_id": 1,
        "message": {
            "message_id": 2,
            "text": text,
            "from": {
                "id": 123,
                "language_code": "ru",
            },
            "chat": {
                "id": 123,
                "type": "private",
            },
        },
    }


def test_language_repository_persists_per_chat(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_session_factory: sessionmaker,
) -> None:
    monkeypatch.setattr(
        telegram_settings,
        "SessionLocal",
        sqlite_session_factory,
    )

    assert telegram_settings.get_telegram_summary_language(
        telegram_chat_id=123,
        default_language="en",
    ) == "en"

    assert telegram_settings.set_telegram_summary_language(
        telegram_chat_id=123,
        language="zh",
    ) == "zh-CN"

    assert telegram_settings.get_telegram_summary_language(
        telegram_chat_id=123,
    ) == "zh-CN"


def test_language_command_changes_summary_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    saved: dict[str, object] = {}

    monkeypatch.setattr(
        telegram_bot,
        "get_telegram_settings",
        settings,
    )
    monkeypatch.setattr(
        telegram_bot,
        "is_telegram_request_allowed",
        lambda **kwargs: True,
    )
    monkeypatch.setattr(
        telegram_bot,
        "get_telegram_summary_language",
        lambda **kwargs: "ru",
    )

    def save_language(
        *,
        telegram_chat_id: int,
        language: str,
    ) -> str:
        saved["chat_id"] = telegram_chat_id
        saved["language"] = language
        return language

    monkeypatch.setattr(
        telegram_bot,
        "set_telegram_summary_language",
        save_language,
    )
    monkeypatch.setattr(
        telegram_bot,
        "send_text",
        lambda *, token, chat_id, text,
        message_thread_id=None: messages.append(text),
    )

    assert telegram_bot.handle_update(
        update=update("/language en"),
        token="SECRET",
        bot_username="holotesbot",
    ) is True

    assert saved == {
        "chat_id": 123,
        "language": "en",
    }
    assert messages == [
        "Financial summary language changed to English."
    ]


def test_summary_uses_saved_chat_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    used: dict[str, object] = {}

    monkeypatch.setattr(
        telegram_bot,
        "get_telegram_settings",
        settings,
    )
    monkeypatch.setattr(
        telegram_bot,
        "is_telegram_request_allowed",
        lambda **kwargs: True,
    )
    monkeypatch.setattr(
        telegram_bot,
        "get_telegram_summary_language",
        lambda **kwargs: "en",
    )
    monkeypatch.setattr(
        telegram_bot,
        "build_telegram_summary",
        lambda **kwargs: SimpleNamespace(),
    )

    def format_summary(
        summary: object,
        *,
        language: str,
    ) -> str:
        del summary
        used["language"] = language
        return "SUMMARY"

    monkeypatch.setattr(
        telegram_bot,
        "format_telegram_summary",
        format_summary,
    )
    monkeypatch.setattr(
        telegram_bot,
        "send_text",
        lambda **kwargs: None,
    )

    telegram_bot.handle_update(
        update=update("/summary"),
        token="SECRET",
        bot_username="holotesbot",
    )

    assert used["language"] == "en"
