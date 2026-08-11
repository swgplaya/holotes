from __future__ import annotations

from collections.abc import Callable
import asyncio
from pathlib import Path
import tempfile

import streamlit as st

from src.database_backup import (
    DatabaseBackupError,
    create_database_backup,
    inspect_holotes_database,
    resolve_sqlite_database_path,
    restore_database,
)
from src.telegram_token import (
    TelegramBotIdentity,
    TelegramTokenError,
    delete_telegram_bot_token,
    get_configured_bot_identity,
    is_telegram_bot_token_configured,
    load_telegram_bot_token,
    save_telegram_bot_token,
    store_telegram_bot_token,
)
from src.telegram_transport_config import (
    TelegramTransportConfigError,
    get_telegram_transport_config,
    save_telegram_transport_config,
)
from src.telegram_mtproto import (
    TelegramMtprotoConfigError,
    TelegramMtprotoConnectionError,
    load_mtproto_settings,
    probe_mtproto_bot,
)
from src.telegram_settings import (
    SUMMARY_PERIODS,
    TELEGRAM_CHAT_TYPES,
    delete_allowed_chat,
    delete_allowed_user,
    get_allowed_chats_dataframe,
    get_allowed_users_dataframe,
    get_telegram_settings,
    save_allowed_chat,
    save_allowed_user,
    set_allowed_chat_active,
    set_allowed_user_active,
    update_telegram_settings,
)


Translator = Callable[..., str]

BACKUP_BYTES_STATE_KEY = (
    "settings_database_backup_bytes"
)
BACKUP_NAME_STATE_KEY = (
    "settings_database_backup_name"
)
BACKUP_PATH_STATE_KEY = (
    "settings_database_backup_path"
)
RESTORE_MESSAGE_STATE_KEY = (
    "settings_database_restore_message"
)
RESTORE_UPLOAD_VERSION_STATE_KEY = (
    "settings_database_restore_upload_version"
)

TELEGRAM_TOKEN_VERSION_STATE_KEY = (
    "settings_telegram_token_version"
)
TELEGRAM_TOKEN_MESSAGE_STATE_KEY = (
    "settings_telegram_token_message"
)
TELEGRAM_IDENTITY_STATE_KEY = (
    "settings_telegram_bot_identity"
)


TELEGRAM_SETTINGS_MESSAGE_STATE_KEY = (
    "settings_telegram_management_message"
)


def _format_file_size(
    size_bytes: int,
) -> str:
    """Formats a file size for the interface."""

    size = float(
        max(0, size_bytes)
    )

    units = (
        "B",
        "KB",
        "MB",
        "GB",
    )

    for unit in units:
        if (
            size < 1024
            or unit == units[-1]
        ):
            if unit == "B":
                return f"{int(size)} {unit}"

            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size_bytes} B"


def _write_uploaded_database(
    data: bytes,
    directory: Path,
) -> Path:
    """Writes an uploaded database to a closed temp file."""

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix="holotes-upload-",
        suffix=".db",
        dir=directory,
        delete=False,
    ) as temporary_file:
        temporary_file.write(
            data
        )

        return Path(
            temporary_file.name
        )


def _show_database_error(
    *,
    t: Translator,
    error: Exception,
) -> None:
    """Shows a localized error with technical details."""

    st.error(
        t(
            "settings.database.error"
        )
    )

    with st.expander(
        t(
            "settings.database.error_details"
        )
    ):
        st.code(
            str(error),
            language=None,
        )


def _render_database_information(
    *,
    t: Translator,
    database_path: Path,
) -> None:
    """Shows information about the active database."""

    inspection = (
        inspect_holotes_database(
            database_path
        )
    )

    st.subheader(
        t(
            "settings.database.title"
        )
    )

    st.caption(
        t(
            "settings.database.caption"
        )
    )

    st.markdown(
        f"**{t('settings.database.path')}**"
    )

    st.code(
        str(database_path),
        language=None,
    )

    metric_columns = st.columns(
        3
    )

    metric_columns[0].metric(
        t(
            "settings.database.size"
        ),
        _format_file_size(
            inspection.size_bytes
        ),
    )

    metric_columns[1].metric(
        t(
            "settings.database.revision"
        ),
        inspection.revision,
    )

    metric_columns[2].metric(
        t(
            "settings.database.schema"
        ),
        t(
            (
                "settings.database."
                "schema.current"
            )
            if inspection.is_head
            else (
                "settings.database."
                "schema.old"
            )
        ),
    )


