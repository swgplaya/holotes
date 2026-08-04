from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from html import escape

import pandas as pd
import streamlit as st
import plotly.express as px

from src.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    translate,
)

from src.categories import (
    CF_CATEGORIES,
)

from src.database import init_db
from src.ui.operations import (
    render_operations_tab,
)
from src.ui.classification import (
    render_classification_tab,
)
from src.ui.option_formatting import (
    format_option_label,
)
from src.ui.rules import (
    render_rules_tab,
)
from src.ui.reports import (
    render_cash_flow_tab,
    render_pnl_tab,
)
from src.ui.imports import (
    render_import_tab,
)
from src.payment_calendar import (
    DIRECTION_LABELS,
    RECURRENCE_LABELS,
    build_cash_forecast,
    create_planned_cash_flow,
    delete_planned_cash_flow,
    expand_planned_cash_flows,
    get_planned_cash_flows_dataframe,
    set_planned_cash_flow_active,
)

from src.unit_economics import (
    COST_TYPE_LABELS,
    PRICING_METHOD_LABELS,
    build_unit_economics_summary,
    create_unit_economics_cost_item,
    create_unit_economics_product,
    delete_unit_economics_cost_item,
    delete_unit_economics_product,
    get_unit_economics_cost_items_dataframe,
    get_unit_economics_products_dataframe,
    set_unit_economics_cost_item_active,
    set_unit_economics_product_active,
    update_unit_economics_pricing,
)

st.set_page_config(
    page_title="Open MAS",
    page_icon="📊",
    layout="wide",
)

APP_ROOT = Path(__file__).resolve().parent

st.html(
    APP_ROOT / "assets" / "styles.css"
)

init_db()

LANGUAGE_STATE_KEY = "ui_language"
MAIN_NAVIGATION_KEY = "main_navigation"

MAIN_TAB_TRANSLATION_KEYS = (
    "tabs.operations",
    "tabs.classification",
    "tabs.rules",
    "tabs.pnl",
    "tabs.cash_flow",
    "tabs.unit_economics",
    "tabs.payment_calendar",
    "tabs.import",
)


def t(
    key: str,
    **values: object,
) -> str:
    """Возвращает перевод для текущего языка."""

    return translate(
        key=key,
        language=st.session_state.get(
            LANGUAGE_STATE_KEY,
            DEFAULT_LANGUAGE,
        ),
        **values,
    )

def sync_main_navigation_language() -> None:
    """Сохраняет активный раздел при смене языка."""

    active_label = st.session_state.get(
        MAIN_NAVIGATION_KEY
    )

    if active_label is None:
        return

    active_translation_key = None

    for translation_key in MAIN_TAB_TRANSLATION_KEYS:
        for language in SUPPORTED_LANGUAGES:
            translated_label = translate(
                key=translation_key,
                language=language,
            )

            if translated_label == active_label:
                active_translation_key = translation_key
                break

        if active_translation_key is not None:
            break

    if active_translation_key is None:
        return

    new_language = st.session_state.get(
        LANGUAGE_STATE_KEY,
        DEFAULT_LANGUAGE,
    )

    st.session_state[MAIN_NAVIGATION_KEY] = translate(
        key=active_translation_key,
        language=new_language,
    )

def format_rubles(kopecks: int) -> str:
    """Форматирует копейки в российский денежный формат."""

    amount = Decimal(int(kopecks)) / Decimal("100")
    formatted = f"{amount:,.2f}"

    formatted = (
        formatted
        .replace(",", " ")
        .replace(".", ",")
    )

    return f"{formatted} ₽"

def rubles_to_kopecks(value: float) -> int:
    """Безопасно преобразует рубли в копейки."""

    amount = Decimal(str(value))

    kopecks = (
        amount * Decimal("100")
    ).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )

    return int(kopecks)

def percent_to_basis_points(
    value: float,
) -> int:
    """Преобразует проценты в базисные пункты."""

    basis_points = (
        Decimal(str(value))
        * Decimal("100")
    ).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )

    return int(basis_points)

UNIT_COST_TYPE_TRANSLATION_KEYS = {
    "fixed_per_unit": "unit.cost_type.fixed_per_unit",
    "fixed_period": "unit.cost_type.fixed_period",
    "percent_of_price": "unit.cost_type.percent_of_price",
    "percent_of_revenue": "unit.cost_type.percent_of_revenue",
}

UNIT_PRICING_METHOD_TRANSLATION_KEYS = {
    "not_set": "unit.pricing_method.not_set",
    "manual": "unit.pricing_method.manual",
    "markup": "unit.pricing_method.markup",
    "target_margin": "unit.pricing_method.target_margin",
}

CALENDAR_DIRECTION_TRANSLATION_KEYS = {
    "inflow": "calendar.direction.inflow",
    "outflow": "calendar.direction.outflow",
}

CALENDAR_RECURRENCE_TRANSLATION_KEYS = {
    "once": "calendar.recurrence.once",
    "monthly": "calendar.recurrence.monthly",
    "yearly": "calendar.recurrence.yearly",
}

UNIT_PRICING_ERROR_TRANSLATION_KEYS = {
    "Способ ценообразования не выбран.":
        "unit.pricing_error.not_set",
    "Не указана ручная цена.":
        "unit.pricing_error.manual_missing",
    "Не указана наценка.":
        "unit.pricing_error.markup_missing",
    "Сумма процентных расходов должна быть меньше 100%.":
        "unit.pricing_error.percentage_too_high",
    "Не указана целевая маржинальность.":
        "unit.pricing_error.margin_missing",
    (
        "Процентные расходы и целевая маржинальность "
        "вместе должны быть меньше 100%."
    ): "unit.pricing_error.margin_total_too_high",
    "Неизвестный способ ценообразования.":
        "unit.pricing_error.unknown_method",
}


