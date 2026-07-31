from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import delete, func, select

from src.database import SessionLocal
from src.models import (
    BankTransaction,
    ImportBatch,
    ImportBatchTransaction,
)
from src.categories import (
    EXCLUDE_ACTION,
    INCLUDE_ACTION,
    UNDEFINED_ACTION
)


@dataclass(frozen=True)
class SaveResult:
    """Результат сохранения банковской выписки."""

    received: int
    inserted: int
    duplicates: int
    import_batch_id: int | None = None

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

def _serialize_warnings(
    warnings: tuple[str, ...],
) -> str | None:
    """Сериализует предупреждения импорта в JSON."""

    normalized_warnings = [
        str(warning).strip()
        for warning in warnings
        if str(warning).strip()
    ]

    if not normalized_warnings:
        return None

    return json.dumps(
        normalized_warnings,
        ensure_ascii=False,
    )


def _deserialize_warnings(
    value: str | None,
) -> str:
    """Преобразует JSON предупреждений в читаемый текст."""

    if not value:
        return ""

    try:
        warnings = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return str(value)

    if not isinstance(warnings, list):
        return str(warnings)

    return "\n".join(
        str(warning)
        for warning in warnings
    )

def _get_existing_transactions(
    session,
    source_hashes: list[str],
) -> dict[str, int]:
    """Возвращает соответствие source_hash → ID операции."""

    existing_transactions: dict[str, int] = {}

    # Не упираемся в лимит SQLite
    # на количество параметров одного запроса.
    chunk_size = 500

    unique_hashes = list(
        dict.fromkeys(source_hashes)
    )

    for start in range(
        0,
        len(unique_hashes),
        chunk_size,
    ):
        chunk = unique_hashes[
            start:start + chunk_size
        ]

        statement = select(
            BankTransaction.source_hash,
            BankTransaction.id,
        ).where(
            BankTransaction.source_hash.in_(
                chunk
            )
        )

        for source_hash, transaction_id in (
            session.execute(statement)
        ):
            existing_transactions[
                str(source_hash)
            ] = int(transaction_id)

    return existing_transactions

