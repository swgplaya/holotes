from collections.abc import Callable

import pandas as pd
import plotly.express as px
import streamlit as st

from src.categories import (
    BUILT_IN_CATEGORY_TRANSLATION_KEYS,
)
from src.reporting import (
    COMPARISON_MODES,
    ReportResult,
    build_cash_flow_report,
    build_category_comparison,
    build_pnl_report,
    filter_transactions_by_period,
    get_comparison_period,
)

from src.transaction_repository import (
    get_transactions_dataframe,
)

from src.ui.data_cache import (
    cached_transaction_date_bounds,
)

Translator = Callable[..., str]
MoneyFormatter = Callable[[int], str]


def _translate_report_category(
    category: object,
    *,
    t: Translator,
    empty_label: str,
) -> str:
    """Translates built-in categories and preserves custom names."""

    if category is None or pd.isna(category):
        return empty_label

    category_name = str(category).strip()

    if not category_name:
        return empty_label

    translation_key = (
        BUILT_IN_CATEGORY_TRANSLATION_KEYS.get(
            category_name
        )
    )

    if translation_key is None:
        return category_name

    return t(translation_key)


def _render_financial_report_tab(
    *,
    t: Translator,
    format_rubles: MoneyFormatter,
    report_type: str,
) -> None:
    """Отображает одну из финансовых вкладок."""

    def prepare_report_details(
        transactions: pd.DataFrame,
        category_column: str,
    ) -> pd.DataFrame:
        """Подготавливает детализацию финансового отчёта."""

        details = transactions.copy()

        date_label = t(
            "operations.columns.date"
        )
        amount_label = t(
            "reports.columns.amount"
        )
        category_label = t(
            "reports.columns.category"
        )
        counterparty_label = t(
            "operations.columns.counterparty"
        )
        description_label = t(
            "operations.columns.description"
        )
        payment_purpose_label = t(
            "operations.columns.payment_purpose"
        )

        details["posted_at"] = pd.to_datetime(
            details["posted_at"],
            errors="coerce",
        )

        details[date_label] = details[
            "posted_at"
        ].dt.strftime("%d.%m.%Y")

        details[amount_label] = (
            details["signed_amount_kopecks"] / 100
        )

        no_category_label = t(
            "reports.columns.no_category"
        )

        details[category_label] = details[
            category_column
        ].map(
            lambda category: (
                _translate_report_category(
                    category,
                    t=t,
                    empty_label=no_category_label,
                )
            )
        )

        details[counterparty_label] = (
            details["counterparty_name"]
            .fillna("")
        )

        details[description_label] = (
            details["description"]
            .fillna("")
        )

        details[payment_purpose_label] = (
            details["payment_purpose"]
            .fillna("")
        )

        return details[
            [
                date_label,
                amount_label,
                category_label,
                counterparty_label,
                description_label,
                payment_purpose_label,
            ]
        ]

    def _safe_percent(
        numerator: int | float,
        denominator: int | float,
    ) -> float | None:
        """Безопасно рассчитывает процентное отношение."""

        if denominator <= 0:
            return None

        return (
            float(numerator)
            / float(denominator)
            * 100
        )


    def _format_optional_percent(
        value: float | None,
    ) -> str:
        """Форматирует процент или выводит прочерк."""

        if value is None or pd.isna(value):
            return "—"

        return f"{float(value):.1f}%"


    def _format_optional_rubles(
        value: float | int | None,
    ) -> str:
        """Форматирует сумму или выводит прочерк."""

        if value is None or pd.isna(value):
            return "—"

        return format_rubles(
            int(round(float(value)))
        )


    def _percentage_point_delta(
        current_value: float | None,
        comparison_value: float | None,
    ) -> str | None:
        """Возвращает изменение процентного показателя."""

        if (
            current_value is None
            or comparison_value is None
            or pd.isna(current_value)
            or pd.isna(comparison_value)
        ):
            return None

        difference = (
            float(current_value)
            - float(comparison_value)
        )

        return t(
            "reports.percentage_point_delta",
            value=difference,
        )

    def _rubles_delta(
        current_value: float | None,
        comparison_value: float | None,
    ) -> str | None:
        """Возвращает изменение денежного показателя."""

        if (
            current_value is None
            or comparison_value is None
            or pd.isna(current_value)
            or pd.isna(comparison_value)
        ):
            return None

        difference = int(
            round(
                float(current_value)
                - float(comparison_value)
            )
        )

        formatted_difference = format_rubles(
            difference
        )

        if difference > 0:
            return f"+{formatted_difference}"

        return formatted_difference


    def _count_delta(
        current_value: int,
        comparison_value: int,
    ) -> str:
        """Возвращает изменение количества операций."""

        difference = (
            int(current_value)
            - int(comparison_value)
        )

        return f"{difference:+d}"


    def _get_report_operation_counts(
        report: ReportResult,
    ) -> tuple[int, int]:
        """Считает доходные и расходные операции отчёта."""

        transactions = report.transactions

        if transactions.empty:
            return 0, 0

        if (
            "signed_amount_kopecks"
            in transactions.columns
        ):
            amounts = pd.to_numeric(
                transactions[
                    "signed_amount_kopecks"
                ],
                errors="coerce",
            ).fillna(0)

            income_count = int(
                (amounts > 0).sum()
            )

            expense_count = int(
                (amounts < 0).sum()
            )

            return income_count, expense_count

        if "direction" in transactions.columns:
            directions = (
                transactions["direction"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
            )

            income_values = {
                "income",
                "inflow",
                "credit",
                "поступление",
                "приход",
            }

            expense_values = {
                "expense",
                "outflow",
                "debit",
                "списание",
                "расход",
            }

            income_count = int(
                directions.isin(
                    income_values
                ).sum()
            )

            expense_count = int(
                directions.isin(
                    expense_values
                ).sum()
            )

            return income_count, expense_count

        return 0, 0


    def _build_pnl_kpis(
        report: ReportResult,
    ) -> dict[str, float | int | None]:
        """Рассчитывает доступные KPI кассового P&L."""

        income_count, expense_count = (
            _get_report_operation_counts(report)
        )

        decided_count = (
            report.included_count
            + report.excluded_count
        )

        total_count = (
            decided_count
            + report.pending_count
        )

        profitability = _safe_percent(
            numerator=report.net_kopecks,
            denominator=report.inflow_kopecks,
        )

        expense_share = _safe_percent(
            numerator=report.outflow_kopecks,
            denominator=report.inflow_kopecks,
        )

        expense_coverage = _safe_percent(
            numerator=report.inflow_kopecks,
            denominator=report.outflow_kopecks,
        )

        classification_rate = _safe_percent(
            numerator=decided_count,
            denominator=total_count,
        )

        average_income = (
            report.inflow_kopecks / income_count
            if income_count > 0
            else None
        )

        average_expense = (
            report.outflow_kopecks / expense_count
            if expense_count > 0
            else None
        )

        return {
            "profitability": profitability,
            "expense_share": expense_share,
            "expense_coverage": expense_coverage,
            "classification_rate":
                classification_rate,
            "average_income": average_income,
            "average_expense": average_expense,
            "income_count": income_count,
            "expense_count": expense_count,
        }


    def show_pnl_kpis(
        report: ReportResult,
        comparison_report: ReportResult | None,
    ) -> None:
        """Показывает KPI текущего кассового P&L."""

        current = _build_pnl_kpis(
            report
        )

        comparison = (
            _build_pnl_kpis(
                comparison_report
            )
            if comparison_report is not None
            else None
        )

        st.subheader(
            t("reports.pnl.kpi_title")
        )

        first_row = st.columns(4)

        first_row[0].metric(
            t("reports.pnl.kpi.profitability"),
            _format_optional_percent(
                current["profitability"]
            ),
            delta=(
                _percentage_point_delta(
                    current["profitability"],
                    comparison["profitability"],
                )
                if comparison is not None
                else None
            ),
        )

        first_row[1].metric(
            t("reports.pnl.kpi.expense_share"),
            _format_optional_percent(
                current["expense_share"]
            ),
            delta=(
                _percentage_point_delta(
                    current["expense_share"],
                    comparison["expense_share"],
                )
                if comparison is not None
                else None
            ),
            delta_color="inverse",
        )

        first_row[2].metric(
            t("reports.pnl.kpi.expense_coverage"),
            _format_optional_percent(
                current["expense_coverage"]
            ),
            delta=(
                _percentage_point_delta(
                    current["expense_coverage"],
                    comparison[
                        "expense_coverage"
                    ],
                )
                if comparison is not None
                else None
            ),
        )

        first_row[3].metric(
            t("reports.pnl.kpi.classification_rate"),
            _format_optional_percent(
                current["classification_rate"]
            ),
            delta=(
                _percentage_point_delta(
                    current[
                        "classification_rate"
                    ],
                    comparison[
                        "classification_rate"
                    ],
                )
                if comparison is not None
                else None
            ),
        )

        second_row = st.columns(4)

        second_row[0].metric(
            t("reports.pnl.kpi.average_income"),
            _format_optional_rubles(
                current["average_income"]
            ),
            delta=(
                _rubles_delta(
                    current["average_income"],
                    comparison["average_income"],
                )
                if comparison is not None
                else None
            ),
        )

        second_row[1].metric(
            t("reports.pnl.kpi.average_expense"),
            _format_optional_rubles(
                current["average_expense"]
            ),
            delta=(
                _rubles_delta(
                    current["average_expense"],
                    comparison["average_expense"],
                )
                if comparison is not None
                else None
            ),
            delta_color="off",
        )

        second_row[2].metric(
            t("reports.pnl.kpi.income_count"),
            int(current["income_count"]),
            delta=(
                _count_delta(
                    int(current["income_count"]),
                    int(comparison["income_count"]),
                )
                if comparison is not None
                else None
            ),
        )

        second_row[3].metric(
            t("reports.pnl.kpi.expense_count"),
            int(current["expense_count"]),
            delta=(
                _count_delta(
                    int(current["expense_count"]),
                    int(comparison["expense_count"]),
                )
                if comparison is not None
                else None
            ),
            delta_color="off",
        )

        st.caption(
            t("reports.pnl.kpi_caption")
        )

    def style_report_chart(
        chart,
        *,
        show_legend: bool = False,
    ) -> None:
        """Применяет единый стиль к финансовым графикам."""

        layout_options = {
            "height": 420,
            "margin": {
                "l": 16,
                "r": 16,
                "t": 32,
                "b": 16,
            },
            "bargap": 0.22,
            "hovermode": (
                "x unified"
                if show_legend
                else "closest"
            ),
            "showlegend": show_legend,
        }

        if show_legend:
            layout_options["legend"] = {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "left",
                "x": 0,
                "title_text": "",
            }

        chart.update_layout(
            **layout_options
        )

        chart.update_xaxes(
            title_text="",
            showgrid=False,
            automargin=True,
            tickangle=-15,
        )

        chart.update_yaxes(
            title_text=t(
                "reports.columns.amount"
            ),
            automargin=True,
            gridcolor="rgba(128, 128, 128, 0.18)",
            zerolinecolor="rgba(128, 128, 128, 0.30)",
        )

        chart.update_traces(
            marker_line_width=0,
        )

    def show_report_result(
        report: ReportResult,
        report_type: str,
        category_column: str,
        inflow_label: str,
        outflow_label: str,
        net_label: str,
        current_label: str,
        comparison_report: ReportResult | None = None,
        comparison_label: str | None = None,
    ) -> None:
        """Отображает финансовый отчёт и сравнение периодов."""

        def money_delta(
            current_value: int,
            comparison_value: int,
        ) -> str:
            difference = (
                current_value - comparison_value
            )

            prefix = "+" if difference > 0 else ""

            return (
                prefix
                + format_rubles(difference)
            )

        metric_columns = st.columns(4)

        inflow_delta = None
        outflow_delta = None
        net_delta = None
        count_delta = None

        if comparison_report is not None:
            inflow_delta = money_delta(
                report.inflow_kopecks,
                comparison_report.inflow_kopecks,
            )

            outflow_delta = money_delta(
                report.outflow_kopecks,
                comparison_report.outflow_kopecks,
            )

            net_delta = money_delta(
                report.net_kopecks,
                comparison_report.net_kopecks,
            )

            operation_difference = (
                report.included_count
                - comparison_report.included_count
            )

            count_delta = (
                f"{operation_difference:+d}"
            )

        metric_columns[0].metric(
            inflow_label,
            format_rubles(report.inflow_kopecks),
            delta=inflow_delta,
        )

        metric_columns[1].metric(
            outflow_label,
            format_rubles(report.outflow_kopecks),
            delta=outflow_delta,
        )

        metric_columns[2].metric(
            net_label,
            format_rubles(report.net_kopecks),
            delta=net_delta,
        )

        metric_columns[3].metric(
            t("reports.metrics.included"),
            report.included_count,
            delta=count_delta,
        )

        st.caption(
            t(
                "reports.current_summary",
                label=current_label,
                excluded=report.excluded_count,
                pending=report.pending_count,
            )
        )

        if (
            comparison_report is not None
            and comparison_label is not None
        ):
            st.caption(
                t(
                    "reports.comparison_summary",
                    label=comparison_label,
                    included=(
                        comparison_report.included_count
                    ),
                    excluded=(
                        comparison_report.excluded_count
                    ),
                    pending=(
                        comparison_report.pending_count
                    ),
                )
            )

        if report.pending_count:
            st.warning(
                t("reports.pending_warning")
            )

        if report_type == "pnl":
            show_pnl_kpis(
                report=report,
                comparison_report=comparison_report,
            )

        if report.transactions.empty:
            st.info(
                t("reports.empty_period")
            )

            if comparison_report is None:
                return

        st.subheader(
            t("reports.category_structure")
        )

        category_label = t(
            "reports.columns.category"
        )
        amount_label = t(
            "reports.columns.amount"
        )
        current_amount_label = t(
            "reports.columns.current_amount"
        )
        comparison_amount_label = t(
            "reports.columns.comparison_amount"
        )
        delta_amount_label = t(
            "reports.columns.delta_amount"
        )
        delta_percent_label = t(
            "reports.columns.delta_percent"
        )
        period_label = t(
            "reports.columns.period"
        )
        no_category_label = t(
            "reports.columns.no_category"
        )

        if comparison_report is None:
            category_table = (
                report.category_totals.copy()
            )

            category_table["category"] = (
                category_table["category"].map(
                    lambda category: (
                        _translate_report_category(
                            category,
                            t=t,
                            empty_label=(
                                no_category_label
                            ),
                        )
                    )
                )
            )

            category_table[amount_label] = (
                category_table[
                    "amount_kopecks"
                ] / 100
            )

            category_table = category_table.rename(
                columns={
                    "category": category_label,
                }
            )

            if category_table.empty:
                st.info(
                    t("reports.no_category_data")
                )
            else:
                chart = px.bar(
                    category_table,
                    x=category_label,
                    y=amount_label,
                    text_auto=".2s",
                )

                style_report_chart(chart)

                st.plotly_chart(
                    chart,
                    use_container_width=True,
                )

                st.dataframe(
                    category_table[
                        [
                            category_label,
                            amount_label,
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        amount_label:
                            st.column_config.NumberColumn(
                                amount_label,
                                format="%.2f",
                            ),
                    },
                )

        else:
            comparison_table = (
                build_category_comparison(
                    current_report=report,
                    comparison_report=comparison_report,
                )
            )

            comparison_table["category"] = (
                comparison_table["category"].map(
                    lambda category: (
                        _translate_report_category(
                            category,
                            t=t,
                            empty_label=(
                                no_category_label
                            ),
                        )
                    )
                )
            )

            comparison_table[
                current_amount_label
            ] = (
                comparison_table[
                    "current_amount_kopecks"
                ] / 100
            )

            comparison_table[
                comparison_amount_label
            ] = (
                comparison_table[
                    "comparison_amount_kopecks"
                ] / 100
            )

            comparison_table[delta_amount_label] = (
                comparison_table[
                    "delta_kopecks"
                ] / 100
            )

            comparison_table = (
                comparison_table.rename(
                    columns={
                        "category": category_label,
                        "change_percent":
                            delta_percent_label,
                    }
                )
            )

            if comparison_table.empty:
                st.info(
                    t("reports.no_comparison_data")
                )
            else:
                chart_data = comparison_table[
                    [
                        category_label,
                        current_amount_label,
                        comparison_amount_label,
                    ]
                ].melt(
                    id_vars=category_label,
                    var_name=period_label,
                    value_name=amount_label,
                )

                comparison_chart = px.bar(
                    chart_data,
                    x=category_label,
                    y=amount_label,
                    color=period_label,
                    barmode="group",
                )

                style_report_chart(
                    comparison_chart,
                    show_legend=True,
                )

                st.plotly_chart(
                    comparison_chart,
                    use_container_width=True,
                )

                st.dataframe(
                    comparison_table[
                        [
                            category_label,
                            current_amount_label,
                            comparison_amount_label,
                            delta_amount_label,
                            delta_percent_label,
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        current_amount_label:
                            st.column_config.NumberColumn(
                                current_amount_label,
                                format="%.2f",
                            ),
                        comparison_amount_label:
                            st.column_config.NumberColumn(
                                comparison_amount_label,
                                format="%.2f",
                            ),
                        delta_amount_label:
                            st.column_config.NumberColumn(
                                delta_amount_label,
                                format="%.2f",
                            ),
                        delta_percent_label:
                            st.column_config.NumberColumn(
                                delta_percent_label,
                                format="%.1f%%",
                            ),
                    },
                )

        if not report.transactions.empty:
            with st.expander(
                t("reports.current_operations"),
                expanded=False,
            ):
                details = prepare_report_details(
                    transactions=report.transactions,
                    category_column=category_column,
                )

                st.dataframe(
                    details,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        amount_label:
                            st.column_config.NumberColumn(
                                amount_label,
                                format="%.2f",
                            ),
                    },
                )

        if (
            comparison_report is not None
            and not comparison_report.transactions.empty
        ):
            with st.expander(
                t("reports.comparison_operations"),
                expanded=False,
            ):
                comparison_details = (
                    prepare_report_details(
                        transactions=(
                            comparison_report.transactions
                        ),
                        category_column=category_column,
                    )
                )

                st.dataframe(
                    comparison_details,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        amount_label:
                            st.column_config.NumberColumn(
                                amount_label,
                                format="%.2f",
                            ),
                    },
                )

    REPORT_START_DATE_STATE_KEY = (
        "shared_report_start_date"
    )

    REPORT_END_DATE_STATE_KEY = (
        "shared_report_end_date"
    )

    REPORT_COMPARISON_STATE_KEY = (
        "shared_report_comparison_mode"
    )


    REPORT_START_DATE_WIDGET_KEYS = {
        "pnl": "pnl_report_start_date",
        "cash_flow": "cash_flow_report_start_date",
    }

    REPORT_END_DATE_WIDGET_KEYS = {
        "pnl": "pnl_report_end_date",
        "cash_flow": "cash_flow_report_end_date",
    }

    REPORT_COMPARISON_WIDGET_KEYS = {
        "pnl": "pnl_report_comparison_mode",
        "cash_flow": "cash_flow_report_comparison_mode",
    }


    def _clamp_report_date(
        value,
        min_date,
        max_date,
        default_date,
    ):
        """Ограничивает дату диапазоном имеющихся операций."""

        # None и pandas.NaT не являются корректными датами.
        if value is None or pd.isna(value):
            return default_date

        try:
            timestamp = pd.Timestamp(value)
        except (TypeError, ValueError, OverflowError):
            return default_date

        # pd.Timestamp(pd.NaT) не выбрасывает ошибку,
        # поэтому NaT требуется проверять отдельно.
        if pd.isna(timestamp):
            return default_date

        result = timestamp.date()

        if result < min_date:
            return min_date

        if result > max_date:
            return max_date

        return result

    def _set_report_widget_values(
        widget_keys: dict[str, str],
        value,
    ) -> None:
        """Устанавливает одно значение всем связанным виджетам."""

        for widget_key in widget_keys.values():
            st.session_state[widget_key] = value


    def _sync_report_start_date(
        source_widget_key: str,
    ) -> None:
        """Синхронизирует начало периода между отчётами."""

        selected_start = st.session_state.get(
            source_widget_key
        )

        if (
                selected_start is None
                or pd.isna(selected_start)
        ):
            return

        st.session_state[
            REPORT_START_DATE_STATE_KEY
        ] = selected_start

        _set_report_widget_values(
            REPORT_START_DATE_WIDGET_KEYS,
            selected_start,
        )

        current_end = st.session_state.get(
            REPORT_END_DATE_STATE_KEY
        )

        if (
                current_end is not None
                and not pd.isna(current_end)
                and selected_start > current_end
        ):
            st.session_state[
                REPORT_END_DATE_STATE_KEY
            ] = selected_start

            _set_report_widget_values(
                REPORT_END_DATE_WIDGET_KEYS,
                selected_start,
            )


    def _sync_report_end_date(
        source_widget_key: str,
    ) -> None:
        """Синхронизирует конец периода между отчётами."""

        selected_end = st.session_state.get(
            source_widget_key
        )

        if (
            selected_end is None
            or pd.isna(selected_end)
        ):
            return

        st.session_state[
            REPORT_END_DATE_STATE_KEY
        ] = selected_end

        _set_report_widget_values(
            REPORT_END_DATE_WIDGET_KEYS,
            selected_end,
        )

        current_start = st.session_state.get(
            REPORT_START_DATE_STATE_KEY
        )

        if (
            current_start is not None
            and not pd.isna(current_start)
            and selected_end < current_start
        ):
            st.session_state[
                REPORT_START_DATE_STATE_KEY
            ] = selected_end

            _set_report_widget_values(
                REPORT_START_DATE_WIDGET_KEYS,
                selected_end,
            )

    def _sync_report_comparison_mode(
        source_widget_key: str,
    ) -> None:
        """Синхронизирует режим сравнения отчётов."""

        selected_mode = st.session_state.get(
            source_widget_key
        )

        if selected_mode not in COMPARISON_MODES:
            return

        st.session_state[
            REPORT_COMPARISON_STATE_KEY
        ] = selected_mode

        _set_report_widget_values(
            REPORT_COMPARISON_WIDGET_KEYS,
            selected_mode,
        )


    def _prepare_report_filter_state(
        *,
        report_key: str,
        min_date,
        max_date,
    ) -> None:
        """Подготавливает общий период перед созданием виджетов."""

        if report_key not in {
            "pnl",
            "cash_flow",
        }:
            raise ValueError(
                f"Неизвестный ключ отчёта: {report_key}"
            )

        shared_start = _clamp_report_date(
            value=st.session_state.get(
                REPORT_START_DATE_STATE_KEY
            ),
            min_date=min_date,
            max_date=max_date,
            default_date=min_date,
        )

        shared_end = _clamp_report_date(
            value=st.session_state.get(
                REPORT_END_DATE_STATE_KEY
            ),
            min_date=min_date,
            max_date=max_date,
            default_date=max_date,
        )

        if shared_start > shared_end:
            shared_end = shared_start

        comparison_mode = st.session_state.get(
            REPORT_COMPARISON_STATE_KEY,
            "none",
        )

        if comparison_mode not in COMPARISON_MODES:
            comparison_mode = "none"

        st.session_state[
            REPORT_START_DATE_STATE_KEY
        ] = shared_start

        st.session_state[
            REPORT_END_DATE_STATE_KEY
        ] = shared_end

        st.session_state[
            REPORT_COMPARISON_STATE_KEY
        ] = comparison_mode

        start_widget_key = (
            REPORT_START_DATE_WIDGET_KEYS[
                report_key
            ]
        )

        end_widget_key = (
            REPORT_END_DATE_WIDGET_KEYS[
                report_key
            ]
        )

        comparison_widget_key = (
            REPORT_COMPARISON_WIDGET_KEYS[
                report_key
            ]
        )

        if (
            st.session_state.get(start_widget_key)
            != shared_start
        ):
            st.session_state[
                start_widget_key
            ] = shared_start

        if (
            st.session_state.get(end_widget_key)
            != shared_end
        ):
            st.session_state[
                end_widget_key
            ] = shared_end

        if (
            st.session_state.get(
                comparison_widget_key
            )
            != comparison_mode
        ):
            st.session_state[
                comparison_widget_key
            ] = comparison_mode

    def show_financial_report(
            report_type: str,
            key_prefix: str,
    ) -> None:
        """Показывает отчёт с общими финансовыми фильтрами."""

        date_bounds = (
            cached_transaction_date_bounds()
        )

        if date_bounds is None:
            st.info(
                t("reports.empty_database")
            )
            return

        min_date, max_date = date_bounds

        try:
            _prepare_report_filter_state(
                report_key=key_prefix,
                min_date=min_date,
                max_date=max_date,
            )
        except ValueError as exc:
            st.error(str(exc))
            return

        start_widget_key = (
            REPORT_START_DATE_WIDGET_KEYS[
                key_prefix
            ]
        )

        end_widget_key = (
            REPORT_END_DATE_WIDGET_KEYS[
                key_prefix
            ]
        )

        comparison_widget_key = (
            REPORT_COMPARISON_WIDGET_KEYS[
                key_prefix
            ]
        )

        with st.container(
            border=True,
            key=f"{key_prefix}_period_panel",
        ):
            st.markdown(
                f"#### {t('reports.period.title')}"
            )

            start_column, end_column, comparison_column = (
                st.columns(
                    [1, 1, 1.25],
                    gap="medium",
                )
            )

            with start_column:
                start_date = st.date_input(
                    t("reports.period.start"),
                    min_value=min_date,
                    max_value=max_date,
                    format="DD.MM.YYYY",
                    key=start_widget_key,
                    on_change=_sync_report_start_date,
                    args=(start_widget_key,),
                )

            with end_column:
                end_date = st.date_input(
                    t("reports.period.end"),
                    min_value=min_date,
                    max_value=max_date,
                    format="DD.MM.YYYY",
                    key=end_widget_key,
                    on_change=_sync_report_end_date,
                    args=(end_widget_key,),
                )

            with comparison_column:
                comparison_mode = st.selectbox(
                    t("reports.period.compare"),
                    options=list(COMPARISON_MODES),
                    format_func=lambda mode: t(
                        f"reports.comparison.{mode}"
                    ),
                    key=comparison_widget_key,
                    on_change=(
                        _sync_report_comparison_mode
                    ),
                    args=(comparison_widget_key,),
                )

            st.caption(
                t("reports.period.synced")
            )

        try:
            comparison_dates = (
                get_comparison_period(
                    start_date=start_date,
                    end_date=end_date,
                    mode=comparison_mode,
                )
            )
        except ValueError as exc:
            st.error(str(exc))
            return

        query_start = start_date
        query_end = end_date

        if comparison_dates is not None:
            comparison_start, comparison_end = (
                comparison_dates
            )

            query_start = min(
                query_start,
                comparison_start,
            )

            query_end = max(
                query_end,
                comparison_end,
            )

        transactions = (
            get_transactions_dataframe(
                start_date=query_start,
                end_date=query_end,
            )
        )

        period_transactions = (
            filter_transactions_by_period(
                transactions=transactions,
                start_date=start_date,
                end_date=end_date,
            )
        )

        current_label = (
            f"{start_date.strftime('%d.%m.%Y')} — "
            f"{end_date.strftime('%d.%m.%Y')}"
        )

        if report_type == "pnl":
            report_builder = build_pnl_report
            category_column = "pnl_category"
            inflow_label = t(
                "reports.pnl.inflow"
            )
            outflow_label = t(
                "reports.pnl.outflow"
            )
            net_label = t(
                "reports.pnl.net"
            )

        elif report_type == "cash_flow":
            report_builder = build_cash_flow_report
            category_column = "cf_category"
            inflow_label = t(
                "reports.cash_flow.inflow"
            )
            outflow_label = t(
                "reports.cash_flow.outflow"
            )
            net_label = t(
                "reports.cash_flow.net"
            )

        else:
            raise ValueError(
                t(
                    "reports.unknown_type",
                    report_type=report_type,
                )
            )

        report = report_builder(
            period_transactions
        )

        comparison_report = None
        comparison_label = None

        if comparison_dates is not None:
            comparison_start, comparison_end = (
                comparison_dates
            )

            comparison_transactions = (
                filter_transactions_by_period(
                    transactions=transactions,
                    start_date=comparison_start,
                    end_date=comparison_end,
                )
            )

            comparison_report = report_builder(
                comparison_transactions
            )

            comparison_label = (
                f"{comparison_start.strftime('%d.%m.%Y')} — "
                f"{comparison_end.strftime('%d.%m.%Y')}"
            )

        if comparison_label is None:
            st.caption(
                t(
                    "reports.period.current",
                    current=current_label,
                )
            )
        else:
            st.caption(
                t(
                    "reports.period.with_comparison",
                    current=current_label,
                    comparison=comparison_label,
                )
            )

        show_report_result(
            report=report,
            report_type=report_type,
            category_column=category_column,
            inflow_label=inflow_label,
            outflow_label=outflow_label,
            net_label=net_label,
            current_label=current_label,
            comparison_report=comparison_report,
            comparison_label=comparison_label,
        )
    if report_type == "pnl":
        title_key = "reports.pnl.title"
        caption_key = "reports.pnl.caption"

    elif report_type == "cash_flow":
        title_key = "reports.cash_flow.title"
        caption_key = "reports.cash_flow.caption"

    else:
        raise ValueError(
            t(
                "reports.unknown_type",
                report_type=report_type,
            )
        )

    st.subheader(
        t(title_key)
    )

    st.caption(
        t(caption_key)
    )

    show_financial_report(
        report_type=report_type,
        key_prefix=report_type,
    )


def render_pnl_tab(
    *,
    t: Translator,
    format_rubles: MoneyFormatter,
) -> None:
    """Отображает кассовый P&L."""

    _render_financial_report_tab(
        t=t,
        format_rubles=format_rubles,
        report_type="pnl",
    )


def render_cash_flow_tab(
    *,
    t: Translator,
    format_rubles: MoneyFormatter,
) -> None:
    """Отображает отчёт о движении денег."""

    _render_financial_report_tab(
        t=t,
        format_rubles=format_rubles,
        report_type="cash_flow",
    )
