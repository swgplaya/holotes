from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
import re
from types import SimpleNamespace
from typing import Any

import pandas as pd

from src.classification_summary import (
    build_unclassified_summary,
)
from src.payment_calendar import (
    expand_planned_cash_flows,
    get_planned_cash_flows_dataframe,
)
from src.reporting import (
    build_cash_flow_report,
    build_pnl_report,
)
from src.telegram_settings import (
    TelegramSettings,
    get_telegram_settings,
)
from src.transaction_repository import (
    get_transactions_dataframe,
)


NAMED_SUMMARY_PERIODS = (
    "current_month",
    "previous_month",
    "last_30_days",
    "current_quarter",
    "current_year",
)

EXPLICIT_MONTH_PATTERN = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})$"
)

DEFAULT_CALENDAR_DAYS = 14
DEFAULT_CALENDAR_LIMIT = 5


class TelegramSummaryError(RuntimeError):
    """Raised when a Telegram summary cannot be built."""


@dataclass(frozen=True)
class SummaryPeriod:
    """Resolved reporting period."""

    code: str
    start_date: date
    end_date: date


@dataclass(frozen=True)
class ReportTotals:
    """Compact financial report totals."""

    inflow_kopecks: int
    outflow_kopecks: int
    net_kopecks: int
    included_count: int
    pending_count: int


@dataclass(frozen=True)
class PendingClassificationTotals:
    """Totals for unfinished classification."""

    operation_count: int
    inflow_kopecks: int
    outflow_kopecks: int
    net_kopecks: int


@dataclass(frozen=True)
class PlannedOccurrence:
    """One expanded payment-calendar occurrence."""

    occurrence_date: date
    name: str
    signed_amount_kopecks: int


@dataclass(frozen=True)
class TelegramFinancialSummary:
    """Financial data prepared for Telegram."""

    period: SummaryPeriod
    cash_flow: ReportTotals | None
    pnl: ReportTotals | None
    pending_classification: (
        PendingClassificationTotals
        | None
    )
    payment_calendar: tuple[
        PlannedOccurrence,
        ...,
    ] | None
    calendar_start_date: date | None
    calendar_end_date: date | None


def _month_end(
    year: int,
    month: int,
) -> date:
    """Returns the final day of a month."""

    return date(
        year,
        month,
        monthrange(
            year,
            month,
        )[1],
    )


def resolve_summary_period(
    period: str,
    *,
    as_of: date | None = None,
) -> SummaryPeriod:
    """Resolves a named period or YYYY-MM."""

    current_date = as_of or date.today()

    normalized_period = str(
        period
    ).strip()

    explicit_month = (
        EXPLICIT_MONTH_PATTERN.fullmatch(
            normalized_period
        )
    )

    if explicit_month is not None:
        year = int(
            explicit_month.group(
                "year"
            )
        )

        month = int(
            explicit_month.group(
                "month"
            )
        )

        if not 1 <= month <= 12:
            raise ValueError(
                "Summary month must be "
                "between 01 and 12."
            )

        return SummaryPeriod(
            code=normalized_period,
            start_date=date(
                year,
                month,
                1,
            ),
            end_date=_month_end(
                year,
                month,
            ),
        )

    if (
        normalized_period
        not in NAMED_SUMMARY_PERIODS
    ):
        raise ValueError(
            "Unknown Telegram summary period."
        )

    if normalized_period == "current_month":
        return SummaryPeriod(
            code=normalized_period,
            start_date=current_date.replace(
                day=1
            ),
            end_date=current_date,
        )

    if normalized_period == "previous_month":
        current_month_start = (
            current_date.replace(
                day=1
            )
        )

        previous_month_end = (
            current_month_start
            - timedelta(days=1)
        )

        return SummaryPeriod(
            code=normalized_period,
            start_date=(
                previous_month_end.replace(
                    day=1
                )
            ),
            end_date=previous_month_end,
        )

    if normalized_period == "last_30_days":
        return SummaryPeriod(
            code=normalized_period,
            start_date=(
                current_date
                - timedelta(days=29)
            ),
            end_date=current_date,
        )

    if normalized_period == "current_quarter":
        quarter_start_month = (
            (
                current_date.month - 1
            )
            // 3
            * 3
            + 1
        )

        return SummaryPeriod(
            code=normalized_period,
            start_date=date(
                current_date.year,
                quarter_start_month,
                1,
            ),
            end_date=current_date,
        )

    return SummaryPeriod(
        code=normalized_period,
        start_date=date(
            current_date.year,
            1,
            1,
        ),
        end_date=current_date,
    )


