from __future__ import annotations

import argparse
import json
import time
from dataclasses import replace
from pathlib import Path

import cv2

try:
    from .capture import CameraCapture, VideoCaptureSampler, resolve_source
    from .config import DEFAULT_CONFIG_PATH, load_config
    from .detector import EggDetector
    from .size_classifier import SizeClassifier, count_sizes
    from .stabilizer import CaptureSnapshot, RollingStabilizer
except ImportError:
    from capture import CameraCapture, VideoCaptureSampler, resolve_source
    from config import DEFAULT_CONFIG_PATH, load_config
    from detector import EggDetector
    from size_classifier import SizeClassifier, count_sizes
    from stabilizer import CaptureSnapshot, RollingStabilizer

WINDOW_NAME = "EggSentry Edge Agent"
UNKNOWN_COLOR = (0, 255, 255)
SIZE_COLORS = {
    "small": (0, 200, 255),
    "medium": (0, 255, 0),
    "large": (255, 200, 0),
    "extra-large": (255, 0, 150),
    "jumbo": (0, 0, 255),
    "unknown": UNKNOWN_COLOR,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EggSentry Phase 1 edge agent: capture, infer, classify, stabilize."
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Camera index or video file path. Use a video path for test mode.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Capture interval in seconds. Defaults to config.json / env value.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=None,
        help="YOLO confidence threshold. Defaults to config.json / env value.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the edge config JSON file.",
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Show annotated detections in an OpenCV window.",
    )
    parser.add_argument(
        "--no-video-loop",
        action="store_true",
        help="Exit instead of looping when the test video reaches EOF.",
    )
    return parser.parse_args()


def build_runtime_config(args: argparse.Namespace):
    config = load_config(args.config)
    if args.interval is not None:
        config = replace(config, capture_interval_seconds=args.interval)
    if args.conf is not None:
        config = replace(config, confidence_threshold=args.conf)
    if args.no_video_loop:
        config = replace(config, video_loop=False)
    return config


def format_detection_record(detection, classification) -> dict[str, object]:
    return {
        "bbox": list(detection.bbox),
        "confidence": round(detection.confidence, 4),
        "label": detection.label,
        "track_id": detection.track_id,
        "size": classification.size,
        "normalized_area": round(classification.normalized_area, 6),
        "aspect_ratio": round(classification.aspect_ratio, 4),
        "reason": classification.reason,
    }


def annotate_frame(frame, detections, classifications, stabilized, cycle_index, source_label):
    annotated = frame.copy()

    for detection, classification in zip(detections, classifications):
        color = SIZE_COLORS.get(classification.size, UNKNOWN_COLOR)
        x1, y1, x2, y2 = detection.bbox
        label = f"{classification.size} {detection.confidence:.0%}"
        if detection.track_id is not None:
            label = f"#{detection.track_id} {label}"

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        (text_width, text_height), _ = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )
        cv2.rectangle(
            annotated,
            (x1, max(0, y1 - text_height - 8)),
            (x1 + text_width + 6, y1),
            color,
            -1,
        )
        cv2.putText(
            annotated,
            label,
            (x1 + 3, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )

    panel_lines = [
        f"Cycle: {cycle_index}",
        f"Source: {source_label}",
        f"Raw count: {len(detections)}",
        f"Stable count: {stabilized.total_count}",
    ]
    if stabilized.size_counts:
        panel_lines.append(
            "Stable sizes: "
            + ", ".join(f"{key}={value}" for key, value in stabilized.size_counts.items())
        )

    line_height = 22
    panel_height = (line_height * len(panel_lines)) + 14
    panel_width = 360
    overlay = annotated.copy()
    cv2.rectangle(overlay, (10, 10), (10 + panel_width, 10 + panel_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.58, annotated, 0.42, 0, annotated)

    for index, line in enumerate(panel_lines):
        y = 32 + index * line_height
        cv2.putText(
            annotated,
            line,
            (18, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    return annotated


def run() -> int:
    args = parse_args()
    config = build_runtime_config(args)
    source = resolve_source(args.source)
    source_label = f"camera:{source}" if isinstance(source, int) else str(source)

    detector = EggDetector(
        model_path=Path(config.model_path),
        confidence_threshold=config.confidence_threshold,
    )
    classifier = SizeClassifier(
        thresholds=config.size_thresholds,
        edge_margin_pixels=config.edge_margin_pixels,
        aspect_ratio_min=config.aspect_ratio_min,
        aspect_ratio_max=config.aspect_ratio_max,
    )
    stabilizer = RollingStabilizer(window_size=config.stabilization_window)

    if isinstance(source, int):
        frame_source = CameraCapture(
            source=source,
            warmup_seconds=config.camera_warmup_seconds,
        )
        use_tracking = False
    else:
        frame_source = VideoCaptureSampler(
            source=source,
            interval_seconds=config.capture_interval_seconds,
            loop=config.video_loop,
        )
        use_tracking = args.display

    cycle_index = 0
    try:
        while True:
            if isinstance(source, int) and cycle_index > 0:
                time.sleep(config.capture_interval_seconds)

            captured = frame_source.capture_frame()
            cycle_index += 1

            detections = detector.detect(captured.frame, use_tracking=use_tracking)
            classifications = [
                classifier.classify(detection.bbox, captured.frame.shape)
                for detection in detections
            ]
            size_counts = count_sizes(classifications)
            detection_records = [
                format_detection_record(detection, classification)
                for detection, classification in zip(detections, classifications)
            ]

            snapshot = CaptureSnapshot(
                total_count=len(detections),
                size_counts=size_counts,
                detections=detection_records,
            )
            stabilized = stabilizer.update(snapshot)

            payload = {
                "cycle": cycle_index,
                "source": source_label,
                "frame_index": captured.frame_index,
                "timestamp_seconds": (
                    None
                    if captured.timestamp_seconds is None
                    else round(captured.timestamp_seconds, 3)
                ),
                "raw_count": snapshot.total_count,
                "raw_size_counts": snapshot.size_counts,
                "stable_count": stabilized.total_count,
                "stable_size_counts": stabilized.size_counts,
                "detections": snapshot.detections,
            }
            print(json.dumps(payload, sort_keys=True))

            if args.display:
                annotated = annotate_frame(
                    captured.frame,
                    detections,
                    classifications,
                    stabilized,
                    cycle_index,
                    source_label,
                )
                cv2.imshow(WINDOW_NAME, annotated)
                wait_ms = 750 if isinstance(source, int) else 1
                key = cv2.waitKey(wait_ms) & 0xFF
                if key in {ord("q"), 27}:
                    break
    except StopIteration:
        print("Video source exhausted; exiting because --no-video-loop was set.")
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        frame_source.close()
        if args.display:
            cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(run())