def save_transactions(
    transactions: pd.DataFrame,
    *,
    source_filename: str = "Неизвестный файл",
    source_size_bytes: int | None = None,
    source_sha256: str | None = None,
    warnings: tuple[str, ...] = (),
) -> SaveResult:
    """
    Сохраняет банковскую выписку и журнал импорта.

    Уже существующие операции определяются по source_hash
    и повторно не добавляются, но связываются с новым
    журналом импорта.
    """

    received = len(transactions)

    if transactions.empty:
        return SaveResult(
            received=0,
            inserted=0,
            duplicates=0,
            import_batch_id=None,
        )

    if "source_hash" not in transactions.columns:
        raise ValueError(
            "В данных отсутствует столбец source_hash."
        )

    source_hashes = (
        transactions["source_hash"]
        .astype(str)
        .tolist()
    )

    normalized_filename = (
        _optional_text(source_filename)
        or "Неизвестный файл"
    )

    normalized_file_hash = _optional_text(
        source_sha256
    )

    normalized_file_size = (
        int(source_size_bytes)
        if source_size_bytes is not None
        else None
    )

    with SessionLocal() as session:
        existing_transactions = (
            _get_existing_transactions(
                session,
                source_hashes,
            )
        )

        import_batch = ImportBatch(
            source_filename=normalized_filename,
            source_size_bytes=normalized_file_size,
            source_sha256=normalized_file_hash,
            received_count=received,
            inserted_count=0,
            duplicate_count=0,
            warnings_json=_serialize_warnings(
                warnings
            ),
        )

        session.add(import_batch)
        session.flush()

        new_transactions: list[
            BankTransaction
        ] = []

        new_hashes: set[str] = set()

        for _, row in transactions.iterrows():
            source_hash = str(
                row["source_hash"]
            )

            if source_hash in existing_transactions:
                continue

            # Дополнительная защита, если вызывающая сторона
            # передала дубли внутри одного DataFrame.
            if source_hash in new_hashes:
                continue

            posted_at = _optional_datetime(
                row["posted_at"]
            )

            if posted_at is None:
                raise ValueError(
                    "Операция не содержит дату проведения."
                )

            transaction = BankTransaction(
                source_hash=source_hash,
                account_number=_optional_text(
                    row["account_number"]
                ),
                direction=str(
                    row["direction"]
                ),
                bank_operation_type=_optional_text(
                    row["bank_operation_type"]
                ),
                bank_category=_optional_text(
                    row["bank_category"]
                ),
                bank_operation_kind=_optional_text(
                    row["bank_operation_kind"]
                ),
                status=_optional_text(
                    row["status"]
                ),
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
                currency=_optional_text(
                    row["currency"]
                ),
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
                mcc=_optional_text(
                    row["mcc"]
                ),
                tax_code=_optional_text(
                    row["tax_code"]
                ),
                classification_status=(
                    "unclassified"
                ),
            )

            session.add(transaction)
            new_transactions.append(
                transaction
            )
            new_hashes.add(source_hash)

        # После flush новые операции получают ID.
        session.flush()

        transaction_ids_by_hash = dict(
            existing_transactions
        )

        for transaction in new_transactions:
            transaction_ids_by_hash[
                transaction.source_hash
            ] = int(transaction.id)

        linked_transaction_ids: set[int] = set()

        for source_hash in source_hashes:
            transaction_id = (
                transaction_ids_by_hash.get(
                    source_hash
                )
            )

            if transaction_id is None:
                raise ValueError(
                    "Не удалось связать операцию "
                    "с журналом импорта."
                )

            if (
                transaction_id
                in linked_transaction_ids
            ):
                continue

            session.add(
                ImportBatchTransaction(
                    import_batch_id=(
                        import_batch.id
                    ),
                    transaction_id=(
                        transaction_id
                    ),
                )
            )

            linked_transaction_ids.add(
                transaction_id
            )

        inserted = len(new_transactions)
        duplicates = received - inserted

        import_batch.inserted_count = (
            inserted
        )

        import_batch.duplicate_count = (
            duplicates
        )

        session.commit()

        import_batch_id = int(
            import_batch.id
        )

    return SaveResult(
        received=received,
        inserted=inserted,
        duplicates=duplicates,
        import_batch_id=import_batch_id,
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
class ImportBatchDeleteResult:
    """Результат удаления одной загрузки."""

    import_batch_id: int
    links_deleted: int
    transactions_deleted: int


@dataclass(frozen=True)
class BankDataClearResult:
    """Результат очистки банковских данных."""

    import_batches_deleted: int
    links_deleted: int
    transactions_deleted: int


def get_import_batches_dataframe() -> pd.DataFrame:
    """Возвращает журнал загруженных выписок."""

    columns = [
        "id",
        "source_filename",
        "source_size_bytes",
        "source_sha256",
        "received_count",
        "inserted_count",
        "duplicate_count",
        "linked_transaction_count",
        "warnings",
        "imported_at",
    ]

    statement = select(
        ImportBatch
    ).order_by(
        ImportBatch.imported_at.desc(),
        ImportBatch.id.desc(),
    )

    with SessionLocal() as session:
        import_batches = (
            session.scalars(statement).all()
        )

        rows: list[dict[str, Any]] = []

        for import_batch in import_batches:
            linked_count = session.scalar(
                select(
                    func.count(
                        ImportBatchTransaction.transaction_id
                    )
                ).where(
                    ImportBatchTransaction.import_batch_id
                    == import_batch.id
                )
            )

            rows.append(
                {
                    "id": import_batch.id,
                    "source_filename":
                        import_batch.source_filename,
                    "source_size_bytes":
                        import_batch.source_size_bytes,
                    "source_sha256":
                        import_batch.source_sha256,
                    "received_count":
                        import_batch.received_count,
                    "inserted_count":
                        import_batch.inserted_count,
                    "duplicate_count":
                        import_batch.duplicate_count,
                    "linked_transaction_count":
                        int(linked_count or 0),
                    "warnings":
                        _deserialize_warnings(
                            import_batch.warnings_json
                        ),
                    "imported_at":
                        import_batch.imported_at,
                }
            )

    return pd.DataFrame(
        rows,
        columns=columns,
    )


def get_import_batch_transactions_dataframe(
    import_batch_id: int,
) -> pd.DataFrame:
    """Возвращает операции конкретной загрузки."""

    columns = [
        "id",
        "posted_at",
        "signed_amount_kopecks",
        "direction",
        "counterparty_name",
        "description",
        "payment_purpose",
        "classification_status",
    ]

    statement = (
        select(BankTransaction)
        .join(
            ImportBatchTransaction,
            (
                ImportBatchTransaction.transaction_id
                == BankTransaction.id
            ),
        )
        .where(
            ImportBatchTransaction.import_batch_id
            == int(import_batch_id)
        )
        .order_by(
            BankTransaction.posted_at.desc(),
            BankTransaction.id.desc(),
        )
    )

    with SessionLocal() as session:
        transactions = (
            session.scalars(statement).all()
        )

        rows = [
            {
                "id": transaction.id,
                "posted_at":
                    transaction.posted_at,
                "signed_amount_kopecks":
                    transaction.signed_amount_kopecks,
                "direction":
                    transaction.direction,
                "counterparty_name":
                    transaction.counterparty_name,
                "description":
                    transaction.description,
                "payment_purpose":
                    transaction.payment_purpose,
                "classification_status":
                    transaction.classification_status,
            }
            for transaction in transactions
        ]

    return pd.DataFrame(
        rows,
        columns=columns,
    )


def get_untracked_transaction_count() -> int:
    """
    Возвращает количество операций без журнала импорта.

    Это операции, созданные до появления import_batches.
    """

    link_exists = select(
        ImportBatchTransaction.transaction_id
    ).where(
        ImportBatchTransaction.transaction_id
        == BankTransaction.id
    ).exists()

    statement = select(
        func.count(BankTransaction.id)
    ).where(
        ~link_exists
    )

    with SessionLocal() as session:
        count = session.scalar(statement)

    return int(count or 0)


def delete_import_batch(
    import_batch_id: int,
) -> ImportBatchDeleteResult:
    """
    Удаляет одну загрузку.

    Операция удаляется только тогда, когда она больше
    не связана ни с одной другой загрузкой.
    """

    normalized_batch_id = int(
        import_batch_id
    )

    with SessionLocal() as session:
        import_batch = session.get(
            ImportBatch,
            normalized_batch_id,
        )

        if import_batch is None:
            raise ValueError(
                "Указанная загрузка не найдена."
            )

        transaction_ids = list(
            session.scalars(
                select(
                    ImportBatchTransaction.transaction_id
                ).where(
                    ImportBatchTransaction.import_batch_id
                    == normalized_batch_id
                )
            ).all()
        )

        session.execute(
            delete(
                ImportBatchTransaction
            ).where(
                ImportBatchTransaction.import_batch_id
                == normalized_batch_id
            )
        )

        session.flush()

        deleted_transactions = 0

        for transaction_id in set(
            int(value)
            for value in transaction_ids
        ):
            remaining_links = session.scalar(
                select(
                    func.count(
                        ImportBatchTransaction.import_batch_id
                    )
                ).where(
                    ImportBatchTransaction.transaction_id
                    == transaction_id
                )
            )

            if int(remaining_links or 0) > 0:
                continue

            transaction = session.get(
                BankTransaction,
                transaction_id,
            )

            if transaction is not None:
                session.delete(transaction)
                deleted_transactions += 1

        session.delete(import_batch)
        session.commit()

    return ImportBatchDeleteResult(
        import_batch_id=normalized_batch_id,
        links_deleted=len(
            set(transaction_ids)
        ),
        transactions_deleted=(
            deleted_transactions
        ),
    )


def delete_untracked_transactions() -> int:
    """
    Удаляет операции, не относящиеся ни к одному импорту.

    Правила, календарь и Unit Economics не затрагиваются.
    """

    link_exists = select(
        ImportBatchTransaction.transaction_id
    ).where(
        ImportBatchTransaction.transaction_id
        == BankTransaction.id
    ).exists()

    statement = select(
        BankTransaction
    ).where(
        ~link_exists
    )

    with SessionLocal() as session:
        transactions = list(
            session.scalars(statement).all()
        )

        deleted_count = len(transactions)

        for transaction in transactions:
            session.delete(transaction)

        session.commit()

    return deleted_count


def clear_bank_data() -> BankDataClearResult:
    """
    Удаляет все банковские операции и журналы импортов.

    Не удаляет правила классификации, платёжный календарь
    и данные Unit Economics.
    """

    with SessionLocal() as session:
        import_batch_count = session.scalar(
            select(
                func.count(ImportBatch.id)
            )
        )

        link_count = session.scalar(
            select(
                func.count(
                    ImportBatchTransaction.transaction_id
                )
            )
        )

        transaction_count = session.scalar(
            select(
                func.count(BankTransaction.id)
            )
        )

        session.execute(
            delete(ImportBatchTransaction)
        )

        session.execute(
            delete(BankTransaction)
        )

        session.execute(
            delete(ImportBatch)
        )

        session.commit()

    return BankDataClearResult(
        import_batches_deleted=int(
            import_batch_count or 0
        ),
        links_deleted=int(
            link_count or 0
        ),
        transactions_deleted=int(
            transaction_count or 0
        ),
    )

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