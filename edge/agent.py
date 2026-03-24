from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path

import cv2

try:
    from .capture import CameraCapture, VideoCaptureSampler, resolve_source
    from .config import DEFAULT_CONFIG_PATH, EdgeConfig, load_config
    from .detector import EggDetector
    from .reporter import EventReporter, PermanentReporterError, RetryableReporterError
    from .size_classifier import SIZE_ORDER, SizeClassifier, count_sizes
    from .stabilizer import CaptureSnapshot, RollingStabilizer
except ImportError:
    from capture import CameraCapture, VideoCaptureSampler, resolve_source
    from config import DEFAULT_CONFIG_PATH, EdgeConfig, load_config
    from detector import EggDetector
    from reporter import EventReporter, PermanentReporterError, RetryableReporterError
    from size_classifier import SIZE_ORDER, SizeClassifier, count_sizes
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


@dataclass
class ReportingState:
    live_count: int = 0
    size_counts: dict[str, int] = field(default_factory=dict)
    next_heartbeat_at: float = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EggSentry edge agent: capture, infer, classify, stabilize, and report."
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
        "--backend-url",
        default=None,
        help="Backend API base URL, for example http://127.0.0.1:8000/api.",
    )
    parser.add_argument(
        "--device-id",
        default=None,
        help="Device identifier sent to the backend.",
    )
    parser.add_argument(
        "--device-key",
        default=None,
        help="Device API key used for X-Device-Key authentication.",
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=int,
        default=None,
        help="Heartbeat interval in seconds. Defaults to config.json / env value.",
    )
    parser.add_argument(
        "--queue-path",
        default=None,
        help="Path to the offline event queue JSON file.",
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


def build_runtime_config(args: argparse.Namespace) -> EdgeConfig:
    config = load_config(args.config)
    if args.interval is not None:
        config = replace(config, capture_interval_seconds=args.interval)
    if args.conf is not None:
        config = replace(config, confidence_threshold=args.conf)
    if args.no_video_loop:
        config = replace(config, video_loop=False)
    if args.backend_url is not None:
        config = replace(config, backend_api_base_url=args.backend_url.rstrip("/"))
    if args.device_id is not None:
        config = replace(config, device_id=args.device_id)
    if args.device_key is not None:
        config = replace(config, device_api_key=args.device_key)
    if args.heartbeat_interval is not None:
        config = replace(config, heartbeat_interval_seconds=args.heartbeat_interval)
    if args.queue_path is not None:
        config = replace(config, offline_queue_path=Path(args.queue_path))
    return config


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


def _ordered_sizes(*size_maps: dict[str, int]) -> list[str]:
    ordered = list(SIZE_ORDER)
    extras: list[str] = []
    for size_map in size_maps:
        for size in size_map:
            if size not in SIZE_ORDER and size not in extras:
                extras.append(size)
    return ordered + extras


def build_new_egg_records(
    previous_size_counts: dict[str, int],
    current_size_counts: dict[str, int],
    detections: list[dict[str, object]],
    detected_at: datetime,
) -> list[dict[str, object]]:
    timestamp = detected_at.isoformat()
    detections_by_size: dict[str, list[dict[str, object]]] = {}
    for detection in detections:
        size = str(detection.get("size", "unknown"))
        detections_by_size.setdefault(size, []).append(dict(detection))

    new_eggs: list[dict[str, object]] = []
    for size in _ordered_sizes(previous_size_counts, current_size_counts):
        needed = max(0, current_size_counts.get(size, 0) - previous_size_counts.get(size, 0))
        if needed <= 0:
            continue

        candidates = detections_by_size.get(size, [])
        for _ in range(needed):
            detection = candidates.pop(0) if candidates else {}
            new_eggs.append(
                {
                    "size": size,
                    "confidence": detection.get("confidence"),
                    "bbox_area_normalized": detection.get("normalized_area"),
                    "detected_at": timestamp,
                }
            )

    return new_eggs


def sync_reporting_state(state: ReportingState, stabilized) -> None:
    state.live_count = stabilized.total_count
    state.size_counts = dict(stabilized.size_counts)


def flush_queue(reporter: EventReporter | None) -> dict[str, int] | None:
    if reporter is None:
        return None
    return asdict(reporter.flush_event_queue())


def maybe_send_heartbeat(
    reporter: EventReporter | None,
    state: ReportingState,
    heartbeat_interval_seconds: int,
    current_count: int,
) -> dict[str, object] | None:
    if reporter is None:
        return None

    now_monotonic = time.monotonic()
    if now_monotonic < state.next_heartbeat_at:
        return None

    state.next_heartbeat_at = now_monotonic + heartbeat_interval_seconds
    try:
        heartbeat = reporter.send_heartbeat(timestamp=utc_now(), current_count=current_count)
    except RetryableReporterError:
        return {
            "delivery": {
                "delivered": False,
                "queued": False,
                "status_code": None,
                "response_body": None,
                "queue_depth": reporter.queue_depth(),
            },
            "queue_flush": None,
        }

    queue_flush = reporter.flush_event_queue()
    return {
        "delivery": asdict(heartbeat),
        "queue_flush": asdict(queue_flush),
    }


def wait_until_next_capture(
    deadline: float,
    reporter: EventReporter | None,
    state: ReportingState,
    heartbeat_interval_seconds: int,
    current_count: int,
) -> None:
    while True:
        maybe_send_heartbeat(reporter, state, heartbeat_interval_seconds, current_count)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return

        sleep_slice = min(1.0, remaining)
        if reporter is not None:
            until_heartbeat = max(0.0, state.next_heartbeat_at - time.monotonic())
            if until_heartbeat == 0.0:
                continue
            sleep_slice = min(sleep_slice, until_heartbeat)
        time.sleep(max(0.0, sleep_slice))


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
    reporter = EventReporter(
        backend_api_base_url=config.backend_api_base_url,
        device_id=config.device_id,
        device_api_key=config.device_api_key,
        timeout_seconds=config.request_timeout_seconds,
        retry_max_attempts=config.retry_max_attempts,
        retry_backoff_seconds=config.retry_backoff_seconds,
        retry_backoff_max_seconds=config.retry_backoff_max_seconds,
        offline_queue_path=config.offline_queue_path,
    )
    reporting_state = ReportingState(next_heartbeat_at=0.0)

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
                wait_until_next_capture(
                    deadline=time.monotonic() + config.capture_interval_seconds,
                    reporter=reporter,
                    state=reporting_state,
                    heartbeat_interval_seconds=config.heartbeat_interval_seconds,
                    current_count=reporting_state.live_count,
                )

            captured = frame_source.capture_frame()
            event_timestamp = utc_now()
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

            previous_live_count = reporting_state.live_count
            previous_size_counts = dict(reporting_state.size_counts)
            queue_status = flush_queue(reporter)
            event_status = None

            if stabilized.total_count > previous_live_count:
                new_eggs = build_new_egg_records(
                    previous_size_counts,
                    stabilized.size_counts,
                    snapshot.detections,
                    event_timestamp,
                )
                event_status = asdict(
                    reporter.send_event(
                        timestamp=event_timestamp,
                        total_count=stabilized.total_count,
                        new_eggs=new_eggs,
                        size_breakdown=stabilized.size_counts,
                    )
                )
                sync_reporting_state(reporting_state, stabilized)
            else:
                event_status = asdict(
                    reporter.send_snapshot(
                        timestamp=event_timestamp,
                        total_count=stabilized.total_count,
                        size_breakdown=stabilized.size_counts,
                    )
                )
                if (
                    stabilized.total_count != previous_live_count
                    or stabilized.size_counts != previous_size_counts
                ):
                    sync_reporting_state(reporting_state, stabilized)

            heartbeat_status = maybe_send_heartbeat(
                reporter,
                reporting_state,
                config.heartbeat_interval_seconds,
                stabilized.total_count,
            )

            payload = {
                "cycle": cycle_index,
                "source": source_label,
                "frame_index": captured.frame_index,
                "timestamp_seconds": (
                    None
                    if captured.timestamp_seconds is None
                    else round(captured.timestamp_seconds, 3)
                ),
                "captured_at": event_timestamp.isoformat(),
                "raw_count": snapshot.total_count,
                "raw_size_counts": snapshot.size_counts,
                "stable_count": stabilized.total_count,
                "stable_size_counts": stabilized.size_counts,
                "detections": snapshot.detections,
                "reporting": {
                    "previous_live_count": previous_live_count,
                    "queue_flush": queue_status,
                    "event": event_status,
                    "heartbeat": heartbeat_status,
                    "queue_depth": reporter.queue_depth(),
                },
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
    except PermanentReporterError as exc:
        print(f"Backend rejected the edge request: {exc}")
        return 1
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        frame_source.close()
        reporter.close()
        if args.display:
            cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
