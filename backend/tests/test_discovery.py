from app.services import discovery


def _network(client, headers, cidr="10.90.0.0/29"):
    response = client.post("/api/v1/networks", json={"cidr": cidr, "name": "lab"},
                           headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_discover_records_alive_hosts(client, auth_headers, monkeypatch):
    network = _network(client, auth_headers)
    # pre-existing allocations: one used, one reserved (will conflict)
    client.post(f"/api/v1/networks/{network['id']}/addresses",
                json={"ip": "10.90.0.1", "hostname": "gw", "status": "used"},
                headers=auth_headers)
    client.post(f"/api/v1/networks/{network['id']}/addresses",
                json={"ip": "10.90.0.2", "status": "reserved"}, headers=auth_headers)

    alive = {"10.90.0.1", "10.90.0.2", "10.90.0.5"}
    monkeypatch.setattr(discovery, "_ping", lambda ip: ip in alive)

    response = client.post(f"/api/v1/networks/{network['id']}/discover", headers=auth_headers)
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary == {"cidr": "10.90.0.0/29", "scanned": 6, "alive": 3,
                       "created": 1, "updated": 2, "conflicts": 1}

    addresses = {a["ip"]: a for a in client.get(
        f"/api/v1/networks/{network['id']}/addresses", headers=auth_headers).json()}
    assert addresses["10.90.0.5"]["status"] == "discovered"
    assert addresses["10.90.0.1"]["status"] == "used"  # untouched


def test_discover_refuses_large_networks(client, auth_headers, monkeypatch):
    monkeypatch.setattr(discovery, "_ping", lambda ip: False)
    network = _network(client, auth_headers, cidr="10.0.0.0/8")
    response = client.post(f"/api/v1/networks/{network['id']}/discover", headers=auth_headers)
    assert response.status_code == 422
    assert "too large" in response.json()["detail"]
