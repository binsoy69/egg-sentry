from datetime import datetime, timezone

from fastapi.testclient import TestClient

from tests.helpers import create_event_payload


def test_event_ingestion_and_events_alias(client: TestClient, auth_headers: dict, device_headers: dict):
    ingest_response = client.post(
        "/api/events",
        json=create_event_payload(timestamp=datetime.now(timezone.utc), sizes=["medium", "large"]),
        headers=device_headers,
    )

    assert ingest_response.status_code == 201
    assert ingest_response.json()["events_created"] == 2

    events_response = client.get("/api/events", headers=auth_headers)

    assert events_response.status_code == 200
    assert len(events_response.json()) == 2
    assert events_response.json()[0]["device_id"] == "cam-001"


def test_event_ingestion_backfills_missing_history_records(client: TestClient, auth_headers: dict, device_headers: dict):
    timestamp = datetime.now(timezone.utc)
    payload = create_event_payload(timestamp=timestamp, sizes=["jumbo"], total_count=3)
    payload["size_breakdown"] = {"jumbo": 3}

    ingest_response = client.post("/api/events", json=payload, headers=device_headers)

    assert ingest_response.status_code == 201
    assert ingest_response.json()["events_created"] == 3

    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)
    history_response = client.get("/api/history", headers=auth_headers)

    assert summary_response.status_code == 200
    assert summary_response.json()["current_eggs"] == 3
    assert summary_response.json()["all_time_eggs"] == 3

    assert history_response.status_code == 200
    body = history_response.json()
    assert body["total_records"] == 3
    assert len(body["records"]) == 3
    assert all(record["size"] == "jumbo" for record in body["records"])
