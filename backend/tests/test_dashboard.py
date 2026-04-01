from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.models import CountSnapshot, Device, EggDetection
from app.services import create_collection, current_local_date, local_day_bounds


def test_dashboard_summary_and_period_dist(client: TestClient, auth_headers: dict, db_session):
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    device = db_session.query(Device).filter(Device.device_id == "cam-001").one()
    create_collection(
        db_session,
        device=device,
        collected_count=1,
        before_count=1,
        after_count=0,
        source="manual",
        collected_at=yesterday,
        size_breakdown={"medium": 1},
    )
    create_collection(
        db_session,
        device=device,
        collected_count=2,
        before_count=2,
        after_count=0,
        source="manual",
        collected_at=now,
        size_breakdown={"large": 2},
    )
    db_session.commit()

    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)
    period_response = client.get("/api/dashboard/period-dist?period=week", headers=auth_headers)

    assert summary_response.status_code == 200
    body = summary_response.json()
    assert body["total_today"] == 2
    assert body["previous_day_total"] == 1
    assert body["current_eggs"] == 0
    assert body["device"]["device_id"] == "cam-001"

    assert period_response.status_code == 200
    assert period_response.json()["period"] == "week"
    assert len(period_response.json()["daily_data"]) == 7


def test_dashboard_today_total_uses_collections_not_latest_live_count_or_detections(
    client: TestClient,
    auth_headers: dict,
    db_session,
):
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

    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)
    history_response = client.get(f"/api/history?start_date={today.isoformat()}", headers=auth_headers)

    assert summary_response.status_code == 200
    assert history_response.status_code == 200

    summary = summary_response.json()
    history = history_response.json()

    assert summary["current_eggs"] == 11
    assert summary["collected_today"] == 0
    assert summary["today_eggs"] == 0
    assert summary["total_today"] == 0
    assert summary["device"]["today_count"] == 0
    assert history["total_records"] == 0
