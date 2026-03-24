from fastapi.testclient import TestClient


def test_login_and_me(client: TestClient):
    login_response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me_response.status_code == 200
    assert me_response.json()["username"] == "admin"


def test_form_token_login(client: TestClient):
    response = client.post(
        "/api/auth/token",
        data={"username": "viewer", "password": "viewer123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_change_password_updates_credentials(client: TestClient):
    login_response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_response.json()["access_token"]

    change_response = client.post(
        "/api/auth/change-password",
        json={"current_password": "admin123", "new_password": "updated123"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert change_response.status_code == 200
    assert change_response.json()["success"] is True

    old_login_response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    new_login_response = client.post("/api/auth/login", json={"username": "admin", "password": "updated123"})

    assert old_login_response.status_code == 401
    assert new_login_response.status_code == 200