def _report_totals(
    report: Any,
) -> ReportTotals:
    """Extracts stable totals from ReportResult."""

    required_fields = (
        "inflow_kopecks",
        "outflow_kopecks",
        "net_kopecks",
        "included_count",
        "pending_count",
    )

    missing_fields = [
        field_name
        for field_name in required_fields
        if not hasattr(
            report,
            field_name,
        )
    ]

    if missing_fields:
        raise TelegramSummaryError(
            "Financial report is missing "
            "required fields: "
            + ", ".join(
                missing_fields
            )
        )

    return ReportTotals(
        inflow_kopecks=int(
            report.inflow_kopecks
        ),
        outflow_kopecks=int(
            report.outflow_kopecks
        ),
        net_kopecks=int(
            report.net_kopecks
        ),
        included_count=int(
            report.included_count
        ),
        pending_count=int(
            report.pending_count
        ),
    )


def _find_occurrence_date_column(
    occurrences: pd.DataFrame,
) -> str:
    """Finds the expanded occurrence date column."""

    candidates = (
        "occurrence_date",
        "planned_date",
        "transaction_date",
        "date",
    )

    for candidate in candidates:
        if candidate in occurrences.columns:
            return candidate

    raise TelegramSummaryError(
        "Expanded payment calendar does not "
        "contain an occurrence date column."
    )


def _occurrence_date(
    value: Any,
) -> date | None:
    """Converts an occurrence date safely."""

    converted = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(converted):
        return None

    if isinstance(
        converted,
        pd.Timestamp,
    ):
        return converted.date()

    return None


def _occurrence_amount(
    row: dict[str, Any],
) -> int:
    """Returns a signed occurrence amount."""

    signed_amount = row.get(
        "signed_amount_kopecks"
    )

    if (
        signed_amount is not None
        and not pd.isna(
            signed_amount
        )
    ):
        return int(
            signed_amount
        )

    raw_amount = row.get(
        "amount_kopecks",
        0,
    )

    if pd.isna(raw_amount):
        raw_amount = 0

    amount = abs(
        int(raw_amount)
    )

    direction = str(
        row.get(
            "direction",
            "",
        )
    ).strip().lower()

    inflow_values = {
        "income",
        "inflow",
        "incoming",
        "поступление",
        "приход",
        "доход",
    }

    outflow_values = {
        "expense",
        "outflow",
        "outgoing",
        "списание",
        "расход",
        "платёж",
        "платеж",
    }

    if direction in inflow_values:
        return amount

    if direction in outflow_values:
        return -amount

    return int(
        raw_amount
    )


