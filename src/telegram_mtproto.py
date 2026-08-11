from __future__ import annotations

from dataclasses import dataclass
import asyncio
import logging
import os
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dotenv import dotenv_values
from telethon import TelegramClient, connection, events
from telethon.tl.types import (
    Channel,
    Chat,
    User,
)


LOGGER = logging.getLogger(
    "holotes.telegram_mtproto"
)


class TelegramMtprotoConfigError(ValueError):
    """Raised when Telegram MTProto configuration is invalid."""


class TelegramMtProxyConfigError(
    TelegramMtprotoConfigError
):
    """Raised when an MTProxy deep link is invalid."""


@dataclass(frozen=True)
class TelegramMtProxyConfig:
    """Validated Telegram MTProxy connection settings."""

    host: str
    port: int
    secret: str


def _single_query_value(
    query: dict[str, list[str]],
    name: str,
) -> str:
    values = query.get(name)

    if not values or len(values) != 1:
        raise TelegramMtProxyConfigError(
            f"MTProxy link must contain exactly one "
            f"'{name}' parameter."
        )

    value = values[0].strip()

    if not value:
        raise TelegramMtProxyConfigError(
            f"MTProxy parameter '{name}' must not be empty."
        )

    return value


def parse_mtproxy_url(
    value: str,
) -> TelegramMtProxyConfig:
    """
    Parse an official Telegram MTProxy deep link.

    Supported forms:

    tg://proxy?server=host&port=443&secret=...
    https://t.me/proxy?server=host&port=443&secret=...
    """

    raw = value.strip()

    if not raw:
        raise TelegramMtProxyConfigError(
            "MTProxy link must not be empty."
        )

    parsed = urlparse(raw)

    is_tg_link = (
        parsed.scheme.lower() == "tg"
        and parsed.netloc.lower() == "proxy"
    )

    is_tme_link = (
        parsed.scheme.lower() in {"http", "https"}
        and parsed.netloc.lower() in {
            "t.me",
            "telegram.me",
            "telegram.dog",
        }
        and parsed.path.rstrip("/").lower() == "/proxy"
    )

    if not (is_tg_link or is_tme_link):
        raise TelegramMtProxyConfigError(
            "Unsupported proxy link. Use a Telegram "
            "MTProxy link starting with tg://proxy or "
            "https://t.me/proxy."
        )

    query = parse_qs(
        parsed.query,
        keep_blank_values=True,
        strict_parsing=False,
    )

    host = _single_query_value(
        query,
        "server",
    )

    port_raw = _single_query_value(
        query,
        "port",
    )

    secret = _single_query_value(
        query,
        "secret",
    )

    try:
        port = int(port_raw)
    except ValueError as exc:
        raise TelegramMtProxyConfigError(
            "MTProxy port must be an integer."
        ) from exc

    if not 1 <= port <= 65535:
        raise TelegramMtProxyConfigError(
            "MTProxy port must be between 1 and 65535."
        )

    if any(
        character.isspace()
        for character in host
    ):
        raise TelegramMtProxyConfigError(
            "MTProxy server must not contain whitespace."
        )

    return TelegramMtProxyConfig(
        host=host,
        port=port,
        secret=secret,
    )


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"
DEFAULT_SESSION_PATH = (
    PROJECT_ROOT / "data" / "telegram_mtproto"
)

SUPPORTED_TELEGRAM_TRANSPORTS = {
    "bot_api",
    "mtproto",
}


class TelegramMtprotoConnectionError(RuntimeError):
    """Raised when an MTProto bot connection fails."""


@dataclass(frozen=True)
class TelegramMtprotoSettings:
    """Configuration required by a Telethon bot client."""

    api_id: int
    api_hash: str
    proxy: TelegramMtProxyConfig | None
    session_path: Path


@dataclass(frozen=True)
class TelegramMtprotoBotIdentity:
    """Minimal identity returned by an MTProto bot probe."""

    telegram_user_id: int
    username: str


