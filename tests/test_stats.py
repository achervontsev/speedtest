import pytest

from speedmeter.meter import Measurement
from speedmeter.stats import summarize


def test_summarize_aggregates_measurements() -> None:
    summary = summarize(
        [
            Measurement(size_bytes=2_000_000, elapsed_seconds=1.0),
            Measurement(size_bytes=3_000_000, elapsed_seconds=1.5),
        ]
    )

    assert summary.requests == 2
    assert summary.total_bytes == 5_000_000
    assert summary.total_seconds == pytest.approx(2.5)
    assert summary.average_seconds == pytest.approx(1.25)
    assert summary.total_megabytes == pytest.approx(5.0)
    assert summary.megabytes_per_second == pytest.approx(2.0)
    assert summary.megabits_per_second == pytest.approx(16.0)


def test_speed_is_total_bytes_over_total_time() -> None:
    # The mean of per-request speeds would be (10 + 1) / 2 = 5.5 MB/s,
    # but in reality 20 MB were downloaded in 11 seconds.
    summary = summarize(
        [
            Measurement(size_bytes=10_000_000, elapsed_seconds=1.0),
            Measurement(size_bytes=10_000_000, elapsed_seconds=10.0),
        ]
    )

    assert summary.megabytes_per_second == pytest.approx(20 / 11)


def test_summarize_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="empty"):
        summarize([])
