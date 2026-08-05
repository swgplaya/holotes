from __future__ import annotations

import re

import pytest
from playwright.sync_api import (
    Page,
    expect,
)


pytestmark = pytest.mark.browser


def test_open_mas_starts_and_switches_tabs(
    page: Page,
    streamlit_base_url: str,
) -> None:
    """Проверяет базовый запуск интерфейса в Chromium."""

    page.goto(
        streamlit_base_url,
        wait_until="domcontentloaded",
    )

    expect(page).to_have_title(
        re.compile(
            "Open MAS",
            re.IGNORECASE,
        )
    )

    tabs = page.get_by_role("tab")

    expect(tabs).to_have_count(8)

    first_tab = tabs.nth(0)
    second_tab = tabs.nth(1)

    expect(first_tab).to_have_attribute(
        "aria-selected",
        "true",
    )

    second_tab.click()

    expect(second_tab).to_have_attribute(
        "aria-selected",
        "true",
    )

    expect(
        page.locator(
            '[data-testid="stException"]'
        )
    ).to_have_count(0)