def _render_backup_section(
    *,
    t: Translator,
    database_path: Path,
) -> None:
    """Renders database backup controls."""

    st.divider()

    st.subheader(
        t(
            "settings.database.backup.title"
        )
    )

    st.caption(
        t(
            "settings.database.backup.caption"
        )
    )

    backup_directory = (
        database_path.parent
        / "backups"
    )

    create_backup = st.button(
        t(
            "settings.database.backup.create"
        ),
        type="primary",
        use_container_width=True,
    )

    if create_backup:
        try:
            backup_path = (
                create_database_backup(
                    database_path,
                    backup_directory,
                )
            )

            backup_bytes = (
                backup_path.read_bytes()
            )

        except (
            DatabaseBackupError,
            OSError,
        ) as exc:
            _show_database_error(
                t=t,
                error=exc,
            )

        else:
            st.session_state[
                BACKUP_BYTES_STATE_KEY
            ] = backup_bytes

            st.session_state[
                BACKUP_NAME_STATE_KEY
            ] = backup_path.name

            st.session_state[
                BACKUP_PATH_STATE_KEY
            ] = str(
                backup_path
            )

            st.success(
                t(
                    (
                        "settings.database."
                        "backup.created"
                    ),
                    name=backup_path.name,
                )
            )

    backup_bytes = (
        st.session_state.get(
            BACKUP_BYTES_STATE_KEY
        )
    )

    backup_name = (
        st.session_state.get(
            BACKUP_NAME_STATE_KEY
        )
    )

    backup_path_value = (
        st.session_state.get(
            BACKUP_PATH_STATE_KEY
        )
    )

    if (
        backup_bytes is not None
        and backup_name
    ):
        st.download_button(
            label=t(
                (
                    "settings.database."
                    "backup.download"
                )
            ),
            data=backup_bytes,
            file_name=backup_name,
            mime=(
                "application/"
                "vnd.sqlite3"
            ),
            use_container_width=True,
        )

        if backup_path_value:
            st.caption(
                t(
                    (
                        "settings.database."
                        "backup.saved_path"
                    ),
                    path=backup_path_value,
                )
            )


def _render_restore_preview(
    *,
    t: Translator,
    revision: str,
    size_bytes: int,
    migration_required: bool,
) -> None:
    """Shows information about an uploaded backup."""

    st.markdown(
        f"#### "
        f"{t('settings.database.restore.preview_title')}"
    )

    preview_columns = st.columns(
        2
    )

    preview_columns[0].metric(
        t(
            (
                "settings.database.restore."
                "preview_revision"
            )
        ),
        revision,
    )

    preview_columns[1].metric(
        t(
            (
                "settings.database.restore."
                "preview_size"
            )
        ),
        _format_file_size(
            size_bytes
        ),
    )

    if migration_required:
        st.info(
            t(
                (
                    "settings.database.restore."
                    "migration_required"
                )
            )
        )
    else:
        st.success(
            t(
                (
                    "settings.database.restore."
                    "migration_not_required"
                )
            )
        )


def _render_restore_section(
    *,
    t: Translator,
    database_path: Path,
) -> None:
    """Renders safe database restoration controls."""

    st.divider()

    restore_message = (
        st.session_state.pop(
            RESTORE_MESSAGE_STATE_KEY,
            None,
        )
    )

    if restore_message:
        st.success(
            restore_message
        )

    st.subheader(
        t(
            "settings.database.restore.title"
        )
    )

    st.caption(
        t(
            "settings.database.restore.caption"
        )
    )

    upload_version = int(
        st.session_state.get(
            RESTORE_UPLOAD_VERSION_STATE_KEY,
            0,
        )
    )

    uploaded_file = st.file_uploader(
        t(
            "settings.database.restore.upload"
        ),
        type=[
            "db",
            "sqlite",
            "sqlite3",
        ],
        accept_multiple_files=False,
        help=t(
            (
                "settings.database.restore."
                "upload_help"
            )
        ),
        key=(
            "settings_database_restore_upload_"
            f"{upload_version}"
        ),
    )

    if uploaded_file is None:
        return

    uploaded_path = (
        _write_uploaded_database(
            uploaded_file.getvalue(),
            database_path.parent,
        )
    )

    try:
        uploaded_inspection = (
            inspect_holotes_database(
                uploaded_path
            )
        )

        _render_restore_preview(
            t=t,
            revision=(
                uploaded_inspection.revision
            ),
            size_bytes=(
                uploaded_inspection.size_bytes
            ),
            migration_required=(
                not uploaded_inspection.is_head
            ),
        )

        st.warning(
            t(
                (
                    "settings.database.restore."
                    "warning"
                )
            )
        )

        confirmation_key = (
            "settings_database_restore_confirm_"
            f"{upload_version}"
        )

        phrase_key = (
            "settings_database_restore_phrase_"
            f"{upload_version}"
        )

        confirmed = st.checkbox(
            t(
                (
                    "settings.database.restore."
                    "confirm_checkbox"
                )
            ),
            key=confirmation_key,
        )

        required_phrase = t(
            (
                "settings.database.restore."
                "confirm_phrase"
            )
        )

        entered_phrase = st.text_input(
            t(
                (
                    "settings.database.restore."
                    "confirm_phrase_label"
                )
            ),
            key=phrase_key,
        )

        restoration_allowed = (
            confirmed
            and entered_phrase.strip()
            == required_phrase
        )

        restore_clicked = st.button(
            t(
                (
                    "settings.database.restore."
                    "button"
                )
            ),
            type="primary",
            disabled=(
                not restoration_allowed
            ),
            use_container_width=True,
        )

        if restore_clicked:
            result = restore_database(
                uploaded_path,
                database_path,
                (
                    database_path.parent
                    / "backups"
                ),
            )

            if result.migrated:
                message = t(
                    (
                        "settings.database.restore."
                        "success_migrated"
                    ),
                    revision=(
                        result.restored_revision
                    ),
                    backup=str(
                        result.safety_backup_path
                    ),
                )
            else:
                message = t(
                    (
                        "settings.database.restore."
                        "success"
                    ),
                    backup=str(
                        result.safety_backup_path
                    ),
                )

            st.session_state[
                RESTORE_MESSAGE_STATE_KEY
            ] = message

            st.session_state[
                RESTORE_UPLOAD_VERSION_STATE_KEY
            ] = upload_version + 1

            for state_key in (
                BACKUP_BYTES_STATE_KEY,
                BACKUP_NAME_STATE_KEY,
                BACKUP_PATH_STATE_KEY,
            ):
                st.session_state.pop(
                    state_key,
                    None,
                )

            st.cache_data.clear()
            st.rerun()

    except (
        DatabaseBackupError,
        OSError,
    ) as exc:
        _show_database_error(
            t=t,
            error=exc,
        )

    finally:
        uploaded_path.unlink(
            missing_ok=True
        )


