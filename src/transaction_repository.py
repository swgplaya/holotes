from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import select

from src.database import SessionLocal
from src.models import BankTransaction
from src.categories import (
    EXCLUDE_ACTION,
    INCLUDE_ACTION,
    UNDEFINED_ACTION
)


@dataclass(frozen=True)
class SaveResult:
    """Результат сохранения операций."""

    received: int
    inserted: int
    duplicates: int


def _optional_text(value: Any) -> str | None:
    """Возвращает очищенный текст либо None."""

    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    return text or None


def _optional_datetime(value: Any) -> datetime | None:
    """Преобразует pandas Timestamp в стандартный datetime."""

    if value is None or pd.isna(value):
        return None

    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()

    if isinstance(value, datetime):
        return value

    return pd.to_datetime(value).to_pydatetime()


def _get_existing_hashes(
    session,
    source_hashes: list[str],
) -> set[str]:
    """Получает хеши операций, уже находящихся в базе."""

    existing_hashes: set[str] = set()

    # Разбиваем список, чтобы не упереться в лимит SQLite
    # на количество параметров одного запроса.
    chunk_size = 500

    for start in range(0, len(source_hashes), chunk_size):
        chunk = source_hashes[start : start + chunk_size]

        statement = select(
            BankTransaction.source_hash
        ).where(
            BankTransaction.source_hash.in_(chunk)
        )

        existing_hashes.update(
            session.scalars(statement).all()
        )

    return existing_hashes


def save_transactions(
    transactions: pd.DataFrame,
) -> SaveResult:
    """
    Сохраняет новые операции.

    Уже существующие операции определяются по source_hash
    и повторно не добавляются.
    """

    received = len(transactions)

    if transactions.empty:
        return SaveResult(
            received=0,
            inserted=0,
            duplicates=0,
        )

    source_hashes = (
        transactions["source_hash"]
        .astype(str)
        .tolist()
    )

    with SessionLocal() as session:
        existing_hashes = _get_existing_hashes(
            session,
            source_hashes,
        )

        objects: list[BankTransaction] = []

        for _, row in transactions.iterrows():
            source_hash = str(row["source_hash"])

            if source_hash in existing_hashes:
                continue

            posted_at = _optional_datetime(row["posted_at"])

            if posted_at is None:
                raise ValueError(
                    "Операция не содержит дату проведения."
                )

            transaction = BankTransaction(
                source_hash=source_hash,
                account_number=_optional_text(
                    row["account_number"]
                ),
                direction=str(row["direction"]),
                bank_operation_type=_optional_text(
                    row["bank_operation_type"]
                ),
                bank_category=_optional_text(
                    row["bank_category"]
                ),
                bank_operation_kind=_optional_text(
                    row["bank_operation_kind"]
                ),
                status=_optional_text(row["status"]),
                posted_at=posted_at,
                transaction_at=_optional_datetime(
                    row["transaction_at"]
                ),
                payment_number=_optional_text(
                    row["payment_number"]
                ),
                amount_kopecks=int(
                    row["amount_kopecks"]
                ),
                signed_amount_kopecks=int(
                    row["signed_amount_kopecks"]
                ),
                currency=_optional_text(row["currency"]),
                description=_optional_text(
                    row["description"]
                ),
                payment_purpose=_optional_text(
                    row["payment_purpose"]
                ),
                counterparty_inn=_optional_text(
                    row["counterparty_inn"]
                ),
                counterparty_name=_optional_text(
                    row["counterparty_name"]
                ),
                mcc=_optional_text(row["mcc"]),
                tax_code=_optional_text(row["tax_code"]),
                classification_status="unclassified",
            )

            objects.append(transaction)

        session.add_all(objects)
        session.commit()

    inserted = len(objects)

    return SaveResult(
        received=received,
        inserted=inserted,
        duplicates=received - inserted,
    )


