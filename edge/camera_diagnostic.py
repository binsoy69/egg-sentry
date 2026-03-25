from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

import cv2

try:
    from .capture import CameraCapture, resolve_source
    from .config import DEFAULT_CONFIG_PATH, EdgeConfig, load_config
    from .detector import Detection, EggDetector
    from .size_classifier import SizeClassifier, count_sizes
except ImportError:
    from capture import CameraCapture, resolve_source
    from config import DEFAULT_CONFIG_PATH, EdgeConfig, load_config
    from detector import Detection, EggDetector
    from size_classifier import SizeClassifier, count_sizes

WINDOW_NAME = "EggSentry Camera Diagnostic"
DEFAULT_SNAPSHOT_DIR = Path(__file__).resolve().parent / "diagnostic_snapshots"
GUIDE_MARGIN_RATIO = 0.12
CENTER_BOX_RATIO = 0.55
EDGE_WARNING_RATIO = 0.08
CENTER_TOLERANCE_RATIO = 0.18
TOO_SMALL_AREA_RATIO = 0.0012
TOO_LARGE_AREA_RATIO = 0.08
UNKNOWN_COLOR = (0, 255, 255)
STATUS_OK_COLOR = (0, 180, 0)
STATUS_WARN_COLOR = (0, 180, 255)
SIZE_COLORS = {
    "small": (0, 200, 255),
    "medium": (0, 255, 0),
    "large": (255, 200, 0),
    "extra-large": (255, 0, 150),
    "jumbo": (0, 0, 255),
    "unknown": UNKNOWN_COLOR,
}


@dataclass(frozen=True)
class PlacementFeedback:
    headline: str
    details: tuple[str, ...]
    ok: bool


@dataclass(frozen=True)
class ResolutionInfo:
    width: int
    height: int

    @property
    def label(self) -> str:
        return f"{self.width}x{self.height}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Live camera diagnostic for camera placement and egg detection.",
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Camera index or video file path.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the edge config JSON file.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional YOLO model override.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=None,
        help="YOLO confidence threshold override.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Requested capture width.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Requested capture height.",
    )
    parser.add_argument(
        "--infer-every",
        type=int,
        default=5,
        help="Run inference every N frames to keep the preview responsive.",
    )
    parser.add_argument(
        "--track",
        action="store_true",
        help="Use YOLO tracking mode for smoother box IDs in continuous video.",
    )
    parser.add_argument(
        "--mirror",
        action="store_true",
        help="Mirror the preview for easier manual camera adjustment.",
    )
    parser.add_argument(
        "--loop-video",
        action="store_true",
        help="Loop back to the start when a video file reaches EOF.",
    )
    parser.add_argument(
        "--snapshot-dir",
        default=str(DEFAULT_SNAPSHOT_DIR),
        help="Directory used when saving a diagnostic snapshot with the S key.",
    )
    return parser.parse_args(argv)


def build_runtime_config(args: argparse.Namespace) -> EdgeConfig:
    config = load_config(args.config)
    if args.conf is not None:
        config = replace(config, confidence_threshold=args.conf)
    if args.model is not None:
        config = replace(config, model_path=Path(args.model).resolve())
    return config


def open_video_source(
    source: int | Path,
    *,
    width: int | None,
    height: int | None,
    warmup_seconds: float,
) -> cv2.VideoCapture:
    raw_source: int | str = source if isinstance(source, int) else str(source)
    cap = cv2.VideoCapture(raw_source)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video source {source}")

    if width is not None:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height is not None:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    if isinstance(source, int) and warmup_seconds > 0:
        time.sleep(warmup_seconds)
        for _ in range(3):
            cap.read()

    return cap


def capture_resolution_info(frame: object) -> ResolutionInfo:
    frame_height, frame_width = frame.shape[:2]
    return ResolutionInfo(width=frame_width, height=frame_height)