def _render_database_settings(
    *,
    t: Translator,
) -> None:
    """Renders all database settings."""

    try:
        database_path = (
            resolve_sqlite_database_path()
        )

        _render_database_information(
            t=t,
            database_path=database_path,
        )

        _render_backup_section(
            t=t,
            database_path=database_path,
        )

        _render_restore_section(
            t=t,
            database_path=database_path,
        )

    except (
        DatabaseBackupError,
        OSError,
    ) as exc:
        _show_database_error(
            t=t,
            error=exc,
        )


def _mtproto_identity_to_state(
    identity: object,
) -> dict[str, object]:
    """Converts a minimal MTProto bot identity to UI state."""

    return {
        "bot_id": int(
            getattr(
                identity,
                "telegram_user_id",
            )
        ),
        "username": str(
            getattr(
                identity,
                "username",
                "",
            )
        ),
        "display_name": "",
    }


def _identity_to_state(
    identity: TelegramBotIdentity,
) -> dict[str, object]:
    """Converts a bot identity to session state."""

    return {
        "bot_id": identity.bot_id,
        "username": identity.username,
        "display_name": identity.display_name,
        "can_join_groups": (
            identity.can_join_groups
        ),
        "can_read_all_group_messages": (
            identity.can_read_all_group_messages
        ),
    }


def _show_telegram_error(
    *,
    t: Translator,
    error: Exception,
) -> None:
    """Shows a safe localized Telegram error."""

    st.error(
        t(
            "settings.telegram.error"
        )
    )

    with st.expander(
        t(
            "settings.telegram.error_details"
        )
    ):
        st.code(
            str(error),
            language=None,
        )


def _render_bot_identity(
    *,
    t: Translator,
    identity: dict[str, object],
) -> None:
    """Shows non-secret Telegram bot information."""

    username = str(
        identity.get(
            "username",
            "",
        )
    ).strip()

    display_name = str(
        identity.get(
            "display_name",
            "",
        )
    ).strip()

    bot_id = identity.get(
        "bot_id",
        "",
    )

    st.markdown(
        f"#### "
        f"{t('settings.telegram.identity.title')}"
    )

    if username:
        st.markdown(
            f"**@{username}**"
        )

    if display_name:
        st.caption(
            display_name
        )

    identity_columns = st.columns(
        3
    )

    identity_columns[0].metric(
        t(
            "settings.telegram.identity.bot_id"
        ),
        str(bot_id),
    )

    identity_columns[1].metric(
        t(
            (
                "settings.telegram.identity."
                "can_join_groups"
            )
        ),
        (
            "?"
            if "can_join_groups" not in identity
            else t(
                "common.yes"
                if bool(
                    identity.get(
                        "can_join_groups"
                    )
                )
                else "common.no"
            )
        ),
    )

    identity_columns[2].metric(
        t(
            (
                "settings.telegram.identity."
                "reads_all_messages"
            )
        ),
        (
            "?"
            if (
                "can_read_all_group_messages"
                not in identity
            )
            else t(
                "common.yes"
                if bool(
                    identity.get(
                        (
                            "can_read_all_"
                            "group_messages"
                        )
                    )
                )
                else "common.no"
            )
        ),
    )


def _render_transport_form(
    *,
    t: Translator,
) -> str:
    """Renders and stores Telegram transport configuration."""

    config = get_telegram_transport_config()

    st.markdown(
        f"#### "
        f"{t('settings.telegram.transport.title')}"
    )

    st.caption(
        t(
            "settings.telegram.transport.caption"
        )
    )

    transport_options = [
        "bot_api",
        "mtproto",
    ]

    selected_index = (
        transport_options.index(
            config.transport
        )
    )

    with st.form(
        "settings_telegram_transport_form"
    ):
        transport = st.selectbox(
            t(
                "settings.telegram.transport.field"
            ),
            options=transport_options,
            index=selected_index,
            format_func=lambda value: t(
                (
                    "settings.telegram.transport."
                    f"option.{value}"
                )
            ),
        )

        api_id = config.api_id
        api_hash = ""
        mtproxy_url = ""

        if transport == "mtproto":
            api_id = st.text_input(
                t(
                    "settings.telegram.transport.api_id"
                ),
                value=config.api_id,
                help=t(
                    (
                        "settings.telegram.transport."
                        "api_id_help"
                    )
                ),
            )

            api_hash = st.text_input(
                t(
                    (
                        "settings.telegram.transport."
                        "api_hash"
                    )
                ),
                value="",
                type="password",
                placeholder=(
                    t(
                        (
                            "settings.telegram.transport."
                            "secret_configured"
                        )
                    )
                    if config.api_hash_configured
                    else ""
                ),
                help=t(
                    (
                        "settings.telegram.transport."
                        "api_hash_help"
                    )
                ),
            )

            mtproxy_url = st.text_input(
                t(
                    (
                        "settings.telegram.transport."
                        "proxy"
                    )
                ),
                value="",
                type="password",
                placeholder=(
                    t(
                        (
                            "settings.telegram.transport."
                            "secret_configured"
                        )
                    )
                    if config.mtproxy_configured
                    else "tg://proxy?server=..."
                ),
                help=t(
                    (
                        "settings.telegram.transport."
                        "proxy_help"
                    )
                ),
            )

        submitted = st.form_submit_button(
            t(
                "settings.telegram.transport.save"
            ),
            type="primary",
            use_container_width=True,
        )

    if submitted:
        try:
            saved = save_telegram_transport_config(
                transport=transport,
                api_id=api_id,
                api_hash=api_hash,
                mtproxy_url=mtproxy_url,
            )

        except TelegramTransportConfigError as exc:
            _show_telegram_error(
                t=t,
                error=exc,
            )

        else:
            st.session_state[
                TELEGRAM_TOKEN_MESSAGE_STATE_KEY
            ] = t(
                (
                    "settings.telegram.transport."
                    "saved"
                )
            )

            st.rerun()

            return saved.transport

    if config.transport == "mtproto":
        st.info(
            t(
                (
                    "settings.telegram.transport."
                    "restart_required"
                )
            )
        )

    return config.transport


