def _setup_config(client, auth_headers):
    network = client.post("/api/v1/networks",
                          json={"cidr": "10.50.0.0/24", "name": "backup-net"},
                          headers=auth_headers).json()
    client.post(f"/api/v1/networks/{network['id']}/addresses",
                json={"ip": "10.50.0.10", "hostname": "srv1"}, headers=auth_headers)
    zone = client.post("/api/v1/zones", json={"name": "backup.example.com"},
                       headers=auth_headers).json()
    client.post(f"/api/v1/zones/{zone['id']}/records",
                json={"name": "www", "type": "A", "value": "10.50.0.10"}, headers=auth_headers)
    client.post("/api/v1/rpz/rules", json={"fqdn": "evil.example.com"}, headers=auth_headers)
    return network, zone


def test_backup_roundtrip(client, auth_headers):
    network, zone = _setup_config(client, auth_headers)

    response = client.get("/api/v1/system/backup", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "m-eyes-backup"
    assert any(row["cidr"] == "10.50.0.0/24" for row in data["tables"]["networks"])
    assert any(row["name"] == "backup.example.com" for row in data["tables"]["zones"])
    assert "users" not in data["tables"]
    assert "certificates" not in data["tables"]

    # mutate the config after the backup
    client.delete(f"/api/v1/zones/{zone['id']}", headers=auth_headers)
    client.post("/api/v1/networks", json={"cidr": "172.16.0.0/24"}, headers=auth_headers)

    response = client.post("/api/v1/system/restore", json=data, headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "restored"

    zones = client.get("/api/v1/zones", headers=auth_headers).json()
    assert [z["name"] for z in zones] == ["backup.example.com"]
    restored_zone = zones[0]
    assert restored_zone["id"] == zone["id"]  # primary keys preserved
    assert restored_zone["record_count"] == 2  # apex NS + www A

    networks = client.get("/api/v1/networks", headers=auth_headers).json()
    assert [n["cidr"] for n in networks] == ["10.50.0.0/24"]

    rules = client.get("/api/v1/rpz/rules", headers=auth_headers).json()
    assert [r["fqdn"] for r in rules] == ["evil.example.com"]

    # login still works: user accounts are untouched by a restore
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert login.status_code == 200


def test_restore_rejects_foreign_files(client, auth_headers):
    response = client.post("/api/v1/system/restore", json={"format": "something-else"},
                           headers=auth_headers)
    assert response.status_code == 422

    response = client.post("/api/v1/system/restore",
                           json={"format": "m-eyes-backup", "format_version": 99, "tables": {}},
                           headers=auth_headers)
    assert response.status_code == 422
    assert "newer" in response.json()["detail"]
