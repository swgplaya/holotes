from collections.abc import Callable

import pandas as pd
import plotly.express as px
import streamlit as st

from src.ui.option_formatting import (
    format_option_label,
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


Translator = Callable[..., str]
MoneyFormatter = Callable[[int], str]
RublesConverter = Callable[[float], int]
BasisPointsConverter = Callable[[float], int]
BooleanFormatter = Callable[[object], str]


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


def _text_or_empty(value: object) -> str:
    """Преобразует пустое значение базы в пустую строку."""

    if value is None or pd.isna(value):
        return ""

    return str(value).strip()


def render_unit_economics_tab(
    *,
    t: Translator,
    format_rubles: MoneyFormatter,
    rubles_to_kopecks: RublesConverter,
    percent_to_basis_points: BasisPointsConverter,
    format_boolean_status: BooleanFormatter,
) -> None:
    """Отображает вкладку юнит-экономики."""

    def format_unit_cost_type(
        value: object,
    ) -> str:
        return format_option_label(
            value,
            t=t,
            translation_keys=(
                UNIT_COST_TYPE_TRANSLATION_KEYS
            ),
            fallback_labels=COST_TYPE_LABELS,
        )

    def format_unit_pricing_method(
        value: object,
    ) -> str:
        return format_option_label(
            value,
            t=t,
            translation_keys=(
                UNIT_PRICING_METHOD_TRANSLATION_KEYS
            ),
            fallback_labels=PRICING_METHOD_LABELS,
        )

    def localize_unit_pricing_error(
        value: object,
    ) -> str:
        message = _text_or_empty(value)

        translation_key = (
            UNIT_PRICING_ERROR_TRANSLATION_KEYS.get(
                message
            )
        )

        if translation_key is not None:
            return t(translation_key)

        return message

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

        # Keep this selector outside the form so changing it
        # immediately rerenders the corresponding value field.
        calculation_type = st.selectbox(
            t("unit.cost.type"),
            options=list(COST_TYPE_LABELS),
            format_func=format_unit_cost_type,
            key=(
                "create_unit_economics_cost_type_"
                f"{selected_product_id}"
            ),
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
                        if not _text_or_empty(value)
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
