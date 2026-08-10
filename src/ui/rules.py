from collections.abc import Callable
from datetime import date

import pandas as pd
import streamlit as st

from src.categories import (
    CF_CATEGORIES,
    INCLUDE_ACTION,
    PNL_CATEGORIES,
    REPORT_ACTIONS,
    UNDEFINED_ACTION,
)
from src.rule_config import (
    export_rule_config_json,
    parse_rule_config_json,
)
from src.rule_repository import (
    DIRECTION_FILTERS,
    MATCH_FIELDS,
    MATCH_TYPES,
    apply_classification_rules,
    create_rule,
    delete_rule,
    get_rules_dataframe,
    import_rule_records,
    set_rule_active,
)
from src.ui.classification import (
    format_report_action,
)
from src.ui.option_formatting import (
    format_option_label,
)


Translator = Callable[..., str]


RULE_DIRECTION_TRANSLATION_KEYS = {
    "any": "rules.options.direction.any",
    "income": "rules.options.direction.income",
    "expense": "rules.options.direction.expense",
}


RULE_FIELD_TRANSLATION_KEYS = {
    "all_text":
        "rules.options.field.all_text",
    "counterparty_name":
        "rules.options.field.counterparty_name",
    "counterparty_inn":
        "rules.options.field.counterparty_inn",
    "bank_category":
        "rules.options.field.bank_category",
    "description":
        "rules.options.field.description",
    "payment_purpose":
        "rules.options.field.payment_purpose",
    "mcc":
        "rules.options.field.mcc",
    "tax_code":
        "rules.options.field.tax_code",
}


RULE_MATCH_TRANSLATION_KEYS = {
    "contains":
        "rules.options.match.contains",
    "equals":
        "rules.options.match.equals",
    "starts_with":
        "rules.options.match.starts_with",
}


def _format_rule_direction(
    value: object,
    *,
    t: Translator,
) -> str:
    """Форматирует направление правила."""

    return format_option_label(
        value,
        t=t,
        translation_keys=(
            RULE_DIRECTION_TRANSLATION_KEYS
        ),
        fallback_labels=DIRECTION_FILTERS,
    )


def _format_rule_field(
    value: object,
    *,
    t: Translator,
) -> str:
    """Форматирует поле поиска правила."""

    return format_option_label(
        value,
        t=t,
        translation_keys=(
            RULE_FIELD_TRANSLATION_KEYS
        ),
        fallback_labels=MATCH_FIELDS,
    )


def _format_rule_match_type(
    value: object,
    *,
    t: Translator,
) -> str:
    """Форматирует условие правила."""

    return format_option_label(
        value,
        t=t,
        translation_keys=(
            RULE_MATCH_TRANSLATION_KEYS
        ),
        fallback_labels=MATCH_TYPES,
    )


def _format_rule_active_status(
    value: object,
    *,
    t: Translator,
) -> str:
    """Возвращает локализованный статус активности."""

    if (
        value is not None
        and not pd.isna(value)
        and bool(value)
    ):
        return t(
            "rules.saved.values.active"
        )

    return t(
        "rules.saved.values.inactive"
    )


