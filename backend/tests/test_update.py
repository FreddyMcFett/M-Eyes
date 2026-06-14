"""In-app software update: capability reporting, request flow and guards."""

from app.services import updater


def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_user(client, auth_headers, username, role, password="secret123"):
    resp = client.post("/api/v1/users", headers=auth_headers,
                       json={"username": username, "password": password, "role": role})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_update_check_reports_capability(client, auth_headers):
    resp = client.get("/api/v1/system/update-check", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_version"]
    assert "in_app_update" in body


def test_trigger_update_writes_request(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(updater, "_dir", lambda: str(tmp_path))

    resp = client.post("/api/v1/system/update", json={"target_version": "9.9.9"},
                       headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["phase"] == "requested"
    assert resp.json()["target_version"] == "9.9.9"
    assert (tmp_path / "request.json").exists()
    assert (tmp_path / "status.json").exists()

    status = client.get("/api/v1/system/update/status", headers=auth_headers).json()
    assert status["phase"] == "requested"
    assert status["target_version"] == "9.9.9"
    assert status["current_version"]  # the running API answered, so it's reachable


def test_trigger_update_rejects_bad_version(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(updater, "_dir", lambda: str(tmp_path))
    resp = client.post("/api/v1/system/update", json={"target_version": "; rm -rf /"},
                       headers=auth_headers)
    assert resp.status_code == 422
    assert not (tmp_path / "request.json").exists()


def test_trigger_update_conflicts_when_already_running(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(updater, "_dir", lambda: str(tmp_path))
    first = client.post("/api/v1/system/update", json={"target_version": "9.9.9"},
                       headers=auth_headers)
    assert first.status_code == 200, first.text
    # A second request while the first is still "requested" is rejected.
    second = client.post("/api/v1/system/update", json={"target_version": "9.9.10"},
                        headers=auth_headers)
    assert second.status_code == 409


def test_trigger_update_is_admin_only(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(updater, "_dir", lambda: str(tmp_path))
    _make_user(client, auth_headers, "ops-upd", "operator")
    operator = _login(client, "ops-upd", "secret123")
    resp = client.post("/api/v1/system/update", json={"target_version": "9.9.9"},
                       headers=operator)
    assert resp.status_code == 403
    assert not (tmp_path / "request.json").exists()


def test_update_unsupported_falls_back(client, auth_headers, tmp_path, monkeypatch):
    # Simulate a deployment without the updater sidecar (no writable volume).
    monkeypatch.setattr(updater, "is_supported", lambda: False)
    resp = client.post("/api/v1/system/update", json={"target_version": "9.9.9"},
                       headers=auth_headers)
    assert resp.status_code == 400
    assert "not available" in resp.json()["detail"]
