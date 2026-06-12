import json


def setup_scope(client, headers, cidr="10.20.0.0/24"):
    network = client.post("/api/v1/networks", json={"cidr": cidr}, headers=headers).json()
    subnet = client.post("/api/v1/dhcp/subnets", json={"network_id": network["id"]},
                         headers=headers).json()
    return network, subnet


def test_subnet_requires_network(client, auth_headers):
    response = client.post("/api/v1/dhcp/subnets", json={"network_id": 9999}, headers=auth_headers)
    assert response.status_code == 404


def test_no_dhcp_on_container(client, auth_headers):
    network = client.post("/api/v1/networks",
                          json={"cidr": "10.30.0.0/16", "is_container": True},
                          headers=auth_headers).json()
    response = client.post("/api/v1/dhcp/subnets", json={"network_id": network["id"]},
                           headers=auth_headers)
    assert response.status_code == 422


def test_reservation_creates_ipam_entry(client, auth_headers):
    network, subnet = setup_scope(client, auth_headers)
    response = client.post(
        f"/api/v1/dhcp/subnets/{subnet['id']}/reservations",
        json={"mac": "AA:BB:CC:DD:EE:FF", "ip": "10.20.0.50", "hostname": "printer"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["mac"] == "aa:bb:cc:dd:ee:ff"  # normalized
    addresses = client.get(f"/api/v1/networks/{network['id']}/addresses",
                           headers=auth_headers).json()
    reserved = [a for a in addresses if a["ip"] == "10.20.0.50"]
    assert len(reserved) == 1
    assert reserved[0]["status"] == "reserved"


def test_invalid_mac_rejected(client, auth_headers):
    _, subnet = setup_scope(client, auth_headers, "10.21.0.0/24")
    response = client.post(f"/api/v1/dhcp/subnets/{subnet['id']}/reservations",
                           json={"mac": "nope", "ip": "10.21.0.5"}, headers=auth_headers)
    assert response.status_code == 422


def test_range_must_be_inside_network(client, auth_headers):
    _, subnet = setup_scope(client, auth_headers, "10.22.0.0/24")
    response = client.post(f"/api/v1/dhcp/subnets/{subnet['id']}/ranges",
                           json={"start_ip": "10.99.0.1", "end_ip": "10.99.0.50"},
                           headers=auth_headers)
    assert response.status_code == 422


def test_kea_config_generation(client, auth_headers):
    _, subnet = setup_scope(client, auth_headers, "10.23.0.0/24")
    client.post(f"/api/v1/dhcp/subnets/{subnet['id']}/ranges",
                json={"start_ip": "10.23.0.100", "end_ip": "10.23.0.200"}, headers=auth_headers)
    client.post(f"/api/v1/dhcp/subnets/{subnet['id']}/reservations",
                json={"mac": "11:22:33:44:55:66", "ip": "10.23.0.10", "hostname": "nas"},
                headers=auth_headers)
    client.post(f"/api/v1/dhcp/subnets/{subnet['id']}/options",
                json={"name": "routers", "value": "10.23.0.1"}, headers=auth_headers)
    client.post("/api/v1/dhcp/options",
                json={"name": "domain-name-servers", "value": "10.23.0.2"}, headers=auth_headers)

    preview = client.get("/api/v1/deploy/kea/preview", headers=auth_headers).json()
    config = json.loads(preview["kea_dhcp4_conf"])  # must be valid pure JSON
    dhcp4 = config["Dhcp4"]
    assert dhcp4["option-data"] == [{"name": "domain-name-servers", "data": "10.23.0.2"}]
    subnets = [s for s in dhcp4["subnet4"] if s["subnet"] == "10.23.0.0/24"]
    assert len(subnets) == 1
    entry = subnets[0]
    assert entry["pools"] == [{"pool": "10.23.0.100 - 10.23.0.200"}]
    assert entry["reservations"] == [
        {"hw-address": "11:22:33:44:55:66", "ip-address": "10.23.0.10", "hostname": "nas"}
    ]
    assert entry["option-data"] == [{"name": "routers", "data": "10.23.0.1"}]
