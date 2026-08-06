from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.parse import quote
from urllib.request import (
    Request,
    urlopen,
)

from dotenv import dotenv_values


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

ENV_PATH = PROJECT_ROOT / ".env"

TOKEN_ENV_NAME = "TELEGRAM_BOT_TOKEN"

TOKEN_ASSIGNMENT_PATTERN = re.compile(
    rf"^\s*(?:export\s+)?"
    rf"{re.escape(TOKEN_ENV_NAME)}\s*="
)


class TelegramTokenError(RuntimeError):
    """Raised when Telegram token handling fails."""


@dataclass(frozen=True)
class TelegramBotIdentity:
    """Public information returned by Telegram getMe."""

    bot_id: int
    username: str
    display_name: str
    can_join_groups: bool
    can_read_all_group_messages: bool


def _resolve_env_path(
    env_path: Path | None,
) -> Path:
    """Returns the active dotenv file path."""

    if env_path is None:
        env_path = ENV_PATH

    return Path(env_path).resolve()


def _normalize_token(
    token: str,
) -> str:
    """Validates basic token input properties."""

    normalized = str(token).strip()

    if not normalized:
        raise TelegramTokenError(
            "Telegram bot token is empty."
        )

    if any(
        character.isspace()
        for character in normalized
    ):
        raise TelegramTokenError(
            "Telegram bot token must not "
            "contain whitespace."
        )

    if ":" not in normalized:
        raise TelegramTokenError(
            "Telegram bot token has an "
            "invalid format."
        )

    return normalized


def _identity_from_payload(
    payload: Any,
) -> TelegramBotIdentity:
    """Builds a bot identity from getMe JSON."""

    if not isinstance(payload, dict):
        raise TelegramTokenError(
            "Telegram returned an invalid response."
        )

    if payload.get("ok") is not True:
        raise TelegramTokenError(
            "Telegram rejected the bot token."
        )

    result = payload.get("result")

    if not isinstance(result, dict):
        raise TelegramTokenError(
            "Telegram returned an invalid bot record."
        )

    if result.get("is_bot") is not True:
        raise TelegramTokenError(
            "The Telegram account is not a bot."
        )

    try:
        bot_id = int(
            result["id"]
        )
    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise TelegramTokenError(
            "Telegram did not return a valid bot ID."
        ) from exc

    first_name = str(
        result.get("first_name")
        or ""
    ).strip()

    last_name = str(
        result.get("last_name")
        or ""
    ).strip()

    display_name = " ".join(
        part
        for part in (
            first_name,
            last_name,
        )
        if part
    )

    username = str(
        result.get("username")
        or ""
    ).strip()

    return TelegramBotIdentity(
        bot_id=bot_id,
        username=username,
        display_name=display_name,
        can_join_groups=bool(
            result.get(
                "can_join_groups",
                False,
            )
        ),
        can_read_all_group_messages=bool(
            result.get(
                "can_read_all_group_messages",
                False,
            )
        ),
    )


