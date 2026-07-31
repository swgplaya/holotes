from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import IO, Any

import pandas as pd


class BankStatementError(ValueError):
    """Ошибка структуры или содержимого банковской выписки."""


@dataclass(frozen=True)
class ImportResult:
    """Результат импорта банковской выписки."""

    transactions: pd.DataFrame
    warnings: tuple[str, ...]


COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "account_number": (
        "Номер счёта",
        "Номер счета",
    ),
    "direction": (
        "Тип операции (пополнение/списание)",
        "Дебет/Кредит",
    ),
    "bank_operation_type": (
        "Тип операции",
    ),
    "bank_category": (
        "Категория операции",
    ),
    "bank_operation_kind": (
        "Вид операции",
    ),
    "status": (
        "Статус",
        "Статус операции",
    ),
    "posted_at": (
        "Дата проведения",
    ),
    "transaction_at": (
        "Дата транзакции",
    ),
    "payment_number": (
        "Номер платежа",
        "Номер документа",
    ),
    "amount": (
        "Сумма в валюте счёта",
        "Сумма в валюте счета",
    ),
    "currency": (
        "Валюта счёта",
        "Валюта счета",
    ),
    "description": (
        "Описание операции",
    ),
    "payment_purpose": (
        "Назначение платежа",
    ),
    "counterparty_inn": (
        "ИНН контрагента",
    ),
    "counterparty_name": (
        "Наименование контрагента",
    ),
    "mcc": (
        "MCC",
        "MCC-код",
        "МСС",
        "МСС-код",
    ),
    "tax_code": (
        "КБК",
        "КБК-код бюджетной классификации",
    ),
}

REQUIRED_FIELDS = {
    "direction",
    "posted_at",
    "amount",
}


def _normalize_label(value: Any) -> str:
    """Нормализует заголовок или текст для сопоставления."""

    text = str(value).replace("\ufeff", "").replace("ё", "е").strip()
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def _resolve_columns(columns: pd.Index) -> dict[str, str]:
    """Сопоставляет реальные заголовки CSV с внутренними названиями."""

    normalized_columns = {
        _normalize_label(column): str(column)
        for column in columns
    }

    resolved: dict[str, str] = {}

    for internal_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            actual_column = normalized_columns.get(_normalize_label(alias))

            if actual_column is not None:
                resolved[internal_name] = actual_column
                break

    missing = sorted(REQUIRED_FIELDS - resolved.keys())

    if missing:
        readable_names = {
            internal_name: COLUMN_ALIASES[internal_name][0]
            for internal_name in missing
        }

        raise BankStatementError(
            "В выписке отсутствуют обязательные столбцы: "
            + ", ".join(readable_names.values())
        )

    return resolved


