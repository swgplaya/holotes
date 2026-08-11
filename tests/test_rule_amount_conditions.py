from datetime import datetime

import pytest

import src.rule_repository as rule_repository
from src.categories import (
    EXCLUDE_ACTION,
    INCLUDE_ACTION,
)
from src.models import (
    BankTransaction,
    ClassificationRule,
)


def make_transaction(
    amount_kopecks: int,
) -> BankTransaction:
    """Создаёт операцию для проверки правил."""

    return BankTransaction(
        source_hash="a" * 64,
        direction="Списание",
        posted_at=datetime(
            2026,
            8,
            11,
            12,
            0,
        ),
        amount_kopecks=amount_kopecks,
        signed_amount_kopecks=-amount_kopecks,
        description="Реклама Яндекс",
        classification_status="unclassified",
    )


def make_rule(
    *,
    amount_operator: str = "any",
    amount_value_kopecks: int | None = None,
    amount_value_to_kopecks: int | None = None,
) -> ClassificationRule:
    """Создаёт правило с текстовым и денежным условием."""

    return ClassificationRule(
        name="Реклама",
        priority=100,
        is_active=True,
        direction_filter="expense",
        match_field="description",
        match_type="contains",
        match_value="реклама",
        amount_operator=amount_operator,
        amount_value_kopecks=(
            amount_value_kopecks
        ),
        amount_value_to_kopecks=(
            amount_value_to_kopecks
        ),
        include_in_pnl=True,
        pnl_category="Маркетинг",
        include_in_cf=True,
        cf_category="Маркетинг",
    )


@pytest.mark.parametrize(
    (
        "operator",
        "value",
        "upper",
        "amount",
        "expected",
    ),
    [
        ("any", None, None, 10_000, True),
        ("gt", 10_000, None, 10_001, True),
        ("gt", 10_000, None, 10_000, False),
        ("gte", 10_000, None, 10_000, True),
        ("lt", 10_000, None, 9_999, True),
        ("lt", 10_000, None, 10_000, False),
        ("lte", 10_000, None, 10_000, True),
        ("eq", 10_000, None, 10_000, True),
        ("eq", 10_000, None, 10_001, False),
        ("between", 10_000, 20_000, 10_000, True),
        ("between", 10_000, 20_000, 20_000, True),
        ("between", 10_000, 20_000, 20_001, False),
    ],
)
def test_amount_conditions(
    operator: str,
    value: int | None,
    upper: int | None,
    amount: int,
    expected: bool,
) -> None:
    rule = make_rule(
        amount_operator=operator,
        amount_value_kopecks=value,
        amount_value_to_kopecks=upper,
    )

    transaction = make_transaction(
        amount
    )

    assert (
        rule_repository._rule_matches(
            rule,
            transaction,
        )
        is expected
    )


def test_amount_condition_is_combined_with_text() -> None:
    rule = make_rule(
        amount_operator="gt",
        amount_value_kopecks=100_000,
    )

    transaction = make_transaction(
        150_000
    )

    transaction.description = (
        "Покупка канцелярии"
    )

    assert (
        rule_repository._rule_matches(
            rule,
            transaction,
        )
        is False
    )


def test_amount_comparison_uses_absolute_amount() -> None:
    rule = make_rule(
        amount_operator="eq",
        amount_value_kopecks=50_000,
    )

    transaction = make_transaction(
        -50_000
    )

    transaction.signed_amount_kopecks = (
        -50_000
    )

    assert (
        rule_repository._rule_matches(
            rule,
            transaction,
        )
        is True
    )


def test_create_rule_defaults_to_no_amount_limit(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_session_factory,
) -> None:
    monkeypatch.setattr(
        rule_repository,
        "SessionLocal",
        sqlite_session_factory,
    )

    rule_id = rule_repository.create_rule(
        name="Без лимита",
        priority=100,
        is_active=True,
        direction_filter="expense",
        match_field="description",
        match_type="contains",
        match_value="комиссия",
        pnl_action=EXCLUDE_ACTION,
        pnl_category="",
        cf_action=INCLUDE_ACTION,
        cf_category="Банковские расходы",
    )

    with sqlite_session_factory() as session:
        rule = session.get(
            ClassificationRule,
            rule_id,
        )

        assert rule is not None
        assert rule.amount_operator == "any"
        assert rule.amount_value_kopecks is None
        assert (
            rule.amount_value_to_kopecks
            is None
        )


