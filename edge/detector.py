from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Detection:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    class_id: int
    label: str
    track_id: int | None = None

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


class EggDetector:
    def __init__(self, model_path: str | Path, confidence_threshold: float = 0.5) -> None:
        from ultralytics import YOLO

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"YOLO model not found at {self.model_path}")

        self.confidence_threshold = confidence_threshold
        self.model = YOLO(str(self.model_path))

    def detect(self, frame: object, use_tracking: bool = False) -> list[Detection]:
        if use_tracking:
            results = self.model.track(
                frame,
                conf=self.confidence_threshold,
                persist=True,
                verbose=False,
            )
        else:
            results = self.model.predict(
                frame,
                conf=self.confidence_threshold,
                verbose=False,
            )

        detections: list[Detection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            names = result.names
            box_ids = getattr(boxes, "id", None)

            for index in range(len(boxes)):
                x1, y1, x2, y2 = [int(value) for value in boxes.xyxy[index].tolist()]
                confidence = float(boxes.conf[index].item())
                class_id = int(boxes.cls[index].item())
                track_id = None
                if box_ids is not None:
                    track_id = int(box_ids[index].item())

                detections.append(
                    Detection(
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                        confidence=confidence,
                        class_id=class_id,
                        label=str(names[class_id]),
                        track_id=track_id,
                    )
                )

        return detections
