from app.models import IPAddress, Network
from app.services import assets


def test_asset_crud(client, auth_headers):
    created = client.post("/api/v1/assets", headers=auth_headers, json={
        "name": "web01", "asset_type": "server", "owner": "ops",
        "interfaces": [{"name": "eth0", "mac": "AA-BB-CC-DD-EE-FF", "ip": "10.0.0.5"}],
    })
    assert created.status_code == 201, created.text
    asset_id = created.json()["id"]
    assert created.json()["interfaces"][0]["mac"] == "aa:bb:cc:dd:ee:ff"  # normalized

    listed = client.get("/api/v1/assets", headers=auth_headers)
    assert listed.status_code == 200 and len(listed.json()) == 1

    patched = client.patch(f"/api/v1/assets/{asset_id}", headers=auth_headers,
                           json={"status": "retired"})
    assert patched.status_code == 200 and patched.json()["status"] == "retired"

    assert client.delete(f"/api/v1/assets/{asset_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/assets/{asset_id}", headers=auth_headers).status_code == 404


def test_asset_invalid_enum_rejected(client, auth_headers):
    resp = client.post("/api/v1/assets", headers=auth_headers,
                       json={"name": "x", "asset_type": "spaceship"})
    assert resp.status_code == 422


def test_interface_links_to_ipam(client, db_session, auth_headers):
    net = Network(cidr="10.0.0.0/24", name="lan")
    db_session.add(net)
    db_session.flush()
    ip = IPAddress(network_id=net.id, ip="10.0.0.5")
    db_session.add(ip)
    db_session.commit()

    created = client.post("/api/v1/assets", headers=auth_headers, json={
        "name": "host", "interfaces": [{"ip": "10.0.0.5"}],
    })
    assert created.status_code == 201
    assert created.json()["interfaces"][0]["ip_id"] == ip.id


def test_sync_from_ipam_creates_assets(db_session):
    net = Network(cidr="10.0.0.0/24")
    db_session.add(net)
    db_session.flush()
    db_session.add(IPAddress(network_id=net.id, ip="10.0.0.9", mac="11:22:33:44:55:66",
                             hostname="printer"))
    db_session.commit()
    result = assets.sync_from_ipam(db_session, "tester")
    assert result["created"] == 1
    # Re-running is idempotent (matched by MAC, no duplicate).
    again = assets.sync_from_ipam(db_session, "tester")
    assert again["created"] == 0
