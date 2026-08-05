from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models import (
    TelegramAllowedChat,
    TelegramAllowedUser,
    TelegramBotSettings,
)


SUMMARY_PERIODS = (
    "current_month",
    "previous_month",
    "last_30_days",
    "current_quarter",
    "current_year",
)

TELEGRAM_CHAT_TYPES = (
    "group",
    "supergroup",
)

SIGNED_BIGINT_MIN = -(2**63)
SIGNED_BIGINT_MAX = 2**63 - 1


@dataclass(frozen=True)
class TelegramSettings:
    """Read-only Telegram bot settings snapshot."""

    is_enabled: bool
    default_summary_period: str
    include_cash_flow: bool
    include_pnl: bool
    include_pending_count: bool
    include_payment_calendar: bool


def _optional_text(
    value: Any,
    *,
    max_length: int = 255,
) -> str | None:
    """Returns cleaned optional text."""

    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    if len(text) > max_length:
        raise ValueError(
            f"Text must not exceed "
            f"{max_length} characters."
        )

    return text


def _telegram_id(
    value: int | str,
    *,
    field_name: str,
    require_positive: bool,
) -> int:
    """Validates a signed 64-bit Telegram ID."""

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be an integer."
        )

    try:
        normalized = int(
            str(value).strip()
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"{field_name} must be an integer."
        ) from exc

    if not (
        SIGNED_BIGINT_MIN
        <= normalized
        <= SIGNED_BIGINT_MAX
    ):
        raise ValueError(
            f"{field_name} is outside the "
            "signed 64-bit range."
        )

    if (
        require_positive
        and normalized <= 0
    ):
        raise ValueError(
            f"{field_name} must be positive."
        )

    if (
        not require_positive
        and normalized >= 0
    ):
        raise ValueError(
            f"{field_name} must be negative "
            "for a group chat."
        )

    return normalized


def _record_id(
    value: int | str,
) -> int:
    """Validates a local database record ID."""

    if isinstance(value, bool):
        raise ValueError(
            "Record ID must be positive."
        )

    try:
        normalized = int(
            str(value).strip()
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Record ID must be positive."
        ) from exc

    if normalized <= 0:
        raise ValueError(
            "Record ID must be positive."
        )

    return normalized


def _settings_snapshot(
    settings: TelegramBotSettings,
) -> TelegramSettings:
    """Converts an ORM model to a snapshot."""

    return TelegramSettings(
        is_enabled=bool(
            settings.is_enabled
        ),
        default_summary_period=str(
            settings.default_summary_period
        ),
        include_cash_flow=bool(
            settings.include_cash_flow
        ),
        include_pnl=bool(
            settings.include_pnl
        ),
        include_pending_count=bool(
            settings.include_pending_count
        ),
        include_payment_calendar=bool(
            settings.include_payment_calendar
        ),
    )


def _get_or_create_settings(
    session: Session,
) -> tuple[
    TelegramBotSettings,
    bool,
]:
    """Returns or creates the singleton row."""

    settings = session.get(
        TelegramBotSettings,
        1,
    )

    if settings is not None:
        return settings, False

    settings = TelegramBotSettings(
        id=1,
    )

    session.add(
        settings
    )

    session.flush()

    return settings, True


def get_telegram_settings() -> TelegramSettings:
    """Returns current Telegram settings."""

    with SessionLocal() as session:
        settings, created = (
            _get_or_create_settings(
                session
            )
        )

        if created:
            session.commit()

        return _settings_snapshot(
            settings
        )


def update_telegram_settings(
    *,
    is_enabled: bool,
    default_summary_period: str,
    include_cash_flow: bool,
    include_pnl: bool,
    include_pending_count: bool,
    include_payment_calendar: bool,
) -> TelegramSettings:
    """Validates and stores bot settings."""

    if (
        default_summary_period
        not in SUMMARY_PERIODS
    ):
        raise ValueError(
            "Unknown Telegram summary period."
        )

    include_values = (
        bool(include_cash_flow),
        bool(include_pnl),
        bool(include_pending_count),
        bool(include_payment_calendar),
    )

    if not any(include_values):
        raise ValueError(
            "At least one summary section "
            "must be enabled."
        )

    with SessionLocal() as session:
        settings, _ = (
            _get_or_create_settings(
                session
            )
        )

        settings.is_enabled = bool(
            is_enabled
        )

        settings.default_summary_period = (
            default_summary_period
        )

        settings.include_cash_flow = (
            include_values[0]
        )

        settings.include_pnl = (
            include_values[1]
        )

        settings.include_pending_count = (
            include_values[2]
        )

        settings.include_payment_calendar = (
            include_values[3]
        )

        session.commit()

        return _settings_snapshot(
            settings
        )


