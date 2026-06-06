import json

import pytest

from calibrated_egg_programs.calibration_core import (
    CalibrationError,
    DEFAULT_LABEL_NAMES,
    QualityFilters,
    build_calibration,
    classify_area,
    calibration_from_dict,
    calibration_to_dict,
    load_calibration,
    measure_detections,
    save_calibration,
    valid_detection_measurements,
)
from calibrated_egg_programs.detector import Detection


def test_derive_six_label_thresholds_sorts_by_measured_area() -> None:
    samples = {
        "jumbo": [0.0080, 0.0082],
        "xl": [0.0067, 0.0068],
        "large": [0.0051, 0.0052],
        "medium": [0.0035, 0.0036],
        "small": [0.0024, 0.0025],
        "peewee": [0.0008, 0.0009],
    }

    calibration = build_calibration(
        samples,
        labels=DEFAULT_LABEL_NAMES,
        quality_filters=QualityFilters(),
        min_samples=2,
        created_at="2026-04-26T00:00:00+00:00",
    )

    assert calibration.labels_ordered_by_area == (
        "peewee",
        "small",
        "medium",
        "large",
        "xl",
        "jumbo",
    )
    assert len(calibration.threshold_values) == 5
    assert all(
        left < right
        for left, right in zip(calibration.threshold_values, calibration.threshold_values[1:])
    )
    assert calibration.sample_summary["peewee"].count == 2


def test_classification_boundaries_roll_into_next_calibrated_band() -> None:
    calibration = build_calibration(
        {
            "jumbo": [0.0080, 0.0082],
            "xl": [0.0067, 0.0068],
            "large": [0.0051, 0.0052],
            "medium": [0.0035, 0.0036],
            "small": [0.0024, 0.0025],
            "peewee": [0.0008, 0.0009],
        },
        labels=DEFAULT_LABEL_NAMES,
        min_samples=2,
    )

    first_threshold = calibration.threshold_values[0]

    assert classify_area(first_threshold - 0.000001, calibration).label_id == "peewee"
    assert classify_area(first_threshold, calibration).label_id == "small"
    assert classify_area(0.00515, calibration).label_id == "large"


def test_label_can_be_renamed_by_editing_label_mapping_only() -> None:
    calibration = build_calibration(
        {
            "jumbo": [0.0080],
            "xl": [0.0067],
            "large": [0.0051],
            "medium": [0.0035],
            "small": [0.0024],
            "peewee": [0.0008],
        },
        labels=DEFAULT_LABEL_NAMES,
    )
    payload = json.loads(json.dumps(calibration_to_dict(calibration)))
    payload["labels"]["peewee"] = "custom-size"
    renamed = calibration_from_dict(payload)

    result = classify_area(0.0008, renamed)

    assert result.label_id == "peewee"
    assert result.label == "custom-size"


def test_calibration_json_round_trip(tmp_path) -> None:
    calibration = build_calibration(
        {
            "jumbo": [0.0080],
            "xl": [0.0067],
            "large": [0.0051],
            "medium": [0.0035],
            "small": [0.0024],
            "peewee": [0.0008],
        },
        labels=DEFAULT_LABEL_NAMES,
        quality_filters=QualityFilters(edge_margin_pixels=12),
        created_at="2026-04-26T00:00:00+00:00",
    )
    path = tmp_path / "calibration.json"

    save_calibration(calibration, path)
    loaded = load_calibration(path)

    assert loaded.labels == calibration.labels
    assert loaded.labels_ordered_by_area == calibration.labels_ordered_by_area
    assert loaded.threshold_values == calibration.threshold_values
    assert loaded.quality_filters.edge_margin_pixels == 12
    assert loaded.sample_summary["jumbo"].median == 0.0080


def test_invalid_detections_are_excluded_from_calibration_samples() -> None:
    detections = [
        Detection(100, 100, 160, 160, confidence=0.9, class_id=0, label="egg"),
        Detection(5, 100, 65, 160, confidence=0.9, class_id=0, label="egg"),
        Detection(200, 100, 210, 700, confidence=0.9, class_id=0, label="egg"),
    ]
    filters = QualityFilters(edge_margin_pixels=10, aspect_ratio_min=0.5, aspect_ratio_max=2.0)

    all_measurements = measure_detections(detections, (1000, 1000, 3), filters, label_id="small")
    valid_measurements = valid_detection_measurements(
        detections,
        (1000, 1000, 3),
        filters,
        label_id="small",
    )

    assert len(all_measurements) == 3
    assert [measurement.reason for measurement in all_measurements] == [
        None,
        "touches_frame_edge",
        "aspect_ratio_out_of_bounds",
    ]
    assert len(valid_measurements) == 1
    assert valid_measurements[0].label_id == "small"


def test_build_calibration_requires_minimum_samples() -> None:
    samples = {
        "jumbo": [0.0080],
        "xl": [0.0067],
        "large": [0.0051],
        "medium": [0.0035],
        "small": [0.0024],
        "peewee": [],
    }

    with pytest.raises(CalibrationError):
        build_calibration(samples, labels=DEFAULT_LABEL_NAMES, min_samples=1)
