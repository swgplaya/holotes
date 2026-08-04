from collections.abc import Callable


Translator = Callable[..., str]


def format_option_label(
    value: object,
    *,
    t: Translator,
    translation_keys: dict[str, str],
    fallback_labels: dict[str, str],
) -> str:
    """Возвращает локализованную подпись внутреннего значения."""

    value_text = str(value).strip()
    option_key = value_text

    if option_key not in fallback_labels:
        reverse_labels = {
            label: key
            for key, label in fallback_labels.items()
        }

        option_key = reverse_labels.get(
            value_text,
            value_text,
        )

    translation_key = translation_keys.get(
        option_key
    )

    if translation_key is not None:
        return t(translation_key)

    return fallback_labels.get(
        option_key,
        value_text,
    )
