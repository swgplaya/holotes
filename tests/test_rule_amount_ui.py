import pytest

from src.ui.rules import (
    _format_kopecks_as_rubles,
    _format_rule_amount_condition,
    _parse_rubles_to_kopecks,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", 0),
        ("1", 100),
        ("1,5", 150),
        ("1.50", 150),
        ("1000,50", 100_050),
        ("1 000,50", 100_050),
        ("12 345", 1_234_500),
        ("0.01", 1),
    ],
)
def test_parse_rubles_to_kopecks(
    value: str,
    expected: int,
) -> None:
    assert (
        _parse_rubles_to_kopecks(
            value
        )
        == expected
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "-1",
        "abc",
        "1.234",
        "1,234",
        "1,2,3",
        "1 000.001",
    ],
)
def test_parse_rubles_rejects_invalid_values(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        _parse_rubles_to_kopecks(
            value
        )


@pytest.mark.parametrize(
    ("kopecks", "expected"),
    [
        (0, "0 ₽"),
        (100, "1 ₽"),
        (150, "1,50 ₽"),
        (100_000, "1 000 ₽"),
        (100_050, "1 000,50 ₽"),
    ],
)
def test_format_kopecks_as_rubles(
    kopecks: int,
    expected: str,
) -> None:
    assert (
        _format_kopecks_as_rubles(
            kopecks
        )
        == expected
    )


def translator(
    key: str,
    **kwargs: object,
) -> str:
    values = {
        "rules.options.amount.any":
            "Без ограничения",
        "rules.saved.amount.between":
            "От {lower} до {upper}",
    }

    template = values.get(
        key,
        key,
    )

    return template.format(
        **kwargs
    )


def test_format_unlimited_amount_condition() -> None:
    assert (
        _format_rule_amount_condition(
            operator="any",
            value=None,
            upper_value=None,
            t=translator,
        )
        == "Без ограничения"
    )


def test_format_single_amount_condition() -> None:
    assert (
        _format_rule_amount_condition(
            operator="gt",
            value=100_000,
            upper_value=None,
            t=translator,
        )
        == "> 1 000 ₽"
    )


def test_format_between_amount_condition() -> None:
    assert (
        _format_rule_amount_condition(
            operator="between",
            value=100_000,
            upper_value=500_000,
            t=translator,
        )
        == (
            "От 1 000 ₽ "
            "до 5 000 ₽"
        )
    )
