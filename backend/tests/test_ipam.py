def make_network(client, headers, cidr, **kwargs):
    response = client.post("/api/v1/networks", json={"cidr": cidr, **kwargs}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_network_and_hierarchy(client, auth_headers):
    container = make_network(client, auth_headers, "10.0.0.0/8", name="corp", is_container=True)
    subnet = make_network(client, auth_headers, "10.1.0.0/24", name="office")
    assert subnet["parent_id"] == container["id"]

    # a /16 inserted between them re-parents the /24
    middle = make_network(client, auth_headers, "10.1.0.0/16", is_container=True)
    networks = {n["cidr"]: n for n in client.get("/api/v1/networks", headers=auth_headers).json()}
    assert networks["10.1.0.0/24"]["parent_id"] == middle["id"]
    assert networks["10.1.0.0/16"]["parent_id"] == container["id"]


def test_duplicate_cidr_rejected(client, auth_headers):
    make_network(client, auth_headers, "192.168.1.0/24")
    response = client.post("/api/v1/networks", json={"cidr": "192.168.1.0/24"}, headers=auth_headers)
    assert response.status_code == 409


def test_invalid_cidr_rejected(client, auth_headers):
    response = client.post("/api/v1/networks", json={"cidr": "not-a-cidr"}, headers=auth_headers)
    assert response.status_code == 422


def test_next_ip_skips_network_broadcast_and_used(client, auth_headers):
    network = make_network(client, auth_headers, "192.168.5.0/30")
    # /30: hosts are .1 and .2
    response = client.get(f"/api/v1/networks/{network['id']}/next-ip", headers=auth_headers)
    assert response.json()["ip"] == "192.168.5.1"

    client.post(f"/api/v1/networks/{network['id']}/addresses",
                json={"ip": "192.168.5.1"}, headers=auth_headers)
    response = client.get(f"/api/v1/networks/{network['id']}/next-ip", headers=auth_headers)
    assert response.json()["ip"] == "192.168.5.2"

    client.post(f"/api/v1/networks/{network['id']}/addresses",
                json={"ip": "192.168.5.2"}, headers=auth_headers)
    response = client.get(f"/api/v1/networks/{network['id']}/next-ip", headers=auth_headers)
    assert response.status_code == 409  # exhausted


def test_next_ip_skips_dhcp_range(client, auth_headers):
    network = make_network(client, auth_headers, "10.9.0.0/24")
    subnet = client.post("/api/v1/dhcp/subnets", json={"network_id": network["id"]},
                         headers=auth_headers).json()
    client.post(f"/api/v1/dhcp/subnets/{subnet['id']}/ranges",
                json={"start_ip": "10.9.0.1", "end_ip": "10.9.0.100"}, headers=auth_headers)
    response = client.get(f"/api/v1/networks/{network['id']}/next-ip", headers=auth_headers)
    assert response.json()["ip"] == "10.9.0.101"


def test_next_ip_refuses_huge_network(client, auth_headers):
    network = make_network(client, auth_headers, "10.0.0.0/8")
    response = client.get(f"/api/v1/networks/{network['id']}/next-ip", headers=auth_headers)
    assert response.status_code == 422


def test_utilization(client, auth_headers):
    network = make_network(client, auth_headers, "172.16.0.0/24")
    client.post(f"/api/v1/networks/{network['id']}/addresses", json={}, headers=auth_headers)
    client.post(f"/api/v1/networks/{network['id']}/addresses", json={}, headers=auth_headers)
    detail = client.get(f"/api/v1/networks/{network['id']}", headers=auth_headers).json()
    util = detail["utilization"]
    assert util["total"] == 254
    assert util["used"] == 2
    assert util["free"] == 252


def test_address_outside_network_rejected(client, auth_headers):
    network = make_network(client, auth_headers, "172.20.0.0/24")
    response = client.post(f"/api/v1/networks/{network['id']}/addresses",
                           json={"ip": "10.0.0.1"}, headers=auth_headers)
    assert response.status_code == 422