def render_rules_tab(
    *,
    t: Translator,
) -> None:
    """Отображает вкладку правил классификации."""

    def format_rule_direction(
        value: object,
    ) -> str:
        return _format_rule_direction(
            value,
            t=t,
        )

    def format_rule_field(
        value: object,
    ) -> str:
        return _format_rule_field(
            value,
            t=t,
        )

    def format_rule_match_type(
        value: object,
    ) -> str:
        return _format_rule_match_type(
            value,
            t=t,
        )

    def format_rule_active_status(
        value: object,
    ) -> str:
        return _format_rule_active_status(
            value,
            t=t,
        )

    st.subheader(
        t("rules.title")
    )

    st.caption(
        t("rules.caption")
    )

    if st.button(
        t("rules.apply_button"),
        type="primary",
        use_container_width=True,
    ):
        apply_result = (
            apply_classification_rules()
        )

        st.session_state["rule_message"] = t(
            "rules.messages.applied",
            checked=apply_result.checked,
            matched=apply_result.matched,
            unmatched=apply_result.unmatched,
        )

        st.rerun()

    with st.expander(
        t("rules.create_title"),
        expanded=True,
    ):
        with st.form("create_rule_form"):
            rule_name = st.text_input(
                t("rules.fields.name"),
                placeholder=t(
                    "rules.placeholders.name"
                ),
            )

            priority = st.number_input(
                t("rules.fields.priority"),
                min_value=0,
                max_value=10_000,
                value=100,
                step=10,
                help=t(
                    "rules.help.priority"
                ),
            )

            is_active = st.checkbox(
                t("rules.fields.active"),
                value=True,
            )

            direction_filter = st.selectbox(
                t("rules.fields.direction"),
                options=list(
                    DIRECTION_FILTERS
                ),
                format_func=(
                    format_rule_direction
                ),
            )

            match_field = st.selectbox(
                t("rules.fields.match_field"),
                options=list(
                    MATCH_FIELDS
                ),
                format_func=(
                    format_rule_field
                ),
            )

            match_type = st.selectbox(
                t("rules.fields.match_type"),
                options=list(
                    MATCH_TYPES
                ),
                format_func=(
                    format_rule_match_type
                ),
            )

            match_value = st.text_input(
                t("rules.fields.match_value"),
                placeholder=t(
                    "rules.placeholders."
                    "match_value"
                ),
            )

            pnl_column, cf_column = (
                st.columns(2)
            )

            with pnl_column:
                st.markdown(
                    "**"
                    + t("reports.pnl.title")
                    + "**"
                )

                pnl_action = st.selectbox(
                    t(
                        "classification.columns."
                        "pnl_action"
                    ),
                    options=list(
                        REPORT_ACTIONS
                    ),
                    format_func=lambda value: (
                        format_report_action(
                            value,
                            t=t,
                        )
                    ),
                    key="rule_pnl_action",
                )

                pnl_category = st.selectbox(
                    t(
                        "classification.columns."
                        "pnl_category"
                    ),
                    options=list(
                        PNL_CATEGORIES
                    ),
                    key="rule_pnl_category",
                )

            with cf_column:
                st.markdown(
                    "**"
                    + t(
                        "reports.cash_flow.title"
                    )
                    + "**"
                )

                cf_action = st.selectbox(
                    t(
                        "classification.columns."
                        "cf_action"
                    ),
                    options=list(
                        REPORT_ACTIONS
                    ),
                    format_func=lambda value: (
                        format_report_action(
                            value,
                            t=t,
                        )
                    ),
                    key="rule_cf_action",
                )

                cf_category = st.selectbox(
                    t(
                        "classification.columns."
                        "cf_category"
                    ),
                    options=list(
                        CF_CATEGORIES
                    ),
                    key="rule_cf_category",
                )

            create_rule_submitted = (
                st.form_submit_button(
                    t("rules.create_button"),
                    type="primary",
                    use_container_width=True,
                )
            )

            if create_rule_submitted:
                validation_errors: list[str] = []

                if not rule_name.strip():
                    validation_errors.append(
                        t(
                            "rules.errors."
                            "name_required"
                        )
                    )

                if not match_value.strip():
                    validation_errors.append(
                        t(
                            "rules.errors."
                            "match_value_required"
                        )
                    )

                if (
                    pnl_action
                    == UNDEFINED_ACTION
                    and cf_action
                    == UNDEFINED_ACTION
                ):
                    validation_errors.append(
                        t(
                            "rules.errors."
                            "decision_required"
                        )
                    )

                if (
                    pnl_action
                    == INCLUDE_ACTION
                    and not pnl_category
                ):
                    validation_errors.append(
                        t(
                            "rules.errors."
                            "pnl_category_required"
                        )
                    )

                if (
                    cf_action
                    == INCLUDE_ACTION
                    and not cf_category
                ):
                    validation_errors.append(
                        t(
                            "rules.errors."
                            "cf_category_required"
                        )
                    )

                if validation_errors:
                    for error_message in (
                        validation_errors
                    ):
                        st.error(error_message)

                else:
                    try:
                        new_rule_id = create_rule(
                            name=rule_name,
                            priority=int(priority),
                            is_active=is_active,
                            direction_filter=(
                                direction_filter
                            ),
                            match_field=match_field,
                            match_type=match_type,
                            match_value=match_value,
                            pnl_action=pnl_action,
                            pnl_category=pnl_category,
                            cf_action=cf_action,
                            cf_category=cf_category,
                        )

                    except ValueError as exc:
                        st.error(str(exc))

                    else:
                        st.session_state[
                            "rule_message"
                        ] = t(
                            "rules.messages.created",
                            rule_id=new_rule_id,
                        )

                        st.rerun()

    st.divider()

    st.subheader(
        t("rules.transfer.title")
    )

    st.caption(
        t("rules.transfer.caption")
    )

    export_json = export_rule_config_json()

    export_column, export_info_column = (
        st.columns([1, 2])
    )

    with export_column:
        st.download_button(
            t("rules.transfer.download"),
            data=export_json,
            file_name=(
                "holotes_rules_"
                f"{date.today().isoformat()}.json"
            ),
            mime="application/json",
            use_container_width=True,
            key="download_rule_config",
        )

    with export_info_column:
        st.info(
            t("rules.transfer.export_info")
        )

    uploaded_rule_config = st.file_uploader(
        t("rules.transfer.upload"),
        type=["json"],
        help=t(
            "rules.transfer.upload_help"
        ),
        key="rule_config_uploader",
    )

    if uploaded_rule_config is not None:
        try:
            parsed_rule_config = (
                parse_rule_config_json(
                    uploaded_rule_config.getvalue()
                )
            )

        except (TypeError, ValueError) as exc:
            st.error(str(exc))

        else:
            rule_preview = (
                parsed_rule_config.preview
            )

            st.markdown(
                "#### "
                + t(
                    "rules.transfer.preview_title"
                )
            )

            preview_metrics = st.columns(4)

            preview_metrics[0].metric(
                t(
                    "rules.transfer.metrics."
                    "received"
                ),
                rule_preview.received,
            )

            preview_metrics[1].metric(
                t(
                    "rules.transfer.metrics."
                    "valid"
                ),
                rule_preview.valid_unique,
            )

            preview_metrics[2].metric(
                t(
                    "rules.transfer.metrics."
                    "file_duplicates"
                ),
                rule_preview.duplicates_in_file,
            )

            preview_metrics[3].metric(
                t(
                    "rules.transfer.metrics."
                    "database_duplicates"
                ),
                rule_preview.duplicates_in_database,
            )

            st.caption(
                t(
                    "rules.transfer."
                    "preview_caption",
                    schema_version=(
                        parsed_rule_config.schema_version
                    ),
                    exported_at=(
                        parsed_rule_config.exported_at
                    ),
                )
            )

            if rule_preview.errors:
                st.error(
                    t(
                        "rules.transfer.errors."
                        "blocked"
                    )
                )

                for error_message in (
                        rule_preview.errors
                ):
                    st.error(error_message)

            if (
                    rule_preview.duplicates_in_file
                    > 0
            ):
                st.warning(
                    t(
                        "rules.transfer.warnings."
                        "file_duplicates"
                    )
                )

            if (
                    rule_preview.duplicates_in_database
                    > 0
            ):
                st.info(
                    t(
                        "rules.transfer.info."
                        "database_duplicates"
                    )
                )

            with st.expander(
                    t(
                        "rules.transfer.json_title"
                    ),
                    expanded=False,
            ):
                st.json(
                    {
                        "schema_version":
                            parsed_rule_config.schema_version,
                        "exported_at":
                            parsed_rule_config.exported_at,
                        "rules": list(
                            parsed_rule_config.records
                        ),
                    }
                )

            st.markdown(
                "#### "
                + t(
                    "rules.transfer.import_title"
                )
            )

            import_mode_options = {
                "merge": t(
                    "rules.transfer.import.merge"
                ),
                "replace": t(
                    "rules.transfer.import.replace"
                ),
            }

            import_mode = st.radio(
                t(
                    "rules.transfer.import_action"
                ),
                options=list(
                    import_mode_options
                ),
                format_func=(
                    import_mode_options.get
                ),
                horizontal=True,
                key="rule_import_mode",
            )

            if import_mode == "merge":
                st.caption(
                    t(
                        "rules.transfer.import."
                        "merge_caption"
                    )
                )

                replace_confirmation_valid = True

            else:
                st.warning(
                    t(
                        "rules.transfer.import."
                        "replace_warning"
                    )
                )

                replace_phrase = t(
                    "rules.transfer.import."
                    "replace_phrase"
                )

                replace_confirmation = (
                    st.text_input(
                        t(
                            "rules.transfer.import."
                            "confirmation"
                        ),
                        placeholder=replace_phrase,
                        key=(
                            "replace_rules_confirmation"
                        ),
                    )
                )

                replace_confirmation_valid = (
                        replace_confirmation.strip()
                        == replace_phrase
                )

            import_disabled = (
                    bool(rule_preview.errors)
                    or rule_preview.valid_unique == 0
                    or not replace_confirmation_valid
            )

            import_button_label = (
                t(
                    "rules.transfer.import."
                    "merge_button"
                )
                if import_mode == "merge"
                else t(
                    "rules.transfer.import."
                    "replace_button"
                )
            )

            if st.button(
                    import_button_label,
                    type="primary",
                    use_container_width=True,
                    disabled=import_disabled,
                    key="import_rule_config_button",
            ):
                try:
                    rule_import_result = (
                        import_rule_records(
                            list(
                                parsed_rule_config.records
                            ),
                            mode=import_mode,
                        )
                    )

                except ValueError as exc:
                    st.error(str(exc))

                else:
                    st.session_state[
                        "rule_message"
                    ] = t(
                        "rules.transfer.messages."
                        "completed",
                        received=(
                            rule_import_result.received
                        ),
                        inserted=(
                            rule_import_result.inserted
                        ),
                        skipped=(
                            rule_import_result
                            .skipped_duplicates
                        ),
                        deleted=(
                            rule_import_result
                            .deleted_existing
                        ),
                    )

                    st.rerun()

    rules = get_rules_dataframe()

    st.subheader(
        t("rules.saved.title")
    )

    if rules.empty:
        st.info(
            t("rules.saved.empty")
        )

    else:
        visible_rules = rules.copy()

        visible_rules[
            "direction_filter"
        ] = visible_rules[
            "direction_filter"
        ].apply(
            format_rule_direction
        )

        visible_rules[
            "match_field"
        ] = visible_rules[
            "match_field"
        ].apply(
            format_rule_field
        )

        visible_rules[
            "match_type"
        ] = visible_rules[
            "match_type"
        ].apply(
            format_rule_match_type
        )

        visible_rules[
            "pnl_action"
        ] = visible_rules[
            "pnl_action"
        ].apply(
            lambda value: format_report_action(
                value,
                t=t,
            )
        )

        visible_rules[
            "cf_action"
        ] = visible_rules[
            "cf_action"
        ].apply(
            lambda value: format_report_action(
                value,
                t=t,
            )
        )

        visible_rules[
            "is_active"
        ] = visible_rules[
            "is_active"
        ].apply(
            format_rule_active_status
        )

        id_column = t(
            "rules.saved.columns.id"
        )
        name_column = t(
            "rules.saved.columns.name"
        )
        priority_column = t(
            "rules.saved.columns.priority"
        )
        active_column = t(
            "rules.saved.columns.active"
        )
        direction_column = t(
            "rules.saved.columns.direction"
        )
        field_column = t(
            "rules.saved.columns.field"
        )
        condition_column = t(
            "rules.saved.columns.condition"
        )
        value_column = t(
            "rules.saved.columns.value"
        )
        pnl_action_column = t(
            "rules.saved.columns.pnl_action"
        )
        pnl_category_column = t(
            "rules.saved.columns.pnl_category"
        )
        cf_action_column = t(
            "rules.saved.columns.cf_action"
        )
        cf_category_column = t(
            "rules.saved.columns.cf_category"
        )

        visible_rules = visible_rules.rename(
            columns={
                "id": id_column,
                "name": name_column,
                "priority": priority_column,
                "is_active": active_column,
                "direction_filter":
                    direction_column,
                "match_field": field_column,
                "match_type": condition_column,
                "match_value": value_column,
                "pnl_action": pnl_action_column,
                "pnl_category":
                    pnl_category_column,
                "cf_action": cf_action_column,
                "cf_category":
                    cf_category_column,
            }
        )

        visible_rule_columns = [
            id_column,
            name_column,
            priority_column,
            active_column,
            direction_column,
            field_column,
            condition_column,
            value_column,
            pnl_action_column,
            pnl_category_column,
            cf_action_column,
            cf_category_column,
        ]

        st.dataframe(
            visible_rules[
                visible_rule_columns
            ],
            use_container_width=True,
            hide_index=True,
        )

        rule_options = {
            (
                f"{int(row['id'])} — "
                f"{row['name']}"
            ): int(row["id"])
            for _, row in rules.iterrows()
        }

        selected_rule_label = st.selectbox(
            t("rules.saved.manage"),
            options=list(rule_options),
        )

        selected_rule_id = rule_options[
            selected_rule_label
        ]

        selected_rule = rules.loc[
            rules["id"] == selected_rule_id
            ].iloc[0]

        selected_rule_active = st.checkbox(
            t("rules.fields.active"),
            value=bool(
                selected_rule["is_active"]
            ),
            key=(
                "selected_rule_active_"
                f"{selected_rule_id}"
            ),
        )

        action_column, delete_column = (
            st.columns(2)
        )

        with action_column:
            if st.button(
                    t(
                        "rules.saved."
                        "save_activity"
                    ),
                    use_container_width=True,
                    key=(
                            "save_rule_activity_"
                            f"{selected_rule_id}"
                    ),
            ):
                set_rule_active(
                    rule_id=selected_rule_id,
                    is_active=(
                        selected_rule_active
                    ),
                )

                st.session_state[
                    "rule_message"
                ] = t(
                    "rules.messages."
                    "activity_updated"
                )

                st.rerun()

        with delete_column:
            if st.button(
                    t("rules.saved.delete"),
                    type="secondary",
                    use_container_width=True,
                    key=(
                            "delete_rule_"
                            f"{selected_rule_id}"
                    ),
            ):
                delete_rule(
                    selected_rule_id
                )

                st.session_state[
                    "rule_message"
                ] = t(
                    "rules.messages.deleted"
                )

                st.rerun()