def format_unit_cost_type(value: object) -> str:
    """Возвращает локализованный тип затрат."""

    return format_option_label(
        value,
        t=t,
        translation_keys=(
            UNIT_COST_TYPE_TRANSLATION_KEYS
        ),
        fallback_labels=COST_TYPE_LABELS,
    )


def format_unit_pricing_method(value: object) -> str:
    """Возвращает локализованный способ ценообразования."""

    return format_option_label(
        value,
        t=t,
        translation_keys=(
            UNIT_PRICING_METHOD_TRANSLATION_KEYS
        ),
        fallback_labels=PRICING_METHOD_LABELS,
    )


def format_calendar_direction(value: object) -> str:
    """Возвращает локализованное направление платежа."""

    return format_option_label(
        value,
        t=t,
        translation_keys=(
            CALENDAR_DIRECTION_TRANSLATION_KEYS
        ),
        fallback_labels=DIRECTION_LABELS,
    )


def format_calendar_recurrence(value: object) -> str:
    """Возвращает локализованную периодичность."""

    return format_option_label(
        value,
        t=t,
        translation_keys=(
            CALENDAR_RECURRENCE_TRANSLATION_KEYS
        ),
        fallback_labels=RECURRENCE_LABELS,
    )


def format_boolean_status(value: object) -> str:
    """Возвращает локализованный логический статус."""

    if (
        value is not None
        and not pd.isna(value)
        and bool(value)
    ):
        return t("common.yes")

    return t("common.no")


def localize_unit_pricing_error(value: object) -> str:
    """Локализует известную ошибку расчёта цены."""

    message = text_or_empty(value)
    translation_key = (
        UNIT_PRICING_ERROR_TRANSLATION_KEYS.get(
            message
        )
    )

    if translation_key is not None:
        return t(translation_key)

    return message


def text_or_empty(value: object) -> str:
    """Преобразует пустое значение базы в пустую строку."""

    if value is None or pd.isna(value):
        return ""

    return str(value).strip()

if LANGUAGE_STATE_KEY not in st.session_state:
    st.session_state[
        LANGUAGE_STATE_KEY
    ] = DEFAULT_LANGUAGE


_, language_column = st.columns(
    [5, 1],
    vertical_alignment="center",
)

with language_column:
    st.selectbox(
        t("language.selector"),
        options=list(SUPPORTED_LANGUAGES),
        format_func=SUPPORTED_LANGUAGES.get,
        key=LANGUAGE_STATE_KEY,
        on_change=sync_main_navigation_language,
        label_visibility="collapsed",
    )


hero_eyebrow = escape(
    t("app.eyebrow")
)

hero_description = escape(
    t("app.description")
)

hero_badge = escape(
    t("app.badge")
)


st.html(
    f"""
    <section class="openmas-hero">
        <div class="openmas-hero__content">
            <div class="openmas-hero__eyebrow">
                {hero_eyebrow}
            </div>

            <h1 class="openmas-hero__title">
                Open MAS
            </h1>

            <p class="openmas-hero__description">
                {hero_description}
            </p>
        </div>

        <div class="openmas-hero__badge">
            {hero_badge}
        </div>
    </section>
    """
)


last_import_message = st.session_state.pop(
    "last_import_message",
    None,
)

if last_import_message:
    st.success(last_import_message)

(
    operations_tab,
    classification_tab,
    rules_tab,
    pnl_tab,
    cash_flow_tab,
    unit_economics_tab,
    payment_calendar_tab,
    import_tab,
) = st.tabs(
    [
        t(translation_key)
        for translation_key in MAIN_TAB_TRANSLATION_KEYS
    ],
    key=MAIN_NAVIGATION_KEY,
    on_change="rerun",
)

classification_message = st.session_state.pop(
    "classification_message",
    None,
)

if classification_message:
    st.success(classification_message)

unit_economics_message = st.session_state.pop(
    "unit_economics_message",
    None,
)

if unit_economics_message:
    st.success(unit_economics_message)

calendar_message = st.session_state.pop(
    "calendar_message",
    None,
)

if calendar_message:
    st.success(calendar_message)

rule_message = st.session_state.pop(
    "rule_message",
    None,
)

if rule_message:
    st.success(rule_message)

if operations_tab.open:
    with operations_tab:
        render_operations_tab(
            t=t,
            format_rubles=format_rubles,
        )

if classification_tab.open:
    with classification_tab:
        render_classification_tab(
            t=t,
            format_rubles=format_rubles,
        )

if rules_tab.open:
    with rules_tab:
        render_rules_tab(
            t=t,
        )

if pnl_tab.open:
    with pnl_tab:
        render_pnl_tab(
            t=t,
            format_rubles=format_rubles,
        )

if cash_flow_tab.open:
    with cash_flow_tab:
        render_cash_flow_tab(
            t=t,
            format_rubles=format_rubles,
        )