def evaluate_camera_placement(
    frame_shape: tuple[int, int] | tuple[int, int, int],
    detections: list[Detection],
) -> PlacementFeedback:
    frame_height, frame_width = frame_shape[:2]
    if not detections:
        return PlacementFeedback(
            headline="No eggs detected",
            details=("Place an egg in view to validate the model and camera angle.",),
            ok=False,
        )

    frame_area = float(frame_width * frame_height)
    avg_area_ratio = sum(detection.area for detection in detections) / (len(detections) * frame_area)
    center_x = sum((detection.x1 + detection.x2) / 2.0 for detection in detections) / len(detections)
    center_y = sum((detection.y1 + detection.y2) / 2.0 for detection in detections) / len(detections)
    offset_x = (center_x - (frame_width / 2.0)) / frame_width
    offset_y = (center_y - (frame_height / 2.0)) / frame_height

    edge_margin_x = frame_width * EDGE_WARNING_RATIO
    edge_margin_y = frame_height * EDGE_WARNING_RATIO
    edge_hits = [
        detection
        for detection in detections
        if detection.x1 < edge_margin_x
        or detection.y1 < edge_margin_y
        or detection.x2 > frame_width - edge_margin_x
        or detection.y2 > frame_height - edge_margin_y
    ]

    details: list[str] = []
    if edge_hits:
        details.append("Some eggs are too close to the frame edge; widen or re-center the view.")

    if avg_area_ratio < TOO_SMALL_AREA_RATIO:
        details.append("Egg boxes look small; the camera may be too far away.")
    elif avg_area_ratio > TOO_LARGE_AREA_RATIO:
        details.append("Egg boxes fill too much of the frame; move the camera back slightly.")

    if offset_x <= -CENTER_TOLERANCE_RATIO:
        details.append("Eggs are clustered left of center; re-aim until they sit inside the middle guide.")
    elif offset_x >= CENTER_TOLERANCE_RATIO:
        details.append("Eggs are clustered right of center; re-aim until they sit inside the middle guide.")

    if offset_y <= -CENTER_TOLERANCE_RATIO:
        details.append("Eggs are clustered high in the frame; tilt until they sit inside the middle guide.")
    elif offset_y >= CENTER_TOLERANCE_RATIO:
        details.append("Eggs are clustered low in the frame; tilt until they sit inside the middle guide.")

    if details:
        return PlacementFeedback(
            headline="Adjust camera placement",
            details=tuple(details),
            ok=False,
        )

    return PlacementFeedback(
        headline="Placement looks good",
        details=("Eggs are centered and fully visible in the current view.",),
        ok=True,
    )


