from app.generators.named_conf import render_zones_conf
from app.services.deploy import bind as bind_deploy


def _create_zone(client, auth_headers, **payload):
    return client.post("/api/v1/zones", json=payload, headers=auth_headers)


def test_secondary_zone_requires_primaries(client, auth_headers):
    response = _create_zone(client, auth_headers, name="ext.example.com", role="secondary")
    assert response.status_code == 422
    assert "at least one IP" in response.json()["detail"]


def test_secondary_zone_rejects_invalid_ip(client, auth_headers):
    response = _create_zone(client, auth_headers, name="ext.example.com", role="secondary",
                            primaries="not-an-ip")
    assert response.status_code == 422


def test_unknown_role_rejected(client, auth_headers):
    response = _create_zone(client, auth_headers, name="x.example.com", role="hidden")
    assert response.status_code == 422


def test_secondary_zone_rendered_as_slave(client, auth_headers, db_session):
    response = _create_zone(client, auth_headers, name="ext.example.com", role="secondary",
                            primaries="192.0.2.10, 192.0.2.11")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "secondary"
    assert body["primaries"] == "192.0.2.10,192.0.2.11"
    assert body["record_count"] == 0  # no auto NS record on non-primary zones

    conf = render_zones_conf(db_session)
    assert "type slave;" in conf
    assert "masters { 192.0.2.10; 192.0.2.11; };" in conf


def test_forward_zone_rendered_as_forwarder(client, auth_headers, db_session):
    response = _create_zone(client, auth_headers, name="corp.partner.com", role="forward",
                            primaries="198.51.100.1")
    assert response.status_code == 201, response.text

    conf = render_zones_conf(db_session)
    assert "type forward;" in conf
    assert "forwarders { 198.51.100.1; };" in conf
    assert 'file' not in [line.strip().split()[0] for line in conf.splitlines()
                          if "corp.partner.com" in line]


def test_records_rejected_on_non_primary_zone(client, auth_headers):
    zone = _create_zone(client, auth_headers, name="ext2.example.com", role="secondary",
                        primaries="192.0.2.20").json()
    response = client.post(f"/api/v1/zones/{zone['id']}/records",
                           json={"name": "www", "type": "A", "value": "10.0.0.1"},
                           headers=auth_headers)
    assert response.status_code == 422
    assert "primary zones" in response.json()["detail"]


def test_non_primary_zones_have_no_zone_file(client, auth_headers, db_session):
    _create_zone(client, auth_headers, name="zone1.example.com")  # primary
    secondary = _create_zone(client, auth_headers, name="zone2.example.com", role="secondary",
                             primaries="192.0.2.30").json()

    preview = bind_deploy.preview(db_session)
    assert "db.zone1.example.com" in preview["zone_files"]
    assert "db.zone2.example.com" not in preview["zone_files"]
    assert "zone2.example.com" in preview["zones_conf"]

    response = client.get(f"/api/v1/zones/{secondary['id']}/file", headers=auth_headers)
    assert response.status_code == 200
    assert "no local zone file" in response.json()["content"]


def test_role_change_to_primary_clears_primaries(client, auth_headers):
    zone = _create_zone(client, auth_headers, name="flip.example.com", role="forward",
                        primaries="203.0.113.1").json()
    response = client.patch(f"/api/v1/zones/{zone['id']}", json={"role": "primary"},
                            headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "primary"
    assert body["primaries"] == ""
