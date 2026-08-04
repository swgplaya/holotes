from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

import src.rule_repository as rule_repository
from src.categories import (
    EXCLUDE_ACTION,
    INCLUDE_ACTION,
    UNDEFINED_ACTION,
)
from src.models import (
    BankTransaction,
)


def make_rule_record(
    **overrides: object,
) -> dict[str, object]:
    """Создаёт переносимую конфигурацию правила."""

    record: dict[str, object] = {
        "name": "Банковские комиссии",
        "priority": 100,
        "is_active": True,
        "direction_filter": "expense",
        "match_field": "description",
        "match_type": "contains",
        "match_value": "комиссия",
        "pnl_action": EXCLUDE_ACTION,
        "pnl_category": "",
        "cf_action": INCLUDE_ACTION,
        "cf_category": "Банковские расходы",
    }

    record.update(overrides)

    return record


@pytest.fixture
def isolated_repository(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_session_factory: sessionmaker,
) -> sessionmaker:
    """Переключает репозиторий на временную базу."""

    monkeypatch.setattr(
        rule_repository,
        "SessionLocal",
        sqlite_session_factory,
    )

    return sqlite_session_factory


def create_rule_from_record(
    record: dict[str, object],
) -> int:
    """Создаёт правило через публичную функцию репозитория."""

    return rule_repository.create_rule(
        name=str(record["name"]),
        priority=int(record["priority"]),
        is_active=bool(record["is_active"]),
        direction_filter=str(
            record["direction_filter"]
        ),
        match_field=str(
            record["match_field"]
        ),
        match_type=str(
            record["match_type"]
        ),
        match_value=str(
            record["match_value"]
        ),
        pnl_action=str(
            record["pnl_action"]
        ),
        pnl_category=str(
            record["pnl_category"]
        ),
        cf_action=str(
            record["cf_action"]
        ),
        cf_category=str(
            record["cf_category"]
        ),
    )