def _render_token_status(
    *,
    t: Translator,
    configured: bool,
) -> None:
    """Shows token presence without exposing it."""

    status_columns = st.columns(
        2
    )

    status_columns[0].metric(
        t(
            "settings.telegram.status.title"
        ),
        t(
            (
                "settings.telegram.status."
                "configured"
            )
            if configured
            else (
                "settings.telegram.status."
                "not_configured"
            )
        ),
    )

    status_columns[1].metric(
        t(
            "settings.telegram.status.storage"
        ),
        ".env",
    )


def _render_token_form(
    *,
    t: Translator,
    transport: str,
) -> None:
    """Renders transport-aware token validation and save."""

    st.markdown(
        f"#### "
        f"{t('settings.telegram.token.title')}"
    )

    st.caption(
        t(
            (
                "settings.telegram.token."
                "caption_mtproto"
            )
            if transport == "mtproto"
            else "settings.telegram.token.caption"
        )
    )

    token_version = int(
        st.session_state.get(
            TELEGRAM_TOKEN_VERSION_STATE_KEY,
            0,
        )
    )

    input_key = (
        "settings_telegram_token_input_"
        f"{token_version}"
    )

    form_key = (
        "settings_telegram_token_form_"
        f"{token_version}"
    )

    with st.form(
        form_key,
    ):
        token = st.text_input(
            t(
                "settings.telegram.token.field"
            ),
            value="",
            type="password",
            placeholder=(
                "123456789:"
                "AA..."
            ),
            help=t(
                "settings.telegram.token.help"
            ),
            key=input_key,
        )

        submitted = (
            st.form_submit_button(
                t(
                    (
                        "settings.telegram.token."
                        "save"
                    )
                ),
                type="primary",
                use_container_width=True,
            )
        )

    if not submitted:
        return

    if not token.strip():
        st.error(
            t(
                (
                    "settings.telegram.token."
                    "empty"
                )
            )
        )
        return

    try:
        with st.spinner(
            t(
                (
                    "settings.telegram.token."
                    "checking"
                )
            )
        ):
            if transport == "mtproto":
                settings = load_mtproto_settings()

                identity = asyncio.run(
                    probe_mtproto_bot(
                        token,
                        settings,
                    )
                )

                store_telegram_bot_token(
                    token
                )

                identity_state = (
                    _mtproto_identity_to_state(
                        identity
                    )
                )

                username = (
                    f"@{identity.username}"
                    if identity.username
                    else str(
                        identity.telegram_user_id
                    )
                )

            else:
                bot_api_identity = (
                    save_telegram_bot_token(
                        token
                    )
                )

                identity_state = (
                    _identity_to_state(
                        bot_api_identity
                    )
                )

                username = (
                    f"@{bot_api_identity.username}"
                    if bot_api_identity.username
                    else bot_api_identity.display_name
                )

    except (
        TelegramTokenError,
        TelegramMtprotoConfigError,
        TelegramMtprotoConnectionError,
    ) as exc:
        _show_telegram_error(
            t=t,
            error=exc,
        )
        return

    st.session_state[
        TELEGRAM_IDENTITY_STATE_KEY
    ] = identity_state

    st.session_state[
        TELEGRAM_TOKEN_MESSAGE_STATE_KEY
    ] = t(
        "settings.telegram.token.saved",
        username=username,
    )

    st.session_state.pop(
        input_key,
        None,
    )

    st.session_state[
        TELEGRAM_TOKEN_VERSION_STATE_KEY
    ] = token_version + 1

    st.rerun()