def save_allowed_user(
    *,
    telegram_user_id: int | str,
    display_name: str | None,
    is_active: bool = True,
) -> int:
    """Creates or updates an allowed user."""

    normalized_user_id = _telegram_id(
        telegram_user_id,
        field_name="Telegram user ID",
        require_positive=True,
    )

    clean_display_name = _optional_text(
        display_name
    )

    with SessionLocal() as session:
        user = session.scalar(
            select(
                TelegramAllowedUser
            ).where(
                (
                    TelegramAllowedUser
                    .telegram_user_id
                )
                == normalized_user_id
            )
        )

        if user is None:
            user = TelegramAllowedUser(
                telegram_user_id=(
                    normalized_user_id
                ),
            )

            session.add(
                user
            )

        user.display_name = (
            clean_display_name
        )

        user.is_active = bool(
            is_active
        )

        session.commit()
        session.refresh(
            user
        )

        return int(
            user.id
        )


def get_allowed_users_dataframe() -> pd.DataFrame:
    """Returns allowed users for the UI."""

    columns = [
        "id",
        "telegram_user_id",
        "display_name",
        "is_active",
    ]

    statement = (
        select(
            TelegramAllowedUser
        )
        .order_by(
            (
                TelegramAllowedUser
                .is_active
                .desc()
            ),
            TelegramAllowedUser.id.asc(),
        )
    )

    with SessionLocal() as session:
        users = session.scalars(
            statement
        ).all()

    rows = [
        {
            "id": user.id,
            "telegram_user_id": (
                user.telegram_user_id
            ),
            "display_name": (
                user.display_name
            ),
            "is_active": bool(
                user.is_active
            ),
        }
        for user in users
    ]

    return pd.DataFrame(
        rows,
        columns=columns,
    )


def set_allowed_user_active(
    record_id: int | str,
    is_active: bool,
) -> None:
    """Enables or disables an allowed user."""

    normalized_record_id = _record_id(
        record_id
    )

    with SessionLocal() as session:
        user = session.get(
            TelegramAllowedUser,
            normalized_record_id,
        )

        if user is None:
            raise ValueError(
                "Allowed Telegram user "
                "was not found."
            )

        user.is_active = bool(
            is_active
        )

        session.commit()


def delete_allowed_user(
    record_id: int | str,
) -> None:
    """Deletes an allowed Telegram user."""

    normalized_record_id = _record_id(
        record_id
    )

    with SessionLocal() as session:
        user = session.get(
            TelegramAllowedUser,
            normalized_record_id,
        )

        if user is None:
            raise ValueError(
                "Allowed Telegram user "
                "was not found."
            )

        session.delete(
            user
        )

        session.commit()


def save_allowed_chat(
    *,
    telegram_chat_id: int | str,
    display_name: str | None,
    chat_type: str,
    is_active: bool = True,
) -> int:
    """Creates or updates an allowed chat."""

    normalized_chat_id = _telegram_id(
        telegram_chat_id,
        field_name="Telegram chat ID",
        require_positive=False,
    )

    if chat_type not in TELEGRAM_CHAT_TYPES:
        raise ValueError(
            "Unknown Telegram chat type."
        )

    clean_display_name = _optional_text(
        display_name
    )

    with SessionLocal() as session:
        chat = session.scalar(
            select(
                TelegramAllowedChat
            ).where(
                (
                    TelegramAllowedChat
                    .telegram_chat_id
                )
                == normalized_chat_id
            )
        )

        if chat is None:
            chat = TelegramAllowedChat(
                telegram_chat_id=(
                    normalized_chat_id
                ),
            )

            session.add(
                chat
            )

        chat.display_name = (
            clean_display_name
        )

        chat.chat_type = chat_type

        chat.is_active = bool(
            is_active
        )

        session.commit()
        session.refresh(
            chat
        )

        return int(
            chat.id
        )


