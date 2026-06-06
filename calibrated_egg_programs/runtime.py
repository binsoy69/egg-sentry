from __future__ import annotations

import time
from pathlib import Path
import sys

import cv2

PROGRAM_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROGRAM_DIR.parent
if getattr(sys, "frozen", False):
    BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS")).resolve()
    EXE_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_ROOT = REPO_ROOT
    EXE_DIR = PROGRAM_DIR

DEFAULT_CALIBRATION_PATH = EXE_DIR / "calibration.json"
MODEL_NAMES = ("counter-yolo26n_ncnn_model", "counter-yolo26n.pt")


def candidate_model_paths() -> list[Path]:
    candidates: list[Path] = []
    for model_name in MODEL_NAMES:
        candidates.append(EXE_DIR / "models" / model_name)
    for model_name in MODEL_NAMES:
        candidates.append(BUNDLE_ROOT / "models" / model_name)
    for model_name in MODEL_NAMES:
        candidates.append(PROGRAM_DIR / "models" / model_name)
    for model_name in MODEL_NAMES:
        candidates.append(REPO_ROOT / "models" / model_name)
    return list(dict.fromkeys(candidates))


def resolve_model_path(raw_model: str | None = None) -> Path:
    if raw_model:
        model_path = Path(raw_model).resolve()
        if not model_path.exists():
            raise FileNotFoundError(f"YOLO model not found at {model_path}")
        return model_path

    for candidate in candidate_model_paths():
        if candidate.exists():
            return candidate.resolve()

    joined = "\n  ".join(str(path) for path in candidate_model_paths())
    raise FileNotFoundError(f"No YOLO model found. Checked:\n  {joined}")


def parse_source(raw_source: str) -> int | Path:
    value = raw_source.strip()
    if value.isdigit():
        return int(value)

    path = Path(value)
    if not path.exists():
        raise FileNotFoundError(f"Video source not found: {value}")
    return path.resolve()


def source_label(source: int | Path) -> str:
    return f"camera:{source}" if isinstance(source, int) else str(source)


def open_capture(
    source: int | Path,
    *,
    width: int | None = None,
    height: int | None = None,
    warmup_seconds: float = 0.5,
) -> cv2.VideoCapture:
    raw_source: int | str = source if isinstance(source, int) else str(source)
    if isinstance(source, int) and sys.platform.startswith("win"):
        cap = cv2.VideoCapture(raw_source, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(raw_source)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video source {source}")

    if width is not None and width > 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height is not None and height > 0:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    if isinstance(source, int) and warmup_seconds > 0:
        time.sleep(warmup_seconds)
        for _ in range(3):
            cap.read()

    return cap
