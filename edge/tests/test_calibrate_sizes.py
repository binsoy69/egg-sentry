from pathlib import Path

from edge.calibrate_sizes import (
    DetectionMeasurement,
    classify_area,
    derive_thresholds,
    evaluate_thresholds,
)


def measurement(label: str, area: float) -> DetectionMeasurement:
    return DetectionMeasurement(
        image_path=Path(f"{label}.jpg"),
        size_label=label,
        confidence=0.9,
        normalized_area=area,
        aspect_ratio=1.4,
    )


def test_derive_thresholds_produces_ordered_boundaries() -> None:
    measurements = {
        "small": [measurement("small", 0.0018), measurement("small", 0.0019)],
        "medium": [measurement("medium", 0.0024), measurement("medium", 0.0025)],
        "large": [measurement("large", 0.0034), measurement("large", 0.0035)],
        "extra-large": [
            measurement("extra-large", 0.0046),
            measurement("extra-large", 0.0047),
        ],
        "jumbo": [measurement("jumbo", 0.0062), measurement("jumbo", 0.0064)],
    }

    thresholds, method = derive_thresholds(measurements)

    assert method == "adjacent_pair_min_error"
    assert thresholds.small_max == 0.00215
    assert thresholds.medium_max == 0.00295
    assert thresholds.large_max == 0.00405
    assert thresholds.xl_max == 0.00545


def test_evaluate_thresholds_matches_labeled_samples() -> None:
    measurements = {
        "small": [measurement("small", 0.0018), measurement("small", 0.0019)],
        "medium": [measurement("medium", 0.0024), measurement("medium", 0.0025)],
        "large": [measurement("large", 0.0034), measurement("large", 0.0035)],
        "extra-large": [
            measurement("extra-large", 0.0046),
            measurement("extra-large", 0.0047),
        ],
        "jumbo": [measurement("jumbo", 0.0062), measurement("jumbo", 0.0064)],
    }
    thresholds, _ = derive_thresholds(measurements)

    correct, total, per_class = evaluate_thresholds(measurements, thresholds)

    assert correct == total == 10
    assert per_class["small"] == (2, 2)
    assert per_class["jumbo"] == (2, 2)
    assert classify_area(0.0048, thresholds) == "extra-large"


def test_derive_thresholds_falls_back_to_monotonic_fit_when_medians_overlap() -> None:
    measurements = {
        "small": [measurement("small", 0.0010), measurement("small", 0.0011)],
        "medium": [measurement("medium", 0.0014), measurement("medium", 0.0015)],
        "large": [measurement("large", 0.0012), measurement("large", 0.0013)],
        "extra-large": [
            measurement("extra-large", 0.00135),
            measurement("extra-large", 0.00136),
        ],
        "jumbo": [measurement("jumbo", 0.0018), measurement("jumbo", 0.0019)],
    }

    thresholds, method = derive_thresholds(measurements)

    assert method == "isotonic_median_fallback"
    assert thresholds.small_max < thresholds.medium_max < thresholds.large_max < thresholds.xl_max