@pytest.mark.parametrize(
    (
        "operator",
        "value",
        "upper",
        "message",
    ),
    [
        (
            "broken",
            None,
            None,
            "неизвестное условие по сумме",
        ),
        (
            "gt",
            None,
            None,
            "укажи сумму",
        ),
        (
            "between",
            10_000,
            None,
            "верхнюю границу",
        ),
        (
            "between",
            20_000,
            10_000,
            "не может быть меньше",
        ),
        (
            "gt",
            -1,
            None,
            "не может быть отрицательной",
        ),
    ],
)
def test_create_rule_validates_amount_condition(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_session_factory,
    operator: str,
    value: int | None,
    upper: int | None,
    message: str,
) -> None:
    monkeypatch.setattr(
        rule_repository,
        "SessionLocal",
        sqlite_session_factory,
    )

    with pytest.raises(
        ValueError,
        match=message,
    ):
        rule_repository.create_rule(
            name="Проверка суммы",
            priority=100,
            is_active=True,
            direction_filter="expense",
            match_field="description",
            match_type="contains",
            match_value="тест",
            pnl_action=INCLUDE_ACTION,
            pnl_category="Расходы",
            cf_action=INCLUDE_ACTION,
            cf_category="Расходы",
            amount_operator=operator,
            amount_value_kopecks=value,
            amount_value_to_kopecks=upper,
        )



def test_legacy_rule_record_defaults_to_no_amount_limit(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_session_factory,
) -> None:
    monkeypatch.setattr(
        rule_repository,
        "SessionLocal",
        sqlite_session_factory,
    )

    legacy_record = {
        "name": "Старое правило",
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

    preview = (
        rule_repository.preview_rule_records(
            [
                legacy_record,
            ]
        )
    )

    assert preview.errors == ()
    assert preview.valid_unique == 1

    normalized = (
        preview.normalized_rules[0]
    )

    assert (
        normalized["amount_operator"]
        == "any"
    )

    assert (
        normalized["amount_value_kopecks"]
        is None
    )

    assert (
        normalized[
            "amount_value_to_kopecks"
        ]
        is None
    )


def test_rule_config_export_contains_amount_condition(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_session_factory,
) -> None:
    monkeypatch.setattr(
        rule_repository,
        "SessionLocal",
        sqlite_session_factory,
    )

    rule_repository.create_rule(
        name="Крупная реклама",
        priority=200,
        is_active=True,
        direction_filter="expense",
        match_field="description",
        match_type="contains",
        match_value="реклама",
        pnl_action=INCLUDE_ACTION,
        pnl_category="Маркетинг",
        cf_action=INCLUDE_ACTION,
        cf_category="Маркетинг",
        amount_operator="between",
        amount_value_kopecks=100_000,
        amount_value_to_kopecks=500_000,
    )

    records = (
        rule_repository
        .get_rule_config_records()
    )

    assert len(records) == 1

    record = records[0]

    assert (
        record["amount_operator"]
        == "between"
    )

    assert (
        record["amount_value_kopecks"]
        == 100_000
    )

    assert (
        record[
            "amount_value_to_kopecks"
        ]
        == 500_000
    )


def test_rule_fingerprint_includes_amount_condition() -> None:
    common = {
        "name": "Реклама",
        "priority": 100,
        "is_active": True,
        "direction_filter": "expense",
        "match_field": "description",
        "match_type": "contains",
        "match_value": "реклама",
        "include_in_pnl": True,
        "pnl_category": "Маркетинг",
        "include_in_cf": True,
        "cf_category": "Маркетинг",
    }

    unlimited = {
        **common,
        "amount_operator": "any",
        "amount_value_kopecks": None,
        "amount_value_to_kopecks": None,
    }

    limited = {
        **common,
        "amount_operator": "gt",
        "amount_value_kopecks": 100_000,
        "amount_value_to_kopecks": None,
    }

    assert (
        rule_repository._rule_fingerprint(
            unlimited
        )
        != rule_repository._rule_fingerprint(
            limited
        )
    )