def _render_connection_check(
    *,
    t: Translator,
    transport: str,
) -> None:
    """Checks the stored bot through the configured transport."""

    check_clicked = st.button(
        t(
            (
                "settings.telegram.connection."
                "check"
            )
        ),
        use_container_width=True,
    )

    if not check_clicked:
        return

    try:
        with st.spinner(
            t(
                (
                    "settings.telegram.connection."
                    "checking"
                )
            )
        ):
            if transport == "mtproto":
                token = load_telegram_bot_token()
                settings = load_mtproto_settings()

                identity = asyncio.run(
                    probe_mtproto_bot(
                        token,
                        settings,
                    )
                )

                identity_state = (
                    _mtproto_identity_to_state(
                        identity
                    )
                )

                username = (
                    f"@{identity.username}"
                    if identity.username
                    else str(
                        identity.telegram_user_id
                    )
                )

            else:
                bot_api_identity = (
                    get_configured_bot_identity()
                )

                identity_state = (
                    _identity_to_state(
                        bot_api_identity
                    )
                )

                username = (
                    f"@{bot_api_identity.username}"
                    if bot_api_identity.username
                    else bot_api_identity.display_name
                )

    except (
        TelegramTokenError,
        TelegramMtprotoConfigError,
        TelegramMtprotoConnectionError,
    ) as exc:
        _show_telegram_error(
            t=t,
            error=exc,
        )
        return

    st.session_state[
        TELEGRAM_IDENTITY_STATE_KEY
    ] = identity_state

    st.success(
        t(
            (
                "settings.telegram.connection."
                "success"
            ),
            username=username,
        )
    )


def _render_token_deletion(
    *,
    t: Translator,
) -> None:
    """Renders double-confirmed token deletion."""

    with st.expander(
        t(
            "settings.telegram.delete.title"
        )
    ):
        st.warning(
            t(
                "settings.telegram.delete.warning"
            )
        )

        confirmed = st.checkbox(
            t(
                (
                    "settings.telegram.delete."
                    "confirm_checkbox"
                )
            ),
            key=(
                "settings_telegram_delete_"
                "confirm"
            ),
        )

        required_phrase = t(
            (
                "settings.telegram.delete."
                "confirm_phrase"
            )
        )

        entered_phrase = st.text_input(
            t(
                (
                    "settings.telegram.delete."
                    "confirm_label"
                )
            ),
            key=(
                "settings_telegram_delete_"
                "phrase"
            ),
        )

        deletion_allowed = (
            confirmed
            and entered_phrase.strip()
            == required_phrase
        )

        delete_clicked = st.button(
            t(
                "settings.telegram.delete.button"
            ),
            disabled=(
                not deletion_allowed
            ),
            use_container_width=True,
        )

        if not delete_clicked:
            return

        try:
            delete_telegram_bot_token()

        except TelegramTokenError as exc:
            _show_telegram_error(
                t=t,
                error=exc,
            )

            return

        st.session_state.pop(
            TELEGRAM_IDENTITY_STATE_KEY,
            None,
        )

        st.session_state.pop(
            (
                "settings_telegram_delete_"
                "confirm"
            ),
            None,
        )

        st.session_state.pop(
            (
                "settings_telegram_delete_"
                "phrase"
            ),
            None,
        )

        st.session_state[
            TELEGRAM_TOKEN_MESSAGE_STATE_KEY
        ] = t(
            "settings.telegram.delete.success"
        )

        current_version = int(
            st.session_state.get(
                TELEGRAM_TOKEN_VERSION_STATE_KEY,
                0,
            )
        )

        st.session_state[
            TELEGRAM_TOKEN_VERSION_STATE_KEY
        ] = current_version + 1

        st.rerun()


def _render_botfather_instructions(
    *,
    t: Translator,
) -> None:
    """Shows token creation instructions."""

    with st.expander(
        t(
            (
                "settings.telegram.instructions."
                "title"
            )
        )
    ):
        st.markdown(
            t(
                (
                    "settings.telegram.instructions."
                    "body"
                )
            )
        )

        st.warning(
            t(
                (
                    "settings.telegram.instructions."
                    "security"
                )
            )
        )


def _show_telegram_management_error(
    *,
    t: Translator,
    error: Exception,
) -> None:
    """Shows a Telegram settings repository error."""

    st.error(
        t(
            "settings.telegram.management.error"
        )
    )

    with st.expander(
        t(
            (
                "settings.telegram.management."
                "error_details"
            )
        )
    ):
        st.code(
            str(error),
            language=None,
        )


def _summary_period_label(
    *,
    t: Translator,
    period: str,
) -> str:
    """Returns a localized summary period."""

    return t(
        (
            "settings.telegram.runtime."
            f"period.{period}"
        )
    )


def _chat_type_label(
    *,
    t: Translator,
    chat_type: str,
) -> str:
    """Returns a localized Telegram chat type."""

    return t(
        (
            "settings.telegram.chats."
            f"type.{chat_type}"
        )
    )


def _store_telegram_message(
    message: str,
) -> None:
    """Stores a success message across a rerun."""

    st.session_state[
        TELEGRAM_SETTINGS_MESSAGE_STATE_KEY
    ] = message


