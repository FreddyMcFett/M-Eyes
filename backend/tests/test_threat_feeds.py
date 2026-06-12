import httpx

from app.generators.named_conf import rpz_active
from app.generators.rpz_zone import render_rpz_zone
from app.services import threat_feeds

FEED_BODY = """# sample threat feed
bad.example.com
0.0.0.0 hosts.example.net  # hosts-file style
*.wild.example.org
not_a_domain
duplicate.example.com
duplicate.example.com
; comment line
"""


class _FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)


def test_parse_domains_handles_formats():
    domains = threat_feeds.parse_domains(FEED_BODY)
    assert domains == ["bad.example.com", "hosts.example.net", "wild.example.org",
                       "duplicate.example.com"]


def test_feed_crud_and_validation(client, auth_headers):
    response = client.post("/api/v1/rpz/threat-feeds",
                           json={"name": "abuse", "url": "ftp://nope"}, headers=auth_headers)
    assert response.status_code == 422

    response = client.post("/api/v1/rpz/threat-feeds",
                           json={"name": "abuse", "url": "https://feeds.example.com/domains.txt"},
                           headers=auth_headers)
    assert response.status_code == 201, response.text
    feed = response.json()
    assert feed["action"] == "block"
    assert feed["entry_count"] == 0

    duplicate = client.post("/api/v1/rpz/threat-feeds",
                            json={"name": "abuse", "url": "https://other.example.com/x.txt"},
                            headers=auth_headers)
    assert duplicate.status_code == 409

    response = client.patch(f"/api/v1/rpz/threat-feeds/{feed['id']}",
                            json={"action": "nodata"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["action"] == "nodata"

    response = client.delete(f"/api/v1/rpz/threat-feeds/{feed['id']}", headers=auth_headers)
    assert response.status_code == 204
    assert client.get("/api/v1/rpz/threat-feeds", headers=auth_headers).json() == []


def test_sync_populates_rpz_zone(client, auth_headers, db_session, monkeypatch):
    monkeypatch.setattr(threat_feeds.httpx, "get",
                        lambda url, **kwargs: _FakeResponse(FEED_BODY))
    feed = client.post("/api/v1/rpz/threat-feeds",
                       json={"name": "intel", "url": "https://feeds.example.com/domains.txt"},
                       headers=auth_headers).json()
    assert rpz_active(db_session) is False

    response = client.post(f"/api/v1/rpz/threat-feeds/{feed['id']}/sync", headers=auth_headers)
    assert response.status_code == 200, response.text
    synced = response.json()
    assert synced["entry_count"] == 4
    assert synced["last_status"].startswith("ok")
    assert synced["last_synced"] is not None

    assert rpz_active(db_session) is True
    zone = render_rpz_zone(db_session)
    assert "bad.example.com" in zone
    assert "*.bad.example.com" in zone


def test_manual_rule_overrides_feed_entry(client, auth_headers, db_session, monkeypatch):
    monkeypatch.setattr(threat_feeds.httpx, "get",
                        lambda url, **kwargs: _FakeResponse("allowme.example.com\n"))
    feed = client.post("/api/v1/rpz/threat-feeds",
                       json={"name": "intel2", "url": "https://feeds.example.com/d.txt"},
                       headers=auth_headers).json()
    client.post(f"/api/v1/rpz/threat-feeds/{feed['id']}/sync", headers=auth_headers)
    client.post("/api/v1/rpz/rules",
                json={"fqdn": "allowme.example.com", "action": "passthru"}, headers=auth_headers)

    zone = render_rpz_zone(db_session)
    # exactly one pair of rows for the domain: the manual passthru rule
    lines = [line for line in zone.splitlines() if line.startswith("allowme.example.com")]
    assert len(lines) == 1
    assert "rpz-passthru." in lines[0]


def test_sync_failure_keeps_previous_entries(client, auth_headers, monkeypatch):
    monkeypatch.setattr(threat_feeds.httpx, "get",
                        lambda url, **kwargs: _FakeResponse("keep.example.com\n"))
    feed = client.post("/api/v1/rpz/threat-feeds",
                       json={"name": "flaky", "url": "https://feeds.example.com/f.txt"},
                       headers=auth_headers).json()
    client.post(f"/api/v1/rpz/threat-feeds/{feed['id']}/sync", headers=auth_headers)

    def _boom(url, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(threat_feeds.httpx, "get", _boom)
    response = client.post(f"/api/v1/rpz/threat-feeds/{feed['id']}/sync", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["last_status"].startswith("fetch failed")
    assert body["entry_count"] == 1  # previous entries preserved
