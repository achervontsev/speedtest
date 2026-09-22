from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from speedmeter.config import Settings

URL = "https://example.com/image.jpg"


def test_settings_defaults() -> None:
    settings = Settings(url=URL)

    assert str(settings.url) == URL
    assert settings.requests == 10
    assert settings.timeout == 30.0


def test_settings_are_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEEDMETER_URL", URL)
    monkeypatch.setenv("SPEEDMETER_REQUESTS", "5")
    monkeypatch.setenv("SPEEDMETER_TIMEOUT", "2.5")

    assert Settings() == Settings(url=URL, requests=5, timeout=2.5)


def test_settings_are_read_from_env_file() -> None:
    # The `isolated_settings` fixture has made a temporary directory the cwd.
    Path(".env").write_text(f"SPEEDMETER_URL={URL}\nSPEEDMETER_REQUESTS=3\n")

    assert Settings() == Settings(url=URL, requests=3)


def test_env_takes_precedence_over_env_file(monkeypatch: pytest.MonkeyPatch) -> None:
    Path(".env").write_text(f"SPEEDMETER_URL={URL}\nSPEEDMETER_REQUESTS=3\n")
    monkeypatch.setenv("SPEEDMETER_REQUESTS", "7")

    assert Settings().requests == 7


def test_unknown_setting_in_env_file_is_rejected() -> None:
    Path(".env").write_text(f"SPEEDMETER_URL={URL}\nSPEEDMETER_REQUEST=3\n")

    with pytest.raises(ValidationError, match="speedmeter_request"):
        Settings()


@pytest.mark.parametrize(
    "values",
    [
        {"url": "example.com/image.jpg"},
        {"url": "ftp://example.com/image.jpg"},
        {"url": "https://"},
        {"url": URL, "requests": 0},
        {"url": URL, "requests": "ten"},
        {"url": URL, "timeout": -1},
        {"url": URL, "timeout": "nan"},
        {"url": URL, "timeout": "inf"},
    ],
)
def test_settings_reject_invalid_values(values: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Settings(**values)
