from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

import src.telegram_settings as telegram_settings
from src.models import (
    TelegramAllowedChat,
    TelegramAllowedUser,
    TelegramBotSettings,
)


@pytest.fixture
def isolated_repository(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_session_factory: sessionmaker,
) -> sessionmaker:
    """Uses an isolated Telegram database."""

    monkeypatch.setattr(
        telegram_settings,
        "SessionLocal",
        sqlite_session_factory,
    )

    return sqlite_session_factory


def test_get_settings_creates_singleton_with_defaults(
    isolated_repository: sessionmaker,
) -> None:
    settings = (
        telegram_settings
        .get_telegram_settings()
    )

    assert settings.is_enabled is False

    assert (
        settings.default_summary_period
        == "current_month"
    )

    assert settings.include_cash_flow is True
    assert settings.include_pnl is True

    assert (
        settings.include_pending_count
        is True
    )

    assert (
        settings.include_payment_calendar
        is True
    )

    telegram_settings.get_telegram_settings()

    with isolated_repository() as session:
        count = session.scalar(
            select(
                func.count(
                    TelegramBotSettings.id
                )
            )
        )

    assert count == 1


def test_update_settings_persists_values(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    updated = (
        telegram_settings
        .update_telegram_settings(
            is_enabled=True,
            default_summary_period=(
                "last_30_days"
            ),
            include_cash_flow=True,
            include_pnl=False,
            include_pending_count=False,
            include_payment_calendar=True,
        )
    )

    assert updated.is_enabled is True

    assert (
        updated.default_summary_period
        == "last_30_days"
    )

    assert updated.include_cash_flow is True
    assert updated.include_pnl is False

    assert (
        updated.include_pending_count
        is False
    )

    assert (
        updated.include_payment_calendar
        is True
    )

    assert (
        telegram_settings
        .get_telegram_settings()
        == updated
    )


@pytest.mark.parametrize(
    (
        "period",
        "include_values",
        "message",
    ),
    [
        (
            "unknown",
            (
                True,
                True,
                True,
                True,
            ),
            "Unknown Telegram summary period",
        ),
        (
            "current_month",
            (
                False,
                False,
                False,
                False,
            ),
            "At least one summary section",
        ),
    ],
)
def test_update_settings_rejects_invalid_values(
    isolated_repository: sessionmaker,
    period: str,
    include_values: tuple[
        bool,
        bool,
        bool,
        bool,
    ],
    message: str,
) -> None:
    del isolated_repository

    with pytest.raises(
        ValueError,
        match=message,
    ):
        (
            telegram_settings
            .update_telegram_settings(
                is_enabled=True,
                default_summary_period=period,
                include_cash_flow=(
                    include_values[0]
                ),
                include_pnl=(
                    include_values[1]
                ),
                include_pending_count=(
                    include_values[2]
                ),
                include_payment_calendar=(
                    include_values[3]
                ),
            )
        )


def test_save_user_cleans_and_upserts(
    isolated_repository: sessionmaker,
) -> None:
    first_id = (
        telegram_settings.save_allowed_user(
            telegram_user_id=(
                " 123456789 "
            ),
            display_name="  Georgii  ",
            is_active=True,
        )
    )

    second_id = (
        telegram_settings.save_allowed_user(
            telegram_user_id=123456789,
            display_name="Updated name",
            is_active=False,
        )
    )

    assert second_id == first_id

    users = (
        telegram_settings
        .get_allowed_users_dataframe()
    )

    assert len(users) == 1

    assert (
        users.iloc[0][
            "telegram_user_id"
        ]
        == 123456789
    )

    assert (
        users.iloc[0]["display_name"]
        == "Updated name"
    )

    assert (
        bool(
            users.iloc[0]["is_active"]
        )
        is False
    )

    with isolated_repository() as session:
        count = session.scalar(
            select(
                func.count(
                    TelegramAllowedUser.id
                )
            )
        )

    assert count == 1


@pytest.mark.parametrize(
    "telegram_user_id",
    [
        0,
        -1,
        True,
        "not-an-id",
        2**63,
    ],
)
def test_save_user_rejects_invalid_id(
    isolated_repository: sessionmaker,
    telegram_user_id: object,
) -> None:
    del isolated_repository

    with pytest.raises(ValueError):
        telegram_settings.save_allowed_user(
            telegram_user_id=(
                telegram_user_id
            ),  # type: ignore[arg-type]
            display_name=None,
        )


def test_user_management(
    isolated_repository: sessionmaker,
) -> None:
    inactive_id = (
        telegram_settings.save_allowed_user(
            telegram_user_id=100,
            display_name="Inactive",
            is_active=False,
        )
    )

    active_id = (
        telegram_settings.save_allowed_user(
            telegram_user_id=200,
            display_name="Active",
            is_active=True,
        )
    )

    users = (
        telegram_settings
        .get_allowed_users_dataframe()
    )

    assert users["id"].tolist() == [
        active_id,
        inactive_id,
    ]

    telegram_settings.set_allowed_user_active(
        inactive_id,
        True,
    )

    telegram_settings.delete_allowed_user(
        active_id
    )

    remaining = (
        telegram_settings
        .get_allowed_users_dataframe()
    )

    assert remaining["id"].tolist() == [
        inactive_id,
    ]

    assert (
        bool(
            remaining.iloc[0]["is_active"]
        )
        is True
    )

    with pytest.raises(
        ValueError,
        match="was not found",
    ):
        telegram_settings.delete_allowed_user(
            active_id
        )


def test_save_chat_cleans_and_upserts(
    isolated_repository: sessionmaker,
) -> None:
    first_id = (
        telegram_settings.save_allowed_chat(
            telegram_chat_id=(
                " -1001234567890 "
            ),
            display_name="  Finance  ",
            chat_type="group",
            is_active=True,
        )
    )

    second_id = (
        telegram_settings.save_allowed_chat(
            telegram_chat_id=(
                -1001234567890
            ),
            display_name="Management",
            chat_type="supergroup",
            is_active=False,
        )
    )

    assert second_id == first_id

    chats = (
        telegram_settings
        .get_allowed_chats_dataframe()
    )

    assert len(chats) == 1

    assert (
        chats.iloc[0][
            "telegram_chat_id"
        ]
        == -1001234567890
    )

    assert (
        chats.iloc[0]["display_name"]
        == "Management"
    )

    assert (
        chats.iloc[0]["chat_type"]
        == "supergroup"
    )

    assert (
        bool(
            chats.iloc[0]["is_active"]
        )
        is False
    )

    with isolated_repository() as session:
        count = session.scalar(
            select(
                func.count(
                    TelegramAllowedChat.id
                )
            )
        )

    assert count == 1


@pytest.mark.parametrize(
    (
        "telegram_chat_id",
        "chat_type",
    ),
    [
        (
            0,
            "group",
        ),
        (
            123,
            "group",
        ),
        (
            True,
            "group",
        ),
        (
            "not-an-id",
            "group",
        ),
        (
            -(2**63) - 1,
            "group",
        ),
        (
            -100,
            "private",
        ),
    ],
)
def test_save_chat_rejects_invalid_values(
    isolated_repository: sessionmaker,
    telegram_chat_id: object,
    chat_type: str,
) -> None:
    del isolated_repository

    with pytest.raises(ValueError):
        telegram_settings.save_allowed_chat(
            telegram_chat_id=(
                telegram_chat_id
            ),  # type: ignore[arg-type]
            display_name=None,
            chat_type=chat_type,
        )


def test_chat_management(
    isolated_repository: sessionmaker,
) -> None:
    inactive_id = (
        telegram_settings.save_allowed_chat(
            telegram_chat_id=-100,
            display_name="Inactive",
            chat_type="group",
            is_active=False,
        )
    )

    active_id = (
        telegram_settings.save_allowed_chat(
            telegram_chat_id=-200,
            display_name="Active",
            chat_type="supergroup",
            is_active=True,
        )
    )

    chats = (
        telegram_settings
        .get_allowed_chats_dataframe()
    )

    assert chats["id"].tolist() == [
        active_id,
        inactive_id,
    ]

    telegram_settings.set_allowed_chat_active(
        inactive_id,
        True,
    )

    telegram_settings.delete_allowed_chat(
        active_id
    )

    remaining = (
        telegram_settings
        .get_allowed_chats_dataframe()
    )

    assert remaining["id"].tolist() == [
        inactive_id,
    ]

    assert (
        bool(
            remaining.iloc[0]["is_active"]
        )
        is True
    )

    with pytest.raises(
        ValueError,
        match="was not found",
    ):
        (
            telegram_settings
            .set_allowed_chat_active(
                active_id,
                False,
            )
        )


def test_private_access(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    user_id = 123456789

    telegram_settings.save_allowed_user(
        telegram_user_id=user_id,
        display_name="Owner",
        is_active=True,
    )

    assert (
        telegram_settings
        .is_telegram_request_allowed(
            telegram_user_id=user_id,
            telegram_chat_id=user_id,
            chat_type="private",
        )
        is True
    )

    assert (
        telegram_settings
        .is_telegram_request_allowed(
            telegram_user_id=user_id,
            telegram_chat_id=(
                user_id + 1
            ),
            chat_type="private",
        )
        is False
    )

    telegram_settings.save_allowed_user(
        telegram_user_id=user_id,
        display_name="Owner",
        is_active=False,
    )

    assert (
        telegram_settings
        .is_telegram_request_allowed(
            telegram_user_id=user_id,
            telegram_chat_id=user_id,
            chat_type="private",
        )
        is False
    )


def test_group_access(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    user_id = 123456789
    chat_id = -1001234567890

    telegram_settings.save_allowed_user(
        telegram_user_id=user_id,
        display_name="Owner",
        is_active=True,
    )

    chat_record_id = (
        telegram_settings.save_allowed_chat(
            telegram_chat_id=chat_id,
            display_name="Management",
            chat_type="supergroup",
            is_active=True,
        )
    )

    assert (
        telegram_settings
        .is_telegram_request_allowed(
            telegram_user_id=user_id,
            telegram_chat_id=chat_id,
            chat_type="supergroup",
        )
        is True
    )

    assert (
        telegram_settings
        .is_telegram_request_allowed(
            telegram_user_id=user_id,
            telegram_chat_id=chat_id,
            chat_type="group",
        )
        is False
    )

    assert (
        telegram_settings
        .is_telegram_request_allowed(
            telegram_user_id=(
                user_id + 1
            ),
            telegram_chat_id=chat_id,
            chat_type="supergroup",
        )
        is False
    )

    telegram_settings.set_allowed_chat_active(
        chat_record_id,
        False,
    )

    assert (
        telegram_settings
        .is_telegram_request_allowed(
            telegram_user_id=user_id,
            telegram_chat_id=chat_id,
            chat_type="supergroup",
        )
        is False
    )
