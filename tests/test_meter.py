import gzip
from collections.abc import Callable

import httpx
import pytest

from speedmeter.meter import measure_download

URL = "https://example.com/image.jpg"

Handler = Callable[[httpx.Request], httpx.Response]


def make_client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def streamed_response(body: bytes, headers: dict[str, str] | None = None) -> httpx.Response:
    # `httpx.Response(content=...)` reads the body eagerly, and then it cannot
    # be streamed with `aiter_raw()`. A real transport returns a stream, so the
    # mocks do the same.
    return httpx.Response(200, stream=httpx.ByteStream(body), headers=headers)


async def test_measure_download_counts_body_bytes() -> None:
    body = b"x" * 10_000

    async with make_client(lambda _: streamed_response(body)) as client:
        measurement = await measure_download(client, URL)

    assert measurement.size_bytes == len(body)
    assert measurement.elapsed_seconds > 0


async def test_measure_download_counts_compressed_bytes() -> None:
    compressed = gzip.compress(b"x" * 10_000)
    headers = {"Content-Encoding": "gzip"}

    async with make_client(lambda _: streamed_response(compressed, headers)) as client:
        measurement = await measure_download(client, URL)

    assert measurement.size_bytes == len(compressed)


async def test_measure_download_raises_on_error_status() -> None:
    async with make_client(lambda _: httpx.Response(404)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await measure_download(client, URL)
