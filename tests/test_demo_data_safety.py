from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

DEMO_STATEMENT_PATH = (
    PROJECT_ROOT
    / "demo_data"
    / "tbank_demo_statement.csv"
)

INN_COLUMNS = (
    "\u0418\u041d\u041d "
    "\u043f\u043b\u0430\u0442\u0435\u043b\u044c\u0449\u0438\u043a\u0430",

    "\u0418\u041d\u041d "
    "\u043f\u043e\u043b\u0443\u0447\u0430\u0442\u0435\u043b\u044f",

    "\u0418\u041d\u041d "
    "\u043a\u043e\u043d\u0442\u0440\u0430\u0433\u0435\u043d\u0442\u0430",
)

ACCOUNT_RULES = (
    (
        "\u0411\u0418\u041a \u0431\u0430\u043d\u043a\u0430 "
        "\u043f\u043b\u0430\u0442\u0435\u043b\u044c\u0449\u0438\u043a\u0430",

        "\u0421\u0447\u0435\u0442 "
        "\u043f\u043b\u0430\u0442\u0435\u043b\u044c\u0449\u0438\u043a\u0430",

        False,
    ),
    (
        "\u0411\u0418\u041a \u0431\u0430\u043d\u043a\u0430 "
        "\u043f\u043b\u0430\u0442\u0435\u043b\u044c\u0449\u0438\u043a\u0430",

        "\u041a\u043e\u0440\u0440. \u0441\u0447\u0435\u0442 "
        "\u043f\u043b\u0430\u0442\u0435\u043b\u044c\u0449\u0438\u043a\u0430",

        True,
    ),
    (
        "\u0411\u0418\u041a \u0431\u0430\u043d\u043a\u0430 "
        "\u043f\u043e\u043b\u0443\u0447\u0430\u0442\u0435\u043b\u044f",

        "\u0421\u0447\u0435\u0442 "
        "\u043f\u043e\u043b\u0443\u0447\u0430\u0442\u0435\u043b\u044f",

        False,
    ),
    (
        "\u0411\u0418\u041a \u0431\u0430\u043d\u043a\u0430 "
        "\u043f\u043e\u043b\u0443\u0447\u0430\u0442\u0435\u043b\u044f",

        "\u041a\u043e\u0440\u0440. \u0441\u0447\u0435\u0442 "
        "\u043f\u043e\u043b\u0443\u0447\u0430\u0442\u0435\u043b\u044f",

        True,
    ),
    (
        "\u0411\u0418\u041a \u0431\u0430\u043d\u043a\u0430 "
        "\u043a\u043e\u043d\u0442\u0440\u0430\u0433\u0435\u043d\u0442\u0430",

        "\u0421\u0447\u0435\u0442 "
        "\u043a\u043e\u043d\u0442\u0440\u0430\u0433\u0435\u043d\u0442\u0430",

        False,
    ),
)

ACCOUNT_WEIGHTS = (7, 1, 3) * 8


def read_rows() -> list[dict[str, str]]:
    with DEMO_STATEMENT_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        return list(
            csv.DictReader(
                csv_file,
                delimiter=";",
            )
        )


def is_valid_inn(value: str) -> bool:
    if not value.isdigit():
        return False

    if len(value) == 10:
        coefficients = (
            2, 4, 10, 3, 5, 9, 4, 6, 8
        )

        checksum = sum(
            int(digit) * coefficient
            for digit, coefficient in zip(
                value[:9],
                coefficients,
            )
        ) % 11 % 10

        return checksum == int(value[9])

    if len(value) == 12:
        coefficients_1 = (
            7, 2, 4, 10, 3,
            5, 9, 4, 6, 8,
        )

        coefficients_2 = (
            3, 7, 2, 4, 10, 3,
            5, 9, 4, 6, 8,
        )

        checksum_1 = sum(
            int(digit) * coefficient
            for digit, coefficient in zip(
                value[:10],
                coefficients_1,
            )
        ) % 11 % 10

        checksum_2 = sum(
            int(digit) * coefficient
            for digit, coefficient in zip(
                value[:11],
                coefficients_2,
            )
        ) % 11 % 10

        return (
            checksum_1 == int(value[10])
            and checksum_2 == int(value[11])
        )

    return False


def is_valid_account(
    bik: str,
    account: str,
    correspondent: bool,
) -> bool:
    if not (
        bik.isdigit()
        and len(bik) == 9
        and account.isdigit()
        and len(account) == 20
    ):
        return False

    if correspondent:
        control_value = (
            "0"
            + bik[4:6]
            + account
        )
    else:
        control_value = (
            bik[-3:]
            + account
        )

    checksum = sum(
        int(digit) * ACCOUNT_WEIGHTS[index]
        for index, digit in enumerate(
            control_value
        )
    )

    return checksum % 10 == 0


def test_demo_inns_are_checksum_invalid() -> None:
    rows = read_rows()

    valid_values = {
        row[column].strip()
        for row in rows
        for column in INN_COLUMNS
        if is_valid_inn(
            row[column].strip()
        )
    }

    assert valid_values == set()


def test_demo_accounts_are_checksum_invalid() -> None:
    rows = read_rows()

    valid_pairs = {
        (
            row[bik_column].strip(),
            row[account_column].strip(),
        )
        for row in rows
        for (
            bik_column,
            account_column,
            correspondent,
        ) in ACCOUNT_RULES
        if is_valid_account(
            row[bik_column].strip(),
            row[account_column].strip(),
            correspondent,
        )
    }

    assert valid_pairs == set()