def _render_telegram_runtime_settings(
    *,
    t: Translator,
    token_configured: bool,
) -> None:
    """Renders bot activation and summary settings."""

    settings = get_telegram_settings()

    st.subheader(
        t(
            "settings.telegram.runtime.title"
        )
    )

    st.caption(
        t(
            "settings.telegram.runtime.caption"
        )
    )

    if (
        settings.is_enabled
        and not token_configured
    ):
        st.warning(
            t(
                (
                    "settings.telegram.runtime."
                    "enabled_without_token"
                )
            )
        )

    try:
        period_index = (
            SUMMARY_PERIODS.index(
                settings.default_summary_period
            )
        )
    except ValueError:
        period_index = 0

    with st.form(
        "settings_telegram_runtime_form"
    ):
        is_enabled = st.checkbox(
            t(
                (
                    "settings.telegram.runtime."
                    "enabled"
                )
            ),
            value=settings.is_enabled,
        )

        selected_period = st.selectbox(
            t(
                (
                    "settings.telegram.runtime."
                    "period"
                )
            ),
            options=list(
                SUMMARY_PERIODS
            ),
            index=period_index,
            format_func=lambda value: (
                _summary_period_label(
                    t=t,
                    period=value,
                )
            ),
        )

        st.markdown(
            f"#### "
            f"{t('settings.telegram.runtime.sections')}"
        )

        section_columns = st.columns(
            2
        )

        with section_columns[0]:
            include_cash_flow = st.checkbox(
                t(
                    (
                        "settings.telegram.runtime."
                        "include_cash_flow"
                    )
                ),
                value=(
                    settings.include_cash_flow
                ),
            )

            include_pending_count = (
                st.checkbox(
                    t(
                        (
                            "settings.telegram."
                            "runtime."
                            "include_pending"
                        )
                    ),
                    value=(
                        settings
                        .include_pending_count
                    ),
                )
            )

        with section_columns[1]:
            include_pnl = st.checkbox(
                t(
                    (
                        "settings.telegram.runtime."
                        "include_pnl"
                    )
                ),
                value=settings.include_pnl,
            )

            include_payment_calendar = (
                st.checkbox(
                    t(
                        (
                            "settings.telegram."
                            "runtime."
                            "include_calendar"
                        )
                    ),
                    value=(
                        settings
                        .include_payment_calendar
                    ),
                )
            )

        submitted = st.form_submit_button(
            t(
                "settings.telegram.runtime.save"
            ),
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    if (
        is_enabled
        and not token_configured
    ):
        st.error(
            t(
                (
                    "settings.telegram.runtime."
                    "token_required"
                )
            )
        )

        return

    try:
        update_telegram_settings(
            is_enabled=is_enabled,
            default_summary_period=(
                selected_period
            ),
            include_cash_flow=(
                include_cash_flow
            ),
            include_pnl=include_pnl,
            include_pending_count=(
                include_pending_count
            ),
            include_payment_calendar=(
                include_payment_calendar
            ),
        )

    except ValueError as exc:
        _show_telegram_management_error(
            t=t,
            error=exc,
        )

        return

    _store_telegram_message(
        t(
            "settings.telegram.runtime.saved"
        )
    )

    st.rerun()


def _render_allowed_users(
    *,
    t: Translator,
) -> None:
    """Renders Telegram user allowlist settings."""

    st.subheader(
        t(
            "settings.telegram.users.title"
        )
    )

    st.caption(
        t(
            "settings.telegram.users.caption"
        )
    )

    with st.form(
        "settings_telegram_add_user_form",
        clear_on_submit=True,
    ):
        telegram_user_id = st.text_input(
            t(
                (
                    "settings.telegram.users."
                    "user_id"
                )
            ),
            placeholder="123456789",
            help=t(
                (
                    "settings.telegram.users."
                    "user_id_help"
                )
            ),
        )

        display_name = st.text_input(
            t(
                (
                    "settings.telegram.users."
                    "display_name"
                )
            ),
            placeholder=(
                t(
                    (
                        "settings.telegram.users."
                        "display_name_placeholder"
                    )
                )
            ),
        )

        is_active = st.checkbox(
            t(
                (
                    "settings.telegram.users."
                    "active"
                )
            ),
            value=True,
        )

        submitted = st.form_submit_button(
            t(
                "settings.telegram.users.save"
            ),
            type="primary",
            use_container_width=True,
        )

    if submitted:
        try:
            save_allowed_user(
                telegram_user_id=(
                    telegram_user_id
                ),
                display_name=display_name,
                is_active=is_active,
            )

        except ValueError as exc:
            _show_telegram_management_error(
                t=t,
                error=exc,
            )

        else:
            _store_telegram_message(
                t(
                    "settings.telegram.users.saved"
                )
            )

            st.rerun()

    users = get_allowed_users_dataframe()

    if users.empty:
        st.info(
            t(
                "settings.telegram.users.empty"
            )
        )

        return

    display_users = users.copy()

    display_users[
        "telegram_user_id"
    ] = display_users[
        "telegram_user_id"
    ].map(
        str
    )

    display_users[
        "is_active"
    ] = display_users[
        "is_active"
    ].map(
        lambda value: t(
            "common.yes"
            if bool(value)
            else "common.no"
        )
    )

    display_users = display_users.rename(
        columns={
            "id": t(
                (
                    "settings.telegram.users."
                    "columns.id"
                )
            ),
            "telegram_user_id": t(
                (
                    "settings.telegram.users."
                    "columns.user_id"
                )
            ),
            "display_name": t(
                (
                    "settings.telegram.users."
                    "columns.name"
                )
            ),
            "is_active": t(
                (
                    "settings.telegram.users."
                    "columns.active"
                )
            ),
        }
    )

    st.dataframe(
        display_users,
        hide_index=True,
        use_container_width=True,
    )

    record_ids = [
        int(value)
        for value in users["id"].tolist()
    ]

    record_labels: dict[
        int,
        str,
    ] = {}

    for row in users.to_dict(
        orient="records"
    ):
        record_id = int(
            row["id"]
        )

        name = str(
            row.get(
                "display_name"
            )
            or ""
        ).strip()

        telegram_id = str(
            row["telegram_user_id"]
        )

        record_labels[record_id] = (
            f"#{record_id} · "
            + (
                f"{name} · "
                if name
                else ""
            )
            + telegram_id
        )

    selected_record_id = st.selectbox(
        t(
            "settings.telegram.users.manage"
        ),
        options=record_ids,
        format_func=lambda value: (
            record_labels[value]
        ),
    )

    selected_row = users.loc[
        users["id"]
        == selected_record_id
    ].iloc[0]

    with st.expander(
        t(
            (
                "settings.telegram.users."
                "manage_title"
            )
        ),
        expanded=True,
    ):
        selected_active = st.checkbox(
            t(
                (
                    "settings.telegram.users."
                    "selected_active"
                )
            ),
            value=bool(
                selected_row["is_active"]
            ),
            key=(
                "settings_telegram_user_active_"
                f"{selected_record_id}"
            ),
        )

        confirm_delete = st.checkbox(
            t(
                (
                    "settings.telegram.users."
                    "confirm_delete"
                )
            ),
            key=(
                "settings_telegram_user_delete_"
                f"{selected_record_id}"
            ),
        )

        action_columns = st.columns(
            2
        )

        save_activity = (
            action_columns[0].button(
                t(
                    (
                        "settings.telegram.users."
                        "save_activity"
                    )
                ),
                use_container_width=True,
                key=(
                    "settings_telegram_user_"
                    "save_activity_"
                    f"{selected_record_id}"
                ),
            )
        )

        delete_user = (
            action_columns[1].button(
                t(
                    (
                        "settings.telegram.users."
                        "delete"
                    )
                ),
                disabled=(
                    not confirm_delete
                ),
                use_container_width=True,
                key=(
                    "settings_telegram_user_delete_"
                    "button_"
                    f"{selected_record_id}"
                ),
            )
        )

    try:
        if save_activity:
            set_allowed_user_active(
                selected_record_id,
                selected_active,
            )

            _store_telegram_message(
                t(
                    (
                        "settings.telegram.users."
                        "activity_saved"
                    )
                )
            )

            st.rerun()

        if delete_user:
            delete_allowed_user(
                selected_record_id
            )

            _store_telegram_message(
                t(
                    "settings.telegram.users.deleted"
                )
            )

            st.rerun()

    except ValueError as exc:
        _show_telegram_management_error(
            t=t,
            error=exc,
        )


def _render_allowed_chats(
    *,
    t: Translator,
) -> None:
    """Renders Telegram chat allowlist settings."""

    st.subheader(
        t(
            "settings.telegram.chats.title"
        )
    )

    st.caption(
        t(
            "settings.telegram.chats.caption"
        )
    )

    default_chat_type_index = (
        TELEGRAM_CHAT_TYPES.index(
            "supergroup"
        )
        if "supergroup"
        in TELEGRAM_CHAT_TYPES
        else 0
    )

    with st.form(
        "settings_telegram_add_chat_form",
        clear_on_submit=True,
    ):
        telegram_chat_id = st.text_input(
            t(
                (
                    "settings.telegram.chats."
                    "chat_id"
                )
            ),
            placeholder="-1001234567890",
            help=t(
                (
                    "settings.telegram.chats."
                    "chat_id_help"
                )
            ),
        )

        display_name = st.text_input(
            t(
                (
                    "settings.telegram.chats."
                    "display_name"
                )
            ),
            placeholder=(
                t(
                    (
                        "settings.telegram.chats."
                        "display_name_placeholder"
                    )
                )
            ),
        )

        chat_type = st.selectbox(
            t(
                (
                    "settings.telegram.chats."
                    "chat_type"
                )
            ),
            options=list(
                TELEGRAM_CHAT_TYPES
            ),
            index=default_chat_type_index,
            format_func=lambda value: (
                _chat_type_label(
                    t=t,
                    chat_type=value,
                )
            ),
        )

        is_active = st.checkbox(
            t(
                (
                    "settings.telegram.chats."
                    "active"
                )
            ),
            value=True,
        )

        submitted = st.form_submit_button(
            t(
                "settings.telegram.chats.save"
            ),
            type="primary",
            use_container_width=True,
        )

    if submitted:
        try:
            save_allowed_chat(
                telegram_chat_id=(
                    telegram_chat_id
                ),
                display_name=display_name,
                chat_type=chat_type,
                is_active=is_active,
            )

        except ValueError as exc:
            _show_telegram_management_error(
                t=t,
                error=exc,
            )

        else:
            _store_telegram_message(
                t(
                    "settings.telegram.chats.saved"
                )
            )

            st.rerun()

    chats = get_allowed_chats_dataframe()

    if chats.empty:
        st.info(
            t(
                "settings.telegram.chats.empty"
            )
        )

        return

    display_chats = chats.copy()

    display_chats[
        "telegram_chat_id"
    ] = display_chats[
        "telegram_chat_id"
    ].map(
        str
    )

    display_chats[
        "chat_type"
    ] = display_chats[
        "chat_type"
    ].map(
        lambda value: (
            _chat_type_label(
                t=t,
                chat_type=str(value),
            )
        )
    )

    display_chats[
        "is_active"
    ] = display_chats[
        "is_active"
    ].map(
        lambda value: t(
            "common.yes"
            if bool(value)
            else "common.no"
        )
    )

    display_chats = display_chats.rename(
        columns={
            "id": t(
                (
                    "settings.telegram.chats."
                    "columns.id"
                )
            ),
            "telegram_chat_id": t(
                (
                    "settings.telegram.chats."
                    "columns.chat_id"
                )
            ),
            "display_name": t(
                (
                    "settings.telegram.chats."
                    "columns.name"
                )
            ),
            "chat_type": t(
                (
                    "settings.telegram.chats."
                    "columns.type"
                )
            ),
            "is_active": t(
                (
                    "settings.telegram.chats."
                    "columns.active"
                )
            ),
        }
    )

    st.dataframe(
        display_chats,
        hide_index=True,
        use_container_width=True,
    )

    record_ids = [
        int(value)
        for value in chats["id"].tolist()
    ]

    record_labels: dict[
        int,
        str,
    ] = {}

    for row in chats.to_dict(
        orient="records"
    ):
        record_id = int(
            row["id"]
        )

        name = str(
            row.get(
                "display_name"
            )
            or ""
        ).strip()

        telegram_id = str(
            row["telegram_chat_id"]
        )

        record_labels[record_id] = (
            f"#{record_id} · "
            + (
                f"{name} · "
                if name
                else ""
            )
            + telegram_id
        )

    selected_record_id = st.selectbox(
        t(
            "settings.telegram.chats.manage"
        ),
        options=record_ids,
        format_func=lambda value: (
            record_labels[value]
        ),
    )

    selected_row = chats.loc[
        chats["id"]
        == selected_record_id
    ].iloc[0]

    with st.expander(
        t(
            (
                "settings.telegram.chats."
                "manage_title"
            )
        ),
        expanded=True,
    ):
        selected_active = st.checkbox(
            t(
                (
                    "settings.telegram.chats."
                    "selected_active"
                )
            ),
            value=bool(
                selected_row["is_active"]
            ),
            key=(
                "settings_telegram_chat_active_"
                f"{selected_record_id}"
            ),
        )

        confirm_delete = st.checkbox(
            t(
                (
                    "settings.telegram.chats."
                    "confirm_delete"
                )
            ),
            key=(
                "settings_telegram_chat_delete_"
                f"{selected_record_id}"
            ),
        )

        action_columns = st.columns(
            2
        )

        save_activity = (
            action_columns[0].button(
                t(
                    (
                        "settings.telegram.chats."
                        "save_activity"
                    )
                ),
                use_container_width=True,
                key=(
                    "settings_telegram_chat_"
                    "save_activity_"
                    f"{selected_record_id}"
                ),
            )
        )

        delete_chat = (
            action_columns[1].button(
                t(
                    (
                        "settings.telegram.chats."
                        "delete"
                    )
                ),
                disabled=(
                    not confirm_delete
                ),
                use_container_width=True,
                key=(
                    "settings_telegram_chat_delete_"
                    "button_"
                    f"{selected_record_id}"
                ),
            )
        )

    try:
        if save_activity:
            set_allowed_chat_active(
                selected_record_id,
                selected_active,
            )

            _store_telegram_message(
                t(
                    (
                        "settings.telegram.chats."
                        "activity_saved"
                    )
                )
            )

            st.rerun()

        if delete_chat:
            delete_allowed_chat(
                selected_record_id
            )

            _store_telegram_message(
                t(
                    "settings.telegram.chats.deleted"
                )
            )

            st.rerun()

    except ValueError as exc:
        _show_telegram_management_error(
            t=t,
            error=exc,
        )


def _render_telegram_settings(
    *,
    t: Translator,
) -> None:
    """Renders all Telegram bot settings."""

    st.subheader(
        t(
            "settings.telegram.title"
        )
    )

    st.caption(
        t(
            "settings.telegram.caption"
        )
    )

    token_message = st.session_state.pop(
        TELEGRAM_TOKEN_MESSAGE_STATE_KEY,
        None,
    )

    if token_message:
        st.success(
            token_message
        )

    settings_message = st.session_state.pop(
        TELEGRAM_SETTINGS_MESSAGE_STATE_KEY,
        None,
    )

    if settings_message:
        st.success(
            settings_message
        )

    _render_botfather_instructions(
        t=t,
    )

    transport = _render_transport_form(
        t=t,
    )

    st.divider()

    token_configured = (
        is_telegram_bot_token_configured()
    )

    _render_token_status(
        t=t,
        configured=token_configured,
    )

    identity = st.session_state.get(
        TELEGRAM_IDENTITY_STATE_KEY
    )

    if isinstance(
        identity,
        dict,
    ):
        _render_bot_identity(
            t=t,
            identity=identity,
        )

    if token_configured:
        _render_connection_check(
            t=t,
            transport=transport,
        )

    st.divider()

    _render_token_form(
        t=t,
        transport=transport,
    )

    if token_configured:
        _render_token_deletion(
            t=t,
        )

    st.divider()

    _render_telegram_runtime_settings(
        t=t,
        token_configured=token_configured,
    )

    st.divider()

    _render_allowed_users(
        t=t,
    )

    st.divider()

    _render_allowed_chats(
        t=t,
    )


def render_settings_tab(
    *,
    t: Translator,
) -> None:
    """Renders the application settings tab."""

    st.header(
        t(
            "settings.title"
        )
    )

    st.caption(
        t(
            "settings.caption"
        )
    )

    database_tab, telegram_tab = (
        st.tabs(
            [
                t(
                    "settings.sections.database"
                ),
                t(
                    "settings.sections.telegram"
                ),
            ]
        )
    )

    with database_tab:
        _render_database_settings(
            t=t,
        )

    with telegram_tab:
        _render_telegram_settings(
            t=t,
        )
