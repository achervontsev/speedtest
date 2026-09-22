import os
from pathlib import Path

import pytest

from speedmeter.config import ENV_PREFIX


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep the developer's environment variables and .env file out of tests."""
    monkeypatch.chdir(tmp_path)
    for name in list(os.environ):
        if name.startswith(ENV_PREFIX):
            monkeypatch.delenv(name)
