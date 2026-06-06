from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2

try:
    from .calibration_core import (
        DEFAULT_LABEL_IDS,
        DEFAULT_LABEL_NAMES,
        DetectionMeasurement,
        QualityFilters,
        build_calibration,
        measure_detections,
        save_calibration,
    )
    from .detector import Detection, EggDetector
    from .runtime import DEFAULT_CALIBRATION_PATH, open_capture, parse_source, resolve_model_path, source_label
except ImportError:
    from calibration_core import (
        DEFAULT_LABEL_IDS,
        DEFAULT_LABEL_NAMES,
        DetectionMeasurement,
        QualityFilters,
        build_calibration,
        measure_detections,
        save_calibration,
    )
    from detector import Detection, EggDetector
    from runtime import DEFAULT_CALIBRATION_PATH, open_capture, parse_source, resolve_model_path, source_label

WINDOW_NAME = "EggSentry Size Calibration"
VALID_COLOR = (0, 220, 80)
INVALID_COLOR = (0, 200, 255)
ACTIVE_COLOR = (255, 180, 0)
TEXT_COLOR = (255, 255, 255)
PANEL_BG = (0, 0, 0)
KEY_ESC = 27
KEY_SPACE = 32
KEY_BACKSPACE = {8, 127}


def _selection_key_range() -> str:
    return f"1-{len(DEFAULT_LABEL_IDS)}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Live camera calibration for EggSentry egg size labels.",
    )
    parser.add_argument("--source", default="1", help="Camera index or video file path.")
    parser.add_argument("--model", default=None, help="Optional YOLO model path override.")
    parser.add_argument("--conf", type=float, default=0.5, help="YOLO confidence threshold.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_CALIBRATION_PATH),
        help="Calibration JSON file to write.",
    )
    parser.add_argument("--width", type=int, default=None, help="Requested capture width.")
    parser.add_argument("--height", type=int, default=None, help="Requested capture height.")
    parser.add_argument(
        "--infer-every",
        type=int,
        default=3,
        help="Run inference every N frames to keep preview responsive.",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=5,
        help="Minimum valid samples required for each size before saving.",
    )
    parser.add_argument("--mirror", action="store_true", help="Mirror the preview horizontally.")
    return parser.parse_args(argv)


def _valid_measurements(measurements: list[DetectionMeasurement]) -> list[DetectionMeasurement]:
    return [measurement for measurement in measurements if measurement.reason is None]


def _ready_to_save(samples: dict[str, list[float]], min_samples: int) -> bool:
    return all(len(samples[label_id]) >= min_samples for label_id in DEFAULT_LABEL_IDS)


def _sample_lines(samples: dict[str, list[float]], min_samples: int) -> list[str]:
    lines: list[str] = []
    for start in range(0, len(DEFAULT_LABEL_IDS), 4):
        parts = []
        for offset, label_id in enumerate(DEFAULT_LABEL_IDS[start : start + 4], start=start + 1):
            parts.append(f"{offset}:{label_id}={len(samples[label_id])}/{min_samples}")
        lines.append("  ".join(parts))
    return lines


