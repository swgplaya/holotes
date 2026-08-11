from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import tempfile

from dotenv import dotenv_values

from src.telegram_mtproto import (
    TelegramMtprotoConfigError,
    parse_mtproxy_url,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

ENV_PATH = PROJECT_ROOT / ".env"

TRANSPORT_ENV_NAME = "TELEGRAM_TRANSPORT"
API_ID_ENV_NAME = "TELEGRAM_API_ID"
API_HASH_ENV_NAME = "TELEGRAM_API_HASH"
MTPROXY_ENV_NAME = "TELEGRAM_MTPROXY_URL"

SUPPORTED_TRANSPORTS = (
    "bot_api",
    "mtproto",
)

MANAGED_ENV_NAMES = (
    TRANSPORT_ENV_NAME,
    API_ID_ENV_NAME,
    API_HASH_ENV_NAME,
    MTPROXY_ENV_NAME,
)


class TelegramTransportConfigError(
    TelegramMtprotoConfigError
):
    """Raised when Telegram transport configuration is invalid."""


@dataclass(frozen=True)
class TelegramTransportConfig:
    """Non-secret Telegram transport configuration snapshot."""

    transport: str
    api_id: str
    api_hash_configured: bool
    mtproxy_configured: bool


def _resolve_env_path(
    env_path: Path | None,
) -> Path:
    if env_path is None:
        env_path = ENV_PATH

    return Path(
        env_path
    ).resolve()


def _load_values(
    env_path: Path,
) -> dict[str, str]:
    values: dict[str, str] = {}

    if env_path.exists():
        try:
            parsed = dotenv_values(
                env_path
            )
        except (
            OSError,
            UnicodeError,
        ) as exc:
            raise TelegramTransportConfigError(
                "Could not read the .env file."
            ) from exc

        for key, value in parsed.items():
            if value is not None:
                values[str(key)] = str(value)

    for key in MANAGED_ENV_NAMES:
        process_value = os.environ.get(
            key
        )

        if process_value is not None:
            values[key] = process_value

    return values


def _normalize_transport(
    value: str,
) -> str:
    normalized = str(
        value
    ).strip().lower()

    if normalized not in SUPPORTED_TRANSPORTS:
        raise TelegramTransportConfigError(
            "Telegram transport must be "
            "'bot_api' or 'mtproto'."
        )

    return normalized


def _normalize_api_id(
    value: str,
) -> str:
    normalized = str(
        value
    ).strip()

    if not normalized:
        raise TelegramTransportConfigError(
            "Telegram API ID is required "
            "for MTProto transport."
        )

    try:
        parsed = int(
            normalized
        )
    except ValueError as exc:
        raise TelegramTransportConfigError(
            "Telegram API ID must be "
            "a positive integer."
        ) from exc

    if parsed <= 0:
        raise TelegramTransportConfigError(
            "Telegram API ID must be "
            "a positive integer."
        )

    return str(
        parsed
    )


def _normalize_api_hash(
    value: str,
) -> str:
    normalized = str(
        value
    ).strip()

    if not normalized:
        raise TelegramTransportConfigError(
            "Telegram API hash is required "
            "for MTProto transport."
        )

    if any(
        character.isspace()
        for character in normalized
    ):
        raise TelegramTransportConfigError(
            "Telegram API hash must not "
            "contain whitespace."
        )

    return normalized


def _normalize_mtproxy_url(
    value: str,
) -> str:
    normalized = str(
        value
    ).strip()

    if not normalized:
        raise TelegramTransportConfigError(
            "Telegram MTProxy link is required "
            "for MTProto transport."
        )

    parse_mtproxy_url(
        normalized
    )

    return normalized


def get_telegram_transport_config(
    *,
    env_path: Path | None = None,
) -> TelegramTransportConfig:
    resolved_path = _resolve_env_path(
        env_path
    )

    values = _load_values(
        resolved_path
    )

    transport = _normalize_transport(
        values.get(
            TRANSPORT_ENV_NAME,
            "bot_api",
        )
    )

    api_id = str(
        values.get(
            API_ID_ENV_NAME,
            "",
        )
    ).strip()

    return TelegramTransportConfig(
        transport=transport,
        api_id=api_id,
        api_hash_configured=bool(
            str(
                values.get(
                    API_HASH_ENV_NAME,
                    "",
                )
            ).strip()
        ),
        mtproxy_configured=bool(
            str(
                values.get(
                    MTPROXY_ENV_NAME,
                    "",
                )
            ).strip()
        ),
    )


def _assignment_pattern(
    name: str,
) -> re.Pattern[str]:
    return re.compile(
        rf"^\s*(?:export\s+)?"
        rf"{re.escape(name)}\s*="
    )


def _build_updated_env_text(
    original_text: str,
    values: dict[str, str],
) -> str:
    managed_patterns = tuple(
        _assignment_pattern(
            name
        )
        for name in values
    )

    retained_lines = [
        line
        for line in original_text.splitlines()
        if not any(
            pattern.match(
                line
            )
            for pattern in managed_patterns
        )
    ]

    while (
        retained_lines
        and not retained_lines[-1].strip()
    ):
        retained_lines.pop()

    if retained_lines:
        retained_lines.append(
            ""
        )

    for name, value in values.items():
        retained_lines.append(
            f"{name}={value}"
        )

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
    """Writes dotenv content safely, including Docker bind mounts."""

    env_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{env_path.name}.",
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

        try:
            os.replace(
                temporary_path,
                env_path,
            )
            return

        except OSError as replace_error:
            if not env_path.exists():
                raise TelegramTransportConfigError(
                    "Could not update the .env file."
                ) from replace_error

        try:
            with env_path.open(
                mode="w",
                encoding="utf-8",
                newline="\n",
            ) as env_file:
                env_file.write(
                    content
                )
                env_file.flush()
                os.fsync(
                    env_file.fileno()
                )

        except OSError as write_error:
            raise TelegramTransportConfigError(
                "Could not update the .env file."
            ) from write_error

    finally:
        temporary_path.unlink(
            missing_ok=True
        )


def save_telegram_transport_config(
    *,
    transport: str,
    api_id: str = "",
    api_hash: str = "",
    mtproxy_url: str = "",
    env_path: Path | None = None,
) -> TelegramTransportConfig:
    """
    Saves Telegram transport configuration.

    Secret fields may be left blank when a saved value already
    exists. This allows the UI to avoid displaying secrets.
    """

    resolved_path = _resolve_env_path(
        env_path
    )

    normalized_transport = (
        _normalize_transport(
            transport
        )
    )

    existing = _load_values(
        resolved_path
    )

    updated_values: dict[str, str] = {
        TRANSPORT_ENV_NAME: (
            normalized_transport
        ),
    }

    if normalized_transport == "mtproto":
        normalized_api_id = (
            _normalize_api_id(
                api_id
                or existing.get(
                    API_ID_ENV_NAME,
                    "",
                )
            )
        )

        normalized_api_hash = (
            _normalize_api_hash(
                api_hash
                or existing.get(
                    API_HASH_ENV_NAME,
                    "",
                )
            )
        )

        normalized_proxy = (
            _normalize_mtproxy_url(
                mtproxy_url
                or existing.get(
                    MTPROXY_ENV_NAME,
                    "",
                )
            )
        )

        updated_values.update(
            {
                API_ID_ENV_NAME: (
                    normalized_api_id
                ),
                API_HASH_ENV_NAME: (
                    normalized_api_hash
                ),
                MTPROXY_ENV_NAME: (
                    normalized_proxy
                ),
            }
        )

    if resolved_path.exists():
        try:
            original_text = (
                resolved_path.read_text(
                    encoding="utf-8-sig"
                )
            )
        except (
            OSError,
            UnicodeError,
        ) as exc:
            raise TelegramTransportConfigError(
                "Could not read the .env file."
            ) from exc
    else:
        original_text = ""

    updated_text = (
        _build_updated_env_text(
            original_text,
            updated_values,
        )
    )

    _write_env_atomically(
        resolved_path,
        updated_text,
    )

    for name, value in updated_values.items():
        os.environ[
            name
        ] = value

    return get_telegram_transport_config(
        env_path=resolved_path
    )