def _parse_money_to_kopecks(value: Any, row_number: int) -> int:
    """Преобразует российский формат суммы в целое число копеек."""

    text = str(value).strip()
    text = text.replace("\u00a0", "").replace(" ", "")

    # В российском CSV запятая обычно является десятичным разделителем.
    if "," in text:
        text = text.replace(".", "").replace(",", ".")

    text = re.sub(r"[^0-9.\-]", "", text)

    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise BankStatementError(
            f"Не удалось прочитать сумму в строке {row_number}: {value!r}"
        ) from exc

    kopecks = (
        abs(amount)
        * Decimal("100")
    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    return int(kopecks)


def _get_direction_sign(value: Any, row_number: int) -> int:
    """Возвращает +1 для поступления и -1 для списания."""

    text = _normalize_label(value)

    income_markers = (
        "кредит",
        "пополнение",
        "поступление",
        "приход",
        "credit",
    )
    expense_markers = (
        "дебет",
        "списание",
        "расход",
        "debit",
    )

    if any(marker in text for marker in income_markers):
        return 1

    if any(marker in text for marker in expense_markers):
        return -1

    raise BankStatementError(
        f"Неизвестный тип движения в строке {row_number}: {value!r}"
    )


def _make_source_hash(row: pd.Series) -> str:
    """Создаёт стабильный идентификатор для защиты от дублей."""

    posted_at = row["posted_at"]

    if pd.isna(posted_at):
        posted_at_text = ""
    else:
        posted_at_text = posted_at.isoformat()

    values = (
        row["account_number"],
        row["payment_number"],
        posted_at_text,
        row["direction"],
        str(row["amount_kopecks"]),
        row["currency"],
        row["description"],
        row["payment_purpose"],
        row["counterparty_inn"],
        row["counterparty_name"],
    )

    payload = "\x1f".join(str(value) for value in values)

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_tbank_csv(
    source: str | Path | IO[str] | IO[bytes],
) -> ImportResult:
    """
    Читает CSV-выписку Т-Бизнеса и преобразует её
    во внутренний формат Open MAS.
    """

    try:
        raw = pd.read_csv(
            source,
            sep=";",
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
            na_filter=False,
            on_bad_lines="error",
        )
    except (UnicodeDecodeError, pd.errors.ParserError) as exc:
        raise BankStatementError(
            "Не удалось прочитать CSV. Проверь кодировку и разделитель файла."
        ) from exc

    if raw.empty:
        raise BankStatementError("Выписка не содержит операций.")

    raw.columns = [
        str(column).replace("\ufeff", "").strip()
        for column in raw.columns
    ]

    resolved = _resolve_columns(raw.columns)

    transactions = pd.DataFrame(index=raw.index)

    for internal_name in COLUMN_ALIASES:
        source_column = resolved.get(internal_name)

        if source_column is None:
            transactions[internal_name] = ""
        else:
            transactions[internal_name] = (
                raw[source_column]
                .astype(str)
                .str.strip()
            )

    transactions["posted_at"] = pd.to_datetime(
        transactions["posted_at"],
        dayfirst=True,
        errors="coerce",
    )

    invalid_posted_dates = transactions["posted_at"].isna()

    if invalid_posted_dates.any():
        rows = [
            str(index + 2)
            for index in transactions.index[invalid_posted_dates][:5]
        ]
        raise BankStatementError(
            "Не удалось прочитать дату проведения в строках: "
            + ", ".join(rows)
        )

    transactions["transaction_at"] = pd.to_datetime(
        transactions["transaction_at"].replace("", pd.NA),
        dayfirst=True,
        errors="coerce",
    )

    amount_kopecks: list[int] = []
    signed_amount_kopecks: list[int] = []

    for index, row in transactions.iterrows():
        csv_row_number = int(index) + 2

        amount = _parse_money_to_kopecks(
            row["amount"],
            csv_row_number,
        )
        sign = _get_direction_sign(
            row["direction"],
            csv_row_number,
        )

        amount_kopecks.append(amount)
        signed_amount_kopecks.append(amount * sign)

    transactions["amount_kopecks"] = amount_kopecks
    transactions["signed_amount_kopecks"] = signed_amount_kopecks

    transactions["source_hash"] = transactions.apply(
        _make_source_hash,
        axis=1,
    )

    warnings: list[str] = []

    duplicate_mask = transactions.duplicated(
        subset=["source_hash"],
        keep="first",
    )
    duplicate_count = int(duplicate_mask.sum())

    if duplicate_count:
        warnings.append(
            f"Внутри файла найдено повторных операций: {duplicate_count}. "
            "Они были удалены."
        )
        transactions = transactions.loc[~duplicate_mask].copy()

    for identifier_column, readable_name in (
        ("account_number", "номере счёта"),
        ("counterparty_inn", "ИНН контрагента"),
    ):
        scientific_notation = transactions[
            identifier_column
        ].str.contains(
            r"[eE][+\-]?\d+$",
            regex=True,
            na=False,
        )

        if scientific_notation.any():
            warnings.append(
                f"В {readable_name} обнаружена научная запись. "
                "Вероятно, файл ранее открывался и сохранялся через Excel."
            )

    output_columns = [
        "source_hash",
        "account_number",
        "direction",
        "bank_operation_type",
        "bank_category",
        "bank_operation_kind",
        "status",
        "posted_at",
        "transaction_at",
        "payment_number",
        "amount_kopecks",
        "signed_amount_kopecks",
        "currency",
        "description",
        "payment_purpose",
        "counterparty_inn",
        "counterparty_name",
        "mcc",
        "tax_code",
    ]

    transactions = (
        transactions[output_columns]
        .sort_values(
            by=["posted_at", "payment_number"],
            kind="stable",
        )
        .reset_index(drop=True)
    )

    return ImportResult(
        transactions=transactions,
        warnings=tuple(warnings),
    )