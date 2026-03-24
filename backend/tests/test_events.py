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
