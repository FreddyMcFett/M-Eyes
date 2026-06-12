from unittest.mock import MagicMock, patch

from app.services import events as events_service


def test_events_emitted_for_actions(client, auth_headers):
    client.post("/api/v1/networks", json={"cidr": "10.95.0.0/24"}, headers=auth_headers)
    rows = client.get("/api/v1/events", headers=auth_headers).json()
    assert any(e["category"] == "ipam" and "10.95.0.0/24" in e["message"] for e in rows)
    assert any(e["category"] == "auth" for e in rows)  # the login itself


def test_event_filters(client, auth_headers):
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "nope"})
    warnings = client.get("/api/v1/events?severity=warning&category=auth",
                          headers=auth_headers).json()
    assert warnings and all(e["severity"] == "warning" for e in warnings)


def test_settings_roundtrip(client, auth_headers):
    response = client.put(
        "/api/v1/system/settings",
        json={"values": {"syslog_enabled": "true", "syslog_host": "192.0.2.99",
                         "debug_mode": "true", "bogus_key": "ignored"}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    values = response.json()["values"]
    assert values["syslog_enabled"] == "true"
    assert values["syslog_host"] == "192.0.2.99"
    assert "bogus_key" not in values


def test_syslog_forwarding_invoked_when_enabled(client, auth_headers, db_session):
    client.put("/api/v1/system/settings",
               json={"values": {"syslog_enabled": "true", "syslog_host": "192.0.2.50",
                                "syslog_port": "514", "syslog_protocol": "udp"}},
               headers=auth_headers)
    fake_logger = MagicMock()
    with patch.object(events_service, "_build_syslog_logger", return_value=fake_logger):
        events_service.reset_syslog()
        events_service.emit(db_session, "error", "system", "syslog test")
        db_session.commit()
    assert fake_logger.log.called
    args = fake_logger.log.call_args[0]
    assert "syslog test" in args[2:]
    events_service.reset_syslog()


def test_syslog_not_invoked_when_disabled(client, auth_headers, db_session):
    client.put("/api/v1/system/settings", json={"values": {"syslog_enabled": "false"}},
               headers=auth_headers)
    with patch.object(events_service, "_build_syslog_logger") as builder:
        events_service.reset_syslog()
        events_service.emit(db_session, "error", "system", "no syslog")
        db_session.commit()
    assert not builder.called


def test_syslog_min_severity_filter(client, auth_headers, db_session):
    client.put("/api/v1/system/settings",
               json={"values": {"syslog_enabled": "true", "syslog_host": "192.0.2.50",
                                "syslog_min_severity": "error"}},
               headers=auth_headers)
    fake_logger = MagicMock()
    with patch.object(events_service, "_build_syslog_logger", return_value=fake_logger):
        events_service.reset_syslog()
        events_service.emit(db_session, "info", "system", "below threshold")
        db_session.commit()
    assert not fake_logger.log.called
    events_service.reset_syslog()


def test_diagnostics_endpoint(client, auth_headers):
    response = client.get("/api/v1/system/diagnostics", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["version"]
    assert "db_stats" in body and "last_deployments" in body


def test_syslog_test_endpoint(client, auth_headers):
    response = client.post("/api/v1/system/syslog-test", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] in ("sent", "logged-only")