def _upcoming_payment_calendar(
    *,
    as_of: date,
    days: int,
    limit: int,
) -> tuple[
    tuple[PlannedOccurrence, ...],
    date,
]:
    """Loads and expands upcoming planned movements."""

    if days <= 0:
        raise ValueError(
            "Calendar horizon must be positive."
        )

    if limit <= 0:
        raise ValueError(
            "Calendar result limit must be positive."
        )

    calendar_end = (
        as_of
        + timedelta(
            days=days - 1
        )
    )

    plans = (
        get_planned_cash_flows_dataframe()
    )

    if plans.empty:
        return (), calendar_end

    occurrences = expand_planned_cash_flows(
        plans=plans,
        period_start=as_of,
        period_end=calendar_end,
    )

    if occurrences.empty:
        return (), calendar_end

    date_column = (
        _find_occurrence_date_column(
            occurrences
        )
    )

    normalized_occurrences: list[
        PlannedOccurrence
    ] = []

    for row in occurrences.to_dict(
        orient="records"
    ):
        occurrence_date = (
            _occurrence_date(
                row.get(
                    date_column
                )
            )
        )

        if occurrence_date is None:
            continue

        if not (
            as_of
            <= occurrence_date
            <= calendar_end
        ):
            continue

        name = str(
            row.get(
                "name",
                "",
            )
            or ""
        ).strip()

        if not name:
            name = "Planned transaction"

        normalized_occurrences.append(
            PlannedOccurrence(
                occurrence_date=(
                    occurrence_date
                ),
                name=name,
                signed_amount_kopecks=(
                    _occurrence_amount(
                        row
                    )
                ),
            )
        )

    normalized_occurrences.sort(
        key=lambda occurrence: (
            occurrence.occurrence_date,
            occurrence.name.casefold(),
            occurrence.signed_amount_kopecks,
        )
    )

    return (
        tuple(
            normalized_occurrences[
                :limit
            ]
        ),
        calendar_end,
    )


def build_telegram_summary(
    *,
    period: str | None = None,
    as_of: date | None = None,
    settings: TelegramSettings | None = None,
    calendar_days: int = (
        DEFAULT_CALENDAR_DAYS
    ),
    calendar_limit: int = (
        DEFAULT_CALENDAR_LIMIT
    ),
) -> TelegramFinancialSummary:
    """Builds a summary without using Telegram API."""

    current_date = as_of or date.today()

    active_settings = (
        settings
        or get_telegram_settings()
    )

    requested_period = (
        period
        or active_settings
        .default_summary_period
    )

    resolved_period = (
        resolve_summary_period(
            requested_period,
            as_of=current_date,
        )
    )

    transactions: pd.DataFrame | None = (
        None
    )

    if (
        active_settings.include_cash_flow
        or active_settings.include_pnl
    ):
        transactions = (
            get_transactions_dataframe(
                start_date=(
                    resolved_period.start_date
                ),
                end_date=(
                    resolved_period.end_date
                ),
            )
        )

    cash_flow = None

    if (
        active_settings.include_cash_flow
    ):
        if transactions is None:
            raise TelegramSummaryError(
                "Transactions were not loaded."
            )

        cash_flow = _report_totals(
            build_cash_flow_report(
                transactions
            )
        )

    pnl = None

    if active_settings.include_pnl:
        if transactions is None:
            raise TelegramSummaryError(
                "Transactions were not loaded."
            )

        pnl = _report_totals(
            build_pnl_report(
                transactions
            )
        )

    pending_classification = None

    if (
        active_settings
        .include_pending_count
    ):
        pending_transactions = (
            get_transactions_dataframe(
                start_date=(
                    resolved_period.start_date
                ),
                end_date=(
                    resolved_period.end_date
                ),
                pending_only=True,
            )
        )

        pending_summary = (
            build_unclassified_summary(
                pending_transactions
            )
        )

        pending_classification = (
            PendingClassificationTotals(
                operation_count=int(
                    pending_summary
                    .operation_count
                ),
                inflow_kopecks=int(
                    pending_summary
                    .inflow_kopecks
                ),
                outflow_kopecks=int(
                    pending_summary
                    .outflow_kopecks
                ),
                net_kopecks=int(
                    pending_summary
                    .net_kopecks
                ),
            )
        )

    payment_calendar = None
    calendar_start_date = None
    calendar_end_date = None

    if (
        active_settings
        .include_payment_calendar
    ):
        (
            payment_calendar,
            calendar_end_date,
        ) = _upcoming_payment_calendar(
            as_of=current_date,
            days=calendar_days,
            limit=calendar_limit,
        )

        calendar_start_date = current_date

    return TelegramFinancialSummary(
        period=resolved_period,
        cash_flow=cash_flow,
        pnl=pnl,
        pending_classification=(
            pending_classification
        ),
        payment_calendar=(
            payment_calendar
        ),
        calendar_start_date=(
            calendar_start_date
        ),
        calendar_end_date=(
            calendar_end_date
        ),
    )


