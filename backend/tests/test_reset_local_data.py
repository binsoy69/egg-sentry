from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models import Alert, CountSnapshot, Device, EggDetection, User
from app.services import clear_runtime_data


def test_clear_runtime_data_preserves_accounts_and_devices(db_session) -> None:
    device = db_session.execute(select(Device).where(Device.device_id == "cam-001")).scalar_one()
    user_count_before = db_session.execute(select(func.count(User.id))).scalar_one()
    device_count_before = db_session.execute(select(func.count(Device.id))).scalar_one()

    device.last_heartbeat = datetime.now(timezone.utc)
    db_session.add(device)
    db_session.add(
        CountSnapshot(
            device_id=device.id,
            total_count=3,
            size_breakdown={"medium": 3},
            captured_at=datetime.now(timezone.utc),
        )
    )
    db_session.add(
        EggDetection(
            device_id=device.id,
            size="medium",
            confidence=0.92,
            bbox_area_normalized=0.0031,
            detected_at=datetime.now(timezone.utc),
        )
    )
    db_session.add(
        Alert(
            device_id=device.id,
            type="device_offline",
            severity="warning",
            message="Test alert",
        )
    )
    db_session.commit()

    result = clear_runtime_data(db_session)
    db_session.commit()
    db_session.refresh(device)

    assert result["detections_cleared"] == 1
    assert result["snapshots_cleared"] == 1
    assert result["alerts_cleared"] == 1
    assert result["devices_reset"] == device_count_before
    assert db_session.execute(select(func.count(User.id))).scalar_one() == user_count_before
    assert db_session.execute(select(func.count(Device.id))).scalar_one() == device_count_before
    assert db_session.execute(select(func.count(EggDetection.id))).scalar_one() == 0
    assert db_session.execute(select(func.count(CountSnapshot.id))).scalar_one() == 0
    assert db_session.execute(select(func.count(Alert.id))).scalar_one() == 0
    assert device.last_heartbeat is None
