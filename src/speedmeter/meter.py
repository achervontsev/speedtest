"""Network part: downloading a URL and timing it."""

import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True, slots=True)
class Measurement:
    """Outcome of a single download."""

    size_bytes: int
    elapsed_seconds: float


async def measure_download(client: httpx.AsyncClient, url: str) -> Measurement:
    """Download ``url`` completely and measure how long it took.

    The timer covers the whole request: sending it, waiting for the response
    and reading the full body. The body is streamed and thrown away chunk by
    chunk, so even very large files do not end up in memory.

    Raw (not decompressed) bytes are counted, because that is what actually
    travelled over the network.

    Raises:
        httpx.HTTPStatusError: if the server responds with a 4xx/5xx status.
        httpx.RequestError: on network problems (DNS, connection, timeout...).
    """
    started = time.perf_counter()
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        size_bytes = 0
        async for chunk in response.aiter_raw():
            size_bytes += len(chunk)
    elapsed_seconds = time.perf_counter() - started
    return Measurement(size_bytes=size_bytes, elapsed_seconds=elapsed_seconds)
