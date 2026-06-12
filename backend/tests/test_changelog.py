def test_changelog_records_crud_cycle(client, auth_headers):
    network = client.post("/api/v1/networks", json={"cidr": "10.70.0.0/24", "name": "v1"},
                          headers=auth_headers).json()
    client.patch(f"/api/v1/networks/{network['id']}", json={"name": "v2"}, headers=auth_headers)
    client.delete(f"/api/v1/networks/{network['id']}", headers=auth_headers)

    changes = client.get("/api/v1/changelog?object_type=network", headers=auth_headers).json()
    assert [c["action"] for c in changes] == ["delete", "update", "create"]

    create, update, delete = changes[2], changes[1], changes[0]
    assert create["before"] is None and create["after"]["name"] == "v1"
    assert update["before"]["name"] == "v1" and update["after"]["name"] == "v2"
    assert delete["before"]["name"] == "v2" and delete["after"] is None
    assert create["actor"] == "admin"


def test_config_version_increments(client, auth_headers):
    v0 = client.get("/api/v1/changelog/version", headers=auth_headers).json()["config_version"]
    client.post("/api/v1/networks", json={"cidr": "10.71.0.0/24"}, headers=auth_headers)
    v1 = client.get("/api/v1/changelog/version", headers=auth_headers).json()["config_version"]
    assert v1 > v0


def test_rollback_update(client, auth_headers):
    network = client.post("/api/v1/networks", json={"cidr": "10.72.0.0/24", "name": "before"},
                          headers=auth_headers).json()
    client.patch(f"/api/v1/networks/{network['id']}", json={"name": "after"}, headers=auth_headers)
    update_entry = client.get("/api/v1/changelog?object_type=network",
                              headers=auth_headers).json()[0]
    assert update_entry["action"] == "update"

    response = client.post(f"/api/v1/changelog/{update_entry['id']}/rollback", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["action"] == "rollback"
    assert response.json()["after"]["_rollback_of"] == update_entry["id"]

    current = client.get(f"/api/v1/networks/{network['id']}", headers=auth_headers).json()
    assert current["name"] == "before"


def test_rollback_delete_restores_object(client, auth_headers):
    network = client.post("/api/v1/networks", json={"cidr": "10.73.0.0/24", "name": "phoenix"},
                          headers=auth_headers).json()
    client.delete(f"/api/v1/networks/{network['id']}", headers=auth_headers)
    delete_entry = client.get("/api/v1/changelog?object_type=network",
                              headers=auth_headers).json()[0]
    assert delete_entry["action"] == "delete"

    response = client.post(f"/api/v1/changelog/{delete_entry['id']}/rollback", headers=auth_headers)
    assert response.status_code == 200
    networks = client.get("/api/v1/networks", headers=auth_headers).json()
    restored = [n for n in networks if n["cidr"] == "10.73.0.0/24"]
    assert restored and restored[0]["name"] == "phoenix"


def test_rollback_create_deletes_object(client, auth_headers):
    network = client.post("/api/v1/networks", json={"cidr": "10.74.0.0/24"},
                          headers=auth_headers).json()
    create_entry = client.get("/api/v1/changelog?object_type=network",
                              headers=auth_headers).json()[0]
    assert create_entry["action"] == "create"

    response = client.post(f"/api/v1/changelog/{create_entry['id']}/rollback", headers=auth_headers)
    assert response.status_code == 200
    networks = client.get("/api/v1/networks", headers=auth_headers).json()
    assert not any(n["id"] == network["id"] for n in networks)


def test_runbook_reflects_config(client, auth_headers):
    client.post("/api/v1/networks", json={"cidr": "10.75.0.0/24", "name": "runbook-net"},
                headers=auth_headers)
    client.post("/api/v1/zones", json={"name": "runbook.example"}, headers=auth_headers)
    response = client.get("/api/v1/runbook", headers=auth_headers).json()
    assert "10.75.0.0/24" in response["markdown"]
    assert "runbook.example" in response["markdown"]
    assert response["config_version"] > 0
