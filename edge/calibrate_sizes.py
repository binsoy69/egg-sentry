from __future__ import annotations

import argparse
import statistics
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import cv2

try:
    from .config import DEFAULT_CONFIG_PATH, SizeThresholds, load_config, save_size_thresholds
    from .detector import Detection, EggDetector
except ImportError:
    from config import DEFAULT_CONFIG_PATH, SizeThresholds, load_config, save_size_thresholds
    from detector import Detection, EggDetector

SIZE_LABELS = ("small", "medium", "large", "extra-large", "jumbo")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class CalibrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class DetectionMeasurement:
    image_path: Path
    size_label: str
    confidence: float
    normalized_area: float
    aspect_ratio: float
    reason: str | None = None


@dataclass
class SizeFolderStats:
    images_total: int = 0
    images_unreadable: int = 0
    images_without_detections: int = 0
    detections_total: int = 0
    detections_used: int = 0
    detections_skipped: int = 0
    skipped_reasons: Counter[str] = field(default_factory=Counter)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run YOLO on size-labeled folders, calibrate normalized-area thresholds, "
            "and write them into the edge config."
        )
    )
    parser.add_argument(
        "dataset",
        help="Folder containing subfolders named small, medium, large, extra-large, and jumbo.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the edge config JSON file to read and update.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional YOLO model override. Defaults to the model path from config.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=None,
        help="Optional confidence override. Defaults to the confidence threshold from config.",
    )
    return parser.parse_args()


