"""In-app software update: capability reporting, request flow and guards."""

import httpx

from app.api.v1 import system
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


# --- update-check gating on container-image availability ---------------------
#
# The GitHub release/tag is published a few minutes before the multi-arch images
# land in GHCR; offering the update in that window is what made `docker compose
# pull` fail with "not found". So a newer release is only advertised once its
# images are actually pullable.

class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)

    def json(self):
        return self._payload


def _stub_latest_release(monkeypatch, tag):
    payload = {"tag_name": tag, "html_url": f"https://example.test/{tag}"}
    monkeypatch.setattr(system.httpx, "get", lambda *a, **k: _FakeResponse(200, payload))


def test_update_check_waits_for_unpublished_images(client, auth_headers, monkeypatch):
    _stub_latest_release(monkeypatch, "v999.0.0")
    monkeypatch.setattr(system, "_images_published", lambda tag: False)
    body = client.get("/api/v1/system/update-check?force=true", headers=auth_headers).json()
    assert body["latest_version"] == "999.0.0"
    assert body["update_available"] is False
    assert body["pending_images"] is True


def test_update_check_offers_update_when_images_ready(client, auth_headers, monkeypatch):
    _stub_latest_release(monkeypatch, "v999.0.0")
    monkeypatch.setattr(system, "_images_published", lambda tag: True)
    body = client.get("/api/v1/system/update-check?force=true", headers=auth_headers).json()
    assert body["update_available"] is True
    assert body["pending_images"] is False


def test_update_check_offers_update_when_registry_inconclusive(client, auth_headers, monkeypatch):
    # A flaky/unreachable registry must never hide a real update.
    _stub_latest_release(monkeypatch, "v999.0.0")
    monkeypatch.setattr(system, "_images_published", lambda tag: None)
    body = client.get("/api/v1/system/update-check?force=true", headers=auth_headers).json()
    assert body["update_available"] is True
    assert body["pending_images"] is False


def _stub_ghcr(monkeypatch, manifest_status):
    class _FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, params=None):
            return _FakeResponse(200, {"token": "anon"})

        def head(self, url, headers=None):
            return _FakeResponse(manifest_status)

    monkeypatch.setattr(system.httpx, "Client", lambda *a, **k: _FakeClient())


def test_images_published_maps_registry_status(monkeypatch):
    _stub_ghcr(monkeypatch, 200)
    assert system._images_published("1.0.0") is True

    _stub_ghcr(monkeypatch, 404)
    assert system._images_published("1.0.0") is False

    _stub_ghcr(monkeypatch, 503)
    assert system._images_published("1.0.0") is None
