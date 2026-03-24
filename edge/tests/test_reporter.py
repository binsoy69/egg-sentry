from datetime import datetime, timezone

import httpx

from edge.reporter import EventReporter


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


class ScriptedClient:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def post(self, endpoint: str, json: dict, headers: dict) -> FakeResponse:
        self.calls.append({"endpoint": endpoint, "json": json, "headers": headers})
        current = self.responses.pop(0)
        if isinstance(current, Exception):
            raise current
        return current

    def close(self) -> None:
        return None


def build_reporter(tmp_path, client: ScriptedClient) -> EventReporter:
    return EventReporter(
        backend_api_base_url="http://edge.test/api",
        device_id="cam-001",
        device_api_key="device-key",
        retry_max_attempts=2,
        retry_backoff_seconds=0,
        retry_backoff_max_seconds=0,
        offline_queue_path=tmp_path / "offline-events.json",
        client=client,
        sleep_func=lambda _: None,
    )


def connect_error() -> httpx.ConnectError:
    request = httpx.Request("POST", "http://edge.test/api/events")
    return httpx.ConnectError("backend unavailable", request=request)


def test_send_event_queues_when_backend_is_unreachable(tmp_path) -> None:
    client = ScriptedClient([connect_error(), connect_error()])
    reporter = build_reporter(tmp_path, client)

    result = reporter.send_event(
        timestamp=datetime.now(timezone.utc),
        total_count=1,
        new_eggs=[
            {
                "size": "medium",
                "confidence": 0.92,
                "bbox_area_normalized": 0.0031,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
        size_breakdown={"medium": 1},
    )

    assert result.delivered is False
    assert result.queued is True
    assert result.queue_depth == 1
    assert len(client.calls) == 2
    assert client.calls[0]["headers"] == {"X-Device-Key": "device-key"}
    assert reporter.queue_depth() == 1


def test_send_snapshot_does_not_queue_when_backend_is_unreachable(tmp_path) -> None:
    client = ScriptedClient([connect_error(), connect_error()])
    reporter = build_reporter(tmp_path, client)

    result = reporter.send_snapshot(
        timestamp=datetime.now(timezone.utc),
        total_count=2,
        size_breakdown={"medium": 2},
    )

    assert result.delivered is False
    assert result.queued is False
    assert result.queue_depth == 0
    assert reporter.queue_depth() == 0


def test_flush_event_queue_replays_buffered_events(tmp_path) -> None:
    client = ScriptedClient([connect_error(), connect_error()])
    reporter = build_reporter(tmp_path, client)
    reporter.send_event(
        timestamp=datetime.now(timezone.utc),
        total_count=1,
        new_eggs=[
            {
                "size": "large",
                "confidence": 0.88,
                "bbox_area_normalized": 0.0038,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
        size_breakdown={"large": 1},
    )

    client.responses = [FakeResponse(201, {"accepted": True, "events_created": 1, "daily_total": 1})]
    flush = reporter.flush_event_queue()

    assert flush.flushed == 1
    assert flush.dropped == 0
    assert flush.remaining == 0
    assert reporter.queue_depth() == 0
