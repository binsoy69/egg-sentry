from datetime import datetime, timedelta, timezone


def create_event_payload(*, timestamp: datetime | None = None, sizes: list[str] | None = None, total_count: int | None = None):
    event_time = timestamp or datetime.now(timezone.utc)
    egg_sizes = sizes or ["medium", "large"]
    breakdown = {"small": 0, "medium": 0, "large": 0, "extra-large": 0, "jumbo": 0, "unknown": 0}
    for size in egg_sizes:
        breakdown[size] = breakdown.get(size, 0) + 1
    return {
        "device_id": "cam-001",
        "timestamp": event_time.isoformat(),
        "total_count": total_count if total_count is not None else len(egg_sizes),
        "new_eggs": [
            {
                "size": size,
                "confidence": 0.91,
                "bbox_area_normalized": 0.0031,
                "detected_at": (event_time + timedelta(seconds=index)).isoformat(),
            }
            for index, size in enumerate(egg_sizes)
        ],
        "size_breakdown": breakdown,
    }
