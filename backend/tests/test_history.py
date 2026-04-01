from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from tests.helpers import create_event_payload


def test_history_filters_and_pagination(client: TestClient, auth_headers: dict, device_headers: dict):
    now = datetime.now(timezone.utc)
    client.post("/api/events", json=create_event_payload(timestamp=now, sizes=["medium", "medium", "large"]), headers=device_headers)
    client.post("/api/collections", json={"device_id": "cam-001"}, headers=auth_headers)

    response = client.get(
        "/api/history?size=medium&page=1&limit=2",
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_records"] == 2
    assert len(body["records"]) == 2
    assert all(record["size"] == "medium" for record in body["records"])
