"""Command-line interface: argument parsing and console output."""

import argparse
import asyncio
import sys
from collections.abc import Sequence

import httpx
from pydantic import ValidationError

from speedmeter import __version__
from speedmeter.config import (
    DEFAULT_REQUESTS,
    DEFAULT_TIMEOUT_SECONDS,
    ENV_PREFIX,
    USER_AGENT,
    Settings,
)
from speedmeter.meter import Measurement, measure_download
from speedmeter.stats import BYTES_PER_MEGABYTE, Summary, summarize


def parse_args(argv: Sequence[str] | None = None) -> Settings:
    """Build settings from command-line arguments, the environment and ``.env``."""
    parser = argparse.ArgumentParser(
        prog="speedmeter",
        description="Measure download speed by fetching a URL several times in a row.",
        epilog=f"Every option can also be set with a {ENV_PREFIX}* environment variable "
        "or in a .env file; command-line arguments take precedence.",
    )
    # No argparse defaults and no type conversion here: an omitted argument
    # must not override the environment, and validation lives in `Settings`.
    parser.add_argument(
        "url",
        nargs="?",
        help=f"URL of a large file to download, e.g. a heavy image (env: {ENV_PREFIX}URL)",
    )
    parser.add_argument(
        "-n",
        "--requests",
        help=f"number of sequential requests "
        f"(default: {DEFAULT_REQUESTS}, env: {ENV_PREFIX}REQUESTS)",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        help=f"timeout in seconds for connecting and for each read; it does not "
        f"limit the whole download (default: {DEFAULT_TIMEOUT_SECONDS:g}, "
        f"env: {ENV_PREFIX}TIMEOUT)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args(argv)
    overrides = {name: value for name, value in vars(args).items() if value is not None}
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        parser.error(_describe_invalid_settings(exc))


async def run(
    settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
) -> list[Measurement]:
    """Run the speed test, printing each measurement as soon as it is ready.

    A single client is reused for all requests, so the connection is kept
    alive and only the first request pays for the TCP/TLS handshake.

    ``transport`` lets tests substitute the network with a mock.
    """
    url = str(settings.url)
    # Flush explicitly so progress shows up immediately even when piped.
    print(f"Downloading {url} {settings.requests} time(s)...\n", flush=True)

    measurements: list[Measurement] = []
    async with httpx.AsyncClient(
        timeout=settings.timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        transport=transport,
    ) as client:
        # Strictly sequential: the next request starts only after the previous
        # file has been downloaded completely.
        for number in range(1, settings.requests + 1):
            measurement = await measure_download(client, url)
            measurements.append(measurement)
            print(format_measurement(number, settings.requests, measurement), flush=True)
    return measurements


def format_measurement(number: int, total: int, measurement: Measurement) -> str:
    width = len(str(total))
    megabytes = measurement.size_bytes / BYTES_PER_MEGABYTE
    return f"[{number:>{width}}/{total}] {megabytes:.2f} MB in {measurement.elapsed_seconds:.3f} s"


def format_summary(summary: Summary) -> str:
    return "\n".join(
        [
            f"Requests:             {summary.requests}",
            f"Downloaded:           {summary.total_megabytes:.2f} MB",
            f"Average request time: {summary.average_seconds:.3f} s",
            f"Speed:                {summary.megabytes_per_second:.2f} MB/s"
            f" ({summary.megabits_per_second:.2f} Mbit/s)",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point of the ``speedmeter`` command; returns the exit code."""
    settings = parse_args(argv)
    try:
        measurements = asyncio.run(run(settings))
    except httpx.HTTPStatusError as exc:
        return _fail(f"server responded with HTTP {exc.response.status_code} for {exc.request.url}")
    except httpx.RequestError as exc:
        return _fail(f"request failed: {_describe(exc)}")
    except KeyboardInterrupt:
        return _fail("interrupted by user", exit_code=130)

    print()
    print(format_summary(summarize(measurements)))
    return 0


def _fail(message: str, exit_code: int = 1) -> int:
    print(f"error: {message}", file=sys.stderr)
    return exit_code


def _describe(exc: Exception) -> str:
    # Some httpx errors (e.g. timeouts) have an empty message, so the
    # exception type is the most informative part.
    name = type(exc).__name__
    return f"{name}: {exc}" if str(exc) else name


def _describe_invalid_settings(exc: ValidationError) -> str:
    problems = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"])
        if error["type"] == "missing":
            env_var = f"{ENV_PREFIX}{field.upper()}"
            problems.append(f"{field} is required: pass it as an argument or set {env_var}")
        else:
            problems.append(f"invalid {field} {error['input']!r}: {error['msg']}")
    return "; ".join(problems)
