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
    size_thresholds: SizeThresholds = SizeThresholds()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> EdgeConfig:
    config_path = Path(path)
    data = _read_json(config_path)

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
        model_path=Path(data.get("model_path", DEFAULT_MODEL_PATH)),
        size_thresholds=thresholds,
    )
    return apply_environment_overrides(config)


def apply_environment_overrides(config: EdgeConfig) -> EdgeConfig:
    model_path = Path(os.getenv("MODEL_PATH", str(config.model_path)))
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
    )

