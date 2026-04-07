from datetime import datetime, timezone

from app.models import CountSnapshot
from app.schemas import EventEggCreate
from app.services import correct_event_egg_sizes, correct_size_breakdown_bias, derive_snapshot_size_breakdown


def test_correct_size_breakdown_bias_redistributes_small_and_jumbo_extremes():
    corrected = correct_size_breakdown_bias({"small": 2, "jumbo": 3})

    assert corrected == {
        "small": 1,
        "medium": 1,
        "large": 1,
        "extra-large": 1,
        "jumbo": 1,
    }


def test_correct_size_breakdown_bias_preserves_mixed_breakdowns():
    corrected = correct_size_breakdown_bias({"small": 2, "medium": 1, "large": 1})

    assert corrected == {"small": 2, "medium": 1, "large": 1}


def test_correct_event_egg_sizes_redistributes_placeholder_extremes_without_area():
    detected_at = datetime.now(timezone.utc)
    corrected = correct_event_egg_sizes(
        [
            EventEggCreate(size="jumbo", confidence=None, bbox_area_normalized=None, detected_at=detected_at)
            for _ in range(4)
        ]
    )

    assert [egg.size for egg in corrected] == ["medium", "large", "extra-large", "jumbo"]


def test_derive_snapshot_size_breakdown_corrects_biased_reported_fallback():
    snapshot = derive_snapshot_size_breakdown(
        previous_snapshot=None,
        total_count=5,
        new_eggs=[],
        reported_size_breakdown={"small": 2, "jumbo": 3},
    )

    assert snapshot == {
        "small": 1,
        "medium": 1,
        "large": 1,
        "extra-large": 1,
        "jumbo": 1,
    }


def test_derive_snapshot_size_breakdown_corrects_biased_drop_report():
    previous_snapshot = CountSnapshot(
        total_count=7,
        size_breakdown={"small": 2, "medium": 1, "large": 1, "extra-large": 1, "jumbo": 2},
        captured_at=datetime.now(timezone.utc),
    )

    snapshot = derive_snapshot_size_breakdown(
        previous_snapshot=previous_snapshot,
        total_count=5,
        new_eggs=[],
        reported_size_breakdown={"small": 2, "jumbo": 3},
    )

    assert snapshot == {
        "small": 1,
        "medium": 1,
        "large": 1,
        "extra-large": 1,
        "jumbo": 1,
    }
