import re

from src.version import APP_NAME, __version__


def test_application_name() -> None:
    assert APP_NAME == "Holotes"


def test_version_uses_semantic_versioning() -> None:
    assert re.fullmatch(
        r"\d+\.\d+\.\d+",
        __version__,
    )