def draw_guides(frame: object) -> None:
    frame_height, frame_width = frame.shape[:2]
    margin_x = int(frame_width * GUIDE_MARGIN_RATIO)
    margin_y = int(frame_height * GUIDE_MARGIN_RATIO)
    center_box_width = int(frame_width * CENTER_BOX_RATIO)
    center_box_height = int(frame_height * CENTER_BOX_RATIO)
    center_x = frame_width // 2
    center_y = frame_height // 2
    left = max(0, center_x - (center_box_width // 2))
    top = max(0, center_y - (center_box_height // 2))
    right = min(frame_width, center_x + (center_box_width // 2))
    bottom = min(frame_height, center_y + (center_box_height // 2))

    guide_color = (90, 90, 90)
    center_color = (40, 160, 40)

    cv2.rectangle(
        frame,
        (margin_x, margin_y),
        (frame_width - margin_x, frame_height - margin_y),
        guide_color,
        1,
    )
    cv2.rectangle(frame, (left, top), (right, bottom), center_color, 1)
    cv2.line(frame, (frame_width // 3, 0), (frame_width // 3, frame_height), guide_color, 1)
    cv2.line(frame, ((frame_width * 2) // 3, 0), ((frame_width * 2) // 3, frame_height), guide_color, 1)
    cv2.line(frame, (0, frame_height // 3), (frame_width, frame_height // 3), guide_color, 1)
    cv2.line(frame, (0, (frame_height * 2) // 3), (frame_width, (frame_height * 2) // 3), guide_color, 1)
    cv2.drawMarker(
        frame,
        (center_x, center_y),
        center_color,
        markerType=cv2.MARKER_CROSS,
        markerSize=18,
        thickness=1,
    )


def draw_detection_overlay(frame: object, detections: list[Detection], classifications: list[object]) -> None:
    for detection, classification in zip(detections, classifications):
        color = SIZE_COLORS.get(classification.size, UNKNOWN_COLOR)
        x1, y1, x2, y2 = detection.bbox
        label = f"{detection.label} {detection.confidence:.0%}"
        if classification.size != "unknown":
            label = f"{label} {classification.size}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        (text_width, text_height), _ = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            1,
        )
        text_top = max(0, y1 - text_height - 10)
        cv2.rectangle(
            frame,
            (x1, text_top),
            (x1 + text_width + 8, y1),
            color,
            -1,
        )
        cv2.putText(
            frame,
            label,
            (x1 + 4, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )


def draw_status_panel(
    frame: object,
    *,
    source_label: str,
    frame_index: int,
    actual_resolution: ResolutionInfo | None,
    detection_enabled: bool,
    show_guides: bool,
    confidence_threshold: float,
    detections: list[Detection],
    classifications: list[object],
    feedback: PlacementFeedback,
    inference_ms: float | None,
) -> None:
    size_counts = count_sizes(classifications)
    status_color = STATUS_OK_COLOR if feedback.ok else STATUS_WARN_COLOR
    panel_lines = [
        f"Source: {source_label}",
        f"Frame: {frame_index}",
        f"Detector: {'on' if detection_enabled else 'paused'}  conf={confidence_threshold:.2f}",
        feedback.headline,
    ]
    if actual_resolution is not None:
        panel_lines.append(f"Agent frame resolution: {actual_resolution.label}")
    panel_lines.append(f"Egg detections: {len(detections)}")
    if inference_ms is not None:
        panel_lines.append(f"Inference: {inference_ms:.1f} ms")
    if size_counts:
        panel_lines.append(
            "Sizes: " + ", ".join(f"{size}={count}" for size, count in size_counts.items())
        )
    panel_lines.extend(feedback.details[:2])

    line_height = 22
    panel_width = 520
    panel_height = 18 + (line_height * len(panel_lines))
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (10 + panel_width, 10 + panel_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.58, frame, 0.42, 0, frame)
    cv2.rectangle(frame, (10, 10), (10 + panel_width, 10 + panel_height), status_color, 2)

    for index, line in enumerate(panel_lines):
        cv2.putText(
            frame,
            line,
            (20, 36 + (index * line_height)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    controls = "Keys: q quit | g guides | d detector | s save frame"
    if not show_guides:
        controls += " | guides hidden"
    cv2.putText(
        frame,
        controls,
        (14, frame.shape[0] - 14),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (235, 235, 235),
        1,
        cv2.LINE_AA,
    )


def save_snapshot(snapshot_dir: Path, frame: object) -> Path:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = snapshot_dir / f"diagnostic-{timestamp}.jpg"
    cv2.imwrite(str(path), frame)
    return path


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
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
    snapshot_dir = Path(args.snapshot_dir)
    use_agent_camera_capture = isinstance(source, int)
    camera_capture = None
    cap = None
    use_tracking = args.track and not use_agent_camera_capture
    if use_agent_camera_capture:
        if args.width is not None or args.height is not None:
            print("Ignoring --width/--height for live camera sources to match edge agent capture behavior.")
        camera_capture = CameraCapture(
            source=source,
            warmup_seconds=config.camera_warmup_seconds,
        )
    else:
        cap = open_video_source(
            source,
            width=args.width,
            height=args.height,
            warmup_seconds=config.camera_warmup_seconds,
        )

    detections: list[Detection] = []
    classifications: list[object] = []
    feedback = PlacementFeedback(
        headline="Waiting for inference",
        details=("The live preview is running. Detection results will appear shortly.",),
        ok=False,
    )
    inference_ms: float | None = None
    actual_resolution: ResolutionInfo | None = None
    detection_enabled = True
    show_guides = True
    frame_index = 0

    startup_message = (
        "Camera diagnostic started using the same live-camera capture and predict logic as the edge agent. "
        "Press q to quit, g to toggle guides, d to pause detection, and s to save a frame."
    )
    print(startup_message)

    try:
        while True:
            if use_agent_camera_capture:
                assert camera_capture is not None
                captured = camera_capture.capture_frame()
                frame = captured.frame
                frame_index = captured.frame_index or (frame_index + 1)
            else:
                assert cap is not None
                ok, frame = cap.read()
                if not ok:
                    if isinstance(source, Path) and args.loop_video:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    if isinstance(source, Path):
                        print(f"Video source ended: {source}")
                        break
                    raise RuntimeError(f"Unable to read frame from video source {source}")
                frame_index += 1

            if args.mirror:
                frame = cv2.flip(frame, 1)
            if actual_resolution is None:
                actual_resolution = capture_resolution_info(frame)
                print(f"Camera source {source_label} opened at {actual_resolution.label}")

            should_infer = False
            if detection_enabled:
                if use_agent_camera_capture:
                    should_infer = True
                else:
                    should_infer = frame_index == 1 or frame_index % max(1, args.infer_every) == 0

            if should_infer:
                start = time.perf_counter()
                detections = detector.detect(frame, use_tracking=use_tracking)
                classifications = [
                    classifier.classify(detection.bbox, frame.shape)
                    for detection in detections
                ]
                feedback = evaluate_camera_placement(frame.shape, detections)
                inference_ms = (time.perf_counter() - start) * 1000.0

            annotated = frame.copy()
            if show_guides:
                draw_guides(annotated)
            draw_detection_overlay(annotated, detections, classifications)
            draw_status_panel(
                annotated,
                source_label=source_label,
                frame_index=frame_index,
                actual_resolution=actual_resolution,
                detection_enabled=detection_enabled,
                show_guides=show_guides,
                confidence_threshold=config.confidence_threshold,
                detections=detections,
                classifications=classifications,
                feedback=feedback,
                inference_ms=inference_ms,
            )

            cv2.imshow(WINDOW_NAME, annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in {ord("q"), 27}:
                break
            if key == ord("g"):
                show_guides = not show_guides
            elif key == ord("d"):
                detection_enabled = not detection_enabled
            elif key == ord("s"):
                saved_path = save_snapshot(snapshot_dir, annotated)
                print(f"Saved diagnostic snapshot to {saved_path}")
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        if cap is not None:
            cap.release()
        if camera_capture is not None:
            camera_capture.close()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