def draw_detections(
    frame: object,
    detections: list[Detection],
    measurements: list[DetectionMeasurement],
    active_label: str,
) -> None:
    for detection, measurement in zip(detections, measurements):
        x1, y1, x2, y2 = detection.bbox
        color = VALID_COLOR if measurement.reason is None else INVALID_COLOR
        label = f"{active_label} {detection.confidence:.0%}"
        if measurement.reason is not None:
            label = measurement.reason

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
    model_path: Path,
    active_index: int,
    samples: dict[str, list[float]],
    min_samples: int,
    valid_visible: int,
    inference_ms: float | None,
    message: str,
) -> None:
    active_label = DEFAULT_LABEL_IDS[active_index]
    ready = _ready_to_save(samples, min_samples)
    lines = [
        "EggSentry live size calibration",
        f"Source: {source}",
        f"Model: {model_path.name}",
        f"Active: {active_index + 1} {active_label}",
        f"Visible valid detections: {valid_visible}",
        f"Ready to save: {'yes' if ready else 'no'}",
    ]
    if inference_ms is not None:
        lines.append(f"Inference: {inference_ms:.0f} ms")
    lines.extend(_sample_lines(samples, min_samples))
    if message:
        lines.append(message)
    lines.append(
        f"Keys: {_selection_key_range()} select | Space/C capture | Backspace undo | S save | Q quit"
    )

    line_height = 24
    panel_width = min(frame.shape[1] - 20, 820)
    panel_height = 18 + (line_height * len(lines))
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (10 + panel_width, 10 + panel_height), PANEL_BG, -1)
    cv2.addWeighted(overlay, 0.62, frame, 0.38, 0, frame)
    cv2.rectangle(frame, (10, 10), (10 + panel_width, 10 + panel_height), ACTIVE_COLOR, 2)

    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (20, 38 + (index * line_height)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            TEXT_COLOR,
            1,
            cv2.LINE_AA,
        )


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.min_samples < 1:
        raise ValueError("--min-samples must be at least 1")

    filters = QualityFilters()
    model_path = resolve_model_path(args.model)
    source = parse_source(args.source)
    label = source_label(source)

    print(f"Loading model: {model_path}")
    detector = EggDetector(model_path=model_path, confidence_threshold=args.conf)
    cap = open_capture(source, width=args.width, height=args.height)
    print("Calibration started.")
    print(
        f"Use {_selection_key_range()} to select a size, "
        "Space/C to capture samples, S to save, Q to quit."
    )

    samples: dict[str, list[float]] = {label_id: [] for label_id in DEFAULT_LABEL_IDS}
    active_index = 0
    frame_index = 0
    detections: list[Detection] = []
    measurements: list[DetectionMeasurement] = []
    inference_ms: float | None = None
    message = ""
    message_until = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Unable to read frame from source {source}")
            frame_index += 1

            if args.mirror:
                frame = cv2.flip(frame, 1)

            should_infer = frame_index == 1 or frame_index % max(1, args.infer_every) == 0
            active_label = DEFAULT_LABEL_IDS[active_index]
            if should_infer:
                start = time.perf_counter()
                detections = detector.detect(frame)
                measurements = measure_detections(
                    detections,
                    frame.shape,
                    filters,
                    label_id=active_label,
                )
                inference_ms = (time.perf_counter() - start) * 1000.0

            if message and time.monotonic() > message_until:
                message = ""

            annotated = frame.copy()
            draw_detections(annotated, detections, measurements, active_label)
            valid_visible = len(_valid_measurements(measurements))
            draw_panel(
                annotated,
                source=label,
                model_path=model_path,
                active_index=active_index,
                samples=samples,
                min_samples=args.min_samples,
                valid_visible=valid_visible,
                inference_ms=inference_ms,
                message=message,
            )
            cv2.imshow(WINDOW_NAME, annotated)
            key = cv2.waitKeyEx(1)

            if key in {KEY_ESC, ord("q"), ord("Q")}:
                break

            if ord("1") <= key < ord("1") + len(DEFAULT_LABEL_IDS):
                active_index = key - ord("1")
                active_label = DEFAULT_LABEL_IDS[active_index]
                message = f"Selected {active_index + 1}: {active_label}"
                message_until = time.monotonic() + 2.0
                continue

            if key in {KEY_SPACE, ord("c"), ord("C")}:
                active_label = DEFAULT_LABEL_IDS[active_index]
                valid = _valid_measurements(measurements)
                if not valid:
                    message = "No valid visible detections to capture."
                else:
                    samples[active_label].extend(
                        measurement.normalized_area for measurement in valid
                    )
                    message = f"Captured {len(valid)} sample(s) for {active_label}."
                message_until = time.monotonic() + 2.5
                continue

            if key in KEY_BACKSPACE:
                active_label = DEFAULT_LABEL_IDS[active_index]
                if samples[active_label]:
                    removed = samples[active_label].pop()
                    message = f"Removed last {active_label} sample ({removed:.8f})."
                else:
                    message = f"No {active_label} samples to remove."
                message_until = time.monotonic() + 2.5
                continue

            if key in {ord("s"), ord("S")}:
                if not _ready_to_save(samples, args.min_samples):
                    missing = [
                        f"{label_id}={len(samples[label_id])}/{args.min_samples}"
                        for label_id in DEFAULT_LABEL_IDS
                        if len(samples[label_id]) < args.min_samples
                    ]
                    message = "Need more samples: " + ", ".join(missing)
                    message_until = time.monotonic() + 4.0
                    continue

                calibration = build_calibration(
                    samples,
                    labels=DEFAULT_LABEL_NAMES,
                    quality_filters=filters,
                    min_samples=args.min_samples,
                )
                saved_path = save_calibration(calibration, args.output)
                message = f"Saved calibration: {saved_path}"
                message_until = time.monotonic() + 5.0
                print(message)
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
