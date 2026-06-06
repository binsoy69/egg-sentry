from __future__ import annotations

import bisect
import json
import statistics
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CALIBRATION_VERSION = 1
DEFAULT_LABEL_IDS = (
    "jumbo",
    "xl",
    "large",
    "medium",
    "small",
    "peewee",
)
DEFAULT_LABEL_NAMES = {label_id: label_id for label_id in DEFAULT_LABEL_IDS}
UNKNOWN_LABEL_ID = "unknown"


class CalibrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class QualityFilters:
    edge_margin_pixels: int = 10
    aspect_ratio_min: float = 0.5
    aspect_ratio_max: float = 2.0


@dataclass(frozen=True)
class DetectionMeasurement:
    bbox: tuple[int, int, int, int]
    normalized_area: float
    aspect_ratio: float
    confidence: float | None = None
    label_id: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class AreaSummary:
    count: int
    min: float
    median: float
    max: float


@dataclass(frozen=True)
class SizeClassification:
    label_id: str
    label: str
    normalized_area: float
    aspect_ratio: float | None = None
    reason: str | None = None


@dataclass(frozen=True)
class SizeCalibration:
    labels: dict[str, str]
    labels_ordered_by_area: tuple[str, ...]
    threshold_values: tuple[float, ...]
    quality_filters: QualityFilters
    sample_summary: dict[str, AreaSummary]
    created_at: str
    threshold_method: str
    version: int = CALIBRATION_VERSION


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def measure_bbox(
    bbox: tuple[int, int, int, int],
    frame_shape: tuple[int, int] | tuple[int, int, int],
    filters: QualityFilters,
    *,
    confidence: float | None = None,
    label_id: str | None = None,
) -> DetectionMeasurement:
    frame_height, frame_width = frame_shape[:2]
    x1, y1, x2, y2 = bbox
    box_width = max(1, x2 - x1)
    box_height = max(1, y2 - y1)
    aspect_ratio = box_height / box_width
    normalized_area = (box_width * box_height) / float(frame_width * frame_height)

    if aspect_ratio < filters.aspect_ratio_min or aspect_ratio > filters.aspect_ratio_max:
        return DetectionMeasurement(
            bbox=bbox,
            normalized_area=normalized_area,
            aspect_ratio=aspect_ratio,
            confidence=confidence,
            label_id=label_id,
            reason="aspect_ratio_out_of_bounds",
        )

    margin = filters.edge_margin_pixels
    at_frame_edge = (
        x1 < margin
        or y1 < margin
        or x2 > frame_width - margin
        or y2 > frame_height - margin
    )
    if at_frame_edge:
        return DetectionMeasurement(
            bbox=bbox,
            normalized_area=normalized_area,
            aspect_ratio=aspect_ratio,
            confidence=confidence,
            label_id=label_id,
            reason="touches_frame_edge",
        )

    return DetectionMeasurement(
        bbox=bbox,
        normalized_area=normalized_area,
        aspect_ratio=aspect_ratio,
        confidence=confidence,
        label_id=label_id,
    )


def measure_detection(
    detection: Any,
    frame_shape: tuple[int, int] | tuple[int, int, int],
    filters: QualityFilters,
    *,
    label_id: str | None = None,
) -> DetectionMeasurement:
    bbox = tuple(detection.bbox)
    return measure_bbox(
        (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])),
        frame_shape,
        filters,
        confidence=getattr(detection, "confidence", None),
        label_id=label_id,
    )


def measure_detections(
    detections: list[Any],
    frame_shape: tuple[int, int] | tuple[int, int, int],
    filters: QualityFilters,
    *,
    label_id: str | None = None,
) -> list[DetectionMeasurement]:
    return [
        measure_detection(detection, frame_shape, filters, label_id=label_id)
        for detection in detections
    ]


def valid_detection_measurements(
    detections: list[Any],
    frame_shape: tuple[int, int] | tuple[int, int, int],
    filters: QualityFilters,
    *,
    label_id: str | None = None,
) -> list[DetectionMeasurement]:
    return [
        measurement
        for measurement in measure_detections(detections, frame_shape, filters, label_id=label_id)
        if measurement.reason is None
    ]


