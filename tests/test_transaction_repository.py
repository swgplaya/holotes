from datetime import datetime

import pandas as pd
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

import src.transaction_repository as transaction_repository
from src.categories import (
    EXCLUDE_ACTION,
    INCLUDE_ACTION,
    UNDEFINED_ACTION,
)
from src.models import (
    BankTransaction,
    ClassificationRule,
    ImportBatch,
    ImportBatchTransaction,
)


TRANSACTION_COLUMNS = [
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


def make_transaction(
    number: int,
    **overrides: object,
) -> dict[str, object]:
    """Создаёт нормализованную банковскую операцию."""

    transaction: dict[str, object] = {
        "source_hash": str(number) * 64,
        "account_number": " 40817810000000000001 ",
        "direction": (
            "Пополнение"
            if number % 2
            else "Списание"
        ),
        "bank_operation_type": "Перевод",
        "bank_category": "Прочее",
        "bank_operation_kind": None,
        "status": "OK",
        "posted_at": datetime(
            2026,
            1,
            number,
            12,
            0,
        ),
        "transaction_at": None,
        "payment_number": None,
        "amount_kopecks": number * 10_000,
        "signed_amount_kopecks": (
            number * 10_000
            if number % 2
            else -number * 10_000
        ),
        "currency": "RUB",
        "description": f"Операция {number}",
        "payment_purpose": None,
        "counterparty_inn": None,
        "counterparty_name": f"Контрагент {number}",
        "mcc": None,
        "tax_code": None,
    }

    transaction.update(overrides)

    return transaction


def make_transactions(
    *rows: dict[str, object],
) -> pd.DataFrame:
    """Создаёт DataFrame с полным набором столбцов импорта."""

    return pd.DataFrame(
        rows,
        columns=TRANSACTION_COLUMNS,
    )


@pytest.fixture
def isolated_repository(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_session_factory: sessionmaker,
) -> sessionmaker:
    """Переключает репозиторий операций на временную базу."""

    monkeypatch.setattr(
        transaction_repository,
        "SessionLocal",
        sqlite_session_factory,
    )

    return sqlite_session_factory


def test_empty_import_creates_nothing(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    result = transaction_repository.save_transactions(
        make_transactions()
    )

    assert result == transaction_repository.SaveResult(
        received=0,
        inserted=0,
        duplicates=0,
        import_batch_id=None,
    )

    assert (
        transaction_repository
        .get_transactions_dataframe()
        .empty
    )

    assert (
        transaction_repository
        .get_import_batches_dataframe()
        .empty
    )

def test_transaction_count_tracks_saved_and_cleared_data(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    assert (
        transaction_repository
        .get_transaction_count()
        == 0
    )

    transaction_repository.save_transactions(
        make_transactions(
            make_transaction(1),
            make_transaction(2),
        ),
        source_filename="first.csv",
    )

    assert (
        transaction_repository
        .get_transaction_count()
        == 2
    )

    transaction_repository.save_transactions(
        make_transactions(
            make_transaction(2),
            make_transaction(3),
        ),
        source_filename="second.csv",
    )

    assert (
        transaction_repository
        .get_transaction_count()
        == 3
    )

    transaction_repository.clear_bank_data()

    assert (
        transaction_repository
        .get_transaction_count()
        == 0
    )

def test_save_import_and_read_journal(
    isolated_repository: sessionmaker,
) -> None:
    result = transaction_repository.save_transactions(
        make_transactions(
            make_transaction(1),
            make_transaction(2),
        ),
        source_filename="  january.csv  ",
        source_size_bytes=1_024,
        source_sha256="a" * 64,
        warnings=(
            "Предупреждение 1",
            "",
            "Предупреждение 2",
        ),
    )

    assert result.received == 2
    assert result.inserted == 2
    assert result.duplicates == 0
    assert result.import_batch_id is not None

    transactions = (
        transaction_repository
        .get_transactions_dataframe()
    )

    assert transactions[
        "source_hash"
    ].tolist() == [
        "2" * 64,
        "1" * 64,
    ]

    with isolated_repository() as session:
        saved_first = session.scalar(
            select(BankTransaction).where(
                BankTransaction.source_hash
                == "1" * 64
            )
        )

    assert saved_first is not None
    assert saved_first.account_number == (
        "40817810000000000001"
    )

    assert transactions[
        "classification_status"
    ].tolist() == [
        "unclassified",
        "unclassified",
    ]

    batches = (
        transaction_repository
        .get_import_batches_dataframe()
    )

    assert len(batches) == 1

    batch = batches.iloc[0]

    assert batch["source_filename"] == "january.csv"
    assert batch["source_size_bytes"] == 1_024
    assert batch["source_sha256"] == "a" * 64
    assert batch["received_count"] == 2
    assert batch["inserted_count"] == 2
    assert batch["duplicate_count"] == 0
    assert batch["linked_transaction_count"] == 2

    assert batch["warnings"] == (
        "Предупреждение 1\n"
        "Предупреждение 2"
    )

    batch_transactions = (
        transaction_repository
        .get_import_batch_transactions_dataframe(
            int(result.import_batch_id)
        )
    )

    assert len(batch_transactions) == 2

    assert batch_transactions[
        "signed_amount_kopecks"
    ].tolist() == [
        -20_000,
        10_000,
    ]


def test_duplicate_imports_link_existing_transactions(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    first = transaction_repository.save_transactions(
        make_transactions(
            make_transaction(1),
            make_transaction(2),
        ),
        source_filename="first.csv",
    )

    second = transaction_repository.save_transactions(
        make_transactions(
            make_transaction(2),
            make_transaction(3),
            make_transaction(3),
        ),
        source_filename="second.csv",
    )

    assert first.inserted == 2
    assert first.duplicates == 0

    assert second.received == 3
    assert second.inserted == 1
    assert second.duplicates == 2

    transactions = (
        transaction_repository
        .get_transactions_dataframe()
    )

    assert set(transactions["source_hash"]) == {
        "1" * 64,
        "2" * 64,
        "3" * 64,
    }

    batches = (
        transaction_repository
        .get_import_batches_dataframe()
        .set_index("source_filename")
    )

    assert batches.loc[
        "first.csv",
        "linked_transaction_count",
    ] == 2

    assert batches.loc[
        "second.csv",
        "linked_transaction_count",
    ] == 2


def test_delete_batches_preserves_shared_then_removes_orphans(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    first = transaction_repository.save_transactions(
        make_transactions(
            make_transaction(1),
            make_transaction(2),
        ),
        source_filename="first.csv",
    )

    second = transaction_repository.save_transactions(
        make_transactions(
            make_transaction(2),
            make_transaction(3),
        ),
        source_filename="second.csv",
    )

    first_delete = (
        transaction_repository.delete_import_batch(
            int(first.import_batch_id)
        )
    )

    assert first_delete.links_deleted == 2
    assert first_delete.transactions_deleted == 1

    remaining = (
        transaction_repository
        .get_transactions_dataframe()
    )

    assert set(remaining["source_hash"]) == {
        "2" * 64,
        "3" * 64,
    }

    second_delete = (
        transaction_repository.delete_import_batch(
            int(second.import_batch_id)
        )
    )

    assert second_delete.links_deleted == 2
    assert second_delete.transactions_deleted == 2

    assert (
        transaction_repository
        .get_transactions_dataframe()
        .empty
    )

    with pytest.raises(
        ValueError,
        match="загрузка не найдена",
    ):
        transaction_repository.delete_import_batch(
            int(second.import_batch_id)
        )


def test_save_classifications_sets_statuses_and_sources(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    transaction_repository.save_transactions(
        make_transactions(
            make_transaction(1),
            make_transaction(2),
            make_transaction(3),
        )
    )

    transactions = (
        transaction_repository
        .get_transactions_dataframe()
        .set_index("source_hash")
    )

    result = transaction_repository.save_classifications(
        pd.DataFrame(
            [
                {
                    "id": int(
                        transactions.loc[
                            "1" * 64,
                            "id",
                        ]
                    ),
                    "pnl_action": INCLUDE_ACTION,
                    "pnl_category": "Выручка",
                    "cf_action": EXCLUDE_ACTION,
                    "cf_category": "",
                    "comment": "  Проверено  ",
                },
                {
                    "id": int(
                        transactions.loc[
                            "2" * 64,
                            "id",
                        ]
                    ),
                    "pnl_action": INCLUDE_ACTION,
                    "pnl_category": "Расходы",
                    "cf_action": UNDEFINED_ACTION,
                    "cf_category": "",
                    "comment": None,
                },
                {
                    "id": int(
                        transactions.loc[
                            "3" * 64,
                            "id",
                        ]
                    ),
                    "pnl_action": UNDEFINED_ACTION,
                    "pnl_category": "",
                    "cf_action": UNDEFINED_ACTION,
                    "cf_category": "",
                    "comment": "",
                },
            ]
        )
    )

    assert result == (
        transaction_repository.ClassificationSaveResult(
            received=3,
            updated=3,
            classified=1,
            partial=1,
            unclassified=1,
        )
    )

    saved = (
        transaction_repository
        .get_transactions_dataframe()
        .set_index("source_hash")
    )

    classified = saved.loc["1" * 64]

    assert bool(classified["include_in_pnl"]) is True
    assert bool(classified["include_in_cf"]) is False
    assert classified["pnl_category"] == "Выручка"
    assert classified["cf_category"] is None
    assert classified["classification_status"] == "classified"
    assert classified["classification_source"] == "manual"
    assert classified["comment"] == "Проверено"

    partial = saved.loc["2" * 64]

    assert partial["classification_status"] == "partial"
    assert partial["classification_source"] == "manual"

    unclassified = saved.loc["3" * 64]

    assert (
        unclassified["classification_status"]
        == "unclassified"
    )

    assert pd.isna(
        unclassified["classification_source"]
    )


def test_invalid_classification_rolls_back_all_rows(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    transaction_repository.save_transactions(
        make_transactions(
            make_transaction(1),
            make_transaction(2),
        )
    )

    transactions = (
        transaction_repository
        .get_transactions_dataframe()
        .set_index("source_hash")
    )

    classifications = pd.DataFrame(
        [
            {
                "id": int(
                    transactions.loc[
                        "1" * 64,
                        "id",
                    ]
                ),
                "pnl_action": EXCLUDE_ACTION,
                "pnl_category": "",
                "cf_action": EXCLUDE_ACTION,
                "cf_category": "",
                "comment": "Изменение",
            },
            {
                "id": int(
                    transactions.loc[
                        "2" * 64,
                        "id",
                    ]
                ),
                "pnl_action": INCLUDE_ACTION,
                "pnl_category": "",
                "cf_action": EXCLUDE_ACTION,
                "cf_category": "",
                "comment": "Ошибка",
            },
        ]
    )

    with pytest.raises(
        ValueError,
        match="для включения в P&L",
    ):
        transaction_repository.save_classifications(
            classifications
        )

    saved = (
        transaction_repository
        .get_transactions_dataframe()
    )

    assert saved[
        "classification_status"
    ].tolist() == [
        "unclassified",
        "unclassified",
    ]

    assert saved[
        "classification_source"
    ].isna().all()


def test_untracked_transactions_can_be_counted_and_deleted(
    isolated_repository: sessionmaker,
) -> None:
    transaction_repository.save_transactions(
        make_transactions(
            make_transaction(1),
        )
    )

    with isolated_repository() as session:
        session.add(
            BankTransaction(
                source_hash="9" * 64,
                direction="Списание",
                posted_at=datetime(
                    2026,
                    1,
                    9,
                ),
                amount_kopecks=9_000,
                signed_amount_kopecks=-9_000,
                classification_status="unclassified",
            )
        )

        session.commit()

    assert (
        transaction_repository
        .get_untracked_transaction_count()
        == 1
    )

    assert (
        transaction_repository
        .delete_untracked_transactions()
        == 1
    )

    assert (
        transaction_repository
        .get_untracked_transaction_count()
        == 0
    )

    remaining = (
        transaction_repository
        .get_transactions_dataframe()
    )

    assert remaining["source_hash"].tolist() == [
        "1" * 64,
    ]


def test_clear_bank_data_preserves_classification_rules(
    isolated_repository: sessionmaker,
) -> None:
    transaction_repository.save_transactions(
        make_transactions(
            make_transaction(1),
            make_transaction(2),
        ),
        source_filename="first.csv",
    )

    transaction_repository.save_transactions(
        make_transactions(
            make_transaction(2),
        ),
        source_filename="second.csv",
    )

    with isolated_repository() as session:
        session.add(
            ClassificationRule(
                name="Сохраняемое правило",
                priority=100,
                is_active=True,
                direction_filter="any",
                match_field="description",
                match_type="contains",
                match_value="тест",
                include_in_pnl=False,
                pnl_category=None,
                include_in_cf=None,
                cf_category=None,
            )
        )

        session.commit()

    result = transaction_repository.clear_bank_data()

    assert result == (
        transaction_repository.BankDataClearResult(
            import_batches_deleted=2,
            links_deleted=3,
            transactions_deleted=2,
        )
    )

    assert (
        transaction_repository
        .get_transactions_dataframe()
        .empty
    )

    assert (
        transaction_repository
        .get_import_batches_dataframe()
        .empty
    )

    with isolated_repository() as session:
        rule_count = session.scalar(
            select(
                func.count(
                    ClassificationRule.id
                )
            )
        )

        batch_count = session.scalar(
            select(
                func.count(
                    ImportBatch.id
                )
            )
        )

        link_count = session.scalar(
            select(
                func.count(
                    ImportBatchTransaction.transaction_id
                )
            )
        )

    assert rule_count == 1
    assert batch_count == 0
    assert link_count == 0


def test_invalid_import_rolls_back_batch(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    with pytest.raises(
        ValueError,
        match="не содержит дату проведения",
    ):
        transaction_repository.save_transactions(
            make_transactions(
                make_transaction(
                    1,
                    posted_at=None,
                )
            ),
            source_filename="broken.csv",
        )

    assert (
        transaction_repository
        .get_transactions_dataframe()
        .empty
    )

    assert (
        transaction_repository
        .get_import_batches_dataframe()
        .empty
    )