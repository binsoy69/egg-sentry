from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any

try:
    from .size_classifier import SIZE_ORDER
except ImportError:
    from size_classifier import SIZE_ORDER


@dataclass(frozen=True)
class CaptureSnapshot:
    total_count: int
    size_counts: dict[str, int]
    detections: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class StabilizedSnapshot:
    total_count: int
    size_counts: dict[str, int]
    history_size: int
    latest_snapshot: CaptureSnapshot


def rolling_mode(values: list[int]) -> int:
    if not values:
        return 0

    counts = Counter(values)
    max_frequency = max(counts.values())
    candidates = {value for value, frequency in counts.items() if frequency == max_frequency}

    for value in reversed(values):
        if value in candidates:
            return value

    return values[-1]


class RollingStabilizer:
    def __init__(self, window_size: int = 3) -> None:
        if window_size < 1:
            raise ValueError("window_size must be at least 1")

        self.window_size = window_size
        self.history: deque[CaptureSnapshot] = deque(maxlen=window_size)

    def update(self, snapshot: CaptureSnapshot) -> StabilizedSnapshot:
        self.history.append(snapshot)
        size_counts = self._stabilize_size_counts()
        total_count = rolling_mode([item.total_count for item in self.history])
        return StabilizedSnapshot(
            total_count=total_count,
            size_counts=size_counts,
            history_size=len(self.history),
            latest_snapshot=snapshot,
        )

    def _stabilize_size_counts(self) -> dict[str, int]:
        stabilized: dict[str, int] = {}
        for size in SIZE_ORDER:
            values = [snapshot.size_counts.get(size, 0) for snapshot in self.history]
            value = rolling_mode(values)
            if value > 0:
                stabilized[size] = value
        return stabilized

