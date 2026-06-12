def setup_env(client, headers):
    network = client.post("/api/v1/networks", json={"cidr": "10.50.0.0/24"}, headers=headers).json()
    client.post("/api/v1/zones", json={"name": "corp.example", "kind": "forward"}, headers=headers)
    client.post("/api/v1/zones", json={"name": "0.50.10.in-addr.arpa", "kind": "reverse"},
                headers=headers)
    subnet = client.post("/api/v1/dhcp/subnets", json={"network_id": network["id"]},
                         headers=headers).json()
    return network, subnet


def test_host_composite_create(client, auth_headers):
    network, _ = setup_env(client, auth_headers)
    response = client.post(
        "/api/v1/hosts",
        json={"name": "srv1.corp.example", "network_id": network["id"],
              "mac": "00:11:22:33:44:55", "create_reservation": True},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    host = response.json()
    assert host["ip"] == "10.50.0.1"  # auto-allocated
    assert host["ip_address_id"] and host["a_record_id"] and host["ptr_record_id"]
    assert host["reservation_id"]

    # A record in the forward zone
    zones = {z["name"]: z for z in client.get("/api/v1/zones", headers=auth_headers).json()}
    records = client.get(f"/api/v1/zones/{zones['corp.example']['id']}/records",
                         headers=auth_headers).json()
    a = [r for r in records if r["type"] == "A" and r["name"] == "srv1"]
    assert a and a[0]["value"] == "10.50.0.1"

    # PTR in the reverse zone
    ptr_records = client.get(f"/api/v1/zones/{zones['0.50.10.in-addr.arpa']['id']}/records",
                             headers=auth_headers).json()
    ptrs = [r for r in ptr_records if r["type"] == "PTR"]
    assert ptrs and ptrs[0]["value"] == "srv1.corp.example."

    # changelog has entries for every touched object type
    changes = client.get("/api/v1/changelog?limit=50", headers=auth_headers).json()
    touched = {c["object_type"] for c in changes}
    assert {"host", "ip_address", "record", "dhcp_reservation"} <= touched


def test_host_requires_forward_zone(client, auth_headers):
    network = client.post("/api/v1/networks", json={"cidr": "10.60.0.0/24"},
                          headers=auth_headers).json()
    response = client.post("/api/v1/hosts",
                           json={"name": "x.nozone.example", "network_id": network["id"]},
                           headers=auth_headers)
    assert response.status_code == 422


def test_host_delete_reverses_everything(client, auth_headers):
    network, _ = setup_env(client, auth_headers)
    host = client.post(
        "/api/v1/hosts",
        json={"name": "srv2.corp.example", "network_id": network["id"],
              "mac": "00:11:22:33:44:66", "create_reservation": True},
        headers=auth_headers,
    ).json()

    response = client.delete(f"/api/v1/hosts/{host['id']}", headers=auth_headers)
    assert response.status_code == 204

    assert client.get("/api/v1/hosts", headers=auth_headers).json() == []
    addresses = client.get(f"/api/v1/networks/{network['id']}/addresses",
                           headers=auth_headers).json()
    assert addresses == []
    zones = {z["name"]: z for z in client.get("/api/v1/zones", headers=auth_headers).json()}
    records = client.get(f"/api/v1/zones/{zones['corp.example']['id']}/records",
                         headers=auth_headers).json()
    assert not any(r["name"] == "srv2" for r in records)
    subnets = client.get("/api/v1/dhcp/subnets", headers=auth_headers).json()
    assert subnets[0]["reservations"] == []


def test_duplicate_host_rejected(client, auth_headers):
    network, _ = setup_env(client, auth_headers)
    payload = {"name": "dup.corp.example", "network_id": network["id"]}
    assert client.post("/api/v1/hosts", json=payload, headers=auth_headers).status_code == 201
    assert client.post("/api/v1/hosts", json=payload, headers=auth_headers).status_code == 409
