"""
EggSentry Viewer — standalone egg detection and counting app.

Double-click to launch. Connect your webcam and eggs are detected automatically.
  - Arrow keys or number keys to pick which camera to use
  - Enter / Space to confirm camera selection
  - Q / Esc to quit at any time
  - S to save a screenshot during detection
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Resolve paths for both development and PyInstaller-bundled exe
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    _BUNDLE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    _MODEL_PATH = _BUNDLE_DIR / "models" / "counter-yolo26n_ncnn_model"
    sys.path.insert(0, str(_BUNDLE_DIR / "edge"))
else:
    _BUNDLE_DIR = Path(__file__).resolve().parent.parent
    _MODEL_PATH = _BUNDLE_DIR / "models" / "counter-yolo26n_ncnn_model"

try:
    from detector import Detection, EggDetector
    from size_classifier import SizeClassifier, count_sizes
    from config import SizeThresholds
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from detector import Detection, EggDetector
    from size_classifier import SizeClassifier, count_sizes
    from config import SizeThresholds

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WINDOW_NAME = "EggSentry Viewer"
CONFIDENCE = 0.5
INFER_EVERY = 3
SNAPSHOT_DIR = Path.home() / "EggSentry_Snapshots"
_MAX_CAMERAS_TO_SCAN = 5   # Check indices 0 … _MAX_CAMERAS_TO_SCAN-1

_THRESHOLDS = SizeThresholds(
    small_max=0.001337620132688492,
    medium_max=0.001368816654265873,
    large_max=0.001368916654265873,
    xl_max=0.0014265958271329365,
)

# Arrow-key codes returned by cv2.waitKeyEx() on Windows
_KEY_LEFT  = 2424832
_KEY_RIGHT = 2555904
_KEY_ENTER = 13
_KEY_SPACE = 32
_KEY_ESC   = 27
_KEY_Q     = ord("q")
_KEY_S     = ord("s")

# BGR colours per egg size
_UNKNOWN_COLOR: tuple[int, int, int] = (0, 255, 255)
_SIZE_COLORS: dict[str, tuple[int, int, int]] = {
    "small":       (0, 200, 255),
    "medium":      (0, 255, 0),
    "large":       (255, 200, 0),
    "extra-large": (255, 0, 150),
    "jumbo":       (0, 0, 255),
    "unknown":     _UNKNOWN_COLOR,
}


# ---------------------------------------------------------------------------
# Camera discovery
# ---------------------------------------------------------------------------

def _scan_cameras() -> list[int]:
    """Return indices of all cameras that can actually deliver a frame."""
    found: list[int] = []
    for idx in range(_MAX_CAMERAS_TO_SCAN):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)   # CAP_DSHOW for faster open on Windows
        if cap.isOpened():
            ok, _ = cap.read()
            cap.release()
            if ok:
                found.append(idx)
        else:
            cap.release()
    return found


def _camera_label(idx: int, total: int) -> str:
    """Human-readable label for a camera index."""
    if idx == 0 and total > 1:
        return f"Camera {idx}  (built-in / default)"
    if idx > 0:
        return f"Camera {idx}  (external USB)"
    return f"Camera {idx}"


# ---------------------------------------------------------------------------
# Camera selection screen
# ---------------------------------------------------------------------------

def _select_camera(available: list[int]) -> int | None:
    """
    Show an interactive selection screen.
    Returns the chosen camera index, or None if the user quits.
    """
    if not available:
        return None
    if len(available) == 1:
        print(f"Only one camera found (index {available[0]}), using it automatically.")
        return available[0]

    sel = 0          # index into `available`
    cap: cv2.VideoCapture | None = None
    current_cam_idx = -1

    print(f"Found {len(available)} camera(s): {available}")
    print("Use  ← →  arrow keys  or  number keys  to choose. Press  Enter  to confirm.")

    try:
        while True:
            cam_idx = available[sel]

            # (Re-)open camera when selection changes
            if cam_idx != current_cam_idx:
                if cap is not None:
                    cap.release()
                cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
                time.sleep(0.15)    # brief settle
                current_cam_idx = cam_idx

            ok, frame = cap.read() if cap and cap.isOpened() else (False, None)
            if not ok or frame is None:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)

            _draw_selection_overlay(frame, available, sel)
            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKeyEx(30)

            if key in {_KEY_ESC, _KEY_Q}:
                return None

            if key == _KEY_LEFT:
                sel = (sel - 1) % len(available)

            elif key == _KEY_RIGHT:
                sel = (sel + 1) % len(available)

            elif key in {_KEY_ENTER, _KEY_SPACE}:
                print(f"Selected: {_camera_label(available[sel], len(available))}")
                return available[sel]

            # Number keys 1…9 for direct selection (1 = first camera, etc.)
            elif ord("1") <= key <= ord("9"):
                num = key - ord("1")        # 0-based
                if num < len(available):
                    sel = num

    finally:
        if cap is not None:
            cap.release()


def _draw_selection_overlay(
    frame: np.ndarray,
    available: list[int],
    sel: int,
) -> None:
    h, w = frame.shape[:2]

    # --- Semi-transparent top banner ---
    banner_h = 54
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, banner_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    cv2.putText(
        frame,
        "Select camera   \u2190 \u2192 to cycle   1-9 to jump   Enter to confirm   Q to quit",
        (14, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, cv2.LINE_AA,
    )

    # --- Camera list at the bottom ---
    item_h = 36
    total_h = item_h * len(available) + 16
    by = h - total_h
    overlay2 = frame.copy()
    cv2.rectangle(overlay2, (0, by - 8), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay2, 0.70, frame, 0.30, 0, frame)

    for i, cam_idx in enumerate(available):
        y = by + i * item_h + item_h - 8
        is_selected = i == sel
        color = (50, 220, 50) if is_selected else (180, 180, 180)
        prefix = ">" if is_selected else f"{i + 1}."
        label = _camera_label(cam_idx, len(available))
        text = f"  {prefix}  {label}"
        thickness = 2 if is_selected else 1
        cv2.putText(
            frame, text, (14, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.60, color, thickness, cv2.LINE_AA,
        )


# ---------------------------------------------------------------------------
# Detection drawing helpers
# ---------------------------------------------------------------------------

def _draw_detections(
    frame: np.ndarray,
    detections: list[Detection],
    classifications: list[object],
) -> None:
    for det, cls in zip(detections, classifications):
        color = _SIZE_COLORS.get(cls.size, _UNKNOWN_COLOR)
        x1, y1, x2, y2 = det.bbox
        label = f"{cls.size if cls.size != 'unknown' else 'egg'} {det.confidence:.0%}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        text_top = max(0, y1 - th - 8)
        cv2.rectangle(frame, (x1, text_top), (x1 + tw + 8, y1), color, -1)
        cv2.putText(
            frame, label, (x1 + 4, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA,
        )


def _draw_panel(
    frame: np.ndarray,
    detections: list[Detection],
    classifications: list[object],
    inference_ms: float | None,
    screenshot_msg: str,
    camera_label: str,
) -> None:
    size_counts = count_sizes(classifications)
    total = len(detections)

    lines: list[tuple[str, float, int]] = [
        ("EggSentry Viewer", 0.70, 2),
        (f"Eggs detected: {total}", 0.65, 2),
    ]
    if size_counts:
        parts = "  ".join(f"{s}: {c}" for s, c in size_counts.items())
        lines.append((f"Sizes  {parts}", 0.55, 1))
    lines.append((f"Source: {camera_label}", 0.50, 1))
    if inference_ms is not None:
        lines.append((f"Detection speed: {inference_ms:.0f} ms", 0.50, 1))
    if screenshot_msg:
        lines.append((screenshot_msg, 0.50, 1))
    lines.append(("Q = quit     S = save screenshot", 0.48, 1))

    line_height = 28
    panel_w = 520
    panel_h = 18 + line_height * len(lines)

    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (10 + panel_w, 10 + panel_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.60, frame, 0.40, 0, frame)
    border = (0, 200, 60) if total > 0 else (0, 140, 200)
    cv2.rectangle(frame, (10, 10), (10 + panel_w, 10 + panel_h), border, 2)

    y = 42
    for text, fs, thick in lines:
        cv2.putText(
            frame, text, (20, y),
            cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 255, 255), thick, cv2.LINE_AA,
        )
        y += line_height


def _draw_error_screen(message: str) -> np.ndarray:
    frame = np.zeros((480, 720, 3), dtype=np.uint8)
    y = 160
    for line in message.split("\n"):
        cv2.putText(
            frame, line, (40, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 100, 255), 1, cv2.LINE_AA,
        )
        y += 36
    cv2.putText(
        frame, "Close this window to exit.", (40, y + 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA,
    )
    return frame


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run() -> int:
    print("EggSentry Viewer starting...")

    # --- Validate model ---
    if not _MODEL_PATH.exists():
        msg = (
            f"Model file not found:\n{_MODEL_PATH}\n\n"
            "Make sure the models/ folder is next to this program."
        )
        print(f"ERROR: {msg}")
        cv2.imshow(WINDOW_NAME, _draw_error_screen(msg))
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return 1

    # --- Scan for cameras (before loading the heavy model so the window appears fast) ---
    print("Scanning for cameras...")
    available = _scan_cameras()
    if not available:
        msg = "No webcam found.\n\nPlease connect a USB webcam and try again."
        print(f"ERROR: {msg}")
        cv2.imshow(WINDOW_NAME, _draw_error_screen(msg))
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return 1

    # --- Let user choose which camera ---
    chosen = _select_camera(available)
    if chosen is None:
        print("No camera selected. Exiting.")
        cv2.destroyAllWindows()
        return 0

    cam_label = _camera_label(chosen, len(available))
    print(f"Using {cam_label}")

    # --- Load YOLO model (shown after camera selection so the UI starts quickly) ---
    print("Loading egg detection model... (this may take a moment)")
    detector = EggDetector(model_path=_MODEL_PATH, confidence_threshold=CONFIDENCE)
    classifier = SizeClassifier(
        thresholds=_THRESHOLDS,
        edge_margin_pixels=10,
        aspect_ratio_min=0.5,
        aspect_ratio_max=2.0,
    )

    # --- Open chosen camera ---
    cap = cv2.VideoCapture(chosen, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"ERROR: Could not open camera {chosen}.")
        return 1

    time.sleep(0.5)
    for _ in range(3):
        cap.read()

    print("Ready. Press Q to quit, S to save a screenshot.")

    detections: list[Detection] = []
    classifications: list[object] = []
    inference_ms: float | None = None
    screenshot_msg = ""
    screenshot_msg_frames = 0
    frame_index = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Lost camera feed.")
                break
            frame_index += 1

            if frame_index == 1 or frame_index % INFER_EVERY == 0:
                t0 = time.perf_counter()
                detections = detector.detect(frame)
                classifications = [
                    classifier.classify(d.bbox, frame.shape) for d in detections
                ]
                inference_ms = (time.perf_counter() - t0) * 1000.0

            if screenshot_msg_frames > 0:
                screenshot_msg_frames -= 1
                if screenshot_msg_frames == 0:
                    screenshot_msg = ""

            annotated = frame.copy()
            _draw_detections(annotated, detections, classifications)
            _draw_panel(
                annotated, detections, classifications,
                inference_ms, screenshot_msg, cam_label,
            )

            cv2.imshow(WINDOW_NAME, annotated)
            key = cv2.waitKeyEx(1)

            if key in {_KEY_ESC, _KEY_Q}:
                break

            if key == _KEY_S:
                SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                path = SNAPSHOT_DIR / f"eggsentry-{ts}.jpg"
                cv2.imwrite(str(path), annotated)
                print(f"Screenshot saved: {path}")
                screenshot_msg = f"Saved: {path.name}"
                screenshot_msg_frames = 90

    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
