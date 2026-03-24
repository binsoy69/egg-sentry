from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import cv2


@dataclass(frozen=True)
class CapturedFrame:
    frame: object
    frame_index: int | None = None
    timestamp_seconds: float | None = None


def resolve_source(source: str) -> int | Path:
    if source.isdigit():
        return int(source)

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Video source not found: {source}")
    return path


class CameraCapture:
    def __init__(self, source: int, warmup_seconds: float) -> None:
        self.source = source
        self.warmup_seconds = warmup_seconds
        self.capture_count = 0

    def capture_frame(self) -> CapturedFrame:
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            raise RuntimeError(f"Unable to open camera source {self.source}")

        try:
            time.sleep(self.warmup_seconds)

            # Discard the first frame so auto-exposure can settle before use.
            cap.read()
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Unable to read frame from camera source {self.source}")

            self.capture_count += 1
            return CapturedFrame(frame=frame, frame_index=self.capture_count)
        finally:
            cap.release()

    def close(self) -> None:
        return None


class VideoCaptureSampler:
    def __init__(self, source: Path, interval_seconds: int, loop: bool = True) -> None:
        self.source = Path(source)
        self.interval_seconds = interval_seconds
        self.loop = loop
        self.cap = cv2.VideoCapture(str(self.source))
        if not self.cap.isOpened():
            raise RuntimeError(f"Unable to open video source {self.source}")

        raw_fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0)
        self.fps = raw_fps if raw_fps > 0 else 30.0
        self.frame_step = max(1, int(round(self.fps * self.interval_seconds)))
        self.next_frame_index = 0

    def capture_frame(self) -> CapturedFrame:
        while True:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.next_frame_index)
            ok, frame = self.cap.read()
            if ok:
                frame_index = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                timestamp_seconds = frame_index / self.fps if self.fps else None
                self.next_frame_index = frame_index + self.frame_step
                return CapturedFrame(
                    frame=frame,
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                )

            if not self.loop:
                raise StopIteration("Reached the end of the video source")

            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.next_frame_index = 0

    def close(self) -> None:
        self.cap.release()

