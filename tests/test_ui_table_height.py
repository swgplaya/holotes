from __future__ import annotations

import pytest

from src.ui.table_height import (
    DATAFRAME_BORDER_ALLOWANCE,
    DATAFRAME_HEADER_HEIGHT,
    DATAFRAME_ROW_HEIGHT,
    dataframe_height,
)


@pytest.mark.parametrize(
    ("row_count", "expected_height"),
    [
        (
            0,
            DATAFRAME_HEADER_HEIGHT
            + DATAFRAME_BORDER_ALLOWANCE,
        ),
        (
            10,
            DATAFRAME_HEADER_HEIGHT
            + 10 * DATAFRAME_ROW_HEIGHT
            + DATAFRAME_BORDER_ALLOWANCE,
        ),
        (
            25,
            DATAFRAME_HEADER_HEIGHT
            + 25 * DATAFRAME_ROW_HEIGHT
            + DATAFRAME_BORDER_ALLOWANCE,
        ),
        (
            100,
            DATAFRAME_HEADER_HEIGHT
            + 100 * DATAFRAME_ROW_HEIGHT
            + DATAFRAME_BORDER_ALLOWANCE,
        ),
    ],
)
def test_dataframe_height(
    row_count: int,
    expected_height: int,
) -> None:
    assert (
        dataframe_height(row_count)
        == expected_height
    )


def test_dataframe_height_rejects_negative_rows() -> None:
    with pytest.raises(
        ValueError,
        match="Количество строк",
    ):
        dataframe_height(-1)
