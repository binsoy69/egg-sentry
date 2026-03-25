from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import cv2

WINDOW_NAME = "EggSentry Webcam Preview"


@dataclass(frozen=True)
class ResolutionInfo:
    width: int
    height: int
    fps: float | None = None

    @property
    def label(self) -> str:
        if self.fps and self.fps > 0:
            return f"{self.width}x{self.height} @ {self.fps:.1f} FPS"
        return f"{self.width}x{self.height}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open a live webcam preview and show the camera's default resolution.",
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Camera index like 0 or a device path like /dev/video0.",
    )
    parser.add_argument(
        "--mirror",
        action="store_true",
        help="Mirror the preview horizontally.",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "v4l2"),
        default="auto",
        help="OpenCV capture backend. Use v4l2 on Raspberry Pi if needed.",
    )
    return parser.parse_args(argv)


def parse_source(raw_source: str) -> int | str:
    value = raw_source.strip()
    return int(value) if value.isdigit() else value


def open_capture(source: int | str, backend: str) -> cv2.VideoCapture:
    if backend == "v4l2":
        cap = cv2.VideoCapture(source, cv2.CAP_V4L2)
    else:
        cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open webcam source {source}")
    return cap


def capture_resolution_info(cap: cv2.VideoCapture, frame: object) -> ResolutionInfo:
    frame_height, frame_width = frame.shape[:2]
    raw_width = int(round(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or frame_width))
    raw_height = int(round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or frame_height))
    raw_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    width = raw_width if raw_width > 0 else frame_width
    height = raw_height if raw_height > 0 else frame_height
    fps = raw_fps if raw_fps > 0 else None
    return ResolutionInfo(width=width, height=height, fps=fps)


def draw_overlay(frame: object, *, source_label: str, resolution: ResolutionInfo) -> None:
    panel_lines = [
        f"Source: {source_label}",
        f"Default resolution: {resolution.label}",
        "Press q or ESC to quit",
    ]

    line_height = 24
    panel_width = 420
    panel_height = 18 + (line_height * len(panel_lines))
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (10 + panel_width, 10 + panel_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.58, frame, 0.42, 0, frame)
    cv2.rectangle(frame, (10, 10), (10 + panel_width, 10 + panel_height), (0, 180, 255), 2)

    for index, line in enumerate(panel_lines):
        cv2.putText(
            frame,
            line,
            (20, 38 + (index * line_height)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = parse_source(args.source)
    source_label = str(source)
    cap = open_capture(source, args.backend)

    try:
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Unable to read an initial frame from webcam source {source}")

        resolution = capture_resolution_info(cap, frame)
        print(f"Webcam source {source_label} opened at default resolution {resolution.label}")

        while True:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Unable to read frame from webcam source {source}")

            if args.mirror:
                frame = cv2.flip(frame, 1)

            annotated = frame.copy()
            draw_overlay(annotated, source_label=source_label, resolution=resolution)
            cv2.imshow(WINDOW_NAME, annotated)

            key = cv2.waitKey(1) & 0xFF
            if key in {ord("q"), 27}:
                break
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
