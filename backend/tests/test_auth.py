def test_login_success(client):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_failure(client):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_me(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_protected_endpoint_requires_auth(client):
    assert client.get("/api/v1/networks").status_code == 401


def test_change_password(client, auth_headers):
    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "admin", "new_password": "newpass123"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert client.post("/api/v1/auth/login",
                       json={"username": "admin", "password": "admin"}).status_code == 401
    assert client.post("/api/v1/auth/login",
                       json={"username": "admin", "password": "newpass123"}).status_code == 200
