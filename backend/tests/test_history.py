from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.services import current_local_date, local_day_bounds
from tests.helpers import create_event_payload


def _login_headers(client: TestClient, username: str, password: str) -> dict:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _history_payload(*, collected_at: datetime | None = None, device_id: str = "cam-001", **sizes):
    breakdown = {"small": 0, "medium": 0, "large": 0, "extra-large": 0, "jumbo": 0, "unknown": 0}
    breakdown.update(sizes)
    if collected_at is None:
        start, _ = local_day_bounds(current_local_date())
        collected_at = start + timedelta(hours=9)
    return {
        "device_id": device_id,
        "collected_at": collected_at.isoformat(),
        "size_breakdown": breakdown,
    }


def test_history_filters_and_pagination(client: TestClient, auth_headers: dict, device_headers: dict):
    now = datetime.now(timezone.utc)
    client.post(
        "/api/events",
        json=create_event_payload(timestamp=now, sizes=["medium", "medium", "large"]),
        headers=device_headers,
    )
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


def test_history_collection_endpoints_require_history_editor(client: TestClient, auth_headers: dict):
    viewer_headers = _login_headers(client, "viewer", "viewer123")
    payload = _history_payload(medium=1)

    admin_response = client.post("/api/history/collections", json=payload, headers=auth_headers)
    viewer_response = client.post("/api/history/collections", json=payload, headers=viewer_headers)

    assert admin_response.status_code == 403
    assert viewer_response.status_code == 403
    assert admin_response.json()["detail"] == "History editor access required"


def test_history_editor_create_update_delete_updates_history_and_dashboard(client: TestClient, auth_headers: dict):
    editor_headers = _login_headers(client, "editor", "editor123")
    today = current_local_date()
    start, _ = local_day_bounds(today)

    create_response = client.post(
        "/api/history/collections",
        json=_history_payload(collected_at=start + timedelta(hours=9), medium=2, large=1),
        headers=editor_headers,
    )
    list_response = client.get("/api/history/collections?size=medium", headers=editor_headers)
    history_response = client.get("/api/history?size=medium", headers=auth_headers)
    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["count"] == 3
    assert created["size_breakdown"]["medium"] == 2
    assert list_response.status_code == 200
    assert list_response.json()["total_records"] == 1
    assert history_response.json()["total_records"] == 2
    assert summary_response.json()["collected_today"] == 3
    assert summary_response.json()["all_time_eggs"] == 3

    update_response = client.patch(
        f"/api/history/collections/{created['id']}",
        json=_history_payload(collected_at=start + timedelta(hours=10), jumbo=2, unknown=1),
        headers=editor_headers,
    )
    jumbo_history_response = client.get("/api/history?size=jumbo", headers=auth_headers)
    old_medium_response = client.get("/api/history?size=medium", headers=auth_headers)
    updated_summary_response = client.get("/api/dashboard/summary", headers=auth_headers)

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["count"] == 3
    assert updated["size_breakdown"]["jumbo"] == 2
    assert updated["size_breakdown"]["unknown"] == 1
    assert jumbo_history_response.json()["total_records"] == 2
    assert old_medium_response.json()["total_records"] == 0
    assert updated_summary_response.json()["collected_today"] == 3
    assert updated_summary_response.json()["size_distribution"] == {"Jumbo": 2}

    delete_response = client.delete(f"/api/history/collections/{created['id']}", headers=editor_headers)
    deleted_history_response = client.get("/api/history", headers=auth_headers)
    deleted_summary_response = client.get("/api/dashboard/summary", headers=auth_headers)

    assert delete_response.status_code == 204
    assert deleted_history_response.json()["total_records"] == 0
    assert deleted_summary_response.json()["collected_today"] == 0
    assert deleted_summary_response.json()["all_time_eggs"] == 0


def test_history_collection_filters_by_date_device_and_size(client: TestClient, auth_headers: dict):
    editor_headers = _login_headers(client, "editor", "editor123")
    today = current_local_date()
    today_start, _ = local_day_bounds(today)
    yesterday_start, _ = local_day_bounds(today - timedelta(days=1))

    client.post(
        "/api/history/collections",
        json=_history_payload(collected_at=today_start + timedelta(hours=8), medium=1),
        headers=editor_headers,
    )
    client.post(
        "/api/history/collections",
        json=_history_payload(collected_at=yesterday_start + timedelta(hours=8), large=2),
        headers=editor_headers,
    )

    today_response = client.get(
        f"/api/history/collections?device_id=cam-001&start_date={today.isoformat()}&end_date={today.isoformat()}",
        headers=editor_headers,
    )
    large_response = client.get("/api/history/collections?size=large", headers=editor_headers)
    history_large_response = client.get("/api/history?size=large", headers=auth_headers)

    assert today_response.status_code == 200
    assert today_response.json()["total_records"] == 1
    assert today_response.json()["records"][0]["size_breakdown"]["medium"] == 1
    assert large_response.json()["total_records"] == 1
    assert history_large_response.json()["total_records"] == 2


def test_history_collection_mutation_validation(client: TestClient):
    editor_headers = _login_headers(client, "editor", "editor123")

    invalid_device_response = client.post(
        "/api/history/collections",
        json=_history_payload(device_id="missing-device", medium=1),
        headers=editor_headers,
    )
    invalid_size_response = client.post(
        "/api/history/collections",
        json={
            "device_id": "cam-001",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "size_breakdown": {"medium": 1, "tiny": 1},
        },
        headers=editor_headers,
    )
    negative_count_response = client.post(
        "/api/history/collections",
        json=_history_payload(medium=-1),
        headers=editor_headers,
    )
    zero_count_response = client.post(
        "/api/history/collections",
        json=_history_payload(),
        headers=editor_headers,
    )

    assert invalid_device_response.status_code == 404
    assert invalid_size_response.status_code == 422
    assert negative_count_response.status_code == 422
    assert zero_count_response.status_code == 422
