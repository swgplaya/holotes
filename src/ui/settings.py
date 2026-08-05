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


def _render_telegram_settings(
    *,
    t: Translator,
) -> None:
    """Renders the Telegram settings placeholder."""

    st.subheader(
        t(
            "settings.telegram.title"
        )
    )

    st.info(
        t(
            "settings.telegram.placeholder"
        )
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
