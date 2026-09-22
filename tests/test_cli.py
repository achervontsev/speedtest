import httpx
import pytest

from speedmeter import cli
from speedmeter.cli import format_summary, parse_args, run
from speedmeter.config import Settings
from speedmeter.meter import Measurement
from speedmeter.stats import Summary

URL = "https://example.com/image.jpg"


def test_parse_args_uses_defaults() -> None:
    assert parse_args([URL]) == Settings(url=URL, requests=10, timeout=30.0)


def test_parse_args_reads_options() -> None:
    assert parse_args([URL, "-n", "3", "--timeout", "2.5"]) == Settings(
        url=URL, requests=3, timeout=2.5
    )


def test_parse_args_falls_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEEDMETER_URL", URL)
    monkeypatch.setenv("SPEEDMETER_REQUESTS", "5")

    assert parse_args([]) == Settings(url=URL, requests=5)


def test_arguments_take_precedence_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEEDMETER_URL", "https://example.org/other.jpg")
    monkeypatch.setenv("SPEEDMETER_REQUESTS", "5")

    assert parse_args([URL, "-n", "2"]) == Settings(url=URL, requests=2)


def test_parse_args_requires_url(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args([])

    assert exc_info.value.code == 2
    assert "url is required: pass it as an argument or set SPEEDMETER_URL" in (
        capsys.readouterr().err
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["example.com/image.jpg"],
        [URL, "-n", "0"],
        [URL, "--timeout", "nan"],
    ],
)
def test_parse_args_rejects_invalid_input(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args(argv)

    assert exc_info.value.code == 2
    assert "speedmeter: error: invalid" in capsys.readouterr().err


async def test_run_downloads_url_requested_number_of_times(
    capsys: pytest.CaptureFixture[str],
) -> None:
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(200, stream=httpx.ByteStream(b"x" * 500_000))

    measurements = await run(Settings(url=URL, requests=3), transport=httpx.MockTransport(handler))

    assert requested_urls == [URL] * 3
    assert [m.size_bytes for m in measurements] == [500_000] * 3
    output = capsys.readouterr().out
    assert "[1/3] 0.50 MB in" in output
    assert "[3/3] 0.50 MB in" in output


def test_format_summary() -> None:
    summary = Summary(requests=10, total_bytes=50_000_000, total_seconds=5.0)

    assert format_summary(summary).splitlines() == [
        "Requests:             10",
        "Downloaded:           50.00 MB",
        "Average request time: 0.500 s",
        "Speed:                10.00 MB/s (80.00 Mbit/s)",
    ]


def test_main_prints_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_run(settings: Settings) -> list[Measurement]:
        return [Measurement(size_bytes=1_000_000, elapsed_seconds=0.5)] * settings.requests

    monkeypatch.setattr(cli, "run", fake_run)

    assert cli.main([URL, "-n", "2"]) == 0
    assert "Speed:                2.00 MB/s (16.00 Mbit/s)" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            httpx.ConnectError("connection refused"),
            "error: request failed: ConnectError: connection refused",
        ),
        (httpx.ReadTimeout(""), "error: request failed: ReadTimeout"),
        (
            httpx.HTTPStatusError(
                "not found",
                request=httpx.Request("GET", URL),
                response=httpx.Response(404),
            ),
            f"error: server responded with HTTP 404 for {URL}",
        ),
    ],
)
def test_main_reports_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: httpx.HTTPError,
    message: str,
) -> None:
    async def failing_run(settings: Settings) -> list[Measurement]:
        raise error

    monkeypatch.setattr(cli, "run", failing_run)

    assert cli.main([URL]) == 1
    assert message in capsys.readouterr().err
