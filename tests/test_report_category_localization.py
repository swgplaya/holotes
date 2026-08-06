from __future__ import annotations

from src.categories import (
    BUILT_IN_CATEGORY_TRANSLATION_KEYS,
    CF_CATEGORIES,
    PNL_CATEGORIES,
)
from src.i18n import (
    SUPPORTED_LANGUAGES,
    translate,
)
from src.ui.reports import (
    _translate_report_category,
)


def test_all_built_in_categories_have_translations() -> None:
    categories = {
        *PNL_CATEGORIES,
        *CF_CATEGORIES,
    }
    categories.discard("")

    assert categories == set(
        BUILT_IN_CATEGORY_TRANSLATION_KEYS
    )

    for category in categories:
        key = BUILT_IN_CATEGORY_TRANSLATION_KEYS[
            category
        ]

        for language in SUPPORTED_LANGUAGES:
            assert (
                translate(
                    key,
                    language,
                )
                != key
            )


def test_report_category_translation_preserves_custom_names() -> None:
    def translate_to_english(
        key: str,
    ) -> str:
        return translate(
            key,
            "en",
        )

    assert _translate_report_category(
        PNL_CATEGORIES[1],
        t=translate_to_english,
        empty_label="No category",
    ) == "Revenue"

    assert _translate_report_category(
        "Custom category",
        t=translate_to_english,
        empty_label="No category",
    ) == "Custom category"

    assert _translate_report_category(
        None,
        t=translate_to_english,
        empty_label="No category",
    ) == "No category"
