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
