from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import Device


def test_alerts_list_and_dismiss(client: TestClient, auth_headers: dict, db_session):
    device = db_session.execute(select(Device).where(Device.device_id == "cam-001")).scalar_one()
    device.last_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=10)
    db_session.add(device)
    db_session.commit()

    response = client.get("/api/alerts", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    alert_id = body["alerts"][0]["id"]

    dismiss_response = client.put(f"/api/alerts/{alert_id}/dismiss", headers=auth_headers)
    assert dismiss_response.status_code == 200
    assert dismiss_response.json()["dismissed"] is True