def candidate_thresholds(lower_values: list[float], upper_values: list[float]) -> list[float]:
    pooled = sorted(set(lower_values + upper_values))
    if len(pooled) == 1:
        return [pooled[0]]
    return [(left + right) / 2.0 for left, right in zip(pooled, pooled[1:])]


def choose_pair_threshold(lower_values: list[float], upper_values: list[float]) -> float:
    median_midpoint = statistics.median(
        [statistics.median(lower_values), statistics.median(upper_values)]
    )

    def score(threshold: float) -> tuple[int, float]:
        lower_errors = sum(value >= threshold for value in lower_values)
        upper_errors = sum(value < threshold for value in upper_values)
        return lower_errors + upper_errors, abs(threshold - median_midpoint)

    return min(candidate_thresholds(lower_values, upper_values), key=score)


def is_strictly_increasing(values: list[float]) -> bool:
    return all(left < right for left, right in zip(values, values[1:]))


def isotonic_regression(values: list[float], weights: list[int]) -> list[float]:
    blocks: list[dict[str, float | int]] = []
    for index, (value, weight) in enumerate(zip(values, weights)):
        blocks.append(
            {
                "start": index,
                "end": index,
                "weight": float(weight),
                "value": float(value),
            }
        )
        while len(blocks) >= 2 and float(blocks[-2]["value"]) > float(blocks[-1]["value"]):
            right = blocks.pop()
            left = blocks.pop()
            merged_weight = float(left["weight"]) + float(right["weight"])
            merged_value = (
                (float(left["value"]) * float(left["weight"]))
                + (float(right["value"]) * float(right["weight"]))
            ) / merged_weight
            blocks.append(
                {
                    "start": int(left["start"]),
                    "end": int(right["end"]),
                    "weight": merged_weight,
                    "value": merged_value,
                }
            )

    fitted = [0.0] * len(values)
    for block in blocks:
        for index in range(int(block["start"]), int(block["end"]) + 1):
            fitted[index] = float(block["value"])
    return fitted


def ensure_strict_thresholds(values: list[float]) -> list[float]:
    adjusted: list[float] = []
    for value in values:
        if not adjusted:
            adjusted.append(float(value))
            continue

        minimum_step = max(abs(adjusted[-1]) * 1e-6, 1e-7)
        adjusted.append(max(float(value), adjusted[-1] + minimum_step))
    return adjusted


def _label_ids_from_names(labels: dict[str, str] | None) -> tuple[str, ...]:
    if labels is None:
        return DEFAULT_LABEL_IDS
    return tuple(labels.keys())


def _coerce_samples(
    samples_by_label: dict[str, list[float]],
    label_ids: tuple[str, ...],
) -> dict[str, list[float]]:
    coerced: dict[str, list[float]] = {}
    for label_id in label_ids:
        values = [float(value) for value in samples_by_label.get(label_id, [])]
        coerced[label_id] = sorted(values)
    return coerced


def _missing_sample_labels(
    values_by_label: dict[str, list[float]],
    min_samples: int,
) -> list[str]:
    return [
        label_id
        for label_id, values in values_by_label.items()
        if len(values) < min_samples
    ]


def _area_summary(values: list[float]) -> AreaSummary:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise CalibrationError("Cannot summarize an empty sample list")
    return AreaSummary(
        count=len(ordered),
        min=ordered[0],
        median=float(statistics.median(ordered)),
        max=ordered[-1],
    )


