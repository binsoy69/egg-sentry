from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2

try:
    from .calibration_core import (
        CalibrationError,
        SizeClassification,
        classify_bbox,
        count_classifications,
        load_calibration,
    )
    from .detector import Detection, EggDetector
    from .runtime import DEFAULT_CALIBRATION_PATH, open_capture, parse_source, resolve_model_path, source_label
except ImportError:
    from calibration_core import (
        CalibrationError,
        SizeClassification,
        classify_bbox,
        count_classifications,
        load_calibration,
    )
    from detector import Detection, EggDetector
    from runtime import DEFAULT_CALIBRATION_PATH, open_capture, parse_source, resolve_model_path, source_label

WINDOW_NAME = "EggSentry Calibrated Counter"
UNKNOWN_COLOR = (0, 255, 255)
SIZE_COLORS = {
    "jumbo": (0, 0, 255),
    "xl": (255, 0, 150),
    "large": (255, 200, 0),
    "medium": (0, 255, 0),
    "small": (0, 200, 255),
    "peewee": (180, 180, 180),
    "unknown": UNKNOWN_COLOR,
}
REMOVED_LABEL_IDS = frozenset({"xs", "placeholder"})
KEY_ESC = 27


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Standalone calibrated EggSentry detector and counter.",
    )
    parser.add_argument("--source", default="1", help="Camera index or video file path.")
    parser.add_argument("--model", default=None, help="Optional YOLO model path override.")
    parser.add_argument("--conf", type=float, default=0.5, help="YOLO confidence threshold.")
    parser.add_argument(
        "--calibration",
        default=str(DEFAULT_CALIBRATION_PATH),
        help="Calibration JSON file to read.",
    )
    parser.add_argument("--width", type=int, default=None, help="Requested capture width.")
    parser.add_argument("--height", type=int, default=None, help="Requested capture height.")
    parser.add_argument(
        "--infer-every",
        type=int,
        default=3,
        help="Run inference every N frames to keep preview responsive.",
    )
    parser.add_argument("--mirror", action="store_true", help="Mirror the preview horizontally.")
    return parser.parse_args(argv)


def _ensure_supported_calibration(calibration) -> None:
    removed_labels = sorted(
        REMOVED_LABEL_IDS
        & (set(calibration.labels.keys()) | set(calibration.labels_ordered_by_area))
    )
    if removed_labels:
        raise CalibrationError(
            "Calibration contains removed size labels: "
            + ", ".join(removed_labels)
            + ". Re-run calibrate_camera.py to create a peewee-only smallest-size calibration."
        )


def draw_detections(
    frame: object,
    detections: list[Detection],
    classifications: list[SizeClassification],
) -> None:
    for detection, classification in zip(detections, classifications):
        color = SIZE_COLORS.get(classification.label_id, UNKNOWN_COLOR)
        x1, y1, x2, y2 = detection.bbox
        label = f"{classification.label} {detection.confidence:.0%}"
        if classification.reason is not None:
            label = f"unknown {classification.reason}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        (text_width, text_height), _ = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            1,
        )
        text_top = max(0, y1 - text_height - 8)
        cv2.rectangle(frame, (x1, text_top), (x1 + text_width + 8, y1), color, -1)
        cv2.putText(
            frame,
            label,
            (x1 + 4, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )


def draw_panel(
    frame: object,
    *,
    source: str,
    calibration_path: Path,
    detections: list[Detection],
    classifications: list[SizeClassification],
    calibration,
    inference_ms: float | None,
) -> None:
    size_counts = count_classifications(classifications, calibration)
    lines = [
        "EggSentry calibrated counter",
        f"Eggs detected: {len(detections)}",
    ]
    if size_counts:
        lines.append("Sizes: " + "  ".join(f"{size}={count}" for size, count in size_counts.items()))
    lines.append(f"Source: {source}")
    lines.append(f"Calibration: {calibration_path.name}")
    if inference_ms is not None:
        lines.append(f"Inference: {inference_ms:.0f} ms")
    lines.append("Q or Esc = quit")

    line_height = 26
    panel_width = min(frame.shape[1] - 20, 760)
    panel_height = 18 + (line_height * len(lines))
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (10 + panel_width, 10 + panel_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.62, frame, 0.38, 0, frame)
    cv2.rectangle(frame, (10, 10), (10 + panel_width, 10 + panel_height), (0, 190, 80), 2)

    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (20, 40 + (index * line_height)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    calibration_path = Path(args.calibration).resolve()
    calibration = load_calibration(calibration_path)
    _ensure_supported_calibration(calibration)
    model_path = resolve_model_path(args.model)
    source = parse_source(args.source)
    label = source_label(source)

    print(f"Loaded calibration: {calibration_path}")
    print(f"Loading model: {model_path}")
    detector = EggDetector(model_path=model_path, confidence_threshold=args.conf)
    cap = open_capture(source, width=args.width, height=args.height)

    detections: list[Detection] = []
    classifications: list[SizeClassification] = []
    inference_ms: float | None = None
    frame_index = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Unable to read frame from source {source}")
            frame_index += 1

            if args.mirror:
                frame = cv2.flip(frame, 1)

            should_infer = frame_index == 1 or frame_index % max(1, args.infer_every) == 0
            if should_infer:
                start = time.perf_counter()
                detections = detector.detect(frame)
                classifications = [
                    classify_bbox(
                        detection.bbox,
                        frame.shape,
                        calibration,
                        confidence=detection.confidence,
                    )
                    for detection in detections
                ]
                inference_ms = (time.perf_counter() - start) * 1000.0

            annotated = frame.copy()
            draw_detections(annotated, detections, classifications)
            draw_panel(
                annotated,
                source=label,
                calibration_path=calibration_path,
                detections=detections,
                classifications=classifications,
                calibration=calibration,
                inference_ms=inference_ms,
            )
            cv2.imshow(WINDOW_NAME, annotated)
            key = cv2.waitKeyEx(1)
            if key in {KEY_ESC, ord("q"), ord("Q")}:
                break
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
