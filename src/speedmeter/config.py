"""Application configuration: constants and user settings.

User settings are taken from the following sources, highest priority first:

1. command-line arguments (the CLI passes them to ``Settings`` explicitly);
2. environment variables prefixed with ``SPEEDMETER_``;
3. the ``.env`` file in the current working directory;
4. the defaults below.
"""

from typing import Annotated

from pydantic import Field, HttpUrl, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

from speedmeter import __version__

PROJECT_URL = "https://github.com/achervontsev/speedtest"
# Some servers (e.g. Wikimedia) throttle clients with a generic User-Agent,
# so identify ourselves and leave a way to contact the author.
USER_AGENT = f"speedmeter/{__version__} (+{PROJECT_URL})"

ENV_PREFIX = "SPEEDMETER_"
ENV_FILE = ".env"

DEFAULT_REQUESTS = 10
DEFAULT_TIMEOUT_SECONDS = 30.0


class Settings(BaseSettings):
    """Validated speed test settings."""

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        frozen=True,
    )

    url: HttpUrl
    """URL of a large file to download."""

    requests: PositiveInt = DEFAULT_REQUESTS
    """Number of sequential requests."""

    timeout: Annotated[float, Field(gt=0, allow_inf_nan=False)] = DEFAULT_TIMEOUT_SECONDS
    """Timeout in seconds for connecting and for each read (waiting for the next
    chunk of data). It does not limit the whole download, so a large file may
    take longer as long as the data keeps flowing."""