def derive_thresholds(
    samples_by_label: dict[str, list[float]],
    *,
    labels: dict[str, str] | None = None,
    min_samples: int = 1,
) -> tuple[tuple[str, ...], tuple[float, ...], str]:
    if min_samples < 1:
        raise ValueError("min_samples must be at least 1")

    label_ids = _label_ids_from_names(labels)
    values_by_label = _coerce_samples(samples_by_label, label_ids)
    missing = _missing_sample_labels(values_by_label, min_samples)
    if missing:
        joined = ", ".join(missing)
        raise CalibrationError(f"Not enough calibration samples for: {joined}")

    label_position = {label_id: index for index, label_id in enumerate(label_ids)}
    labels_ordered_by_area = tuple(
        sorted(
            label_ids,
            key=lambda label_id: (
                statistics.median(values_by_label[label_id]),
                label_position[label_id],
            ),
        )
    )

    optimal = [
        choose_pair_threshold(values_by_label[lower], values_by_label[upper])
        for lower, upper in zip(labels_ordered_by_area, labels_ordered_by_area[1:])
    ]
    if is_strictly_increasing(optimal):
        return labels_ordered_by_area, tuple(float(value) for value in optimal), "adjacent_pair_min_error"

    medians = [statistics.median(values_by_label[label_id]) for label_id in labels_ordered_by_area]
    weights = [len(values_by_label[label_id]) for label_id in labels_ordered_by_area]
    fitted_medians = isotonic_regression(medians, weights)
    fallback = ensure_strict_thresholds(
        [(left + right) / 2.0 for left, right in zip(fitted_medians, fitted_medians[1:])]
    )
    return labels_ordered_by_area, tuple(float(value) for value in fallback), "isotonic_median_fallback"


def build_calibration(
    samples_by_label: dict[str, list[float]],
    *,
    labels: dict[str, str] | None = None,
    quality_filters: QualityFilters | None = None,
    min_samples: int = 1,
    created_at: str | None = None,
) -> SizeCalibration:
    label_names = dict(labels or DEFAULT_LABEL_NAMES)
    values_by_label = _coerce_samples(samples_by_label, tuple(label_names.keys()))
    labels_ordered_by_area, threshold_values, method = derive_thresholds(
        values_by_label,
        labels=label_names,
        min_samples=min_samples,
    )
    return SizeCalibration(
        labels=label_names,
        labels_ordered_by_area=labels_ordered_by_area,
        threshold_values=threshold_values,
        quality_filters=quality_filters or QualityFilters(),
        sample_summary={
            label_id: _area_summary(values)
            for label_id, values in values_by_label.items()
        },
        created_at=created_at or utc_timestamp(),
        threshold_method=method,
    )


def classify_area(normalized_area: float, calibration: SizeCalibration) -> SizeClassification:
    index = bisect.bisect_right(calibration.threshold_values, float(normalized_area))
    index = min(index, len(calibration.labels_ordered_by_area) - 1)
    label_id = calibration.labels_ordered_by_area[index]
    return SizeClassification(
        label_id=label_id,
        label=calibration.labels.get(label_id, label_id),
        normalized_area=float(normalized_area),
    )


def classify_bbox(
    bbox: tuple[int, int, int, int],
    frame_shape: tuple[int, int] | tuple[int, int, int],
    calibration: SizeCalibration,
    *,
    confidence: float | None = None,
) -> SizeClassification:
    measurement = measure_bbox(
        bbox,
        frame_shape,
        calibration.quality_filters,
        confidence=confidence,
    )
    if measurement.reason is not None:
        return SizeClassification(
            label_id=UNKNOWN_LABEL_ID,
            label=UNKNOWN_LABEL_ID,
            normalized_area=measurement.normalized_area,
            aspect_ratio=measurement.aspect_ratio,
            reason=measurement.reason,
        )

    classification = classify_area(measurement.normalized_area, calibration)
    return SizeClassification(
        label_id=classification.label_id,
        label=classification.label,
        normalized_area=classification.normalized_area,
        aspect_ratio=measurement.aspect_ratio,
    )


def count_classifications(
    classifications: list[SizeClassification],
    calibration: SizeCalibration,
) -> dict[str, int]:
    counts = Counter(classification.label for classification in classifications)
    ordered_labels = [
        calibration.labels.get(label_id, label_id)
        for label_id in reversed(calibration.labels_ordered_by_area)
    ]
    ordered_labels.append(UNKNOWN_LABEL_ID)
    return {
        label: int(counts[label])
        for label in ordered_labels
        if counts.get(label, 0) > 0
    }


