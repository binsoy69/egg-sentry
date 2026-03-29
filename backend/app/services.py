from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import SIZE_DISPLAY_MAP, SIZE_ORDER
from app.models import Alert, CountSnapshot, Device, EggCollection, EggDetection, User
from app.schemas import CollectionEntryRead, EventEggCreate, HistoryRecord


settings = get_settings()
CORRECTABLE_SIZE_ORDER = [size for size in SIZE_ORDER if size != "unknown"]
CORRECTABLE_SIZE_INDEX = {size: index for index, size in enumerate(CORRECTABLE_SIZE_ORDER)}
EVENT_SIZE_CORRECTION_MIN_SPREAD = 0.00005
EVENT_SIZE_CORRECTION_RELATIVE_SPREAD = 0.04


def app_tz() -> ZoneInfo:
    return ZoneInfo(settings.app_timezone)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def local_day_bounds(target_date: date) -> tuple[datetime, datetime]:
    tz = app_tz()
    start_local = datetime.combine(target_date, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def current_local_date() -> date:
    return utc_now().astimezone(app_tz()).date()


def localize(dt: datetime) -> datetime:
    return ensure_aware(dt).astimezone(app_tz())


def size_display(size: str | None) -> str:
    if not size:
        return "?"
    return SIZE_DISPLAY_MAP.get(size, size.upper())


def _size_correction_indices(size: str, count: int) -> list[int]:
    base_index = CORRECTABLE_SIZE_INDEX[size]
    max_index = len(CORRECTABLE_SIZE_ORDER) - 1
    if count <= len(CORRECTABLE_SIZE_ORDER):
        start = min(max(base_index - count + 1, 0), max_index - count + 1)
        return [start + offset for offset in range(count)]
    return [min(offset, max_index) for offset in range(count)]


def _has_meaningful_area_spread(event_eggs: list[EventEggCreate]) -> bool:
    areas = [
        float(egg.bbox_area_normalized)
        for egg in event_eggs
        if egg.bbox_area_normalized is not None
    ]
    if len(areas) < 2:
        return False
    spread = max(areas) - min(areas)
    threshold = max(EVENT_SIZE_CORRECTION_MIN_SPREAD, max(areas) * EVENT_SIZE_CORRECTION_RELATIVE_SPREAD)
    return spread >= threshold


def _should_redistribute_run(raw_size: str, run: list[tuple[int, EventEggCreate]]) -> bool:
    if len(run) < 2:
        return False
    if raw_size in {"small", "jumbo"}:
        return True
    return _has_meaningful_area_spread([egg for _, egg in run])


def correct_event_egg_sizes(new_eggs: list[EventEggCreate]) -> list[EventEggCreate]:
    if len(new_eggs) < 2:
        return list(new_eggs)

    corrected = list(new_eggs)
    sortable = [
        (index, egg)
        for index, egg in enumerate(new_eggs)
        if egg.size in CORRECTABLE_SIZE_INDEX and egg.bbox_area_normalized is not None
    ]
    if len(sortable) < 2:
        return corrected

    sortable.sort(
        key=lambda item: (
            float(item[1].bbox_area_normalized or 0.0),
            ensure_aware(item[1].detected_at),
            item[0],
        )
    )

    cursor = 0
    while cursor < len(sortable):
        run_end = cursor + 1
        raw_size = sortable[cursor][1].size
        while run_end < len(sortable) and sortable[run_end][1].size == raw_size:
            run_end += 1

        run = sortable[cursor:run_end]
        if _should_redistribute_run(raw_size, run):
            assigned_indices = _size_correction_indices(raw_size, len(run))
            for assigned_index, (original_index, egg) in zip(assigned_indices, run):
                corrected[original_index] = egg.model_copy(
                    update={"size": CORRECTABLE_SIZE_ORDER[assigned_index]}
                )

        cursor = run_end

    return corrected


def aggregate_event_egg_sizes(new_eggs: list[EventEggCreate]) -> dict[str, int]:
    counts = Counter(egg.size for egg in new_eggs)
    return {size: count for size, count in counts.items() if count > 0}


def derive_snapshot_size_breakdown(
    *,
    previous_snapshot: CountSnapshot | None,
    total_count: int,
    new_eggs: list[EventEggCreate],
) -> dict[str, int] | None:
    previous_total = previous_snapshot.total_count if previous_snapshot else 0
    if total_count < previous_total:
        return None

    expected_increase = max(0, total_count - previous_total)
    if previous_snapshot is None:
        if expected_increase != total_count:
            return None
        snapshot_counts = aggregate_event_egg_sizes(new_eggs[:expected_increase])
        return snapshot_counts or None

    previous_sizes = previous_snapshot.size_breakdown or {}
    if previous_total > 0 and not previous_sizes:
        return None

    current_sizes = Counter({size: int(count) for size, count in previous_sizes.items() if int(count) > 0})
    if current_sizes and sum(current_sizes.values()) != previous_total:
        return None

    if expected_increase == 0:
        return dict(current_sizes) or None

    current_sizes.update(aggregate_event_egg_sizes(new_eggs[:expected_increase]))
    if sum(current_sizes.values()) != total_count:
        return None
    return dict(current_sizes)


def status_for_device(device: Device) -> tuple[bool, str]:
    if not device.last_heartbeat:
        return False, "offline"
    heartbeat_age = utc_now() - ensure_aware(device.last_heartbeat)
    is_online = heartbeat_age <= timedelta(minutes=settings.alert_heartbeat_timeout_minutes)
    return is_online, "online" if is_online else "offline"


def _maybe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def get_device_by_identifier(db: Session, identifier: str | None) -> Device | None:
    if not identifier:
        return None
    stmt = select(Device).where(Device.device_id == identifier)
    device = db.execute(stmt).scalar_one_or_none()
    if device is not None:
        return device
    numeric = _maybe_int(identifier)
    if numeric is None:
        return None
    stmt = select(Device).where(Device.id == numeric)
    return db.execute(stmt).scalar_one_or_none()


def get_primary_device(db: Session) -> Device | None:
    stmt = select(Device).where(Device.is_active.is_(True)).order_by(Device.id.asc())
    device = db.execute(stmt).scalar_one_or_none()
    if device:
        return device
    stmt = select(Device).order_by(Device.id.asc())
    return db.execute(stmt).scalar_one_or_none()


def build_history_record(detection: EggDetection) -> HistoryRecord:
    local_dt = localize(detection.detected_at)
    display = size_display(detection.size)
    device = detection.device.device_id if detection.device else ""
    return HistoryRecord(
        id=detection.id,
        date=local_dt.strftime("%a, %b %d, %Y"),
        size=detection.size,
        size_display=display,
        detected_at=local_dt.strftime("%b %d, %Y, %I:%M %p"),
        confidence=detection.confidence,
        timestamp=local_dt.isoformat(),
        device_id=device,
        estimated_size=display,
        count=1,
        image_url=None,
    )


def ensure_event_egg_records(
    *,
    previous_snapshot: CountSnapshot | None,
    total_count: int,
    size_breakdown: dict[str, int] | None,
    new_eggs: list[EventEggCreate],
    timestamp: datetime,
) -> list[EventEggCreate]:
    previous_total = previous_snapshot.total_count if previous_snapshot else 0
    expected_increase = max(0, total_count - previous_total)
    if expected_increase <= 0:
        return list(new_eggs)

    records = list(new_eggs)
    if len(records) >= expected_increase:
        return records

    previous_sizes = previous_snapshot.size_breakdown or {} if previous_snapshot else {}
    current_sizes = size_breakdown or {}
    actual_by_size = Counter(egg.size for egg in records)
    sizes_in_order = list(dict.fromkeys([*SIZE_ORDER, *current_sizes.keys(), *previous_sizes.keys()]))

    for size in sizes_in_order:
        expected_for_size = max(0, int(current_sizes.get(size, 0)) - int(previous_sizes.get(size, 0)))
        missing_for_size = expected_for_size - actual_by_size.get(size, 0)
        while missing_for_size > 0 and len(records) < expected_increase:
            records.append(
                EventEggCreate(
                    size=size,
                    confidence=None,
                    bbox_area_normalized=None,
                    detected_at=timestamp,
                )
            )
            actual_by_size[size] += 1
            missing_for_size -= 1

    fallback_size = next(
        (
            size
            for size in sizes_in_order
            if int(current_sizes.get(size, 0)) > actual_by_size.get(size, 0)
        ),
        records[0].size if records else "unknown",
    )
    while len(records) < expected_increase:
        records.append(
            EventEggCreate(
                size=fallback_size,
                confidence=None,
                bbox_area_normalized=None,
                detected_at=timestamp,
            )
        )

    return records


def query_detections(
    db: Session,
    *,
    device: Device | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[EggDetection]:
    stmt = select(EggDetection).order_by(EggDetection.detected_at.asc())
    if device:
        stmt = stmt.where(EggDetection.device_id == device.id)
    if start:
        stmt = stmt.where(EggDetection.detected_at >= ensure_aware(start))
    if end:
        stmt = stmt.where(EggDetection.detected_at < ensure_aware(end))
    return list(db.execute(stmt).scalars().all())


def count_for_day(db: Session, device: Device, target_date: date) -> int:
    start, end = local_day_bounds(target_date)
    stmt = select(func.count(EggDetection.id)).where(
        EggDetection.device_id == device.id,
        EggDetection.detected_at >= start,
        EggDetection.detected_at < end,
    )
    return int(db.execute(stmt).scalar_one() or 0)


def latest_snapshot_for_device(db: Session, device: Device) -> CountSnapshot | None:
    stmt = (
        select(CountSnapshot)
        .where(CountSnapshot.device_id == device.id)
        .order_by(CountSnapshot.captured_at.desc(), CountSnapshot.id.desc())
    )
    return db.execute(stmt).scalars().first()


def current_count_for_device(db: Session, device: Device) -> int:
    snapshot = latest_snapshot_for_device(db, device)
    if snapshot is None:
        return 0
    return max(snapshot.total_count, 0)


def clear_runtime_data(db: Session) -> dict[str, int]:
    detection_count = db.execute(delete(EggDetection)).rowcount or 0
    snapshot_count = db.execute(delete(CountSnapshot)).rowcount or 0
    collection_count = db.execute(delete(EggCollection)).rowcount or 0
    alert_count = db.execute(delete(Alert)).rowcount or 0

    device_count = 0
    for device in db.execute(select(Device)).scalars().all():
        device.last_heartbeat = None
        db.add(device)
        device_count += 1

    return {
        "detections_cleared": int(detection_count),
        "snapshots_cleared": int(snapshot_count),
        "collections_cleared": int(collection_count),
        "alerts_cleared": int(alert_count),
        "devices_reset": device_count,
    }


def collected_count_for_day(db: Session, device: Device, target_date: date) -> int:
    start, end = local_day_bounds(target_date)
    stmt = select(func.sum(EggCollection.collected_count)).where(
        EggCollection.device_id == device.id,
        EggCollection.collected_at >= start,
        EggCollection.collected_at < end,
    )
    return int(db.execute(stmt).scalar_one() or 0)


def list_collections_for_day(db: Session, device: Device, target_date: date) -> list[EggCollection]:
    start, end = local_day_bounds(target_date)
    stmt = (
        select(EggCollection)
        .where(
            EggCollection.device_id == device.id,
            EggCollection.collected_at >= start,
            EggCollection.collected_at < end,
        )
        .order_by(EggCollection.collected_at.desc(), EggCollection.id.desc())
    )
    collections = list(db.execute(stmt).scalars().all())
    for collection in collections:
        _ = collection.device
    return collections


def build_collection_entry(collection: EggCollection) -> CollectionEntryRead:
    local_dt = localize(collection.collected_at)
    device = collection.device.device_id if collection.device else ""
    return CollectionEntryRead(
        id=collection.id,
        device_id=device,
        count=collection.collected_count,
        source="manual" if collection.source == "manual" else "automatic",
        before_count=collection.before_count,
        after_count=collection.after_count,
        collected_at=ensure_aware(collection.collected_at),
        collected_at_display=local_dt.strftime("%b %d, %Y, %I:%M %p"),
    )


def should_infer_collection(previous_count: int, new_count: int) -> bool:
    if previous_count <= new_count:
        return False
    drop = previous_count - new_count
    return drop >= settings.collection_drop_threshold or new_count == 0


def create_collection(
    db: Session,
    *,
    device: Device,
    collected_count: int,
    before_count: int,
    after_count: int,
    source: str,
    collected_at: datetime,
    user: User | None = None,
) -> EggCollection:
    collection = EggCollection(
        device_id=device.id,
        user_id=user.id if user else None,
        collected_count=collected_count,
        before_count=before_count,
        after_count=after_count,
        source=source,
        collected_at=ensure_aware(collected_at),
    )
    db.add(collection)
    db.flush()
    _ = collection.device
    return collection


def aggregate_counts_by_day(detections: list[EggDetection]) -> dict[date, int]:
    counts: dict[date, int] = defaultdict(int)
    for detection in detections:
        counts[localize(detection.detected_at).date()] += 1
    return dict(counts)


def aggregate_sizes(detections: list[EggDetection], include_unknown: bool = False) -> dict[str, int]:
    counts: dict[str, int] = {size: 0 for size in SIZE_ORDER if include_unknown or size != "unknown"}
    for detection in detections:
        if detection.size == "unknown" and not include_unknown:
            continue
        counts[detection.size] = counts.get(detection.size, 0) + 1
    return counts


def best_day_from_detections(detections: list[EggDetection]) -> tuple[date | None, int]:
    by_day = aggregate_counts_by_day(detections)
    if not by_day:
        return None, 0
    best_date, count = max(by_day.items(), key=lambda item: (item[1], item[0]))
    return best_date, count


def top_size_from_detections(detections: list[EggDetection]) -> tuple[str | None, int]:
    filtered = [d.size for d in detections if d.size != "unknown"]
    if not filtered:
        return None, 0
    counter = Counter(filtered)
    size, count = counter.most_common(1)[0]
    return size, count


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    tz = app_tz()
    start_local = datetime(year, month, 1, tzinfo=tz)
    if month == 12:
        end_local = datetime(year + 1, 1, 1, tzinfo=tz)
    else:
        end_local = datetime(year, month + 1, 1, tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def year_bounds(year: int) -> tuple[datetime, datetime]:
    tz = app_tz()
    start_local = datetime(year, 1, 1, tzinfo=tz)
    end_local = datetime(year + 1, 1, 1, tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def week_of_month_bounds(year: int, month: int, week: int) -> tuple[datetime, datetime, date, date]:
    start_month, end_month = month_bounds(year, month)
    start_date = start_month.astimezone(app_tz()).date()
    first_day = start_date + timedelta(days=(week - 1) * 7)
    month_end_date = end_month.astimezone(app_tz()).date()
    next_boundary = min(first_day + timedelta(days=7), month_end_date)
    start, _ = local_day_bounds(first_day)
    end, _ = local_day_bounds(next_boundary)
    return start, end, first_day, next_boundary - timedelta(days=1)


def daily_chart_points(detections: list[EggDetection], start_date: date, end_date: date) -> list[dict[str, int | str]]:
    counts = aggregate_counts_by_day(detections)
    points: list[dict[str, int | str]] = []
    current = start_date
    while current <= end_date:
        points.append({"date": current.isoformat(), "count": counts.get(current, 0)})
        current += timedelta(days=1)
    return points


def average_per_day(total: int, day_count: int) -> float:
    if day_count <= 0:
        return 0.0
    return round(total / day_count, 1)


def get_active_alert(db: Session, *, device_id: int | None, alert_type: str) -> Alert | None:
    stmt = (
        select(Alert)
        .where(
            Alert.type == alert_type,
            Alert.device_id == device_id,
            Alert.is_dismissed.is_(False),
        )
        .order_by(Alert.created_at.desc())
    )
    return db.execute(stmt).scalars().first()


def alert_exists_recently(db: Session, *, device_id: int | None, alert_type: str) -> bool:
    stmt = (
        select(Alert)
        .where(
            Alert.type == alert_type,
            Alert.device_id == device_id,
        )
        .order_by(Alert.created_at.desc())
    )
    latest = db.execute(stmt).scalars().first()
    if latest is None:
        return False
    cutoff = utc_now() - timedelta(minutes=settings.alert_cooldown_minutes)
    reference_time = latest.dismissed_at or latest.created_at
    return ensure_aware(reference_time) >= cutoff


def create_or_refresh_alert(
    db: Session,
    *,
    device: Device | None,
    alert_type: str,
    severity: str,
    message: str,
) -> Alert | None:
    device_fk = device.id if device else None
    active_alert = get_active_alert(db, device_id=device_fk, alert_type=alert_type)
    if active_alert is not None:
        active_alert.severity = severity
        active_alert.message = message
        db.add(active_alert)
        db.flush()
        return active_alert

    if alert_exists_recently(db, device_id=device_fk, alert_type=alert_type):
        return None

    alert = Alert(device_id=device_fk, type=alert_type, severity=severity, message=message)
    db.add(alert)
    db.flush()
    return alert


def resolve_alerts(db: Session, *, device: Device | None, alert_type: str) -> int:
    device_fk = device.id if device else None
    stmt = select(Alert).where(
        Alert.type == alert_type,
        Alert.device_id == device_fk,
        Alert.is_dismissed.is_(False),
    )
    active_alerts = list(db.execute(stmt).scalars().all())
    if not active_alerts:
        return 0

    resolved_at = utc_now()
    for alert in active_alerts:
        alert.is_dismissed = True
        alert.dismissed_at = resolved_at
        db.add(alert)
    db.flush()
    return len(active_alerts)


def evaluate_uncertain_detection_alert(db: Session, device: Device) -> None:
    cutoff = utc_now() - timedelta(hours=1)
    stmt = select(func.count(EggDetection.id)).where(
        EggDetection.device_id == device.id,
        EggDetection.detected_at >= cutoff,
        EggDetection.size == "unknown",
    )
    unknown_count = int(db.execute(stmt).scalar_one() or 0)
    if unknown_count > settings.alert_uncertain_threshold:
        create_or_refresh_alert(
            db,
            device=device,
            alert_type="uncertain_detection",
            severity="info",
            message=f"Multiple uncertain detections from {device.name} in the last hour - check camera alignment",
        )
        return

    resolve_alerts(db, device=device, alert_type="uncertain_detection")


def evaluate_device_offline_alert(db: Session, device: Device) -> None:
    is_online, _ = status_for_device(device)
    if is_online or not device.last_heartbeat:
        resolve_alerts(db, device=device, alert_type="device_offline")
        return
    minutes = int((utc_now() - ensure_aware(device.last_heartbeat)).total_seconds() // 60)
    create_or_refresh_alert(
        db,
        device=device,
        alert_type="device_offline",
        severity="warning",
        message=f"{device.name} has not sent a heartbeat in {minutes} minutes",
    )


def evaluate_missing_data_alert(db: Session, device: Device) -> None:
    local_now = utc_now().astimezone(app_tz())
    if local_now.hour < settings.alert_daytime_start_hour or local_now.hour >= settings.alert_daytime_end_hour:
        resolve_alerts(db, device=device, alert_type="missing_data")
        return
    cutoff = utc_now() - timedelta(hours=settings.alert_missing_data_hours)
    stmt = select(EggDetection.id).where(
        EggDetection.device_id == device.id,
        EggDetection.detected_at >= cutoff,
    )
    if db.execute(stmt).first() is None:
        create_or_refresh_alert(
            db,
            device=device,
            alert_type="missing_data",
            severity="warning",
            message=f"No egg detections from {device.name} in the last {settings.alert_missing_data_hours} hours",
        )
        return

    resolve_alerts(db, device=device, alert_type="missing_data")


def evaluate_low_production_alert(db: Session, device: Device) -> None:
    local_now = utc_now().astimezone(app_tz())
    if local_now.hour < settings.alert_low_production_hour:
        resolve_alerts(db, device=device, alert_type="low_production")
        return
    today = local_now.date()
    today_count = count_for_day(db, device, today)
    previous_counts = [count_for_day(db, device, today - timedelta(days=offset)) for offset in range(1, 8)]
    baseline_days = [value for value in previous_counts if value > 0]
    if not baseline_days:
        resolve_alerts(db, device=device, alert_type="low_production")
        return
    average = sum(baseline_days) / len(baseline_days)
    if today_count < average * settings.alert_low_production_threshold:
        create_or_refresh_alert(
            db,
            device=device,
            alert_type="low_production",
            severity="info",
            message=f"Today's egg count ({today_count}) is below the daily average ({average:.1f})",
        )
        return

    resolve_alerts(db, device=device, alert_type="low_production")


def evaluate_alerts(db: Session, device: Device | None = None) -> None:
    if device is not None:
        devices = [device]
    else:
        devices = list(db.execute(select(Device)).scalars().all())
    for current in devices:
        if not current.is_active:
            for alert_type in ("device_offline", "low_production", "uncertain_detection", "missing_data"):
                resolve_alerts(db, device=current, alert_type=alert_type)
            continue
        evaluate_device_offline_alert(db, current)
        evaluate_uncertain_detection_alert(db, current)
        evaluate_missing_data_alert(db, current)
        evaluate_low_production_alert(db, current)