def _load_environment_values(
    env_path: Path = DEFAULT_ENV_PATH,
) -> dict[str, str]:
    values: dict[str, str] = {}

    if env_path.exists():
        for key, value in dotenv_values(
            env_path
        ).items():
            if value is not None:
                values[key] = value

    for key, value in os.environ.items():
        values[key] = value

    return values


def get_telegram_transport(
    *,
    env_path: Path = DEFAULT_ENV_PATH,
) -> str:
    values = _load_environment_values(
        env_path
    )

    transport = (
        values.get(
            "TELEGRAM_TRANSPORT",
            "bot_api",
        )
        .strip()
        .lower()
    )

    if transport not in SUPPORTED_TELEGRAM_TRANSPORTS:
        raise TelegramMtProxyConfigError(
            "TELEGRAM_TRANSPORT must be "
            "'bot_api' or 'mtproto'."
        )

    return transport


def load_mtproto_settings(
    *,
    env_path: Path = DEFAULT_ENV_PATH,
    session_path: Path = DEFAULT_SESSION_PATH,
) -> TelegramMtprotoSettings:
    values = _load_environment_values(
        env_path
    )

    api_id_raw = (
        values.get(
            "TELEGRAM_API_ID",
            "",
        )
        .strip()
    )

    api_hash = (
        values.get(
            "TELEGRAM_API_HASH",
            "",
        )
        .strip()
    )

    proxy_url = (
        values.get(
            "TELEGRAM_MTPROXY_URL",
            "",
        )
        .strip()
    )

    if not api_id_raw:
        raise TelegramMtProxyConfigError(
            "TELEGRAM_API_ID is required "
            "for MTProto transport."
        )

    try:
        api_id = int(
            api_id_raw
        )
    except ValueError as exc:
        raise TelegramMtProxyConfigError(
            "TELEGRAM_API_ID must be "
            "a positive integer."
        ) from exc

    if api_id <= 0:
        raise TelegramMtProxyConfigError(
            "TELEGRAM_API_ID must be "
            "a positive integer."
        )

    if not api_hash:
        raise TelegramMtProxyConfigError(
            "TELEGRAM_API_HASH is required "
            "for MTProto transport."
        )

    proxy = (
        parse_mtproxy_url(
            proxy_url
        )
        if proxy_url
        else None
    )

    return TelegramMtprotoSettings(
        api_id=api_id,
        api_hash=api_hash,
        proxy=proxy,
        session_path=session_path,
    )


def build_mtproto_client(
    settings: TelegramMtprotoSettings,
) -> TelegramClient:
    settings.session_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    kwargs = {}

    if settings.proxy is not None:
        kwargs.update(
            {
                "connection": (
                    connection
                    .ConnectionTcpMTProxyRandomizedIntermediate
                ),
                "proxy": (
                    settings.proxy.host,
                    settings.proxy.port,
                    settings.proxy.secret,
                ),
            }
        )

    return TelegramClient(
        settings.session_path,
        settings.api_id,
        settings.api_hash,
        **kwargs,
    )