def calibration_to_dict(calibration: SizeCalibration) -> dict[str, Any]:
    thresholds = []
    ordered = calibration.labels_ordered_by_area
    for index, value in enumerate(calibration.threshold_values):
        thresholds.append(
            {
                "max_normalized_area": float(value),
                "below_label_id": ordered[index],
                "above_label_id": ordered[index + 1],
            }
        )

    return {
        "version": calibration.version,
        "created_at": calibration.created_at,
        "labels": dict(calibration.labels),
        "labels_ordered_by_area": list(calibration.labels_ordered_by_area),
        "threshold_method": calibration.threshold_method,
        "threshold_values": [float(value) for value in calibration.threshold_values],
        "thresholds": thresholds,
        "quality_filters": asdict(calibration.quality_filters),
        "sample_summary": {
            label_id: asdict(summary)
            for label_id, summary in calibration.sample_summary.items()
        },
    }


def calibration_from_dict(data: dict[str, Any]) -> SizeCalibration:
    version = int(data.get("version", CALIBRATION_VERSION))
    if version != CALIBRATION_VERSION:
        raise CalibrationError(
            f"Unsupported calibration version {version}; expected {CALIBRATION_VERSION}"
        )

    raw_labels = data.get("labels", DEFAULT_LABEL_NAMES)
    if isinstance(raw_labels, list):
        labels = {str(label_id): str(label_id) for label_id in raw_labels}
    elif isinstance(raw_labels, dict):
        labels = {str(label_id): str(label_name) for label_id, label_name in raw_labels.items()}
    else:
        raise CalibrationError("Calibration labels must be an object or list")

    labels_ordered_by_area = tuple(str(label_id) for label_id in data["labels_ordered_by_area"])
    if not labels_ordered_by_area:
        raise CalibrationError("Calibration must include labels_ordered_by_area")

    if "threshold_values" in data:
        threshold_values = tuple(float(value) for value in data["threshold_values"])
    else:
        threshold_values = tuple(
            float(item["max_normalized_area"]) for item in data.get("thresholds", [])
        )
    if len(threshold_values) != len(labels_ordered_by_area) - 1:
        raise CalibrationError("Calibration threshold count does not match label count")
    if not is_strictly_increasing(list(threshold_values)):
        raise CalibrationError("Calibration thresholds must be strictly increasing")

    raw_filters = data.get("quality_filters", {})
    filters = QualityFilters(
        edge_margin_pixels=int(raw_filters.get("edge_margin_pixels", 10)),
        aspect_ratio_min=float(raw_filters.get("aspect_ratio_min", 0.5)),
        aspect_ratio_max=float(raw_filters.get("aspect_ratio_max", 2.0)),
    )

    raw_summary = data.get("sample_summary", {})
    sample_summary = {
        str(label_id): AreaSummary(
            count=int(summary["count"]),
            min=float(summary["min"]),
            median=float(summary["median"]),
            max=float(summary["max"]),
        )
        for label_id, summary in raw_summary.items()
    }

    return SizeCalibration(
        labels=labels,
        labels_ordered_by_area=labels_ordered_by_area,
        threshold_values=threshold_values,
        quality_filters=filters,
        sample_summary=sample_summary,
        created_at=str(data.get("created_at", "")),
        threshold_method=str(data.get("threshold_method", "unknown")),
        version=version,
    )


def save_calibration(calibration: SizeCalibration, path: str | Path) -> Path:
    calibration_path = Path(path).resolve()
    calibration_path.parent.mkdir(parents=True, exist_ok=True)
    with calibration_path.open("w", encoding="utf-8") as handle:
        json.dump(calibration_to_dict(calibration), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return calibration_path


def load_calibration(path: str | Path) -> SizeCalibration:
    calibration_path = Path(path).resolve()
    with calibration_path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise CalibrationError("Calibration file must contain a JSON object")
    return calibration_from_dict(data)
