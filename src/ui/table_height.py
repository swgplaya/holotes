from __future__ import annotations


DATAFRAME_ROW_HEIGHT = 35
DATAFRAME_HEADER_HEIGHT = 38
DATAFRAME_BORDER_ALLOWANCE = 4


def dataframe_height(row_count: int) -> int:
    """Возвращает высоту таблицы без вертикальной прокрутки."""

    if row_count < 0:
        raise ValueError(
            "Количество строк не может быть отрицательным."
        )

    return (
        DATAFRAME_HEADER_HEIGHT
        + row_count * DATAFRAME_ROW_HEIGHT
        + DATAFRAME_BORDER_ALLOWANCE
    )