async def probe_mtproto_bot(
    bot_token: str,
    settings: TelegramMtprotoSettings,
) -> TelegramMtprotoBotIdentity:
    """
    Validates MTProto connectivity and bot authentication.

    A fresh temporary Telethon session is used deliberately so
    an already-authorized persistent session cannot make an
    invalid replacement bot token appear valid.
    """

    token = bot_token.strip()

    if not token:
        raise TelegramMtprotoConfigError(
            "Telegram bot token must not be empty."
        )

    with tempfile.TemporaryDirectory(
        prefix="holotes-telegram-probe-"
    ) as temporary_directory:
        probe_settings = TelegramMtprotoSettings(
            api_id=settings.api_id,
            api_hash=settings.api_hash,
            proxy=settings.proxy,
            session_path=(
                Path(
                    temporary_directory
                )
                / "telegram_probe"
            ),
        )

        client = build_mtproto_client(
            probe_settings
        )

        try:
            await client.start(
                bot_token=token
            )

            identity = await client.get_me()

            if identity is None:
                raise TelegramMtprotoConnectionError(
                    "Telegram returned no bot identity."
                )

            if not getattr(
                identity,
                "bot",
                False,
            ):
                raise TelegramMtprotoConnectionError(
                    "The authenticated Telegram account "
                    "is not a bot."
                )

            username = (
                getattr(
                    identity,
                    "username",
                    None,
                )
                or ""
            )

            return TelegramMtprotoBotIdentity(
                telegram_user_id=int(
                    identity.id
                ),
                username=str(
                    username
                ),
            )

        except TelegramMtprotoConnectionError:
            raise

        except Exception as exc:
            raise TelegramMtprotoConnectionError(
                "Could not connect or authenticate "
                "through Telegram MTProto."
            ) from exc

        finally:
            await client.disconnect()

def mtproto_peer_to_bot_api_chat_id(
    peer: object,
) -> int:
    """
    Converts an MTProto peer ID to the Bot API dialog-ID format.

    This keeps existing Holotes ACL/chat settings compatible
    between Bot API and MTProto transports.
    """

    peer_id = int(
        getattr(
            peer,
            "id",
        )
    )

    if isinstance(
        peer,
        User,
    ):
        return peer_id

    if isinstance(
        peer,
        Chat,
    ):
        return -peer_id

    if isinstance(
        peer,
        Channel,
    ):
        return -(
            1_000_000_000_000
            + peer_id
        )

    raise ValueError(
        "Unsupported Telegram peer type."
    )


def mtproto_chat_type(
    peer: object,
) -> str:
    """Maps an MTProto peer to the Bot API-style chat type."""

    if isinstance(
        peer,
        User,
    ):
        return "private"

    if isinstance(
        peer,
        Chat,
    ):
        return "group"

    if isinstance(
        peer,
        Channel,
    ):
        if bool(
            getattr(
                peer,
                "megagroup",
                False,
            )
        ):
            return "supergroup"

        return "channel"

    return ""


async def extract_mtproto_message_context(
    event: object,
):
    """
    Converts a Telethon NewMessage event into the same
    TelegramMessageContext used by the Bot API transport.

    Imported lazily to avoid coupling the transport module
    to telegram_bot at import time.
    """

    from src.telegram_bot import (
        TelegramMessageContext,
    )

    message = getattr(
        event,
        "message",
        None,
    )

    if message is None:
        return None

    text = str(
        getattr(
            event,
            "raw_text",
            "",
        )
        or ""
    )

    if not text:
        return None

    sender = await event.get_sender()
    chat = await event.get_chat()

    if sender is None or chat is None:
        return None

    sender_id = getattr(
        sender,
        "id",
        None,
    )

    message_id = getattr(
        message,
        "id",
        None,
    )

    if sender_id is None or message_id is None:
        return None

    reply_to = getattr(
        message,
        "reply_to",
        None,
    )

    thread_id = None

    if reply_to is not None:
        thread_id = getattr(
            reply_to,
            "reply_to_top_id",
            None,
        )

    language_code = str(
        getattr(
            sender,
            "lang_code",
            "",
        )
        or ""
    )

    return TelegramMessageContext(
        update_id=int(
            message_id
        ),
        message_id=int(
            message_id
        ),
        telegram_user_id=int(
            sender_id
        ),
        telegram_chat_id=(
            mtproto_peer_to_bot_api_chat_id(
                chat
            )
        ),
        message_thread_id=(
            int(thread_id)
            if thread_id is not None
            else None
        ),
        chat_type=mtproto_chat_type(
            chat
        ),
        language_code=language_code,
        text=text,
    )


