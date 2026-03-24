from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

EDGE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = EDGE_DIR / "config.json"
DEFAULT_MODEL_PATH = EDGE_DIR.parent / "models" / "counter-yolo26n.pt"


@dataclass(frozen=True)
class SizeThresholds:
    small_max: float = 0.0020
    medium_max: float = 0.0030
    large_max: float = 0.0042
    xl_max: float = 0.0055


@dataclass(frozen=True)
class EdgeConfig:
    capture_interval_seconds: int = 120
    confidence_threshold: float = 0.5
    stabilization_window: int = 3
    camera_warmup_seconds: float = 0.5
    edge_margin_pixels: int = 10
    aspect_ratio_min: float = 0.5
    aspect_ratio_max: float = 2.0
    video_loop: bool = True
    model_path: Path = DEFAULT_MODEL_PATH
    backend_api_base_url: str = "http://127.0.0.1:8000/api"
    device_id: str = "cam-001"
    device_api_key: str = "dev-cam-001-key"
    heartbeat_interval_seconds: int = 60
    request_timeout_seconds: float = 10.0
    retry_max_attempts: int = 3
    retry_backoff_seconds: float = 1.0
    retry_backoff_max_seconds: float = 8.0
    offline_queue_path: Path = EDGE_DIR / "offline_events.json"
    size_thresholds: SizeThresholds = SizeThresholds()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(base_dir: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> EdgeConfig:
    config_path = Path(path).resolve()
    data = _read_json(config_path)
    config_dir = config_path.parent

    thresholds = SizeThresholds(**data.get("size_thresholds", {}))
    config = EdgeConfig(
        capture_interval_seconds=int(data.get("capture_interval_seconds", 120)),
        confidence_threshold=float(data.get("confidence_threshold", 0.5)),
        stabilization_window=int(data.get("stabilization_window", 3)),
        camera_warmup_seconds=float(data.get("camera_warmup_seconds", 0.5)),
        edge_margin_pixels=int(data.get("edge_margin_pixels", 10)),
        aspect_ratio_min=float(data.get("aspect_ratio_min", 0.5)),
        aspect_ratio_max=float(data.get("aspect_ratio_max", 2.0)),
        video_loop=bool(data.get("video_loop", True)),
        model_path=_resolve_path(config_dir, data.get("model_path", DEFAULT_MODEL_PATH)),
        backend_api_base_url=str(
            data.get("backend_api_base_url", "http://127.0.0.1:8000/api")
        ).rstrip("/"),
        device_id=str(data.get("device_id", "cam-001")),
        device_api_key=str(data.get("device_api_key", "dev-cam-001-key")),
        heartbeat_interval_seconds=int(data.get("heartbeat_interval_seconds", 60)),
        request_timeout_seconds=float(data.get("request_timeout_seconds", 10.0)),
        retry_max_attempts=int(data.get("retry_max_attempts", 3)),
        retry_backoff_seconds=float(data.get("retry_backoff_seconds", 1.0)),
        retry_backoff_max_seconds=float(data.get("retry_backoff_max_seconds", 8.0)),
        offline_queue_path=_resolve_path(
            config_dir, data.get("offline_queue_path", "offline_events.json")
        ),
        size_thresholds=thresholds,
    )
    return apply_environment_overrides(config)


def apply_environment_overrides(config: EdgeConfig) -> EdgeConfig:
    model_path = Path(os.getenv("MODEL_PATH", str(config.model_path)))
    offline_queue_path = Path(os.getenv("OFFLINE_QUEUE_PATH", str(config.offline_queue_path)))
    return replace(
        config,
        capture_interval_seconds=int(
            os.getenv("CAPTURE_INTERVAL_SECONDS", config.capture_interval_seconds)
        ),
        confidence_threshold=float(
            os.getenv("CONFIDENCE_THRESHOLD", config.confidence_threshold)
        ),
        stabilization_window=int(
            os.getenv("STABILIZATION_WINDOW", config.stabilization_window)
        ),
        camera_warmup_seconds=float(
            os.getenv("CAMERA_WARMUP_SECONDS", config.camera_warmup_seconds)
        ),
        edge_margin_pixels=int(
            os.getenv("EDGE_MARGIN_PIXELS", config.edge_margin_pixels)
        ),
        aspect_ratio_min=float(
            os.getenv("ASPECT_RATIO_MIN", config.aspect_ratio_min)
        ),
        aspect_ratio_max=float(
            os.getenv("ASPECT_RATIO_MAX", config.aspect_ratio_max)
        ),
        video_loop=_bool_env("VIDEO_LOOP", config.video_loop),
        model_path=model_path,
        backend_api_base_url=os.getenv(
            "BACKEND_API_BASE_URL", config.backend_api_base_url
        ).rstrip("/"),
        device_id=os.getenv("DEVICE_ID", config.device_id),
        device_api_key=os.getenv("DEVICE_API_KEY", config.device_api_key),
        heartbeat_interval_seconds=int(
            os.getenv("HEARTBEAT_INTERVAL_SECONDS", config.heartbeat_interval_seconds)
        ),
        request_timeout_seconds=float(
            os.getenv("REQUEST_TIMEOUT_SECONDS", config.request_timeout_seconds)
        ),
        retry_max_attempts=int(
            os.getenv("RETRY_MAX_ATTEMPTS", config.retry_max_attempts)
        ),
        retry_backoff_seconds=float(
            os.getenv("RETRY_BACKOFF_SECONDS", config.retry_backoff_seconds)
        ),
        retry_backoff_max_seconds=float(
            os.getenv("RETRY_BACKOFF_MAX_SECONDS", config.retry_backoff_max_seconds)
        ),
        offline_queue_path=offline_queue_path,
    )