def get_transactions_dataframe() -> pd.DataFrame:
    """Возвращает все операции из SQLite как DataFrame."""

    columns = [
        "id",
        "source_hash",
        "posted_at",
        "transaction_at",
        "signed_amount_kopecks",
        "direction",
        "bank_category",
        "status",
        "counterparty_name",
        "counterparty_inn",
        "description",
        "payment_purpose",
        "pnl_category",
        "cf_category",
        "include_in_pnl",
        "include_in_cf",
        "classification_status",
        "classification_source",
        "comment",
    ]

    statement = select(
        BankTransaction
    ).order_by(
        BankTransaction.posted_at.desc(),
        BankTransaction.id.desc(),
    )

    with SessionLocal() as session:
        transactions = session.scalars(statement).all()

        rows = [
            {
                "id": transaction.id,
                "source_hash": transaction.source_hash,
                "posted_at": transaction.posted_at,
                "transaction_at": transaction.transaction_at,
                "signed_amount_kopecks":
                    transaction.signed_amount_kopecks,
                "direction": transaction.direction,
                "bank_category": transaction.bank_category,
                "status": transaction.status,
                "counterparty_name":
                    transaction.counterparty_name,
                "counterparty_inn":
                    transaction.counterparty_inn,
                "description": transaction.description,
                "payment_purpose":
                    transaction.payment_purpose,
                "pnl_category": transaction.pnl_category,
                "cf_category": transaction.cf_category,
                "classification_status":
                    transaction.classification_status,
                "include_in_pnl":
                    transaction.include_in_pnl,
                "include_in_cf":
                    transaction.include_in_cf,
                "classification_source":
                    transaction.classification_source,
                "comment":
                    transaction.comment,
            }
            for transaction in transactions
        ]

    return pd.DataFrame(rows, columns=columns)

@dataclass(frozen=True)
class ClassificationSaveResult:
    """Результат сохранения ручной классификации."""

    received: int
    updated: int
    classified: int
    partial: int
    unclassified: int


def _action_to_bool(value: Any) -> bool | None:
    """Преобразует решение пользователя во внутреннее значение."""

    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    if text == INCLUDE_ACTION:
        return True

    if text == EXCLUDE_ACTION:
        return False

    if text == UNDEFINED_ACTION or not text:
        return None

    raise ValueError(
        f"Неизвестное решение по операции: {value!r}"
    )


def _get_classification_status(
    include_in_pnl: bool | None,
    include_in_cf: bool | None,
) -> str:
    """Определяет полноту классификации операции."""

    if (
        include_in_pnl is not None
        and include_in_cf is not None
    ):
        return "classified"

    if (
        include_in_pnl is not None
        or include_in_cf is not None
    ):
        return "partial"

    return "unclassified"


def save_classifications(
    classifications: pd.DataFrame,
) -> ClassificationSaveResult:
    """Сохраняет решения пользователя по P&L и Cash Flow."""

    required_columns = {
        "id",
        "pnl_action",
        "pnl_category",
        "cf_action",
        "cf_category",
        "comment",
    }

    missing_columns = (
        required_columns - set(classifications.columns)
    )

    if missing_columns:
        raise ValueError(
            "Не хватает столбцов классификации: "
            + ", ".join(sorted(missing_columns))
        )

    received = len(classifications)
    updated = 0
    classified = 0
    partial = 0
    unclassified = 0

    errors: list[str] = []

    with SessionLocal() as session:
        for _, row in classifications.iterrows():
            row_errors: list[str] = []

            transaction_id = int(row["id"])

            transaction = session.get(
                BankTransaction,
                transaction_id,
            )

            if transaction is None:
                errors.append(
                    f"Операция с ID {transaction_id} не найдена."
                )
                continue

            include_in_pnl = _action_to_bool(
                row["pnl_action"]
            )
            include_in_cf = _action_to_bool(
                row["cf_action"]
            )

            pnl_category = _optional_text(
                row["pnl_category"]
            )
            cf_category = _optional_text(
                row["cf_category"]
            )

            if (
                    include_in_pnl is True
                    and pnl_category is None
            ):
                row_errors.append(
                    f"ID {transaction_id}: "
                    "для включения в P&L выбери категорию."
                )

            if (
                    include_in_cf is True
                    and cf_category is None
            ):
                row_errors.append(
                    f"ID {transaction_id}: "
                    "для включения в Cash Flow выбери категорию."
                )

            if row_errors:
                errors.extend(row_errors)
                continue

            status = _get_classification_status(
                include_in_pnl=include_in_pnl,
                include_in_cf=include_in_cf,
            )

            transaction.include_in_pnl = include_in_pnl
            transaction.include_in_cf = include_in_cf
            transaction.pnl_category = pnl_category
            transaction.cf_category = cf_category
            transaction.comment = _optional_text(
                row["comment"]
            )
            transaction.classification_status = status

            if status == "unclassified":
                transaction.classification_source = None
                unclassified += 1
            else:
                transaction.classification_source = "manual"

                if status == "classified":
                    classified += 1
                else:
                    partial += 1

            updated += 1

        if errors:
            session.rollback()

            raise ValueError(
                "\n".join(errors)
            )

        session.commit()

    return ClassificationSaveResult(
        received=received,
        updated=updated,
        classified=classified,
        partial=partial,
        unclassified=unclassified,
    )