if unit_economics_tab.open:
    with unit_economics_tab:
        st.subheader(t("unit.title"))

        st.caption(t("unit.caption"))

        with st.expander(
            t("unit.product.add_title"),
            expanded=True,
        ):
            with st.form(
                "create_unit_economics_product_form",
                clear_on_submit=True,
            ):
                product_name = st.text_input(
                    t("unit.product.name"),
                    placeholder=t(
                        "unit.product.name_placeholder"
                    ),
                )

                planned_units = st.number_input(
                    t("unit.product.planned_units"),
                    min_value=1,
                    value=100,
                    step=1,
                )

                product_is_active = st.checkbox(
                    t("unit.product.active"),
                    value=True,
                )

                product_comment = st.text_area(
                    t("unit.product.comment"),
                    max_chars=500,
                )

                product_submitted = st.form_submit_button(
                    t("unit.product.add_button"),
                    type="primary",
                    use_container_width=True,
                )

                if product_submitted:
                    try:
                        product_id = (
                            create_unit_economics_product(
                                name=product_name,
                                planned_units=int(
                                    planned_units
                                ),
                                is_active=product_is_active,
                                comment=product_comment,
                            )
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.session_state[
                            "unit_economics_message"
                        ] = t(
                            "unit.product.added",
                            product_id=product_id,
                        )

                        st.rerun()

        products = (
            get_unit_economics_products_dataframe()
        )

        cost_items = (
            get_unit_economics_cost_items_dataframe()
        )

        if products.empty:
            st.info(t("unit.product.empty"))
        else:
            product_options = {
                (
                    f"{int(row['id'])} — "
                    f"{row['name']}"
                ): int(row["id"])
                for _, row in products.iterrows()
            }

            selected_product_label = st.selectbox(
                t("unit.product.select"),
                options=list(product_options),
                key="unit_economics_selected_product",
            )

            selected_product_id = product_options[
                selected_product_label
            ]

            selected_product = products.loc[
                products["id"] == selected_product_id
            ].iloc[0]

            st.subheader(
                t(
                    "unit.costs.title",
                    product_name=selected_product["name"],
                )
            )

            with st.form(
                f"create_cost_item_form_"
                f"{selected_product_id}",
                clear_on_submit=True,
            ):
                cost_name = st.text_input(
                    t("unit.cost.name"),
                    placeholder=t(
                        "unit.cost.name_placeholder"
                    ),
                )

                calculation_type = st.selectbox(
                    t("unit.cost.type"),
                    options=list(COST_TYPE_LABELS),
                    format_func=format_unit_cost_type,
                )

                cost_amount_rubles: float | None
                percentage_value: float | None

                if calculation_type in {
                    "fixed_per_unit",
                    "fixed_period",
                }:
                    cost_amount_rubles = st.number_input(
                        t("common.amount_rub"),
                        min_value=0.00,
                        value=100.00,
                        step=10.00,
                        format="%.2f",
                    )

                    percentage_value = None

                else:
                    percentage_value = st.number_input(
                        t("common.percent"),
                        min_value=0.00,
                        max_value=99.99,
                        value=2.50,
                        step=0.10,
                        format="%.2f",
                    )

                    cost_amount_rubles = None

                cost_is_active = st.checkbox(
                    t("unit.cost.active"),
                    value=True,
                )

                cost_comment = st.text_area(
                    t("unit.cost.comment"),
                    max_chars=500,
                )

                cost_submitted = st.form_submit_button(
                    t("unit.cost.add_button"),
                    type="primary",
                    use_container_width=True,
                )

                if cost_submitted:
                    try:
                        cost_item_id = (
                            create_unit_economics_cost_item(
                                product_id=selected_product_id,
                                name=cost_name,
                                calculation_type=calculation_type,
                                amount_kopecks=(
                                    rubles_to_kopecks(
                                        cost_amount_rubles
                                    )
                                    if cost_amount_rubles
                                    is not None
                                    else None
                                ),
                                percentage_bp=(
                                    percent_to_basis_points(
                                        percentage_value
                                    )
                                    if percentage_value
                                    is not None
                                    else None
                                ),
                                is_active=cost_is_active,
                                comment=cost_comment,
                            )
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.session_state[
                            "unit_economics_message"
                        ] = t(
                            "unit.cost.added",
                            cost_id=cost_item_id,
                        )

                        st.rerun()

            selected_cost_items = cost_items.loc[
                cost_items["product_id"]
                == selected_product_id
            ].copy()

            if selected_cost_items.empty:
                st.info(t("unit.cost.empty"))
            else:
                visible_cost_items = (
                    selected_cost_items.copy()
                )

                id_column = t("common.id")
                item_column = t(
                    "unit.cost.item_column"
                )
                type_column = t("unit.cost.type")
                amount_column = t("common.amount_rub")
                percent_column = t("common.percent")
                active_column = t("common.active")
                comment_column = t("common.comment")

                visible_cost_items[type_column] = (
                    visible_cost_items[
                        "calculation_type"
                    ].apply(format_unit_cost_type)
                )

                visible_cost_items[amount_column] = (
                    pd.to_numeric(
                        visible_cost_items[
                            "amount_kopecks"
                        ],
                        errors="coerce",
                    ) / 100
                )

                visible_cost_items[percent_column] = (
                    pd.to_numeric(
                        visible_cost_items[
                            "percentage_bp"
                        ],
                        errors="coerce",
                    ) / 100
                )

                visible_cost_items[active_column] = (
                    visible_cost_items[
                        "is_active"
                    ].apply(format_boolean_status)
                )

                visible_cost_items = (
                    visible_cost_items.rename(
                        columns={
                            "id": id_column,
                            "name": item_column,
                            "comment": comment_column,
                        }
                    )
                )

                st.dataframe(
                    visible_cost_items[
                        [
                            id_column,
                            item_column,
                            type_column,
                            amount_column,
                            percent_column,
                            active_column,
                            comment_column,
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        amount_column:
                            st.column_config.NumberColumn(
                                amount_column,
                                format="%.2f",
                            ),
                        percent_column:
                            st.column_config.NumberColumn(
                                percent_column,
                                format="%.2f%%",
                            ),
                    },
                )

                cost_item_options = {
                    (
                        f"{int(row['id'])} — "
                        f"{row['name']}"
                    ): int(row["id"])
                    for _, row
                    in selected_cost_items.iterrows()
                }

                selected_cost_item_label = (
                    st.selectbox(
                        t("unit.cost.select_manage"),
                        options=list(cost_item_options),
                        key=(
                            "selected_unit_cost_item_"
                            f"{selected_product_id}"
                        ),
                    )
                )

                selected_cost_item_id = (
                    cost_item_options[
                        selected_cost_item_label
                    ]
                )

                selected_cost_item = (
                    selected_cost_items.loc[
                        selected_cost_items["id"]
                        == selected_cost_item_id
                    ].iloc[0]
                )

                selected_cost_item_active = (
                    st.checkbox(
                        t("unit.cost.active"),
                        value=bool(
                            selected_cost_item[
                                "is_active"
                            ]
                        ),
                        key=(
                            "unit_cost_active_"
                            f"{selected_cost_item_id}"
                        ),
                    )
                )

                cost_active_column, cost_delete_column = (
                    st.columns(2)
                )

                with cost_active_column:
                    if st.button(
                        t("unit.cost.save_activity"),
                        use_container_width=True,
                        key=(
                            "save_unit_cost_activity_"
                            f"{selected_cost_item_id}"
                        ),
                    ):
                        set_unit_economics_cost_item_active(
                            cost_item_id=(
                                selected_cost_item_id
                            ),
                            is_active=(
                                selected_cost_item_active
                            ),
                        )

                        st.session_state[
                            "unit_economics_message"
                        ] = t(
                            "unit.cost.activity_updated"
                        )
                        st.rerun()

                with cost_delete_column:
                    if st.button(
                        t("unit.cost.delete"),
                        use_container_width=True,
                        key=(
                            "delete_unit_cost_"
                            f"{selected_cost_item_id}"
                        ),
                    ):
                        delete_unit_economics_cost_item(
                            selected_cost_item_id
                        )

                        st.session_state[
                            "unit_economics_message"
                        ] = t("unit.cost.deleted")
                        st.rerun()

            st.subheader(t("unit.pricing.title"))

            pricing_options = [
                "manual",
                "markup",
                "target_margin",
            ]

            stored_method = str(
                selected_product["pricing_method"]
            )

            default_pricing_index = (
                pricing_options.index(stored_method)
                if stored_method in pricing_options
                else 2
            )

            pricing_method = st.selectbox(
                t("unit.pricing.method"),
                options=pricing_options,
                index=default_pricing_index,
                format_func=format_unit_pricing_method,
                key=f"pricing_method_{selected_product_id}",
            )

            manual_price_rubles = None
            pricing_percent = None

            if pricing_method == "manual":
                stored_manual_price = (
                    selected_product[
                        "manual_price_kopecks"
                    ]
                )

                manual_price_rubles = st.number_input(
                    t("unit.pricing.manual_price"),
                    min_value=0.01,
                    value=(
                        float(stored_manual_price) / 100
                        if not pd.isna(stored_manual_price)
                        else 1_000.00
                    ),
                    step=100.00,
                    format="%.2f",
                    key=f"manual_price_{selected_product_id}",
                )

            else:
                stored_pricing_value = (
                    selected_product["pricing_value_bp"]
                )

                pricing_percent = st.number_input(
                    (
                        t("unit.pricing.markup")
                        if pricing_method == "markup"
                        else t(
                            "unit.pricing.target_margin"
                        )
                    ),
                    min_value=0.00,
                    max_value=99.99,
                    value=(
                        float(stored_pricing_value) / 100
                        if not pd.isna(stored_pricing_value)
                        else 35.00
                    ),
                    step=1.00,
                    format="%.2f",
                    key=f"pricing_percent_{selected_product_id}",
                )

            stored_rounding_step = int(
                selected_product["rounding_step_kopecks"]
            )

            rounding_step_rubles = st.number_input(
                t("unit.pricing.rounding"),
                min_value=1.00,
                value=float(stored_rounding_step) / 100,
                step=10.00,
                format="%.2f",
                key=f"rounding_step_{selected_product_id}",
            )

            if st.button(
                t("unit.pricing.save"),
                type="primary",
                use_container_width=True,
                key=f"save_pricing_{selected_product_id}",
            ):
                try:
                    update_unit_economics_pricing(
                        product_id=selected_product_id,
                        pricing_method=pricing_method,
                        pricing_value_bp=(
                            percent_to_basis_points(
                                pricing_percent
                            )
                            if pricing_percent is not None
                            else None
                        ),
                        manual_price_kopecks=(
                            rubles_to_kopecks(
                                manual_price_rubles
                            )
                            if manual_price_rubles is not None
                            else None
                        ),
                        rounding_step_kopecks=(
                            rubles_to_kopecks(
                                rounding_step_rubles
                            )
                        ),
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state[
                        "unit_economics_message"
                    ] = t("unit.pricing.saved")

                    st.rerun()

            st.divider()
            st.subheader(t("unit.calculation.title"))

            summary = build_unit_economics_summary(
                products=products,
                cost_items=cost_items,
            )

            selected_summary = summary.loc[
                summary["product_id"] == selected_product_id
            ]

            if selected_summary.empty:
                st.warning(
                    t("unit.calculation.inactive")
                )
            else:
                result = selected_summary.iloc[0]

                base_metrics = st.columns(4)

                base_metrics[0].metric(
                    t("unit.metrics.fixed_per_unit"),
                    format_rubles(
                        int(result["fixed_per_unit_kopecks"])
                    ),
                )

                base_metrics[1].metric(
                    t("unit.metrics.allocated_period"),
                    format_rubles(
                        int(
                            result[
                                "allocated_period_per_unit_kopecks"
                            ]
                        )
                    ),
                )

                base_metrics[2].metric(
                    t("unit.metrics.base_cost"),
                    format_rubles(
                        int(
                            result[
                                "base_cost_per_unit_kopecks"
                            ]
                        )
                    ),
                )

                base_metrics[3].metric(
                    t("unit.metrics.percentage_rate"),
                    (
                        f"{float(result['percentage_cost_rate']):.2f}%"
                    ),
                )

                pricing_error = result["pricing_error"]

                if (
                    pricing_error is not None
                    and not pd.isna(pricing_error)
                    and str(pricing_error).strip()
                ):
                    st.warning(
                        localize_unit_pricing_error(
                            pricing_error
                        )
                    )

                    st.info(
                        t("unit.calculation.setup_hint")
                    )

                else:
                    selling_price = int(
                        result["selling_price_kopecks"]
                    )

                    percentage_cost_per_unit = int(
                        result[
                            "percentage_cost_per_unit_kopecks"
                        ]
                    )

                    total_cost_per_unit = int(
                        result["total_cost_per_unit_kopecks"]
                    )

                    profit_per_unit = int(
                        result["profit_per_unit_kopecks"]
                    )

                    price_metrics = st.columns(4)

                    price_metrics[0].metric(
                        t("unit.metrics.selling_price"),
                        format_rubles(selling_price),
                    )

                    price_metrics[1].metric(
                        t(
                            "unit.metrics.percentage_per_unit"
                        ),
                        format_rubles(
                            percentage_cost_per_unit
                        ),
                    )

                    price_metrics[2].metric(
                        t("unit.metrics.total_cost"),
                        format_rubles(total_cost_per_unit),
                    )

                    price_metrics[3].metric(
                        t("unit.metrics.profit_per_unit"),
                        format_rubles(profit_per_unit),
                    )

                    margin_percent = result["margin_percent"]

                    if (
                        margin_percent is None
                        or pd.isna(margin_percent)
                    ):
                        margin_text = t(
                            "common.not_calculated"
                        )
                    else:
                        margin_text = (
                            f"{float(margin_percent):.1f}%"
                        )

                    break_even_units = result[
                        "break_even_units"
                    ]

                    if (
                        break_even_units is None
                        or pd.isna(break_even_units)
                    ):
                        break_even_text = t(
                            "common.not_calculated"
                        )
                    else:
                        break_even_text = t(
                            "common.units_short",
                            count=int(break_even_units),
                        )

                    st.write(
                        f"**{t('unit.details.sales_plan')}:** "
                        + t(
                            "common.units_short",
                            count=int(result["planned_units"]),
                        )
                    )

                    st.write(
                        f"**{t('unit.details.revenue')}:** "
                        f"{format_rubles(int(result['revenue_kopecks']))}"
                    )

                    st.write(
                        f"**{t('unit.details.total_batch_cost')}:** "
                        f"{format_rubles(int(result['total_cost_kopecks']))}"
                    )

                    st.write(
                        f"**{t('unit.details.batch_result')}:** "
                        f"{format_rubles(int(result['operating_result_kopecks']))}"
                    )

                    st.write(
                        f"**{t('unit.details.margin')}:** "
                        f"{margin_text}"
                    )

                    st.write(
                        f"**{t('unit.details.break_even')}:** "
                        f"{break_even_text}"
                    )

                    metric_column = t("unit.chart.metric")
                    amount_column = t("common.amount_rub")

                    chart_data = pd.DataFrame(
                        {
                            metric_column: [
                                t("unit.chart.price"),
                                t("unit.chart.base_cost"),
                                t(
                                    "unit.chart.percentage_cost"
                                ),
                                t("unit.chart.profit"),
                            ],
                            amount_column: [
                                selling_price / 100,
                                int(
                                    result[
                                        "base_cost_per_unit_kopecks"
                                    ]
                                ) / 100,
                                percentage_cost_per_unit / 100,
                                profit_per_unit / 100,
                            ],
                        }
                    )

                    unit_chart = px.bar(
                        chart_data,
                        x=metric_column,
                        y=amount_column,
                        text_auto=".2s",
                    )

                    unit_chart.update_layout(
                        xaxis_title="",
                        yaxis_title=amount_column,
                    )

                    st.plotly_chart(
                        unit_chart,
                        use_container_width=True,
                    )

            st.divider()
            st.subheader(t("unit.management.title"))

            selected_product_active = st.checkbox(
                t("unit.product.active"),
                value=bool(
                    selected_product["is_active"]
                ),
                key=(
                    "unit_product_active_"
                    f"{selected_product_id}"
                ),
            )

            product_active_column, product_delete_column = (
                st.columns(2)
            )

            with product_active_column:
                if st.button(
                    t("unit.management.save_activity"),
                    use_container_width=True,
                    key=(
                        "save_unit_product_activity_"
                        f"{selected_product_id}"
                    ),
                ):
                    set_unit_economics_product_active(
                        product_id=selected_product_id,
                        is_active=selected_product_active,
                    )

                    st.session_state[
                        "unit_economics_message"
                    ] = t(
                        "unit.management.activity_updated"
                    )
                    st.rerun()

            with product_delete_column:
                if st.button(
                    t("unit.management.delete"),
                    use_container_width=True,
                    key=(
                        "delete_unit_product_"
                        f"{selected_product_id}"
                    ),
                ):
                    delete_unit_economics_product(
                        selected_product_id
                    )

                    st.session_state[
                        "unit_economics_message"
                    ] = t("unit.management.deleted")
                    st.rerun()

            st.divider()
            st.subheader(t("unit.summary.title"))

            if summary.empty:
                st.info(t("unit.summary.empty"))
            else:
                visible_summary = summary.copy()

                product_column = t("unit.summary.product")
                plan_column = t("unit.summary.plan_units")
                pricing_method_column = t(
                    "unit.summary.pricing_method"
                )
                fixed_column = t(
                    "unit.summary.fixed_per_unit"
                )
                period_column = t(
                    "unit.summary.allocated_period"
                )
                base_cost_column = t(
                    "unit.summary.base_cost"
                )
                percentage_rate_column = t(
                    "unit.summary.percentage_rate"
                )
                selling_price_column = t(
                    "unit.summary.selling_price"
                )
                percentage_unit_column = t(
                    "unit.summary.percentage_per_unit"
                )
                total_cost_column = t(
                    "unit.summary.total_cost"
                )
                profit_column = t(
                    "unit.summary.profit_per_unit"
                )
                margin_column = t("unit.summary.margin")
                revenue_column = t("unit.summary.revenue")
                batch_result_column = t(
                    "unit.summary.batch_result"
                )
                break_even_column = t(
                    "unit.summary.break_even"
                )
                status_column = t("unit.summary.status")

                visible_summary[pricing_method_column] = (
                    visible_summary[
                        "pricing_method"
                    ].apply(format_unit_pricing_method)
                )

                money_columns = {
                    "fixed_per_unit_kopecks":
                        fixed_column,
                    "allocated_period_per_unit_kopecks":
                        period_column,
                    "base_cost_per_unit_kopecks":
                        base_cost_column,
                    "selling_price_kopecks":
                        selling_price_column,
                    "percentage_cost_per_unit_kopecks":
                        percentage_unit_column,
                    "total_cost_per_unit_kopecks":
                        total_cost_column,
                    "profit_per_unit_kopecks":
                        profit_column,
                    "revenue_kopecks":
                        revenue_column,
                    "operating_result_kopecks":
                        batch_result_column,
                }

                for source_column, visible_column in (
                    money_columns.items()
                ):
                    visible_summary[visible_column] = (
                        pd.to_numeric(
                            visible_summary[source_column],
                            errors="coerce",
                        ) / 100
                    )

                visible_summary[margin_column] = (
                    pd.to_numeric(
                        visible_summary["margin_percent"],
                        errors="coerce",
                    )
                )

                visible_summary[
                    percentage_rate_column
                ] = pd.to_numeric(
                    visible_summary[
                        "percentage_cost_rate"
                    ],
                    errors="coerce",
                )

                visible_summary[
                    break_even_column
                ] = pd.to_numeric(
                    visible_summary["break_even_units"],
                    errors="coerce",
                )

                visible_summary[status_column] = (
                    visible_summary["pricing_error"]
                    .apply(
                        lambda value: (
                            t("unit.summary.status_ok")
                            if not text_or_empty(value)
                            else localize_unit_pricing_error(
                                value
                            )
                        )
                    )
                )

                visible_summary = visible_summary.rename(
                    columns={
                        "product_name": product_column,
                        "planned_units": plan_column,
                    }
                )

                summary_columns = [
                    product_column,
                    plan_column,
                    pricing_method_column,
                    fixed_column,
                    period_column,
                    base_cost_column,
                    percentage_rate_column,
                    selling_price_column,
                    total_cost_column,
                    profit_column,
                    margin_column,
                    revenue_column,
                    batch_result_column,
                    break_even_column,
                    status_column,
                ]

                st.dataframe(
                    visible_summary[summary_columns],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        fixed_column:
                            st.column_config.NumberColumn(
                                fixed_column,
                                format="%.2f",
                            ),
                        period_column:
                            st.column_config.NumberColumn(
                                period_column,
                                format="%.2f",
                            ),
                        base_cost_column:
                            st.column_config.NumberColumn(
                                base_cost_column,
                                format="%.2f",
                            ),
                        percentage_rate_column:
                            st.column_config.NumberColumn(
                                percentage_rate_column,
                                format="%.2f%%",
                            ),
                        selling_price_column:
                            st.column_config.NumberColumn(
                                selling_price_column,
                                format="%.2f",
                            ),
                        total_cost_column:
                            st.column_config.NumberColumn(
                                total_cost_column,
                                format="%.2f",
                            ),
                        profit_column:
                            st.column_config.NumberColumn(
                                profit_column,
                                format="%.2f",
                            ),
                        margin_column:
                            st.column_config.NumberColumn(
                                margin_column,
                                format="%.1f%%",
                            ),
                        revenue_column:
                            st.column_config.NumberColumn(
                                revenue_column,
                                format="%.2f",
                            ),
                        batch_result_column:
                            st.column_config.NumberColumn(
                                batch_result_column,
                                format="%.2f",
                            ),
                        break_even_column:
                            st.column_config.NumberColumn(
                                break_even_column,
                                format="%d",
                            ),
                    },
                )

if payment_calendar_tab.open:
    with payment_calendar_tab:
        st.subheader(t("calendar.title"))

        st.caption(t("calendar.caption"))

        with st.expander(
            t("calendar.add_title"),
            expanded=True,
        ):
            with st.form(
                "planned_cash_flow_form",
                clear_on_submit=True,
            ):
                plan_name = st.text_input(
                    t("calendar.fields.name"),
                    placeholder=t(
                        "calendar.placeholders.name"
                    ),
                )

                direction = st.selectbox(
                    t("calendar.fields.direction"),
                    options=list(DIRECTION_LABELS),
                    format_func=format_calendar_direction,
                )

                amount_rubles = st.number_input(
                    t("calendar.fields.amount"),
                    min_value=0.01,
                    value=1_000.00,
                    step=100.00,
                    format="%.2f",
                )

                category = st.selectbox(
                    t("calendar.fields.category"),
                    options=list(CF_CATEGORIES),
                )

                counterparty = st.text_input(
                    t("calendar.fields.counterparty"),
                )

                start_date = st.date_input(
                    t("calendar.fields.start_date"),
                    value=date.today(),
                    format="DD.MM.YYYY",
                )

                recurrence = st.selectbox(
                    t("calendar.fields.recurrence"),
                    options=list(RECURRENCE_LABELS),
                    format_func=format_calendar_recurrence,
                )

                use_end_date = st.checkbox(
                    t("calendar.fields.use_end_date"),
                    value=False,
                )

                selected_end_date = st.date_input(
                    t("calendar.fields.end_date"),
                    value=(
                        date.today()
                        + timedelta(days=365)
                    ),
                    format="DD.MM.YYYY",
                )

                is_active = st.checkbox(
                    t("calendar.fields.active"),
                    value=True,
                )

                comment = st.text_area(
                    t("calendar.fields.comment"),
                    max_chars=500,
                )

                create_plan_submitted = (
                    st.form_submit_button(
                        t("calendar.add_button"),
                        type="primary",
                        use_container_width=True,
                    )
                )

                if create_plan_submitted:
                    plan_end_date = (
                        selected_end_date
                        if use_end_date
                        else None
                    )

                    try:
                        new_plan_id = create_planned_cash_flow(
                            name=plan_name,
                            direction=direction,
                            amount_kopecks=(
                                rubles_to_kopecks(
                                    amount_rubles
                                )
                            ),
                            category=category,
                            counterparty=counterparty,
                            start_date=start_date,
                            recurrence=recurrence,
                            end_date=plan_end_date,
                            is_active=is_active,
                            comment=comment,
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.session_state[
                            "calendar_message"
                        ] = t(
                            "calendar.messages.added",
                            plan_id=new_plan_id,
                        )
                        st.rerun()

        plans = get_planned_cash_flows_dataframe()

        st.subheader(t("calendar.plans.title"))

        if plans.empty:
            st.info(t("calendar.plans.empty"))
        else:
            visible_plans = plans.copy()

            id_column = t("common.id")
            name_column = t("common.name")
            type_column = t("calendar.columns.type")
            amount_column = t("common.amount_rub")
            category_column = t("common.category")
            counterparty_column = t(
                "common.counterparty"
            )
            start_column = t("calendar.columns.start")
            recurrence_column = t(
                "calendar.columns.recurrence"
            )
            end_column = t("calendar.columns.end")
            active_column = t("common.active")
            comment_column = t("common.comment")

            visible_plans[type_column] = (
                visible_plans["direction"]
                .apply(format_calendar_direction)
            )

            visible_plans[amount_column] = (
                visible_plans["amount_kopecks"] / 100
            )

            visible_plans[start_column] = pd.to_datetime(
                visible_plans["start_date"]
            ).dt.strftime("%d.%m.%Y")

            visible_plans[end_column] = (
                pd.to_datetime(
                    visible_plans["end_date"],
                    errors="coerce",
                )
                .dt.strftime("%d.%m.%Y")
                .fillna("")
            )

            visible_plans[recurrence_column] = (
                visible_plans["recurrence"]
                .apply(format_calendar_recurrence)
            )

            visible_plans[active_column] = (
                visible_plans["is_active"]
                .apply(format_boolean_status)
            )

            visible_plans = visible_plans.rename(
                columns={
                    "id": id_column,
                    "name": name_column,
                    "category": category_column,
                    "counterparty": counterparty_column,
                    "comment": comment_column,
                }
            )

            plan_columns = [
                id_column,
                name_column,
                type_column,
                amount_column,
                category_column,
                counterparty_column,
                start_column,
                recurrence_column,
                end_column,
                active_column,
                comment_column,
            ]

            st.dataframe(
                visible_plans[plan_columns],
                use_container_width=True,
                hide_index=True,
                column_config={
                    amount_column:
                        st.column_config.NumberColumn(
                            amount_column,
                            format="%.2f",
                        ),
                },
            )

            plan_options = {
                (
                    f"{int(row['id'])} — "
                    f"{row['name']}"
                ): int(row["id"])
                for _, row in plans.iterrows()
            }

            selected_plan_label = st.selectbox(
                t("calendar.select_manage"),
                options=list(plan_options),
            )

            selected_plan_id = plan_options[
                selected_plan_label
            ]

            selected_plan = plans.loc[
                plans["id"] == selected_plan_id
            ].iloc[0]

            selected_plan_active = st.checkbox(
                t("calendar.fields.active"),
                value=bool(
                    selected_plan["is_active"]
                ),
                key=(
                    f"selected_plan_active_"
                    f"{selected_plan_id}"
                ),
            )

            active_action_column, delete_column = (
                st.columns(2)
            )

            with active_action_column:
                if st.button(
                    t("calendar.save_activity"),
                    use_container_width=True,
                    key=(
                        f"save_plan_activity_"
                        f"{selected_plan_id}"
                    ),
                ):
                    set_planned_cash_flow_active(
                        plan_id=selected_plan_id,
                        is_active=selected_plan_active,
                    )

                    st.session_state[
                        "calendar_message"
                    ] = t(
                        "calendar.messages.activity_updated"
                    )
                    st.rerun()

            with delete_column:
                if st.button(
                    t("calendar.delete"),
                    use_container_width=True,
                    key=(
                        f"delete_plan_"
                        f"{selected_plan_id}"
                    ),
                ):
                    delete_planned_cash_flow(
                        selected_plan_id
                    )

                    st.session_state[
                        "calendar_message"
                    ] = t("calendar.messages.deleted")
                    st.rerun()

        st.divider()
        st.subheader(t("calendar.forecast.title"))

        forecast_start = st.date_input(
            t("calendar.forecast.start"),
            value=date.today(),
            format="DD.MM.YYYY",
            key="forecast_start",
        )

        forecast_horizon = st.selectbox(
            t("calendar.forecast.horizon"),
            options=[30, 60, 90, 180, 365],
            index=2,
            format_func=lambda days: t(
                "common.days",
                count=days,
            ),
        )

        opening_balance_rubles = st.number_input(
            t("calendar.forecast.opening_balance"),
            value=0.00,
            step=1_000.00,
            format="%.2f",
        )

        forecast_end = (
            forecast_start
            + timedelta(days=forecast_horizon - 1)
        )

        occurrences = expand_planned_cash_flows(
            plans=plans,
            period_start=forecast_start,
            period_end=forecast_end,
        )

        forecast = build_cash_forecast(
            occurrences=occurrences,
            period_start=forecast_start,
            period_end=forecast_end,
            opening_balance_kopecks=(
                rubles_to_kopecks(
                    opening_balance_rubles
                )
            ),
        )

        total_inflow = int(
            occurrences.loc[
                occurrences[
                    "signed_amount_kopecks"
                ] > 0,
                "signed_amount_kopecks",
            ].sum()
        )

        total_outflow = abs(
            int(
                occurrences.loc[
                    occurrences[
                        "signed_amount_kopecks"
                    ] < 0,
                    "signed_amount_kopecks",
                ].sum()
            )
        )

        ending_balance = int(
            forecast[
                "closing_balance_kopecks"
            ].iloc[-1]
        )

        minimum_balance = int(
            forecast[
                "closing_balance_kopecks"
            ].min()
        )

        forecast_metrics = st.columns(4)

        forecast_metrics[0].metric(
            t("calendar.forecast.inflows"),
            format_rubles(total_inflow),
        )

        forecast_metrics[1].metric(
            t("calendar.forecast.outflows"),
            format_rubles(total_outflow),
        )

        forecast_metrics[2].metric(
            t("calendar.forecast.ending_balance"),
            format_rubles(ending_balance),
        )

        forecast_metrics[3].metric(
            t("calendar.forecast.minimum_balance"),
            format_rubles(minimum_balance),
        )

        cash_gap_rows = forecast.loc[
            forecast["closing_balance_kopecks"] < 0
        ]

        if cash_gap_rows.empty:
            st.success(
                t("calendar.forecast.no_gap")
            )
        else:
            first_cash_gap = (
                cash_gap_rows.iloc[0]["date"]
            )

            cash_gap_amount = abs(
                int(
                    cash_gap_rows[
                        "closing_balance_kopecks"
                    ].min()
                )
            )

            st.error(
                t(
                    "calendar.forecast.gap",
                    date=first_cash_gap.strftime(
                        "%d.%m.%Y"
                    ),
                    amount=format_rubles(
                        cash_gap_amount
                    ),
                )
            )

        chart_data = forecast.copy()

        date_column = t("common.date")
        balance_column = t(
            "calendar.forecast.balance"
        )

        chart_data[date_column] = pd.to_datetime(
            chart_data["date"]
        )

        chart_data[balance_column] = (
            chart_data[
                "closing_balance_kopecks"
            ] / 100
        )

        balance_chart = px.line(
            chart_data,
            x=date_column,
            y=balance_column,
        )

        balance_chart.add_hline(y=0)

        balance_chart.update_layout(
            xaxis_title="",
            yaxis_title=balance_column,
        )

        st.plotly_chart(
            balance_chart,
            use_container_width=True,
        )

        with st.expander(
            t("calendar.events.title"),
            expanded=False,
        ):
            if occurrences.empty:
                st.info(
                    t("calendar.events.empty")
                )
            else:
                visible_occurrences = (
                    occurrences.copy()
                )

                name_column = t("common.name")
                amount_column = t("common.amount_rub")
                category_column = t("common.category")
                counterparty_column = t(
                    "common.counterparty"
                )
                comment_column = t("common.comment")

                visible_occurrences[date_column] = (
                    pd.to_datetime(
                        visible_occurrences["date"]
                    ).dt.strftime("%d.%m.%Y")
                )

                visible_occurrences[amount_column] = (
                    visible_occurrences[
                        "signed_amount_kopecks"
                    ] / 100
                )

                visible_occurrences = (
                    visible_occurrences.rename(
                        columns={
                            "name": name_column,
                            "category": category_column,
                            "counterparty":
                                counterparty_column,
                            "comment": comment_column,
                        }
                    )
                )

                occurrence_columns = [
                    date_column,
                    name_column,
                    amount_column,
                    category_column,
                    counterparty_column,
                    comment_column,
                ]

                st.dataframe(
                    visible_occurrences[
                        occurrence_columns
                    ],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        amount_column:
                            st.column_config.NumberColumn(
                                amount_column,
                                format="%.2f",
                            ),
                    },
                )

if import_tab.open:
    with import_tab:
        render_import_tab(
            t=t,
            format_rubles=format_rubles,
        )

