import argparse
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import CountSnapshot, Device, EggDetection
from edge import agent as edge_agent
from edge.capture import CapturedFrame
from edge.config import EdgeConfig
from edge.detector import Detection
from edge.reporter import EventReporter


class ApiClientAdapter:
    def __init__(self, client: TestClient, prefix: str = "/api") -> None:
        self.client = client
        self.prefix = prefix.rstrip("/")

    def post(self, endpoint: str, json: dict, headers: dict):
        return self.client.post(f"{self.prefix}{endpoint}", json=json, headers=headers)

    def close(self) -> None:
        return None


class FakeVideoCaptureSampler:
    def __init__(self, source: Path, interval_seconds: int, loop: bool = False) -> None:
        frame = np.zeros((1000, 1000, 3), dtype=np.uint8)
        self.frames = [
            CapturedFrame(frame=frame, frame_index=0, timestamp_seconds=0.0),
            CapturedFrame(frame=frame, frame_index=1, timestamp_seconds=1.0),
            CapturedFrame(frame=frame, frame_index=2, timestamp_seconds=2.0),
        ]

    def capture_frame(self) -> CapturedFrame:
        if not self.frames:
            raise StopIteration("test video exhausted")
        return self.frames.pop(0)

    def close(self) -> None:
        return None


class FakeDetector:
    def __init__(self, model_path: Path, confidence_threshold: float = 0.5) -> None:
        self.calls = 0

    def detect(self, frame, use_tracking: bool = False) -> list[Detection]:
        detections_by_cycle = [
            [],
            [Detection(100, 100, 150, 150, 0.93, 0, "egg")],
            [Detection(100, 100, 150, 150, 0.93, 0, "egg")],
        ]
        current = detections_by_cycle[self.calls]
        self.calls += 1
        return current


def test_edge_agent_posts_snapshots_and_events_to_backend(
    client: TestClient,
    db_session,
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        edge_agent,
        "parse_args",
        lambda: argparse.Namespace(source="fake.mp4", display=False),
    )
    monkeypatch.setattr(
        edge_agent,
        "build_runtime_config",
        lambda args: EdgeConfig(
            capture_interval_seconds=1,
            confidence_threshold=0.5,
            stabilization_window=3,
            backend_api_base_url="http://testserver/api",
            device_id="cam-001",
            device_api_key="dev-cam-001-key",
            heartbeat_interval_seconds=60,
            retry_max_attempts=1,
            retry_backoff_seconds=0,
            retry_backoff_max_seconds=0,
            offline_queue_path=tmp_path / "offline-events.json",
            model_path=Path("test-model.pt"),
        ),
    )
    monkeypatch.setattr(edge_agent, "resolve_source", lambda _: Path("fake.mp4"))
    monkeypatch.setattr(edge_agent, "VideoCaptureSampler", FakeVideoCaptureSampler)
    monkeypatch.setattr(edge_agent, "EggDetector", FakeDetector)
    monkeypatch.setattr(
        edge_agent,
        "EventReporter",
        lambda **kwargs: EventReporter(
            **kwargs,
            client=ApiClientAdapter(client),
            sleep_func=lambda _: None,
        ),
    )

    result = edge_agent.run()

    assert result == 0

    db_session.expire_all()
    snapshot_count = db_session.execute(select(func.count(CountSnapshot.id))).scalar_one()
    detection_count = db_session.execute(select(func.count(EggDetection.id))).scalar_one()
    device = db_session.execute(select(Device).where(Device.device_id == "cam-001")).scalar_one()

    assert snapshot_count == 3
    assert detection_count == 1
    assert device.last_heartbeat is not None