def test_create_and_get_rules_orders_by_priority(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    low_id = create_rule_from_record(
        make_rule_record(
            name="Низкий приоритет",
            priority=10,
        )
    )

    high_id = create_rule_from_record(
        make_rule_record(
            name="Высокий приоритет",
            priority=500,
            match_value="обслуживание",
        )
    )

    assert low_id > 0
    assert high_id > low_id

    rules = (
        rule_repository.get_rules_dataframe()
    )

    assert rules["name"].tolist() == [
        "Высокий приоритет",
        "Низкий приоритет",
    ]

    assert rules["priority"].tolist() == [
        500,
        10,
    ]

    assert (
        rules.iloc[0]["direction_filter"]
        == "Только списания"
    )

    assert (
        rules.iloc[0]["match_type"]
        == "Содержит"
    )

    assert (
        rules.iloc[0]["pnl_action"]
        == EXCLUDE_ACTION
    )

    assert (
        rules.iloc[0]["cf_action"]
        == INCLUDE_ACTION
    )


def test_create_rule_validates_required_decisions(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    with pytest.raises(
        ValueError,
        match="хотя бы для одного отчёта",
    ):
        rule_repository.create_rule(
            name="Пустое решение",
            priority=100,
            is_active=True,
            direction_filter="any",
            match_field="description",
            match_type="contains",
            match_value="тест",
            pnl_action=UNDEFINED_ACTION,
            pnl_category="",
            cf_action=UNDEFINED_ACTION,
            cf_category="",
        )


def test_set_active_and_delete_rule(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    rule_id = create_rule_from_record(
        make_rule_record()
    )

    rule_repository.set_rule_active(
        rule_id,
        False,
    )

    rules = (
        rule_repository.get_rules_dataframe()
    )

    assert (
        bool(rules.iloc[0]["is_active"])
        is False
    )

    rule_repository.delete_rule(
        rule_id
    )

    assert (
        rule_repository
        .get_rules_dataframe()
        .empty
    )

    with pytest.raises(
        ValueError,
        match="не найдено",
    ):
        rule_repository.delete_rule(
            rule_id
        )


def test_preview_detects_file_database_and_invalid_rules(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    existing = make_rule_record()

    create_rule_from_record(
        existing
    )

    new_rule = make_rule_record(
        name="Продажи",
        priority=200,
        direction_filter="income",
        match_field="counterparty_name",
        match_value="клиент",
        pnl_action=INCLUDE_ACTION,
        pnl_category="Выручка",
        cf_action=INCLUDE_ACTION,
        cf_category=(
            "Операционные поступления"
        ),
    )

    preview = (
        rule_repository.preview_rule_records(
            [
                existing,
                existing.copy(),
                new_rule,
                {
                    "name":
                        "Повреждённое правило",
                },
            ]
        )
    )

    assert preview.received == 4
    assert preview.valid_unique == 2
    assert preview.duplicates_in_file == 1
    assert preview.duplicates_in_database == 1

    assert len(preview.errors) == 1

    assert preview.errors[0].startswith(
        "Правило 4:"
    )

    assert (
        len(preview.normalized_rules)
        == 2
    )


def test_import_merge_inserts_only_missing_rules(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    existing = make_rule_record()

    create_rule_from_record(
        existing
    )

    new_rule = make_rule_record(
        name="Продажи",
        priority=200,
        direction_filter="income",
        match_field="counterparty_name",
        match_value="клиент",
        pnl_action=INCLUDE_ACTION,
        pnl_category="Выручка",
        cf_action=INCLUDE_ACTION,
        cf_category=(
            "Операционные поступления"
        ),
    )

    result = (
        rule_repository.import_rule_records(
            [
                existing,
                new_rule,
                new_rule.copy(),
            ],
            mode="merge",
        )
    )

    assert result.mode == "merge"
    assert result.received == 3
    assert result.inserted == 1
    assert result.skipped_duplicates == 2
    assert result.deleted_existing == 0

    records = (
        rule_repository
        .get_rule_config_records()
    )

    assert len(records) == 2

    assert {
        record["name"]
        for record in records
    } == {
        "Банковские комиссии",
        "Продажи",
    }


def test_import_replace_is_atomic_replacement(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    create_rule_from_record(
        make_rule_record(
            name="Старое правило 1",
        )
    )

    create_rule_from_record(
        make_rule_record(
            name="Старое правило 2",
            match_value="старое",
        )
    )

    replacement = make_rule_record(
        name="Новое правило",
        priority=300,
        match_value="новое",
    )

    result = (
        rule_repository.import_rule_records(
            [
                replacement,
                replacement.copy(),
            ],
            mode="replace",
        )
    )

    assert result.mode == "replace"
    assert result.received == 2
    assert result.inserted == 1
    assert result.skipped_duplicates == 1
    assert result.deleted_existing == 2

    records = (
        rule_repository
        .get_rule_config_records()
    )

    assert [
        record["name"]
        for record in records
    ] == [
        "Новое правило",
    ]


def test_apply_rules_uses_priority_and_preserves_unmatched(
    isolated_repository: sessionmaker,
) -> None:
    create_rule_from_record(
        make_rule_record(
            name="Низкий приоритет",
            priority=10,
            pnl_action=INCLUDE_ACTION,
            pnl_category="Прочие расходы",
            cf_action=INCLUDE_ACTION,
            cf_category=(
                "Прочие операционные платежи"
            ),
        )
    )

    create_rule_from_record(
        make_rule_record(
            name="Высокий приоритет",
            priority=500,
        )
    )

    create_rule_from_record(
        make_rule_record(
            name="Поступление клиента",
            priority=300,
            direction_filter="income",
            match_field="counterparty_name",
            match_value="клиент",
            pnl_action=INCLUDE_ACTION,
            pnl_category="Выручка",
            cf_action=UNDEFINED_ACTION,
            cf_category="",
        )
    )

    transactions = [
        BankTransaction(
            source_hash="1" * 64,
            direction="Списание",
            posted_at=datetime(
                2026,
                1,
                1,
                10,
                0,
            ),
            amount_kopecks=1_000,
            signed_amount_kopecks=-1_000,
            description="Комиссия банка",
            classification_status=(
                "unclassified"
            ),
        ),
        BankTransaction(
            source_hash="2" * 64,
            direction="Пополнение",
            posted_at=datetime(
                2026,
                1,
                2,
                10,
                0,
            ),
            amount_kopecks=50_000,
            signed_amount_kopecks=50_000,
            counterparty_name=(
                "Клиент Альфа"
            ),
            classification_status=(
                "unclassified"
            ),
        ),
        BankTransaction(
            source_hash="3" * 64,
            direction="Списание",
            posted_at=datetime(
                2026,
                1,
                3,
                10,
                0,
            ),
            amount_kopecks=2_000,
            signed_amount_kopecks=-2_000,
            description="Покупка бумаги",
            classification_status=(
                "unclassified"
            ),
        ),
        BankTransaction(
            source_hash="4" * 64,
            direction="Списание",
            posted_at=datetime(
                2026,
                1,
                4,
                10,
                0,
            ),
            amount_kopecks=3_000,
            signed_amount_kopecks=-3_000,
            description="Комиссия банка",
            include_in_pnl=True,
            pnl_category="Ручная категория",
            include_in_cf=True,
            cf_category="Ручная категория",
            classification_status="classified",
            classification_source="manual",
        ),
    ]

    with isolated_repository() as session:
        session.add_all(
            transactions
        )
        session.commit()

    result = (
        rule_repository
        .apply_classification_rules()
    )

    assert result.checked == 3
    assert result.matched == 2
    assert result.unmatched == 1

    with isolated_repository() as session:
        saved = session.scalars(
            select(
                BankTransaction
            ).order_by(
                BankTransaction.source_hash
            )
        ).all()

    commission = saved[0]

    assert commission.include_in_pnl is False
    assert commission.pnl_category is None
    assert commission.include_in_cf is True

    assert commission.cf_category == (
        "Банковские расходы"
    )

    assert (
        commission.classification_status
        == "classified"
    )

    assert (
        commission.classification_source
        == "rule"
    )

    client = saved[1]

    assert client.include_in_pnl is True
    assert client.pnl_category == "Выручка"
    assert client.include_in_cf is None
    assert client.cf_category is None

    assert (
        client.classification_status
        == "partial"
    )

    assert (
        client.classification_source
        == "rule"
    )

    unmatched = saved[2]

    assert (
        unmatched.classification_status
        == "unclassified"
    )

    assert (
        unmatched.classification_source
        is None
    )

    manual = saved[3]

    assert (
        manual.pnl_category
        == "Ручная категория"
    )

    assert (
        manual.classification_source
        == "manual"
    )