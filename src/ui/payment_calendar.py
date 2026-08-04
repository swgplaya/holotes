from collections.abc import Callable
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from src.categories import (
    CF_CATEGORIES,
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
from src.ui.option_formatting import (
    format_option_label,
)


Translator = Callable[..., str]
MoneyFormatter = Callable[[int], str]
RublesConverter = Callable[[float], int]
BooleanFormatter = Callable[[object], str]


CALENDAR_DIRECTION_TRANSLATION_KEYS = {
    "inflow": "calendar.direction.inflow",
    "outflow": "calendar.direction.outflow",
}


CALENDAR_RECURRENCE_TRANSLATION_KEYS = {
    "once": "calendar.recurrence.once",
    "monthly": "calendar.recurrence.monthly",
    "yearly": "calendar.recurrence.yearly",
}


def render_payment_calendar_tab(
    *,
    t: Translator,
    format_rubles: MoneyFormatter,
    rubles_to_kopecks: RublesConverter,
    format_boolean_status: BooleanFormatter,
) -> None:
    """Отображает платёжный календарь."""

    def format_calendar_direction(
        value: object,
    ) -> str:
        return format_option_label(
            value,
            t=t,
            translation_keys=(
                CALENDAR_DIRECTION_TRANSLATION_KEYS
            ),
            fallback_labels=DIRECTION_LABELS,
        )

    def format_calendar_recurrence(
        value: object,
    ) -> str:
        return format_option_label(
            value,
            t=t,
            translation_keys=(
                CALENDAR_RECURRENCE_TRANSLATION_KEYS
            ),
            fallback_labels=RECURRENCE_LABELS,
        )

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