def _language_code(
    language: str,
) -> str:
    """Normalizes the summary language."""

    normalized = str(
        language
    ).strip().lower()

    if normalized.startswith("en"):
        return "en"

    if normalized.startswith("zh"):
        return "zh-CN"

    return "ru"


def _format_money(
    kopecks: int,
    *,
    language: str,
    force_sign: bool = False,
) -> str:
    """Formats integer kopecks for plain text."""

    normalized_language = (
        _language_code(
            language
        )
    )

    amount = int(
        kopecks
    )

    absolute_value = (
        abs(amount) / 100
    )

    raw_value = (
        f"{absolute_value:,.2f}"
    )

    integer_part, decimal_part = (
        raw_value.split(".")
    )

    integer_part = (
        integer_part.replace(
            ",",
            " ",
        )
    )

    decimal_separator = (
        "."
        if normalized_language == "en"
        else ","
    )

    if amount < 0:
        prefix = "−"
    elif (
        force_sign
        and amount > 0
    ):
        prefix = "+"
    else:
        prefix = ""

    return (
        f"{prefix}"
        f"{integer_part}"
        f"{decimal_separator}"
        f"{decimal_part} ₽"
    )


def _format_date_range(
    start_date: date,
    end_date: date,
) -> str:
    """Formats a compact date range."""

    return (
        f"{start_date:%d.%m.%Y}"
        " — "
        f"{end_date:%d.%m.%Y}"
    )


SUMMARY_LABELS = {
    "ru": {
        "title": "📊 Open MAS — финансовая сводка",
        "period": "Период",
        "cash_flow": "💳 Cash Flow",
        "cf_inflow": "Поступления",
        "cf_outflow": "Списания",
        "cf_net": "Чистый денежный поток",
        "pnl": "📈 P&L · кассовый метод",
        "pnl_inflow": "Доходы",
        "pnl_outflow": "Расходы",
        "pnl_net": "Финансовый результат",
        "pending": "🧩 Неклассифицированные операции",
        "pending_count": "Операций",
        "pending_inflow": "Поступления",
        "pending_outflow": "Списания",
        "pending_net": "Чистое движение",
        "calendar": "📅 Ближайшие плановые движения",
        "calendar_empty": "Запланированных движений нет.",
    },
    "en": {
        "title": "📊 Open MAS — financial summary",
        "period": "Period",
        "cash_flow": "💳 Cash Flow",
        "cf_inflow": "Inflows",
        "cf_outflow": "Outflows",
        "cf_net": "Net cash flow",
        "pnl": "📈 P&L · cash basis",
        "pnl_inflow": "Income",
        "pnl_outflow": "Expenses",
        "pnl_net": "Financial result",
        "pending": "🧩 Unclassified transactions",
        "pending_count": "Transactions",
        "pending_inflow": "Inflows",
        "pending_outflow": "Outflows",
        "pending_net": "Net movement",
        "calendar": "📅 Upcoming planned movements",
        "calendar_empty": "No planned movements.",
    },
    "zh-CN": {
        "title": "📊 Open MAS — 财务摘要",
        "period": "期间",
        "cash_flow": "💳 现金流",
        "cf_inflow": "流入",
        "cf_outflow": "流出",
        "cf_net": "净现金流",
        "pnl": "📈 损益表 · 收付实现制",
        "pnl_inflow": "收入",
        "pnl_outflow": "支出",
        "pnl_net": "财务结果",
        "pending": "🧩 未完成分类的交易",
        "pending_count": "交易数",
        "pending_inflow": "流入",
        "pending_outflow": "流出",
        "pending_net": "净变动",
        "calendar": "📅 即将发生的计划收支",
        "calendar_empty": "没有计划收支。",
    },
}


