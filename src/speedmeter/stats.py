"""Aggregating individual measurements into a summary."""

from collections.abc import Sequence
from dataclasses import dataclass

from speedmeter.meter import Measurement

# Decimal units, the same ones internet providers use: 1 MB = 10^6 bytes.
BYTES_PER_MEGABYTE = 1_000_000
BITS_PER_BYTE = 8


@dataclass(frozen=True, slots=True)
class Summary:
    """Aggregated result of a speed test."""

    requests: int
    total_bytes: int
    total_seconds: float

    @property
    def average_seconds(self) -> float:
        """Average duration of a single request."""
        return self.total_seconds / self.requests

    @property
    def total_megabytes(self) -> float:
        return self.total_bytes / BYTES_PER_MEGABYTE

    @property
    def megabytes_per_second(self) -> float:
        """Download speed in megabytes per second (MB/s)."""
        return self.total_megabytes / self.total_seconds

    @property
    def megabits_per_second(self) -> float:
        """Download speed in megabits per second (Mbit/s)."""
        return self.megabytes_per_second * BITS_PER_BYTE


def summarize(measurements: Sequence[Measurement]) -> Summary:
    """Combine measurements into a single summary.

    Speed is computed as total bytes divided by total time rather than as the
    mean of per-request speeds: the latter overweights short, fast requests.
    """
    if not measurements:
        raise ValueError("cannot summarize an empty list of measurements")

    return Summary(
        requests=len(measurements),
        total_bytes=sum(m.size_bytes for m in measurements),
        total_seconds=sum(m.elapsed_seconds for m in measurements),
    )
