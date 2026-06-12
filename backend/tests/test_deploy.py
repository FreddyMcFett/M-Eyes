import json
import subprocess
from unittest.mock import patch

import httpx


def _setup_zone(client, headers):
    zone = client.post("/api/v1/zones", json={"name": "deploy.example"}, headers=headers).json()
    client.post(f"/api/v1/zones/{zone['id']}/records",
                json={"name": "www", "type": "A", "value": "192.0.2.1"}, headers=headers)
    return zone


def _fake_run(returncode=0, stdout="", stderr=""):
    def runner(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)
    return runner


def test_bind_deploy_success(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("MEYES_BIND_OUTPUT_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    _setup_zone(client, auth_headers)

    with patch("app.services.deploy.bind.subprocess.run", side_effect=_fake_run()):
        response = client.post("/api/v1/deploy/bind", headers=auth_headers)
    assert response.json()["status"] == "success"
    assert (tmp_path / "zones.conf").exists()
    assert (tmp_path / "db.deploy.example").exists()
    content = (tmp_path / "db.deploy.example").read_text()
    assert "www" in content and "192.0.2.1" in content
    get_settings.cache_clear()


def test_bind_deploy_unreachable_still_writes(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("MEYES_BIND_OUTPUT_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    _setup_zone(client, auth_headers)

    def failing_run(cmd, **kwargs):
        if cmd[0] == "rndc":
            raise FileNotFoundError("rndc")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    with patch("app.services.deploy.bind.subprocess.run", side_effect=failing_run):
        response = client.post("/api/v1/deploy/bind", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "unreachable"
    assert (tmp_path / "zones.conf").exists()  # management-only mode: files still written

    history = client.get("/api/v1/deploy/history", headers=auth_headers).json()
    assert history[0]["status"] == "unreachable"
    get_settings.cache_clear()


def test_bind_deploy_validation_failure_aborts(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("MEYES_BIND_OUTPUT_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    _setup_zone(client, auth_headers)

    def checkzone_fails(cmd, **kwargs):
        if cmd[0] == "named-checkzone":
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="syntax error")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    with patch("app.services.deploy.bind.subprocess.run", side_effect=checkzone_fails):
        response = client.post("/api/v1/deploy/bind", headers=auth_headers)
    assert response.json()["status"] == "failed"
    assert not (tmp_path / "zones.conf").exists()  # nothing published
    get_settings.cache_clear()


def _setup_dhcp(client, headers):
    network = client.post("/api/v1/networks", json={"cidr": "10.90.0.0/24"}, headers=headers).json()
    subnet = client.post("/api/v1/dhcp/subnets", json={"network_id": network["id"]},
                         headers=headers).json()
    client.post(f"/api/v1/dhcp/subnets/{subnet['id']}/ranges",
                json={"start_ip": "10.90.0.10", "end_ip": "10.90.0.99"}, headers=headers)


def test_kea_deploy_success(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("MEYES_KEA_OUTPUT_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    _setup_dhcp(client, auth_headers)

    def fake_post(url, **kwargs):
        return httpx.Response(200, json=[{"result": 0, "text": "ok"}],
                              request=httpx.Request("POST", url))

    with patch("app.services.deploy.kea.httpx.post", side_effect=fake_post):
        response = client.post("/api/v1/deploy/kea", headers=auth_headers)
    assert response.json()["status"] == "success"
    written = json.loads((tmp_path / "kea-dhcp4.conf").read_text())
    assert written["Dhcp4"]["subnet4"][0]["subnet"] == "10.90.0.0/24"
    get_settings.cache_clear()


def test_kea_deploy_unreachable(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("MEYES_KEA_OUTPUT_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    _setup_dhcp(client, auth_headers)

    with patch("app.services.deploy.kea.httpx.post",
               side_effect=httpx.ConnectError("refused")):
        response = client.post("/api/v1/deploy/kea", headers=auth_headers)
    assert response.json()["status"] == "unreachable"
    assert (tmp_path / "kea-dhcp4.conf").exists()
    get_settings.cache_clear()


def test_kea_deploy_rejected_config(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("MEYES_KEA_OUTPUT_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    _setup_dhcp(client, auth_headers)

    def fake_post(url, **kwargs):
        return httpx.Response(200, json=[{"result": 1, "text": "bad config"}],
                              request=httpx.Request("POST", url))

    with patch("app.services.deploy.kea.httpx.post", side_effect=fake_post):
        response = client.post("/api/v1/deploy/kea", headers=auth_headers)
    assert response.json()["status"] == "failed"
    assert "bad config" in response.json()["detail"]
    get_settings.cache_clear()


def test_bind_preview(client, auth_headers):
    _setup_zone(client, auth_headers)
    preview = client.get("/api/v1/deploy/bind/preview", headers=auth_headers).json()
    assert 'zone "deploy.example"' in preview["zones_conf"]
    assert "db.deploy.example" in preview["zone_files"]
    assert "rpz_options" in preview


def test_deploy_status_endpoint(client, auth_headers):
    response = client.get("/api/v1/deploy/status", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "bind" in body and "kea" in body