def format_telegram_summary(
    summary: TelegramFinancialSummary,
    *,
    language: str = "ru",
) -> str:
    """Formats a summary as Telegram plain text."""

    language_code = _language_code(
        language
    )

    labels = SUMMARY_LABELS[
        language_code
    ]

    lines = [
        labels["title"],
        (
            f"{labels['period']}: "
            f"{_format_date_range(
                summary.period.start_date,
                summary.period.end_date,
            )}"
        ),
    ]

    if summary.cash_flow is not None:
        lines.extend(
            [
                "",
                labels["cash_flow"],
                (
                    f"{labels['cf_inflow']}: "
                    f"{_format_money(
                        summary.cash_flow
                        .inflow_kopecks,
                        language=language_code,
                    )}"
                ),
                (
                    f"{labels['cf_outflow']}: "
                    f"{_format_money(
                        summary.cash_flow
                        .outflow_kopecks,
                        language=language_code,
                    )}"
                ),
                (
                    f"{labels['cf_net']}: "
                    f"{_format_money(
                        summary.cash_flow
                        .net_kopecks,
                        language=language_code,
                    )}"
                ),
            ]
        )

    if summary.pnl is not None:
        lines.extend(
            [
                "",
                labels["pnl"],
                (
                    f"{labels['pnl_inflow']}: "
                    f"{_format_money(
                        summary.pnl
                        .inflow_kopecks,
                        language=language_code,
                    )}"
                ),
                (
                    f"{labels['pnl_outflow']}: "
                    f"{_format_money(
                        summary.pnl
                        .outflow_kopecks,
                        language=language_code,
                    )}"
                ),
                (
                    f"{labels['pnl_net']}: "
                    f"{_format_money(
                        summary.pnl
                        .net_kopecks,
                        language=language_code,
                    )}"
                ),
            ]
        )

    if (
        summary.pending_classification
        is not None
    ):
        pending = (
            summary.pending_classification
        )

        lines.extend(
            [
                "",
                labels["pending"],
                (
                    f"{labels['pending_count']}: "
                    f"{pending.operation_count}"
                ),
                (
                    f"{labels['pending_inflow']}: "
                    f"{_format_money(
                        pending.inflow_kopecks,
                        language=language_code,
                    )}"
                ),
                (
                    f"{labels['pending_outflow']}: "
                    f"{_format_money(
                        pending.outflow_kopecks,
                        language=language_code,
                    )}"
                ),
                (
                    f"{labels['pending_net']}: "
                    f"{_format_money(
                        pending.net_kopecks,
                        language=language_code,
                    )}"
                ),
            ]
        )

    if (
        summary.payment_calendar
        is not None
    ):
        calendar_title = labels[
            "calendar"
        ]

        if (
            summary.calendar_start_date
            is not None
            and summary.calendar_end_date
            is not None
        ):
            calendar_title += (
                "\n"
                + _format_date_range(
                    summary
                    .calendar_start_date,
                    summary
                    .calendar_end_date,
                )
            )

        lines.extend(
            [
                "",
                calendar_title,
            ]
        )

        if not summary.payment_calendar:
            lines.append(
                labels[
                    "calendar_empty"
                ]
            )
        else:
            for occurrence in (
                summary.payment_calendar
            ):
                lines.append(
                    (
                        f"{occurrence.occurrence_date:%d.%m}"
                        " · "
                        f"{occurrence.name}: "
                        f"{_format_money(
                            occurrence
                            .signed_amount_kopecks,
                            language=language_code,
                            force_sign=True,
                        )}"
                    )
                )

    return "\n".join(
        lines
    )