def iter_image_paths(folder: Path) -> list[Path]:
    return sorted(
        path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def validate_dataset_root(root: Path) -> list[str]:
    if not root.exists():
        raise CalibrationError(f"Dataset folder does not exist: {root}")
    if not root.is_dir():
        raise CalibrationError(f"Dataset path is not a directory: {root}")

    missing = [label for label in SIZE_LABELS if not (root / label).is_dir()]
    if missing:
        joined = ", ".join(missing)
        raise CalibrationError(
            f"Dataset is missing required size folders: {joined}. Expected folders: {', '.join(SIZE_LABELS)}"
        )

    extra_folders = sorted(
        child.name for child in root.iterdir() if child.is_dir() and child.name not in SIZE_LABELS
    )
    return extra_folders


def measure_detection(
    detection: Detection,
    frame_shape: tuple[int, int] | tuple[int, int, int],
    edge_margin_pixels: int,
    aspect_ratio_min: float,
    aspect_ratio_max: float,
) -> DetectionMeasurement:
    frame_height, frame_width = frame_shape[:2]
    box_width = max(1, detection.x2 - detection.x1)
    box_height = max(1, detection.y2 - detection.y1)
    aspect_ratio = box_height / box_width
    normalized_area = (box_width * box_height) / float(frame_width * frame_height)

    if aspect_ratio < aspect_ratio_min or aspect_ratio > aspect_ratio_max:
        return DetectionMeasurement(
            image_path=Path(),
            size_label="",
            confidence=detection.confidence,
            normalized_area=normalized_area,
            aspect_ratio=aspect_ratio,
            reason="aspect_ratio_out_of_bounds",
        )

    margin = edge_margin_pixels
    at_frame_edge = (
        detection.x1 < margin
        or detection.y1 < margin
        or detection.x2 > frame_width - margin
        or detection.y2 > frame_height - margin
    )
    if at_frame_edge:
        return DetectionMeasurement(
            image_path=Path(),
            size_label="",
            confidence=detection.confidence,
            normalized_area=normalized_area,
            aspect_ratio=aspect_ratio,
            reason="touches_frame_edge",
        )

    return DetectionMeasurement(
        image_path=Path(),
        size_label="",
        confidence=detection.confidence,
        normalized_area=normalized_area,
        aspect_ratio=aspect_ratio,
    )


def collect_measurements(
    dataset_root: Path,
    detector: EggDetector,
    edge_margin_pixels: int,
    aspect_ratio_min: float,
    aspect_ratio_max: float,
) -> tuple[dict[str, list[DetectionMeasurement]], dict[str, SizeFolderStats]]:
    measurements = {label: [] for label in SIZE_LABELS}
    stats = {label: SizeFolderStats() for label in SIZE_LABELS}

    for label in SIZE_LABELS:
        folder = dataset_root / label
        image_paths = iter_image_paths(folder)
        if not image_paths:
            raise CalibrationError(f"No supported image files found in {folder}")

        for image_path in image_paths:
            folder_stats = stats[label]
            folder_stats.images_total += 1
            frame = cv2.imread(str(image_path))
            if frame is None:
                folder_stats.images_unreadable += 1
                continue

            detections = detector.detect(frame, use_tracking=False)
            if not detections:
                folder_stats.images_without_detections += 1
                continue

            for detection in detections:
                folder_stats.detections_total += 1
                measurement = measure_detection(
                    detection=detection,
                    frame_shape=frame.shape,
                    edge_margin_pixels=edge_margin_pixels,
                    aspect_ratio_min=aspect_ratio_min,
                    aspect_ratio_max=aspect_ratio_max,
                )
                measurement = DetectionMeasurement(
                    image_path=image_path,
                    size_label=label,
                    confidence=measurement.confidence,
                    normalized_area=measurement.normalized_area,
                    aspect_ratio=measurement.aspect_ratio,
                    reason=measurement.reason,
                )
                if measurement.reason is not None:
                    folder_stats.detections_skipped += 1
                    folder_stats.skipped_reasons[measurement.reason] += 1
                    continue

                folder_stats.detections_used += 1
                measurements[label].append(measurement)

    for label in SIZE_LABELS:
        if not measurements[label]:
            raise CalibrationError(
                f"Calibration could not find any usable detections for '{label}'. "
                "The dataset needs at least one valid detection per size."
            )

    return measurements, stats


def candidate_thresholds(lower_values: list[float], upper_values: list[float]) -> list[float]:
    pooled = sorted(set(lower_values + upper_values))
    if len(pooled) == 1:
        return [pooled[0]]
    return [(left + right) / 2.0 for left, right in zip(pooled, pooled[1:])]


def choose_pair_threshold(lower_values: list[float], upper_values: list[float]) -> float:
    median_midpoint = statistics.median([statistics.median(lower_values), statistics.median(upper_values)])

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


def derive_thresholds(measurements: dict[str, list[DetectionMeasurement]]) -> tuple[SizeThresholds, str]:
    values_by_label = {
        label: sorted(measurement.normalized_area for measurement in measurements[label])
        for label in SIZE_LABELS
    }
    optimal = [
        choose_pair_threshold(values_by_label[lower], values_by_label[upper])
        for lower, upper in zip(SIZE_LABELS, SIZE_LABELS[1:])
    ]
    if is_strictly_increasing(optimal):
        return (
            SizeThresholds(
                small_max=optimal[0],
                medium_max=optimal[1],
                large_max=optimal[2],
                xl_max=optimal[3],
            ),
            "adjacent_pair_min_error",
        )

    medians = [statistics.median(values_by_label[label]) for label in SIZE_LABELS]
    weights = [len(values_by_label[label]) for label in SIZE_LABELS]
    fitted_medians = isotonic_regression(medians, weights)
    fallback = ensure_strict_thresholds(
        [(left + right) / 2.0 for left, right in zip(fitted_medians, fitted_medians[1:])]
    )
    return (
        SizeThresholds(
            small_max=fallback[0],
            medium_max=fallback[1],
            large_max=fallback[2],
            xl_max=fallback[3],
        ),
        "isotonic_median_fallback",
    )


def classify_area(normalized_area: float, thresholds: SizeThresholds) -> str:
    if normalized_area < thresholds.small_max:
        return "small"
    if normalized_area < thresholds.medium_max:
        return "medium"
    if normalized_area < thresholds.large_max:
        return "large"
    if normalized_area < thresholds.xl_max:
        return "extra-large"
    return "jumbo"


def evaluate_thresholds(
    measurements: dict[str, list[DetectionMeasurement]],
    thresholds: SizeThresholds,
) -> tuple[int, int, dict[str, tuple[int, int]]]:
    correct = 0
    total = 0
    per_class: dict[str, tuple[int, int]] = {}
    for label in SIZE_LABELS:
        class_total = len(measurements[label])
        class_correct = sum(
            classify_area(measurement.normalized_area, thresholds) == label
            for measurement in measurements[label]
        )
        per_class[label] = (class_correct, class_total)
        correct += class_correct
        total += class_total
    return correct, total, per_class


def summarize_measurements(
    measurements: dict[str, list[DetectionMeasurement]],
) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {}
    for label in SIZE_LABELS:
        areas = sorted(measurement.normalized_area for measurement in measurements[label])
        summary[label] = {
            "count": float(len(areas)),
            "min": areas[0],
            "median": statistics.median(areas),
            "max": areas[-1],
        }
    return summary


def print_report(
    dataset_root: Path,
    config_path: Path,
    model_path: Path,
    method: str,
    thresholds: SizeThresholds,
    stats: dict[str, SizeFolderStats],
    measurements: dict[str, list[DetectionMeasurement]],
    extra_folders: list[str],
) -> None:
    measurement_summary = summarize_measurements(measurements)
    correct, total, per_class = evaluate_thresholds(measurements, thresholds)

    print("Calibration completed.")
    print(f"Dataset: {dataset_root}")
    print(f"Config updated: {config_path}")
    print(f"Model: {model_path}")
    print(f"Threshold method: {method}")
    if extra_folders:
        print(f"Ignored extra folders: {', '.join(extra_folders)}")
    print("")
    print("Final calibrated thresholds:")
    print(f"  small_max  = {thresholds.small_max:.10f}")
    print(f"  medium_max = {thresholds.medium_max:.10f}")
    print(f"  large_max  = {thresholds.large_max:.10f}")
    print(f"  xl_max     = {thresholds.xl_max:.10f}")
    print("")
    print(f"Fit on usable detections: {correct}/{total} ({(correct / total) * 100:.2f}%)")
    print("")
    print("Per-size dataset summary:")
    for label in SIZE_LABELS:
        folder_stats = stats[label]
        class_correct, class_total = per_class[label]
        area_summary = measurement_summary[label]
        reasons = ", ".join(
            f"{reason}={count}" for reason, count in sorted(folder_stats.skipped_reasons.items())
        )
        if not reasons:
            reasons = "none"
        print(
            f"  {label}: images={folder_stats.images_total}, unreadable={folder_stats.images_unreadable}, "
            f"no_detections={folder_stats.images_without_detections}, detections={folder_stats.detections_total}, "
            f"used={folder_stats.detections_used}, skipped={folder_stats.detections_skipped}, "
            f"fit={class_correct}/{class_total}, area_min={area_summary['min']:.8f}, "
            f"area_median={area_summary['median']:.8f}, area_max={area_summary['max']:.8f}, "
            f"skip_reasons={reasons}"
        )


def run() -> int:
    args = parse_args()
    dataset_root = Path(args.dataset).resolve()
    config_path = Path(args.config).resolve()
    extra_folders = validate_dataset_root(dataset_root)

    config = load_config(config_path)
    model_path = Path(args.model).resolve() if args.model else Path(config.model_path).resolve()
    confidence_threshold = (
        float(args.conf) if args.conf is not None else float(config.confidence_threshold)
    )

    detector = EggDetector(model_path=model_path, confidence_threshold=confidence_threshold)
    measurements, stats = collect_measurements(
        dataset_root=dataset_root,
        detector=detector,
        edge_margin_pixels=config.edge_margin_pixels,
        aspect_ratio_min=config.aspect_ratio_min,
        aspect_ratio_max=config.aspect_ratio_max,
    )
    thresholds, method = derive_thresholds(measurements)
    save_size_thresholds(thresholds, config_path)
    print_report(
        dataset_root=dataset_root,
        config_path=config_path,
        model_path=model_path,
        method=method,
        thresholds=thresholds,
        stats=stats,
        measurements=measurements,
        extra_folders=extra_folders,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except CalibrationError as exc:
        print(f"Calibration failed: {exc}")
        raise SystemExit(1)
