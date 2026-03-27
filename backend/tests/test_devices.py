from datetime import datetime, timezone

from fastapi.testclient import TestClient


def test_devices_list_heartbeat_and_update(client: TestClient, auth_headers: dict, device_headers: dict):
    heartbeat_response = client.post(
        "/api/devices/heartbeat",
        json={
            "device_id": "cam-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_count": 3,
            "status": "ok",
        },
        headers=device_headers,
    )
    assert heartbeat_response.status_code == 200

    list_response = client.get("/api/devices", headers=auth_headers)
    assert list_response.status_code == 200
    assert list_response.json()[0]["status"] == "online"

    update_response = client.put(
        "/api/devices/cam-001",
        json={
            "name": "North Coop Camera",
            "num_cages": 6,
            "num_chickens": 12,
            "age_of_chicken": {"weeks": 2, "days": 3},
        },
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "North Coop Camera"
    assert update_response.json()["num_cages"] == 6
    assert update_response.json()["age_of_chicken"]["weeks"] == 2
    assert update_response.json()["age_of_chicken"]["days"] == 3
    assert update_response.json()["age_of_chicken"]["set_at"] is not None

    refreshed_list_response = client.get("/api/devices", headers=auth_headers)
    assert refreshed_list_response.status_code == 200
    assert refreshed_list_response.json()[0]["age_of_chicken"]["weeks"] == 2
    assert refreshed_list_response.json()[0]["age_of_chicken"]["days"] == 3

    toggle_response = client.put(
        "/api/devices/cam-001/config",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert toggle_response.status_code == 200
    assert toggle_response.json()["is_config_active"] is False
