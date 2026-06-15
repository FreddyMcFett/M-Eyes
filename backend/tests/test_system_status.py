"""System status snapshot, time-zone setting and resource metrics."""

from app.services import system_metrics


def test_status_returns_version_and_resources(client, auth_headers):
    resp = client.get("/api/v1/system/status", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version"]
    assert body["timezone"] == "UTC"  # default
    assert "server_time" in body
    assert "in_app_update" in body
    assert "resources" in body
    assert set(("cpu_percent", "memory", "disk", "load_average")) <= body["resources"].keys()
    assert body["engines"] == {"bind": None, "kea": None}  # nothing deployed yet


def test_status_reflects_configured_timezone(client, auth_headers):
    saved = client.put("/api/v1/system/settings", headers=auth_headers,
                       json={"values": {"timezone": "Europe/Zurich"}})
    assert saved.status_code == 200, saved.text

    body = client.get("/api/v1/system/status", headers=auth_headers).json()
    assert body["timezone"] == "Europe/Zurich"
    # Zurich is +0100 (winter) or +0200 (summer) — never UTC.
    assert body["utc_offset"] in ("+0100", "+0200")


def test_settings_rejects_unknown_timezone(client, auth_headers):
    resp = client.put("/api/v1/system/settings", headers=auth_headers,
                      json={"values": {"timezone": "Mars/Olympus_Mons"}})
    assert resp.status_code == 422
    # The bad value was not persisted.
    body = client.get("/api/v1/system/status", headers=auth_headers).json()
    assert body["timezone"] == "UTC"


def test_timezones_endpoint_lists_common_zones(client, auth_headers):
    resp = client.get("/api/v1/system/timezones", headers=auth_headers)
    assert resp.status_code == 200
    zones = resp.json()["timezones"]
    assert "UTC" in zones
    assert "Europe/Zurich" in zones
    assert zones == sorted(zones)


def test_metrics_snapshot_shape():
    snap = system_metrics.snapshot()
    assert snap["cpu_count"] >= 1
    # On Linux CI these are present; on other platforms they degrade to None.
    for key in ("cpu_percent", "memory", "disk"):
        assert key in snap
    if snap["memory"] is not None:
        assert 0 <= snap["memory"]["percent"] <= 100
        assert snap["memory"]["used"] <= snap["memory"]["total"]
