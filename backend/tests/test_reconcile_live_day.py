from datetime import timedelta

from app.models import CountSnapshot, Device, EggDetection
from app.services import (
    count_for_day,
    current_local_date,
    local_day_bounds,
    reconcile_day_detections_to_target,
)


def test_reconcile_day_detections_to_target_removes_excess_today_rows(db_session):
    device = db_session.query(Device).filter(Device.device_id == "cam-001").one()
    today = current_local_date()
    start, _ = local_day_bounds(today)
    detection_time = start + timedelta(hours=9)

    db_session.add_all(
        [
            EggDetection(
                device_id=device.id,
                size="large",
                confidence=0.91,
                bbox_area_normalized=0.0031,
                detected_at=detection_time + timedelta(seconds=index),
            )
            for index in range(15)
        ]
    )
    db_session.add(
        CountSnapshot(
            device_id=device.id,
            total_count=11,
            size_breakdown={"large": 11},
            captured_at=detection_time + timedelta(minutes=5),
        )
    )
    db_session.commit()

    preview = reconcile_day_detections_to_target(
        db_session,
        device=device,
        target_date=today,
        target_total=11,
        dry_run=True,
    )
    assert preview == {"actual_total": 15, "target_total": 11, "removed": 4}
    assert count_for_day(db_session, device, today) == 15

    applied = reconcile_day_detections_to_target(
        db_session,
        device=device,
        target_date=today,
        target_total=11,
        dry_run=False,
    )
    db_session.commit()

    assert applied == {"actual_total": 15, "target_total": 11, "removed": 4}
    assert count_for_day(db_session, device, today) == 11