async def send_mtproto_text(
    *,
    client: TelegramClient,
    entity: object,
    text: str,
    reply_to: int | None = None,
    chunk_limit: int = 4_000,
) -> None:
    """Sends plain text through MTProto."""

    if chunk_limit <= 0:
        raise ValueError(
            "Message limit must be positive."
        )

    from src.telegram_bot import (
        _split_message,
    )

    for chunk in _split_message(
        text,
        limit=chunk_limit,
    ):
        kwargs = {}

        if reply_to is not None:
            kwargs["reply_to"] = reply_to

        await client.send_message(
            entity,
            chunk,
            **kwargs,
        )


async def handle_mtproto_event(
    *,
    client: TelegramClient,
    event: object,
    bot_token: str,
    bot_username: str,
) -> bool:
    """
    Handles one Telethon NewMessage event through the common
    Holotes Telegram command dispatcher.
    """

    from src.telegram_bot import (
        handle_message_context,
    )

    context = await extract_mtproto_message_context(
        event
    )

    if context is None:
        return False

    outgoing: list[dict[str, object]] = []

    def capture_send(
        **parameters: object,
    ) -> None:
        outgoing.append(
            dict(parameters)
        )

    handled = handle_message_context(
        context=context,
        token=bot_token,
        bot_username=bot_username,
        send=capture_send,
    )

    if not handled:
        return False

    entity = await event.get_chat()

    if entity is None:
        raise TelegramMtprotoConnectionError(
            "Could not resolve the Telegram chat."
        )

    for response in outgoing:
        response_text = response.get(
            "text"
        )

        if response_text is None:
            continue

        thread_id = response.get(
            "message_thread_id"
        )

        await send_mtproto_text(
            client=client,
            entity=entity,
            text=str(
                response_text
            ),
            reply_to=(
                int(thread_id)
                if thread_id is not None
                else None
            ),
        )

    return True


async def run_mtproto_bot(
    *,
    bot_token: str,
    settings: TelegramMtprotoSettings | None = None,
) -> None:
    """Runs the Holotes Telegram bot through MTProto."""

    token = str(
        bot_token
    ).strip()

    if not token:
        raise TelegramMtprotoConfigError(
            "Telegram bot token must not be empty."
        )

    resolved_settings = (
        settings
        if settings is not None
        else load_mtproto_settings()
    )

    client = build_mtproto_client(
        resolved_settings
    )

    handler_lock = asyncio.Lock()

    try:
        await client.start(
            bot_token=token
        )

        identity = await client.get_me()

        if identity is None:
            raise TelegramMtprotoConnectionError(
                "Telegram returned no bot identity."
            )

        if not bool(
            getattr(
                identity,
                "bot",
                False,
            )
        ):
            raise TelegramMtprotoConnectionError(
                "The authenticated Telegram account "
                "is not a bot."
            )

        bot_username = str(
            getattr(
                identity,
                "username",
                "",
            )
            or ""
        ).strip()

        if not bot_username:
            raise TelegramMtprotoConnectionError(
                "Telegram bot does not have a username."
            )

        async def on_new_message(
            event: object,
        ) -> None:
            try:
                async with handler_lock:
                    await handle_mtproto_event(
                        client=client,
                        event=event,
                        bot_token=token,
                        bot_username=bot_username,
                    )

            except Exception:
                LOGGER.exception(
                    "Unexpected Telegram MTProto "
                    "update error."
                )

        client.add_event_handler(
            on_new_message,
            events.NewMessage(
                incoming=True
            ),
        )

        print(
            "Holotes Telegram bot started through MTProto: "
            f"@{bot_username}"
        )
        print(
            "Press Ctrl+C to stop."
        )

        await client.run_until_disconnected()

    except TelegramMtprotoConfigError:
        raise

    except TelegramMtprotoConnectionError:
        raise

    except Exception as exc:
        raise TelegramMtprotoConnectionError(
            "Telegram MTProto runtime failed."
        ) from exc

    finally:
        if client.is_connected():
            await client.disconnect()
