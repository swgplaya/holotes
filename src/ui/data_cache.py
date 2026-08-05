from __future__ import annotations

from datetime import date

import streamlit as st

from src.classification_summary import (
    UnclassifiedSummary,
)
from src.data_revision import (
    get_database_revision,
)
from src.transaction_repository import (
    TransactionSummary,
    get_pending_classification_summary,
    get_transaction_count,
    get_transaction_date_bounds,
    get_transaction_summary,
)


@st.cache_data(
    show_spinner=False,
    max_entries=32,
)
def _cached_transaction_count(
    revision: int,
) -> int:
    """Кэширует количество операций для одной ревизии."""

    del revision

    return get_transaction_count()


def cached_transaction_count() -> int:
    """Возвращает актуальное количество операций."""

    return _cached_transaction_count(
        get_database_revision()
    )


@st.cache_data(
    show_spinner=False,
    max_entries=32,
)
def _cached_transaction_summary(
    revision: int,
) -> TransactionSummary:
    """Кэширует финансовую сводку операций."""

    del revision

    return get_transaction_summary()


def cached_transaction_summary() -> TransactionSummary:
    """Возвращает актуальную финансовую сводку."""

    return _cached_transaction_summary(
        get_database_revision()
    )


@st.cache_data(
    show_spinner=False,
    max_entries=32,
)
def _cached_pending_classification_summary(
    revision: int,
) -> UnclassifiedSummary:
    """Кэширует сводку незавершённой классификации."""

    del revision

    return get_pending_classification_summary()


def cached_pending_classification_summary(
) -> UnclassifiedSummary:
    """Возвращает актуальную сводку классификации."""

    return _cached_pending_classification_summary(
        get_database_revision()
    )


@st.cache_data(
    show_spinner=False,
    max_entries=32,
)
def _cached_transaction_date_bounds(
    revision: int,
) -> tuple[date, date] | None:
    """Кэширует границы истории банковских операций."""

    del revision

    return get_transaction_date_bounds()


def cached_transaction_date_bounds(
) -> tuple[date, date] | None:
    """Возвращает актуальные границы истории."""

    return _cached_transaction_date_bounds(
        get_database_revision()
    )