def get_allowed_chats_dataframe() -> pd.DataFrame:
    """Returns allowed chats for the UI."""

    columns = [
        "id",
        "telegram_chat_id",
        "display_name",
        "chat_type",
        "is_active",
    ]

    statement = (
        select(
            TelegramAllowedChat
        )
        .order_by(
            (
                TelegramAllowedChat
                .is_active
                .desc()
            ),
            TelegramAllowedChat.id.asc(),
        )
    )

    with SessionLocal() as session:
        chats = session.scalars(
            statement
        ).all()

    rows = [
        {
            "id": chat.id,
            "telegram_chat_id": (
                chat.telegram_chat_id
            ),
            "display_name": (
                chat.display_name
            ),
            "chat_type": chat.chat_type,
            "is_active": bool(
                chat.is_active
            ),
        }
        for chat in chats
    ]

    return pd.DataFrame(
        rows,
        columns=columns,
    )


def set_allowed_chat_active(
    record_id: int | str,
    is_active: bool,
) -> None:
    """Enables or disables an allowed chat."""

    normalized_record_id = _record_id(
        record_id
    )

    with SessionLocal() as session:
        chat = session.get(
            TelegramAllowedChat,
            normalized_record_id,
        )

        if chat is None:
            raise ValueError(
                "Allowed Telegram chat "
                "was not found."
            )

        chat.is_active = bool(
            is_active
        )

        session.commit()


def delete_allowed_chat(
    record_id: int | str,
) -> None:
    """Deletes an allowed Telegram chat."""

    normalized_record_id = _record_id(
        record_id
    )

    with SessionLocal() as session:
        chat = session.get(
            TelegramAllowedChat,
            normalized_record_id,
        )

        if chat is None:
            raise ValueError(
                "Allowed Telegram chat "
                "was not found."
            )

        session.delete(
            chat
        )

        session.commit()


def is_telegram_request_allowed(
    *,
    telegram_user_id: int | str,
    telegram_chat_id: int | str,
    chat_type: str,
) -> bool:
    """Checks private or group access."""

    try:
        normalized_user_id = _telegram_id(
            telegram_user_id,
            field_name="Telegram user ID",
            require_positive=True,
        )
    except ValueError:
        return False

    if chat_type == "private":
        try:
            normalized_chat_id = (
                _telegram_id(
                    telegram_chat_id,
                    field_name=(
                        "Telegram chat ID"
                    ),
                    require_positive=True,
                )
            )
        except ValueError:
            return False

        if (
            normalized_chat_id
            != normalized_user_id
        ):
            return False

        with SessionLocal() as session:
            user_exists = session.scalar(
                select(
                    TelegramAllowedUser.id
                ).where(
                    (
                        TelegramAllowedUser
                        .telegram_user_id
                    )
                    == normalized_user_id,
                    (
                        TelegramAllowedUser
                        .is_active
                        .is_(True)
                    ),
                )
            )

        return user_exists is not None

    if chat_type not in TELEGRAM_CHAT_TYPES:
        return False

    try:
        normalized_chat_id = _telegram_id(
            telegram_chat_id,
            field_name="Telegram chat ID",
            require_positive=False,
        )
    except ValueError:
        return False

    with SessionLocal() as session:
        user_exists = session.scalar(
            select(
                TelegramAllowedUser.id
            ).where(
                (
                    TelegramAllowedUser
                    .telegram_user_id
                )
                == normalized_user_id,
                (
                    TelegramAllowedUser
                    .is_active
                    .is_(True)
                ),
            )
        )

        if user_exists is None:
            return False

        chat_exists = session.scalar(
            select(
                TelegramAllowedChat.id
            ).where(
                (
                    TelegramAllowedChat
                    .telegram_chat_id
                )
                == normalized_chat_id,
                (
                    TelegramAllowedChat
                    .chat_type
                )
                == chat_type,
                (
                    TelegramAllowedChat
                    .is_active
                    .is_(True)
                ),
            )
        )

    return chat_exists is not None
