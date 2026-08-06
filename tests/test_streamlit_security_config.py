from pathlib import Path
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_is_bound_to_localhost() -> None:
    config_path = (
        PROJECT_ROOT
        / ".streamlit"
        / "config.toml"
    )

    with config_path.open("rb") as config_file:
        config = tomllib.load(config_file)

    server = config["server"]

    assert server["address"] == "127.0.0.1"
    assert server["headless"] is True
    assert server["enableCORS"] is True
    assert server["enableXsrfProtection"] is True
    assert server["enableStaticServing"] is False
    assert server["maxUploadSize"] <= 50
    assert server["maxMessageSize"] <= 50


def test_streamlit_usage_collection_is_disabled() -> None:
    config_path = (
        PROJECT_ROOT
        / ".streamlit"
        / "config.toml"
    )

    with config_path.open("rb") as config_file:
        config = tomllib.load(config_file)

    assert (
        config["browser"]["gatherUsageStats"]
        is False
    )
