from datetime import datetime, timedelta, timezone

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
