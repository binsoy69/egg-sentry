from datetime import datetime, timedelta, timezone

from app.models import CountSnapshot, Device, EggDetection
from app.services import count_for_day, current_local_date, local_day_bounds
from tests.helpers import create_event_payload


def test_manual_collection_creates_entry_and_resets_current_count(client, auth_headers: dict, device_headers: dict):
    now = datetime.now(timezone.utc)
    client.post(
        "/api/events",
        json=create_event_payload(timestamp=now, sizes=["medium", "medium", "large", "large"], total_count=4),
        headers=device_headers,
    )

    collect_response = client.post("/api/collections", json={"device_id": "cam-001"}, headers=auth_headers)

    assert collect_response.status_code == 201
    body = collect_response.json()
    assert body["entry"]["count"] == 4
    assert body["entry"]["source"] == "manual"
    assert body["current_eggs"] == 0
    assert body["collected_today"] == 4
    assert body["total_today"] == 4

    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)

    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["current_eggs"] == 0
    assert summary["collected_today"] == 4
    assert summary["total_today"] == 4
    assert summary["collection_history"][0]["source"] == "manual"


def test_significant_drop_reconciles_history_without_creating_collection(
    client,
    auth_headers: dict,
    device_headers: dict,
):
    now = datetime.now(timezone.utc)
    client.post(
        "/api/events",
        json=create_event_payload(timestamp=now, sizes=["medium"] * 5, total_count=5),
        headers=device_headers,
    )

    drop_payload = create_event_payload(timestamp=now + timedelta(minutes=10), sizes=[], total_count=1)
    drop_payload["size_breakdown"] = {"medium": 1}
    client.post("/api/events", json=drop_payload, headers=device_headers)

    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)
    history_response = client.get("/api/history", headers=auth_headers)

    assert summary_response.status_code == 200
    assert history_response.status_code == 200

    summary = summary_response.json()
    history = history_response.json()
    assert summary["current_eggs"] == 1
    assert summary["collected_today"] == 0
    assert summary["total_today"] == 1
    assert summary["collection_history"] == []
    assert history["total_records"] == 1


def test_manual_collection_reconciles_excess_today_detections(
    client,
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
            for index in range(13)
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

    collect_response = client.post("/api/collections", json={"device_id": "cam-001"}, headers=auth_headers)
    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)
    history_response = client.get("/api/history", headers=auth_headers)

    assert collect_response.status_code == 201
    assert summary_response.status_code == 200
    assert history_response.status_code == 200

    collect_body = collect_response.json()
    summary = summary_response.json()
    history = history_response.json()

    assert collect_body["entry"]["count"] == 11
    assert collect_body["current_eggs"] == 0
    assert collect_body["collected_today"] == 11
    assert collect_body["total_today"] == 11
    assert summary["current_eggs"] == 0
    assert summary["collected_today"] == 11
    assert summary["total_today"] == 11
    assert history["total_records"] == 11
    assert count_for_day(db_session, device, today) == 11
