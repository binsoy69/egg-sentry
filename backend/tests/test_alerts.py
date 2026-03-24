from datetime import datetime, time, timedelta, timezone

import app.services as services
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import Device, EggDetection
from tests.helpers import create_event_payload


def _local_to_utc(local_date, hour: int) -> datetime:
    return datetime.combine(local_date, time(hour=hour), tzinfo=services.app_tz()).astimezone(timezone.utc)


def test_alerts_list_and_dismiss(client: TestClient, auth_headers: dict, db_session, monkeypatch):
    fixed_now = datetime(2026, 3, 24, 18, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(services, "utc_now", lambda: fixed_now)

    device = db_session.execute(select(Device).where(Device.device_id == "cam-001")).scalar_one()
    device.last_heartbeat = fixed_now - timedelta(minutes=10)
    db_session.add(device)
    db_session.commit()

    response = client.get("/api/alerts", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["alerts"][0]["type"] == "device_offline"

    dismiss_response = client.put(f"/api/alerts/{body['alerts'][0]['id']}/dismiss", headers=auth_headers)
    assert dismiss_response.status_code == 200
    assert dismiss_response.json()["dismissed"] is True


def test_device_offline_alert_dedupes_and_clears(
    client: TestClient,
    auth_headers: dict,
    device_headers: dict,
    db_session,
    monkeypatch,
):
    fixed_now = datetime(2026, 3, 24, 18, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(services, "utc_now", lambda: fixed_now)

    device = db_session.execute(select(Device).where(Device.device_id == "cam-001")).scalar_one()
    device.last_heartbeat = fixed_now - timedelta(minutes=10)
    db_session.add(device)
    db_session.commit()

    first_response = client.get("/api/alerts", headers=auth_headers)
    second_response = client.get("/api/alerts", headers=auth_headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["total"] == 1
    assert second_response.json()["total"] == 1

    heartbeat_response = client.post(
        "/api/devices/heartbeat",
        json={
            "device_id": "cam-001",
            "timestamp": fixed_now.isoformat(),
            "current_count": 0,
            "status": "ok",
        },
        headers=device_headers,
    )
    assert heartbeat_response.status_code == 200

    active_response = client.get("/api/alerts", headers=auth_headers)
    assert active_response.status_code == 200
    assert active_response.json()["total"] == 0


def test_low_production_alert_triggers_once(client: TestClient, auth_headers: dict, db_session, monkeypatch):
    fixed_now = datetime(2026, 3, 24, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(services, "utc_now", lambda: fixed_now)

    device = db_session.execute(select(Device).where(Device.device_id == "cam-001")).scalar_one()
    device.last_heartbeat = fixed_now
    db_session.add(device)

    today = fixed_now.astimezone(services.app_tz()).date()
    for day_offset in range(1, 8):
        detected_at = _local_to_utc(today - timedelta(days=day_offset), 9)
        db_session.add(
            EggDetection(
                device_id=device.id,
                size="medium",
                confidence=0.92,
                bbox_area_normalized=0.0032,
                detected_at=detected_at,
            )
        )
        db_session.add(
            EggDetection(
                device_id=device.id,
                size="large",
                confidence=0.93,
                bbox_area_normalized=0.0038,
                detected_at=detected_at + timedelta(minutes=10),
            )
        )
    db_session.commit()

    first_response = client.get("/api/alerts", headers=auth_headers)
    second_response = client.get("/api/alerts", headers=auth_headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["total"] == 1
    assert second_response.json()["total"] == 1
    assert first_response.json()["alerts"][0]["type"] == "low_production"
    assert "below the daily average (2.0)" in first_response.json()["alerts"][0]["message"]


def test_uncertain_detection_alert_triggers_on_event_ingest(
    client: TestClient,
    auth_headers: dict,
    device_headers: dict,
    monkeypatch,
):
    fixed_now = datetime(2026, 3, 24, 4, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(services, "utc_now", lambda: fixed_now)

    ingest_response = client.post(
        "/api/events",
        json=create_event_payload(timestamp=fixed_now, sizes=["unknown", "unknown", "unknown", "unknown"], total_count=4),
        headers=device_headers,
    )
    assert ingest_response.status_code == 201

    alerts_response = client.get("/api/alerts", headers=auth_headers)
    assert alerts_response.status_code == 200
    assert alerts_response.json()["total"] == 1
    assert alerts_response.json()["alerts"][0]["type"] == "uncertain_detection"


def test_missing_data_alert_triggers_during_daytime(client: TestClient, auth_headers: dict, db_session, monkeypatch):
    fixed_now = datetime(2026, 3, 24, 5, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(services, "utc_now", lambda: fixed_now)

    device = db_session.execute(select(Device).where(Device.device_id == "cam-001")).scalar_one()
    device.last_heartbeat = fixed_now
    db_session.add(device)
    db_session.commit()

    response = client.get("/api/alerts", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["alerts"][0]["type"] == "missing_data"
