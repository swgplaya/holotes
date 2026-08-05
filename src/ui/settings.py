from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tempfile

import streamlit as st

from src.database_backup import (
    DatabaseBackupError,
    create_database_backup,
    inspect_open_mas_database,
    resolve_sqlite_database_path,
    restore_database,
)
from src.telegram_token import (
    TelegramBotIdentity,
    TelegramTokenError,
    delete_telegram_bot_token,
    get_configured_bot_identity,
    is_telegram_bot_token_configured,
    save_telegram_bot_token,
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
        prefix="open-mas-upload-",
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
        inspect_open_mas_database(
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
            inspect_open_mas_database(
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
        t(
            "common.yes"
            if bool(
                identity.get(
                    "can_join_groups",
                    False,
                )
            )
            else "common.no"
        ),
    )

    identity_columns[2].metric(
        t(
            (
                "settings.telegram.identity."
                "reads_all_messages"
            )
        ),
        t(
            "common.yes"
            if bool(
                identity.get(
                    (
                        "can_read_all_"
                        "group_messages"
                    ),
                    False,
                )
            )
            else "common.no"
        ),
    )


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
) -> None:
    """Renders token validation and save form."""

    st.markdown(
        f"#### "
        f"{t('settings.telegram.token.title')}"
    )

    st.caption(
        t(
            "settings.telegram.token.caption"
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
            identity = (
                save_telegram_bot_token(
                    token
                )
            )

    except TelegramTokenError as exc:
        _show_telegram_error(
            t=t,
            error=exc,
        )

        return

    st.session_state[
        TELEGRAM_IDENTITY_STATE_KEY
    ] = _identity_to_state(
        identity
    )

    st.session_state[
        TELEGRAM_TOKEN_MESSAGE_STATE_KEY
    ] = t(
        (
            "settings.telegram.token."
            "saved"
        ),
        username=(
            f"@{identity.username}"
            if identity.username
            else identity.display_name
        ),
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
) -> None:
    """Checks the stored token through getMe."""

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
            identity = (
                get_configured_bot_identity()
            )

    except TelegramTokenError as exc:
        _show_telegram_error(
            t=t,
            error=exc,
        )

        return

    st.session_state[
        TELEGRAM_IDENTITY_STATE_KEY
    ] = _identity_to_state(
        identity
    )

    st.success(
        t(
            (
                "settings.telegram.connection."
                "success"
            ),
            username=(
                f"@{identity.username}"
                if identity.username
                else identity.display_name
            ),
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


def _render_telegram_settings(
    *,
    t: Translator,
) -> None:
    """Renders Telegram bot token settings."""

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

    message = st.session_state.pop(
        TELEGRAM_TOKEN_MESSAGE_STATE_KEY,
        None,
    )

    if message:
        st.success(
            message
        )

    _render_botfather_instructions(
        t=t,
    )

    configured = (
        is_telegram_bot_token_configured()
    )

    _render_token_status(
        t=t,
        configured=configured,
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

    if configured:
        _render_connection_check(
            t=t,
        )

    st.divider()

    _render_token_form(
        t=t,
    )

    if configured:
        st.divider()

        _render_token_deletion(
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
