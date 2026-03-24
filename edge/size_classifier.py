from __future__ import annotations

from dataclasses import dataclass

try:
    from .config import SizeThresholds
except ImportError:
    from config import SizeThresholds

SIZE_ORDER = ("small", "medium", "large", "extra-large", "jumbo", "unknown")


@dataclass(frozen=True)
class SizeClassification:
    size: str
    normalized_area: float
    aspect_ratio: float
    reason: str | None = None


class SizeClassifier:
    def __init__(
        self,
        thresholds: SizeThresholds,
        edge_margin_pixels: int = 10,
        aspect_ratio_min: float = 0.5,
        aspect_ratio_max: float = 2.0,
    ) -> None:
        self.thresholds = thresholds
        self.edge_margin_pixels = edge_margin_pixels
        self.aspect_ratio_min = aspect_ratio_min
        self.aspect_ratio_max = aspect_ratio_max

    def classify(
        self,
        bbox: tuple[int, int, int, int],
        frame_shape: tuple[int, int] | tuple[int, int, int],
    ) -> SizeClassification:
        frame_height, frame_width = frame_shape[:2]
        x1, y1, x2, y2 = bbox

        box_width = max(1, x2 - x1)
        box_height = max(1, y2 - y1)
        aspect_ratio = box_height / box_width
        normalized_area = (box_width * box_height) / float(frame_width * frame_height)

        if aspect_ratio < self.aspect_ratio_min or aspect_ratio > self.aspect_ratio_max:
            return SizeClassification(
                size="unknown",
                normalized_area=normalized_area,
                aspect_ratio=aspect_ratio,
                reason="aspect_ratio_out_of_bounds",
            )

        margin = self.edge_margin_pixels
        at_frame_edge = (
            x1 < margin
            or y1 < margin
            or x2 > frame_width - margin
            or y2 > frame_height - margin
        )
        if at_frame_edge:
            return SizeClassification(
                size="unknown",
                normalized_area=normalized_area,
                aspect_ratio=aspect_ratio,
                reason="touches_frame_edge",
            )

        if normalized_area < self.thresholds.small_max:
            size = "small"
        elif normalized_area < self.thresholds.medium_max:
            size = "medium"
        elif normalized_area < self.thresholds.large_max:
            size = "large"
        elif normalized_area < self.thresholds.xl_max:
            size = "extra-large"
        else:
            size = "jumbo"

        return SizeClassification(
            size=size,
            normalized_area=normalized_area,
            aspect_ratio=aspect_ratio,
        )


def count_sizes(classifications: list[SizeClassification]) -> dict[str, int]:
    counts = {size: 0 for size in SIZE_ORDER}
    for classification in classifications:
        counts[classification.size] = counts.get(classification.size, 0) + 1

    return {size: count for size, count in counts.items() if count > 0}

