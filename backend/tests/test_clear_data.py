from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models import Alert, CountSnapshot, Device, EggDetection, User


def test_clear_data_requires_current_password(client, auth_headers, db_session) -> None:
    response = client.post(
        "/api/auth/clear-data",
        json={"current_password": "wrong-password"},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect"


def test_clear_data_resets_runtime_data_but_preserves_accounts_and_devices(
    client,
    auth_headers,
    db_session,
) -> None:
    device = db_session.execute(select(Device).where(Device.device_id == "cam-001")).scalar_one()
    user_count_before = db_session.execute(select(func.count(User.id))).scalar_one()
    device_count_before = db_session.execute(select(func.count(Device.id))).scalar_one()

    device.last_heartbeat = datetime.now(timezone.utc)
    db_session.add(device)
    db_session.add(
        CountSnapshot(
            device_id=device.id,
            total_count=4,
            size_breakdown={"large": 4},
            captured_at=datetime.now(timezone.utc),
        )
    )
    db_session.add(
        EggDetection(
            device_id=device.id,
            size="large",
            confidence=0.94,
            bbox_area_normalized=0.004,
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

    response = client.post(
        "/api/auth/clear-data",
        json={"current_password": "admin123"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["detections_cleared"] == 1
    assert body["snapshots_cleared"] == 1
    assert body["alerts_cleared"] == 1
    assert body["devices_reset"] == device_count_before

    db_session.expire_all()
    device = db_session.execute(select(Device).where(Device.device_id == "cam-001")).scalar_one()
    assert db_session.execute(select(func.count(User.id))).scalar_one() == user_count_before
    assert db_session.execute(select(func.count(Device.id))).scalar_one() == device_count_before
    assert db_session.execute(select(func.count(EggDetection.id))).scalar_one() == 0
    assert db_session.execute(select(func.count(CountSnapshot.id))).scalar_one() == 0
    assert db_session.execute(select(func.count(Alert.id))).scalar_one() == 0
    assert device.last_heartbeat is None
