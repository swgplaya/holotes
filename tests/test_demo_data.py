from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from src.bank_import import read_tbank_csv


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

DEMO_STATEMENT_PATH = (
    PROJECT_ROOT
    / "demo_data"
    / "tbank_demo_statement.csv"
)

EXPECTED_HEADERS = [
    "Номер счёта",
    "Тип операции (пополнение/списание)",
    "Категория операции",
    "Статус",
    "Дата проведения",
    "Дата транзакции",
    "Номер платежа",
    "Код ВО",
    "Валюта операции",
    "Сумма в валюте счёта",
    "Валюта счёта",
    "Описание операции",
    "Назначение платежа",
    "Счет плательщика",
    "ИНН плательщика",
    "КПП плательщика",
    "Наименование плательщика",
    "БИК банка плательщика",
    "Корр. счет плательщика",
    "Счет получателя",
    "Договор получателя",
    "ИНН получателя",
    "КПП получателя",
    "Наименование получателя",
    "БИК банка получателя",
    "Корр. счет получателя",
    "Счет контрагента",
    "ИНН контрагента",
    "Наименование контрагента",
    "БИК банка контрагента",
    "MCC",
    "Банк",
    "КБК-код бюджетной классификации",
    "Основание налогового платежа",
    "Налоговый период",
    "Код (УИН)",
]

EXPECTED_BANK_CATEGORIES = {
    "Входящие платежи",
    "Исходящие платежи",
    "Услуги банка",
    "Оплата картой",
    "Кредитование",
    "Платежи в налоговую",
    "Возвраты контрагентам",
    "Возвраты от контрагентов",
    "Переводы между счетами",
}


def test_demo_statement_has_expected_csv_structure() -> None:
    """Проверяет стабильность демонстрационной выписки."""

    assert DEMO_STATEMENT_PATH.is_file()

    with DEMO_STATEMENT_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.reader(
            csv_file,
            delimiter=";",
        )

        rows = list(reader)

    assert rows

    header = rows[0]
    transactions = rows[1:]

    assert header == EXPECTED_HEADERS
    assert len(header) == 36
    assert len(transactions) == 877

    assert all(
        len(row) == len(header)
        for row in transactions
    )


def test_demo_statement_is_accepted_by_importer() -> None:
    """Проверяет демо-выписку через реальный импортёр."""

    result = read_tbank_csv(
        DEMO_STATEMENT_PATH
    )

    transactions = result.transactions

    assert result.warnings == ()
    assert len(transactions) == 877

    assert (
        transactions["posted_at"]
        .min()
        .date()
        == date(2024, 8, 1)
    )

    assert (
        transactions["posted_at"]
        .max()
        .date()
        == date(2026, 7, 31)
    )

    assert (
        transactions[
            "source_hash"
        ].is_unique
    )

    assert (
        transactions[
            "signed_amount_kopecks"
        ]
        .gt(0)
        .sum()
        == 357
    )

    assert (
        transactions[
            "signed_amount_kopecks"
        ]
        .lt(0)
        .sum()
        == 520
    )

    assert set(
        transactions[
            "bank_category"
        ].unique()
    ) == EXPECTED_BANK_CATEGORIES

    assert (
        transactions[
            "transaction_at"
        ]
        .isna()
        .sum()
        == 7
    )

    assert (
        transactions["mcc"]
        .ne("")
        .any()
    )

    assert (
        transactions["tax_code"]
        .ne("")
        .any()
    )
