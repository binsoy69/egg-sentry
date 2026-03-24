from edge.agent import ReportingState, maybe_send_heartbeat
from edge.reporter import RetryableReporterError


class RetryableHeartbeatReporter:
    def __init__(self) -> None:
        self._queue_depth = 2

    def send_heartbeat(self, **kwargs):
        raise RetryableReporterError("temporary outage")

    def queue_depth(self) -> int:
        return self._queue_depth


def test_maybe_send_heartbeat_handles_retryable_failure() -> None:
    state = ReportingState(next_heartbeat_at=0.0)

    result = maybe_send_heartbeat(
        RetryableHeartbeatReporter(),
        state,
        heartbeat_interval_seconds=60,
        current_count=3,
    )

    assert result is not None
    assert result["delivery"]["delivered"] is False
    assert result["delivery"]["queue_depth"] == 2
    assert result["queue_flush"] is None
    assert state.next_heartbeat_at > 0
