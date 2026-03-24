from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from tests.helpers import create_event_payload


def test_dashboard_summary_and_period_dist(client: TestClient, auth_headers: dict, device_headers: dict):
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)

    client.post("/api/events", json=create_event_payload(timestamp=yesterday, sizes=["medium"]), headers=device_headers)
    client.post("/api/events", json=create_event_payload(timestamp=now, sizes=["large", "large"]), headers=device_headers)

    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)
    period_response = client.get("/api/dashboard/period-dist?period=week", headers=auth_headers)

    assert summary_response.status_code == 200
    body = summary_response.json()
    assert body["total_today"] == 2
    assert body["previous_day_total"] == 1
    assert body["device"]["device_id"] == "cam-001"

    assert period_response.status_code == 200
    assert period_response.json()["period"] == "week"
    assert len(period_response.json()["daily_data"]) == 7
