from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.telegram_settings import (
    TelegramSettings,
    get_telegram_settings,
    is_telegram_request_allowed,
)
from src.telegram_summary import (
    TelegramSummaryError,
    build_telegram_summary,
    format_telegram_summary,
)
from src.telegram_token import (
    TelegramTokenError,
    get_configured_bot_identity,
    load_telegram_bot_token,
)


TELEGRAM_API_ROOT = "https://api.telegram.org"

POLL_TIMEOUT_SECONDS = 25
NETWORK_TIMEOUT_PADDING_SECONDS = 10
MAX_TELEGRAM_MESSAGE_LENGTH = 4_000

RETRY_DELAYS_SECONDS = (
    1,
    2,
    4,
    8,
    15,
)

LOGGER = logging.getLogger(
    "open_mas.telegram_bot"
)


class TelegramBotApiError(RuntimeError):
    """Raised when a Telegram Bot API request fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            message
        )

        self.status_code = status_code


@dataclass(frozen=True)
class TelegramMessageContext:
    """Minimal information extracted from an update."""

    update_id: int
    message_id: int
    telegram_user_id: int
    telegram_chat_id: int
    message_thread_id: int | None
    chat_type: str
    language_code: str
    text: str


@dataclass(frozen=True)
class ParsedCommand:
    """Parsed Telegram bot command."""

    name: str
    arguments: str


BOT_TEXTS = {
    "ru": {
        "start": (
            "Open MAS Telegram-бот запущен.\n\n"
            "/help — список команд\n"
            "/myid — показать ваш Telegram user ID\n"
            "/chatid — показать ID текущего чата\n"
            "/summary — финансовая сводка\n"
            "/summary 2026-07 — сводка за конкретный месяц"
        ),
        "help": (
            "Команды Open MAS:\n\n"
            "/myid — ваш Telegram user ID\n"
            "/chatid — ID и тип текущего чата\n"
            "/summary — сводка за период по умолчанию\n"
            "/summary YYYY-MM — сводка за выбранный месяц\n\n"
            "Также поддерживаются периоды:\n"
            "current_month\n"
            "previous_month\n"
            "last_30_days\n"
            "current_quarter\n"
            "current_year"
        ),
        "myid": "Ваш Telegram user ID: {user_id}",
        "chatid": (
            "Telegram chat ID: {chat_id}\n"
            "Topic ID: {thread_id}\n"
            "Тип чата: {chat_type}"
        ),
        "disabled": (
            "Финансовые команды Telegram-бота "
            "сейчас отключены в настройках Open MAS."
        ),
        "access_denied": (
            "Доступ к финансовым данным запрещён.\n\n"
            "Ваш user ID: {user_id}\n"
            "Chat ID: {chat_id}\n"
            "Тип чата: {chat_type}\n\n"
            "Добавьте пользователя и, для группы, чат "
            "в Настройки → Telegram."
        ),
        "summary_usage": (
            "Формат команды:\n"
            "/summary\n"
            "/summary 2026-07"
        ),
        "invalid_period": (
            "Не удалось распознать период.\n\n"
            "Используйте YYYY-MM или один из периодов:\n"
            "current_month\n"
            "previous_month\n"
            "last_30_days\n"
            "current_quarter\n"
            "current_year"
        ),
        "summary_error": (
            "Не удалось сформировать финансовую сводку. "
            "Проверьте базу и настройки Open MAS."
        ),
        "unknown": (
            "Неизвестная команда. "
            "Отправьте /help."
        ),
    },
    "en": {
        "start": (
            "Open MAS Telegram bot is running.\n\n"
            "/help — command list\n"
            "/myid — show your Telegram user ID\n"
            "/chatid — show the current chat ID\n"
            "/summary — financial summary\n"
            "/summary 2026-07 — summary for a specific month"
        ),
        "help": (
            "Open MAS commands:\n\n"
            "/myid — your Telegram user ID\n"
            "/chatid — current chat ID and type\n"
            "/summary — summary for the default period\n"
            "/summary YYYY-MM — summary for a selected month\n\n"
            "Named periods:\n"
            "current_month\n"
            "previous_month\n"
            "last_30_days\n"
            "current_quarter\n"
            "current_year"
        ),
        "myid": "Your Telegram user ID: {user_id}",
        "chatid": (
            "Telegram chat ID: {chat_id}\n"
            "Topic ID: {thread_id}\n"
            "Chat type: {chat_type}"
        ),
        "disabled": (
            "Telegram financial commands are currently "
            "disabled in Open MAS settings."
        ),
        "access_denied": (
            "Access to financial data was denied.\n\n"
            "Your user ID: {user_id}\n"
            "Chat ID: {chat_id}\n"
            "Chat type: {chat_type}\n\n"
            "Add the user and, for a group, the chat "
            "under Settings → Telegram."
        ),
        "summary_usage": (
            "Command format:\n"
            "/summary\n"
            "/summary 2026-07"
        ),
        "invalid_period": (
            "The period could not be recognized.\n\n"
            "Use YYYY-MM or one of these periods:\n"
            "current_month\n"
            "previous_month\n"
            "last_30_days\n"
            "current_quarter\n"
            "current_year"
        ),
        "summary_error": (
            "The financial summary could not be generated. "
            "Check the Open MAS database and settings."
        ),
        "unknown": (
            "Unknown command. Send /help."
        ),
    },
    "zh-CN": {
        "start": (
            "Open MAS Telegram 机器人正在运行。\n\n"
            "/help — 命令列表\n"
            "/myid — 显示您的 Telegram 用户 ID\n"
            "/chatid — 显示当前聊天 ID\n"
            "/summary — 财务摘要\n"
            "/summary 2026-07 — 指定月份的摘要"
        ),
        "help": (
            "Open MAS 命令：\n\n"
            "/myid — 您的 Telegram 用户 ID\n"
            "/chatid — 当前聊天 ID 和类型\n"
            "/summary — 默认期间的摘要\n"
            "/summary YYYY-MM — 指定月份的摘要\n\n"
            "可用期间：\n"
            "current_month\n"
            "previous_month\n"
            "last_30_days\n"
            "current_quarter\n"
            "current_year"
        ),
        "myid": "您的 Telegram 用户 ID：{user_id}",
        "chatid": (
            "Telegram 聊天 ID：{chat_id}\n"
            "主题 ID：{thread_id}\n"
            "聊天类型：{chat_type}"
        ),
        "disabled": (
            "Open MAS 设置中当前已禁用 Telegram 财务命令。"
        ),
        "access_denied": (
            "无权访问财务数据。\n\n"
            "您的用户 ID：{user_id}\n"
            "聊天 ID：{chat_id}\n"
            "聊天类型：{chat_type}\n\n"
            "请在设置 → Telegram 中添加用户和群组聊天。"
        ),
        "summary_usage": (
            "命令格式：\n"
            "/summary\n"
            "/summary 2026-07"
        ),
        "invalid_period": (
            "无法识别期间。\n\n"
            "请使用 YYYY-MM 或以下期间：\n"
            "current_month\n"
            "previous_month\n"
            "last_30_days\n"
            "current_quarter\n"
            "current_year"
        ),
        "summary_error": (
            "无法生成财务摘要。"
            "请检查 Open MAS 数据库和设置。"
        ),
        "unknown": (
            "未知命令。请发送 /help。"
        ),
    },
}


BOT_COMMANDS = {
    "en": (
        {
            "command": "start",
            "description": "Start Open MAS and show help",
        },
        {
            "command": "help",
            "description": "Show available commands",
        },
        {
            "command": "myid",
            "description": "Show your Telegram user ID",
        },
        {
            "command": "chatid",
            "description": "Show chat and topic IDs",
        },
        {
            "command": "summary",
            "description": "Generate a financial summary",
        },
    ),
    "ru": (
        {
            "command": "start",
            "description": "Запустить Open MAS и показать справку",
        },
        {
            "command": "help",
            "description": "Показать доступные команды",
        },
        {
            "command": "myid",
            "description": "Показать ваш Telegram user ID",
        },
        {
            "command": "chatid",
            "description": "Показать ID чата и темы",
        },
        {
            "command": "summary",
            "description": "Сформировать финансовую сводку",
        },
    ),
    "zh": (
        {
            "command": "start",
            "description": "启动 Open MAS 并显示帮助",
        },
        {
            "command": "help",
            "description": "显示可用命令",
        },
        {
            "command": "myid",
            "description": "显示您的 Telegram 用户 ID",
        },
        {
            "command": "chatid",
            "description": "显示聊天和主题 ID",
        },
        {
            "command": "summary",
            "description": "生成财务摘要",
        },
    ),
}


def _language_code(
    language_code: str,
) -> str:
    """Normalizes a Telegram language code."""

    normalized = str(
        language_code
    ).strip().lower()

    if normalized.startswith("ru"):
        return "ru"

    if normalized.startswith("zh"):
        return "zh-CN"

    return "en"


def _text(
    language_code: str,
    key: str,
    **values: object,
) -> str:
    """Returns localized bot text."""

    language = _language_code(
        language_code
    )

    template = BOT_TEXTS[
        language
    ][key]

    return template.format(
        **values
    )


def _encode_api_parameters(
    parameters: dict[str, Any],
) -> bytes:
    """Encodes parameters for Bot API POST."""

    encoded: dict[str, str] = {}

    for key, value in parameters.items():
        if isinstance(
            value,
            bool,
        ):
            encoded[key] = (
                "true"
                if value
                else "false"
            )

        elif isinstance(
            value,
            (
                list,
                dict,
            ),
        ):
            encoded[key] = json.dumps(
                value,
                ensure_ascii=False,
            )

        else:
            encoded[key] = str(
                value
            )

    return urlencode(
        encoded
    ).encode(
        "utf-8"
    )


def _telegram_api_request(
    *,
    token: str,
    method: str,
    parameters: dict[str, Any] | None = None,
    timeout: float = 15,
) -> Any:
    """Calls Telegram Bot API without logging token."""

    if timeout <= 0:
        raise ValueError(
            "Telegram API timeout must be positive."
        )

    request = Request(
        (
            f"{TELEGRAM_API_ROOT}/"
            f"bot{token}/{method}"
        ),
        data=_encode_api_parameters(
            parameters or {}
        ),
        headers={
            "Content-Type": (
                "application/x-www-form-urlencoded"
            ),
            "User-Agent": "Open-MAS/0.1",
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            response_bytes = response.read()

    except HTTPError as exc:
        if exc.code == 401:
            raise TelegramBotApiError(
                "Telegram rejected the bot token.",
                status_code=exc.code,
            ) from None

        if exc.code == 409:
            raise TelegramBotApiError(
                "Another Telegram polling process "
                "is already using this bot.",
                status_code=exc.code,
            ) from None

        raise TelegramBotApiError(
            (
                "Telegram API returned "
                f"HTTP {exc.code}."
            ),
            status_code=exc.code,
        ) from None

    except (
        URLError,
        TimeoutError,
        OSError,
    ):
        raise TelegramBotApiError(
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
        raise TelegramBotApiError(
            "Telegram returned invalid JSON."
        ) from None

    if not isinstance(
        payload,
        dict,
    ):
        raise TelegramBotApiError(
            "Telegram returned an invalid response."
        )

    if payload.get("ok") is not True:
        description = str(
            payload.get(
                "description"
            )
            or "Telegram rejected the request."
        )

        raise TelegramBotApiError(
            description
        )

    return payload.get(
        "result"
    )


def register_bot_commands(
    *,
    token: str,
) -> None:
    """Registers localized Telegram command menus."""

    configurations = (
        (
            None,
            BOT_COMMANDS["en"],
        ),
        (
            "ru",
            BOT_COMMANDS["ru"],
        ),
        (
            "zh",
            BOT_COMMANDS["zh"],
        ),
    )

    for (
        language_code,
        commands,
    ) in configurations:
        parameters: dict[
            str,
            Any,
        ] = {
            "commands": list(
                commands
            ),
        }

        if language_code is not None:
            parameters[
                "language_code"
            ] = language_code

        result = _telegram_api_request(
            token=token,
            method="setMyCommands",
            parameters=parameters,
        )

        if result is not True:
            raise TelegramBotApiError(
                "Telegram did not confirm "
                "the command menu."
            )


def prepare_long_polling(
    *,
    token: str,
) -> None:
    """Removes a webhook and discards stale updates."""

    result = _telegram_api_request(
        token=token,
        method="deleteWebhook",
        parameters={
            "drop_pending_updates": True,
        },
    )

    if result is not True:
        raise TelegramBotApiError(
            "Could not prepare Telegram long polling."
        )


def get_updates(
    *,
    token: str,
    offset: int | None,
    poll_timeout: int = (
        POLL_TIMEOUT_SECONDS
    ),
) -> list[dict[str, Any]]:
    """Receives command updates through long polling."""

    if poll_timeout < 0:
        raise ValueError(
            "Poll timeout must not be negative."
        )

    parameters: dict[str, Any] = {
        "timeout": poll_timeout,
        "limit": 100,
        "allowed_updates": [
            "message",
        ],
    }

    if offset is not None:
        parameters["offset"] = offset

    result = _telegram_api_request(
        token=token,
        method="getUpdates",
        parameters=parameters,
        timeout=(
            poll_timeout
            + NETWORK_TIMEOUT_PADDING_SECONDS
        ),
    )

    if not isinstance(
        result,
        list,
    ):
        raise TelegramBotApiError(
            "Telegram returned an invalid updates list."
        )

    return [
        update
        for update in result
        if isinstance(
            update,
            dict,
        )
    ]


def _split_message(
    text: str,
    *,
    limit: int = (
        MAX_TELEGRAM_MESSAGE_LENGTH
    ),
) -> tuple[str, ...]:
    """Splits long plain-text messages by lines."""

    if limit <= 0:
        raise ValueError(
            "Message limit must be positive."
        )

    normalized = str(
        text
    )

    if len(normalized) <= limit:
        return (
            normalized,
        )

    chunks: list[str] = []
    current_lines: list[str] = []
    current_length = 0

    for original_line in normalized.splitlines():
        line = original_line

        while len(line) > limit:
            if current_lines:
                chunks.append(
                    "\n".join(
                        current_lines
                    )
                )

                current_lines = []
                current_length = 0

            chunks.append(
                line[:limit]
            )

            line = line[limit:]

        additional_length = (
            len(line)
            + (
                1
                if current_lines
                else 0
            )
        )

        if (
            current_lines
            and current_length
            + additional_length
            > limit
        ):
            chunks.append(
                "\n".join(
                    current_lines
                )
            )

            current_lines = []
            current_length = 0

        current_lines.append(
            line
        )

        current_length += (
            len(line)
            + (
                1
                if len(
                    current_lines
                ) > 1
                else 0
            )
        )

    if current_lines:
        chunks.append(
            "\n".join(
                current_lines
            )
        )

    return tuple(
        chunk
        for chunk in chunks
        if chunk
    )


def send_text(
    *,
    token: str,
    chat_id: int,
    text: str,
    message_thread_id: int | None = None,
) -> None:
    """Sends plain text to a chat or forum topic."""

    for chunk in _split_message(
        text
    ):
        parameters: dict[str, Any] = {
            "chat_id": chat_id,
            "text": chunk,
        }

        if message_thread_id is not None:
            parameters[
                "message_thread_id"
            ] = message_thread_id

        result = _telegram_api_request(
            token=token,
            method="sendMessage",
            parameters=parameters,
        )

        if not isinstance(
            result,
            dict,
        ):
            raise TelegramBotApiError(
                "Telegram did not confirm "
                "the sent message."
            )


def _required_integer(
    value: Any,
) -> int:
    """Returns a required integer update value."""

    if isinstance(
        value,
        bool,
    ):
        raise ValueError(
            "Telegram ID must be an integer."
        )

    return int(
        value
    )


def extract_message_context(
    update: dict[str, Any],
) -> TelegramMessageContext | None:
    """Extracts a text message from an update."""

    message = update.get(
        "message"
    )

    if not isinstance(
        message,
        dict,
    ):
        return None

    sender = message.get(
        "from"
    )

    chat = message.get(
        "chat"
    )

    text = message.get(
        "text"
    )

    if (
        not isinstance(sender, dict)
        or not isinstance(chat, dict)
        or not isinstance(text, str)
    ):
        return None

    try:
        return TelegramMessageContext(
            update_id=_required_integer(
                update["update_id"]
            ),
            message_id=_required_integer(
                message["message_id"]
            ),
            telegram_user_id=(
                _required_integer(
                    sender["id"]
                )
            ),
            telegram_chat_id=(
                _required_integer(
                    chat["id"]
                )
            ),
            message_thread_id=(
                _required_integer(
                    message[
                        "message_thread_id"
                    ]
                )
                if message.get(
                    "message_thread_id"
                )
                is not None
                else None
            ),
            chat_type=str(
                chat.get(
                    "type",
                    "",
                )
            ).strip(),
            language_code=str(
                sender.get(
                    "language_code",
                    "",
                )
            ).strip(),
            text=text,
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return None


def parse_command(
    text: str,
    *,
    bot_username: str,
) -> ParsedCommand | None:
    """Parses /command and /command@bot forms."""

    normalized = str(
        text
    ).strip()

    if not normalized.startswith(
        "/"
    ):
        return None

    command_token, separator, arguments = (
        normalized.partition(
            " "
        )
    )

    command_body = command_token[
        1:
    ]

    if not command_body:
        return None

    command_name, mention_separator, mention = (
        command_body.partition(
            "@"
        )
    )

    if mention_separator:
        normalized_username = str(
            bot_username
        ).strip().lstrip(
            "@"
        ).casefold()

        if (
            mention.casefold()
            != normalized_username
        ):
            return None

    normalized_command = (
        command_name.strip().lower()
    )

    if not normalized_command:
        return None

    return ParsedCommand(
        name=normalized_command,
        arguments=(
            arguments.strip()
            if separator
            else ""
        ),
    )


def _summary_period_argument(
    arguments: str,
) -> str | None:
    """Validates the optional /summary argument."""

    values = str(
        arguments
    ).split()

    if not values:
        return None

    if len(values) != 1:
        raise ValueError(
            "Summary accepts one period argument."
        )

    return values[0]


def _send_localized(
    *,
    token: str,
    context: TelegramMessageContext,
    key: str,
    **values: object,
) -> None:
    """Sends a localized command response."""

    send_text(
        token=token,
        chat_id=(
            context.telegram_chat_id
        ),
        message_thread_id=(
            context.message_thread_id
        ),
        text=_text(
            context.language_code,
            key,
            **values,
        ),
    )


def _handle_summary_command(
    *,
    token: str,
    context: TelegramMessageContext,
    arguments: str,
) -> None:
    """Handles an authorized financial summary."""

    try:
        settings = (
            get_telegram_settings()
        )

    except Exception:
        LOGGER.exception(
            "Could not read Telegram settings."
        )

        _send_localized(
            token=token,
            context=context,
            key="summary_error",
        )

        return

    if not settings.is_enabled:
        _send_localized(
            token=token,
            context=context,
            key="disabled",
        )

        return

    allowed = (
        is_telegram_request_allowed(
            telegram_user_id=(
                context.telegram_user_id
            ),
            telegram_chat_id=(
                context.telegram_chat_id
            ),
            chat_type=(
                context.chat_type
            ),
        )
    )

    if not allowed:
        _send_localized(
            token=token,
            context=context,
            key="access_denied",
            user_id=(
                context.telegram_user_id
            ),
            chat_id=(
                context.telegram_chat_id
            ),
            chat_type=context.chat_type,
        )

        return

    try:
        period = (
            _summary_period_argument(
                arguments
            )
        )

    except ValueError:
        _send_localized(
            token=token,
            context=context,
            key="summary_usage",
        )

        return

    try:
        summary = build_telegram_summary(
            period=period,
            settings=settings,
        )

    except ValueError:
        _send_localized(
            token=token,
            context=context,
            key="invalid_period",
        )

        return

    except TelegramSummaryError:
        LOGGER.exception(
            "Could not build Telegram summary."
        )

        _send_localized(
            token=token,
            context=context,
            key="summary_error",
        )

        return

    except Exception:
        LOGGER.exception(
            "Unexpected Telegram summary error."
        )

        _send_localized(
            token=token,
            context=context,
            key="summary_error",
        )

        return

    summary_text = (
        format_telegram_summary(
            summary,
            language=(
                context.language_code
            ),
        )
    )

    send_text(
        token=token,
        chat_id=(
            context.telegram_chat_id
        ),
        message_thread_id=(
            context.message_thread_id
        ),
        text=summary_text,
    )


def handle_update(
    *,
    update: dict[str, Any],
    token: str,
    bot_username: str,
) -> bool:
    """Handles one Telegram command update."""

    context = extract_message_context(
        update
    )

    if context is None:
        return False

    command = parse_command(
        context.text,
        bot_username=bot_username,
    )

    if command is None:
        return False

    if command.name == "start":
        _send_localized(
            token=token,
            context=context,
            key="start",
        )

        return True

    if command.name == "help":
        _send_localized(
            token=token,
            context=context,
            key="help",
        )

        return True

    if command.name == "myid":
        _send_localized(
            token=token,
            context=context,
            key="myid",
            user_id=(
                context.telegram_user_id
            ),
        )

        return True

    if command.name == "chatid":
        _send_localized(
            token=token,
            context=context,
            key="chatid",
            chat_id=(
                context.telegram_chat_id
            ),
            thread_id=(
                context.message_thread_id
                if (
                    context.message_thread_id
                    is not None
                )
                else "—"
            ),
            chat_type=context.chat_type,
        )

        return True

    if command.name == "summary":
        _handle_summary_command(
            token=token,
            context=context,
            arguments=command.arguments,
        )

        return True

    _send_localized(
        token=token,
        context=context,
        key="unknown",
    )

    return True


def _polling_error_is_fatal(
    error: TelegramBotApiError,
) -> bool:
    """Checks whether polling must stop immediately."""

    return error.status_code in {
        401,
        409,
    }


def run_bot() -> None:
    """Runs the Open MAS long-polling bot."""

    token = load_telegram_bot_token()

    identity = (
        get_configured_bot_identity()
    )

    bot_username = (
        identity.username
    )

    if not bot_username:
        raise TelegramBotApiError(
            "Telegram bot does not have a username."
        )

    prepare_long_polling(
        token=token
    )

    try:
        register_bot_commands(
            token=token
        )

    except TelegramBotApiError as exc:
        LOGGER.warning(
            "Could not register Telegram "
            "command menu: %s",
            exc,
        )

    print(
        "Open MAS Telegram bot started: "
        f"@{bot_username}"
    )

    print(
        "Press Ctrl+C to stop."
    )

    offset: int | None = None
    retry_index = 0

    while True:
        try:
            updates = get_updates(
                token=token,
                offset=offset,
            )

            retry_index = 0

        except TelegramBotApiError as exc:
            if _polling_error_is_fatal(
                exc
            ):
                raise

            delay = RETRY_DELAYS_SECONDS[
                min(
                    retry_index,
                    len(
                        RETRY_DELAYS_SECONDS
                    ) - 1,
                )
            ]

            retry_index += 1

            LOGGER.warning(
                "%s Retrying in %s seconds.",
                exc,
                delay,
            )

            time.sleep(
                delay
            )

            continue

        for update in updates:
            try:
                update_id = _required_integer(
                    update["update_id"]
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

            offset = update_id + 1

            try:
                handle_update(
                    update=update,
                    token=token,
                    bot_username=(
                        bot_username
                    ),
                )

            except TelegramBotApiError:
                LOGGER.exception(
                    "Telegram command response failed."
                )

            except Exception:
                LOGGER.exception(
                    "Unexpected Telegram update error."
                )


def main() -> None:
    """CLI entry point."""

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s: "
            "%(message)s"
        ),
    )

    try:
        run_bot()

    except KeyboardInterrupt:
        print(
            "\nOpen MAS Telegram bot stopped."
        )

    except (
        TelegramTokenError,
        TelegramBotApiError,
    ) as exc:
        raise SystemExit(
            f"Telegram bot startup failed: {exc}"
        ) from None


if __name__ == "__main__":
    main()
