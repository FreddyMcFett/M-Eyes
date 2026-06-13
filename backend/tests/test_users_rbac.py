"""User management and role-based access control."""


def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_user(client, auth_headers, username, role, password="secret123"):
    resp = client.post("/api/v1/users", headers=auth_headers,
                       json={"username": username, "password": password, "role": role})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_admin_can_manage_users(client, auth_headers):
    user = _make_user(client, auth_headers, "ops1", "operator")
    assert user["role"] == "operator"
    listed = client.get("/api/v1/users", headers=auth_headers)
    assert listed.status_code == 200 and len(listed.json()) == 2  # admin + ops1


def test_viewer_cannot_create_assets(client, auth_headers):
    _make_user(client, auth_headers, "view1", "viewer")
    viewer = _login(client, "view1", "secret123")
    resp = client.post("/api/v1/assets", headers=viewer, json={"name": "x"})
    assert resp.status_code == 403


def test_operator_can_create_assets_but_not_users(client, auth_headers):
    _make_user(client, auth_headers, "ops2", "operator")
    operator = _login(client, "ops2", "secret123")
    assert client.post("/api/v1/assets", headers=operator,
                       json={"name": "srv"}).status_code == 201
    assert client.post("/api/v1/users", headers=operator,
                       json={"username": "x", "password": "secret123"}).status_code == 403


def test_operator_cannot_manage_integrations(client, auth_headers):
    _make_user(client, auth_headers, "ops3", "operator")
    operator = _login(client, "ops3", "secret123")
    # Operators may run a sync/test but not create integrations (admin only).
    resp = client.post("/api/v1/integrations", headers=operator,
                       json={"name": "fw", "kind": "fortigate"})
    assert resp.status_code == 403


def test_disabled_user_cannot_authenticate(client, auth_headers):
    user = _make_user(client, auth_headers, "gone", "viewer")
    headers = _login(client, "gone", "secret123")
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    client.patch(f"/api/v1/users/{user['id']}", headers=auth_headers, json={"is_active": False})
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 403


def test_cannot_disable_self(client, auth_headers):
    me = client.get("/api/v1/auth/me", headers=auth_headers).json()
    resp = client.patch(f"/api/v1/users/{me['id']}", headers=auth_headers,
                        json={"is_active": False})
    assert resp.status_code == 422