def _request_bot_identity(
    token: str,
    *,
    timeout: float,
) -> TelegramBotIdentity:
    """Calls Telegram getMe without exposing token."""

    if timeout <= 0:
        raise ValueError(
            "Timeout must be positive."
        )

    encoded_token = quote(
        token,
        safe=":_-",
    )

    request = Request(
        (
            "https://api.telegram.org/"
            f"bot{encoded_token}/getMe"
        ),
        data=b"",
        headers={
            "User-Agent": (
                "Holotes/0.1"
            ),
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            response_bytes = (
                response.read()
            )

    except HTTPError as exc:
        if exc.code in {
            401,
            404,
        }:
            raise TelegramTokenError(
                "Telegram rejected the bot token."
            ) from None

        raise TelegramTokenError(
            "Telegram API returned an error."
        ) from None

    except (
        URLError,
        TimeoutError,
        OSError,
    ):
        raise TelegramTokenError(
            "Could not connect to Telegram API."
        ) from None

    try:
        payload = json.loads(
            response_bytes.decode(
                "utf-8"
            )
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise TelegramTokenError(
            "Telegram returned an invalid response."
        ) from None

    return _identity_from_payload(
        payload
    )


def validate_telegram_bot_token(
    token: str,
    *,
    timeout: float = 10,
) -> TelegramBotIdentity:
    """Validates a token through Telegram getMe."""

    normalized = _normalize_token(
        token
    )

    return _request_bot_identity(
        normalized,
        timeout=timeout,
    )


def _read_token_from_file(
    env_path: Path,
) -> str | None:
    """Reads the token from a dotenv file."""

    if not env_path.is_file():
        return None

    try:
        values = dotenv_values(
            env_path
        )
    except (
        OSError,
        UnicodeError,
    ) as exc:
        raise TelegramTokenError(
            "Could not read the .env file."
        ) from exc

    value = values.get(
        TOKEN_ENV_NAME
    )

    if value is None:
        return None

    normalized = str(value).strip()

    return normalized or None


def load_telegram_bot_token(
    *,
    env_path: Path | None = None,
) -> str:
    """Loads the configured token for bot runtime."""

    resolved_path = _resolve_env_path(
        env_path
    )

    process_value = os.environ.get(
        TOKEN_ENV_NAME,
        "",
    ).strip()

    if process_value:
        return process_value

    file_value = _read_token_from_file(
        resolved_path
    )

    if file_value:
        return file_value

    raise TelegramTokenError(
        "Telegram bot token is not configured."
    )


def is_telegram_bot_token_configured(
    *,
    env_path: Path | None = None,
) -> bool:
    """Checks token presence without returning it."""

    try:
        load_telegram_bot_token(
            env_path=env_path
        )
    except TelegramTokenError:
        return False

    return True


def _build_updated_env_text(
    original_text: str,
    *,
    token: str | None,
) -> str:
    """Replaces or removes the token assignment."""

    retained_lines = [
        line
        for line
        in original_text.splitlines()
        if not TOKEN_ASSIGNMENT_PATTERN.match(
            line
        )
    ]

    while (
        retained_lines
        and not retained_lines[-1].strip()
    ):
        retained_lines.pop()

    if token is not None:
        if retained_lines:
            retained_lines.append(
                ""
            )

        retained_lines.append(
            f"{TOKEN_ENV_NAME}={token}"
        )

    if not retained_lines:
        return ""

    return (
        "\n".join(
            retained_lines
        )
        + "\n"
    )


def _write_env_atomically(
    env_path: Path,
    content: str,
) -> None:
    """Writes dotenv content through a temp file."""

    env_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=(
                f".{env_path.name}."
            ),
            suffix=".tmp",
            dir=env_path.parent,
            text=True,
        )
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            file_descriptor,
            mode="w",
            encoding="utf-8",
            newline="\n",
        ) as temporary_file:
            temporary_file.write(
                content
            )

            temporary_file.flush()

            os.fsync(
                temporary_file.fileno()
            )

        os.replace(
            temporary_path,
            env_path,
        )

    except OSError as exc:
        raise TelegramTokenError(
            "Could not update the .env file."
        ) from exc

    finally:
        temporary_path.unlink(
            missing_ok=True
        )


def _update_env_token(
    *,
    env_path: Path,
    token: str | None,
) -> None:
    """Updates only TELEGRAM_BOT_TOKEN."""

    if env_path.exists():
        try:
            original_text = (
                env_path.read_text(
                    encoding="utf-8-sig"
                )
            )
        except (
            OSError,
            UnicodeError,
        ) as exc:
            raise TelegramTokenError(
                "Could not read the .env file."
            ) from exc
    else:
        original_text = ""

    updated_text = (
        _build_updated_env_text(
            original_text,
            token=token,
        )
    )

    _write_env_atomically(
        env_path,
        updated_text,
    )


def save_telegram_bot_token(
    token: str,
    *,
    env_path: Path | None = None,
    timeout: float = 10,
) -> TelegramBotIdentity:
    """Validates and saves a Telegram bot token."""

    resolved_path = _resolve_env_path(
        env_path
    )

    normalized = _normalize_token(
        token
    )

    identity = _request_bot_identity(
        normalized,
        timeout=timeout,
    )

    _update_env_token(
        env_path=resolved_path,
        token=normalized,
    )

    os.environ[
        TOKEN_ENV_NAME
    ] = normalized

    return identity


def delete_telegram_bot_token(
    *,
    env_path: Path | None = None,
) -> bool:
    """Removes the token from dotenv and process."""

    resolved_path = _resolve_env_path(
        env_path
    )

    was_configured = (
        is_telegram_bot_token_configured(
            env_path=resolved_path
        )
    )

    _update_env_token(
        env_path=resolved_path,
        token=None,
    )

    os.environ.pop(
        TOKEN_ENV_NAME,
        None,
    )

    return was_configured


def get_configured_bot_identity(
    *,
    env_path: Path | None = None,
    timeout: float = 10,
) -> TelegramBotIdentity:
    """Checks the currently configured bot."""

    token = load_telegram_bot_token(
        env_path=env_path
    )

    return validate_telegram_bot_token(
        token,
        timeout=timeout,
    )
