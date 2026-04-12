from collections import Counter
from datetime import datetime, timedelta, timezone

from app.models import CountSnapshot, Device, EggCollection, EggDetection
from app.services import count_for_day, create_collection, current_local_date, local_day_bounds
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
    assert summary["total_today"] == 0
    assert summary["collection_history"] == []
    assert history["total_records"] == 0


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


def test_update_today_collection_entry_recalculates_totals_and_history(
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
            for index in range(4)
        ]
    )
    collection = create_collection(
        db_session,
        device=device,
        collected_count=4,
        before_count=4,
        after_count=0,
        source="manual",
        collected_at=detection_time + timedelta(minutes=30),
        size_breakdown={"large": 4},
    )
    db_session.commit()

    update_response = client.patch(
        f"/api/collections/{collection.id}",
        json={"count": 3},
        headers=auth_headers,
    )
    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)
    history_response = client.get("/api/history", headers=auth_headers)

    assert update_response.status_code == 200
    assert summary_response.status_code == 200
    assert history_response.status_code == 200

    update_body = update_response.json()
    summary = summary_response.json()
    history = history_response.json()

    assert update_body["affected_count"] == 1
    assert update_body["entry"]["count"] == 3
    assert update_body["collected_today"] == 3
    assert summary["collected_today"] == 3
    assert summary["total_today"] == 3
    assert history["total_records"] == 3
    assert count_for_day(db_session, device, today) == 3


def test_delete_today_collection_entry_recalculates_totals(
    client,
    auth_headers: dict,
    db_session,
):
    device = db_session.query(Device).filter(Device.device_id == "cam-001").one()
    today = current_local_date()
    start, _ = local_day_bounds(today)
    collection_time = start + timedelta(hours=9)
    first = create_collection(
        db_session,
        device=device,
        collected_count=2,
        before_count=2,
        after_count=0,
        source="manual",
        collected_at=collection_time,
        size_breakdown={"medium": 2},
    )
    create_collection(
        db_session,
        device=device,
        collected_count=3,
        before_count=3,
        after_count=0,
        source="manual",
        collected_at=collection_time + timedelta(minutes=30),
        size_breakdown={"large": 3},
    )
    db_session.commit()

    delete_response = client.delete(f"/api/collections/{first.id}", headers=auth_headers)
    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)

    assert delete_response.status_code == 200
    assert summary_response.status_code == 200

    summary = summary_response.json()
    assert delete_response.json()["affected_count"] == 1
    assert summary["collected_today"] == 3
    assert summary["total_today"] == 3
    assert len(summary["collection_history"]) == 1
    assert summary["collection_history"][0]["count"] == 3


def test_clear_today_collections_keeps_non_today_entries(
    client,
    auth_headers: dict,
    db_session,
):
    device = db_session.query(Device).filter(Device.device_id == "cam-001").one()
    today = current_local_date()
    start, _ = local_day_bounds(today)
    yesterday_start, _ = local_day_bounds(today - timedelta(days=1))
    create_collection(
        db_session,
        device=device,
        collected_count=2,
        before_count=2,
        after_count=0,
        source="manual",
        collected_at=start + timedelta(hours=9),
        size_breakdown={"medium": 2},
    )
    create_collection(
        db_session,
        device=device,
        collected_count=3,
        before_count=3,
        after_count=0,
        source="manual",
        collected_at=start + timedelta(hours=10),
        size_breakdown={"large": 3},
    )
    create_collection(
        db_session,
        device=device,
        collected_count=1,
        before_count=1,
        after_count=0,
        source="manual",
        collected_at=yesterday_start + timedelta(hours=9),
        size_breakdown={"small": 1},
    )
    db_session.commit()

    clear_response = client.delete("/api/collections/today?device_id=cam-001", headers=auth_headers)
    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)

    assert clear_response.status_code == 200
    assert clear_response.json()["affected_count"] == 2
    assert summary_response.status_code == 200
    assert summary_response.json()["collected_today"] == 0
    assert summary_response.json()["collection_history"] == []

    db_session.expire_all()
    remaining = db_session.query(EggCollection).all()
    assert len(remaining) == 1
    assert remaining[0].collected_count == 1


def test_non_today_collection_entry_cannot_be_edited_or_deleted(
    client,
    auth_headers: dict,
    db_session,
):
    device = db_session.query(Device).filter(Device.device_id == "cam-001").one()
    yesterday_start, _ = local_day_bounds(current_local_date() - timedelta(days=1))
    collection = create_collection(
        db_session,
        device=device,
        collected_count=2,
        before_count=2,
        after_count=0,
        source="manual",
        collected_at=yesterday_start + timedelta(hours=9),
        size_breakdown={"medium": 2},
    )
    db_session.commit()

    update_response = client.patch(
        f"/api/collections/{collection.id}",
        json={"count": 1},
        headers=auth_headers,
    )
    delete_response = client.delete(f"/api/collections/{collection.id}", headers=auth_headers)

    assert update_response.status_code == 404
    assert delete_response.status_code == 404


def test_legacy_collection_history_recovers_sizes_from_day_detections(
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
                size=size,
                confidence=0.91,
                bbox_area_normalized=0.0031,
                detected_at=detection_time + timedelta(seconds=index),
            )
            for index, size in enumerate(["medium", "large", "large"])
        ]
    )
    create_collection(
        db_session,
        device=device,
        collected_count=3,
        before_count=3,
        after_count=0,
        source="manual",
        collected_at=detection_time + timedelta(minutes=30),
        size_breakdown=None,
    )
    db_session.commit()

    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)
    history_response = client.get("/api/history", headers=auth_headers)

    assert summary_response.status_code == 200
    assert history_response.status_code == 200

    history_sizes = Counter(record["size"] for record in history_response.json()["records"])
    assert history_sizes == {"medium": 1, "large": 2}
    assert summary_response.json()["size_distribution"] == {"M": 1, "L": 2}
