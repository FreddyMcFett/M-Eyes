def _create(client, auth_headers, cidr, **extra):
    response = client.post("/api/v1/networks", json={"cidr": cidr, **extra}, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_next_subnet_skips_existing_children(client, auth_headers):
    container = _create(client, auth_headers, "10.20.0.0/16", is_container=True)
    _create(client, auth_headers, "10.20.0.0/24")
    _create(client, auth_headers, "10.20.1.0/24")

    response = client.get(f"/api/v1/networks/{container['id']}/next-subnet?prefixlen=24",
                          headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["cidr"] == "10.20.2.0/24"


def test_next_subnet_respects_larger_children(client, auth_headers):
    container = _create(client, auth_headers, "10.30.0.0/16", is_container=True)
    _create(client, auth_headers, "10.30.0.0/17")  # occupies the first half

    response = client.get(f"/api/v1/networks/{container['id']}/next-subnet?prefixlen=24",
                          headers=auth_headers)
    assert response.json()["cidr"] == "10.30.128.0/24"


def test_allocate_subnet_creates_child(client, auth_headers):
    container = _create(client, auth_headers, "10.40.0.0/16", is_container=True)

    response = client.post(f"/api/v1/networks/{container['id']}/allocate-subnet",
                           json={"prefixlen": 24, "name": "auto-1"}, headers=auth_headers)
    assert response.status_code == 201, response.text
    first = response.json()
    assert first["cidr"] == "10.40.0.0/24"
    assert first["parent_id"] == container["id"]

    response = client.post(f"/api/v1/networks/{container['id']}/allocate-subnet",
                           json={"prefixlen": 24, "name": "auto-2"}, headers=auth_headers)
    assert response.json()["cidr"] == "10.40.1.0/24"


def test_next_subnet_validation(client, auth_headers):
    container = _create(client, auth_headers, "10.60.0.0/24", is_container=True)

    # prefix must be longer than the container's
    response = client.get(f"/api/v1/networks/{container['id']}/next-subnet?prefixlen=24",
                          headers=auth_headers)
    assert response.status_code == 422

    # /31+ allocations are refused
    response = client.get(f"/api/v1/networks/{container['id']}/next-subnet?prefixlen=31",
                          headers=auth_headers)
    assert response.status_code == 422


def test_next_subnet_exhaustion(client, auth_headers):
    container = _create(client, auth_headers, "10.70.0.0/23", is_container=True)
    _create(client, auth_headers, "10.70.0.0/24")
    _create(client, auth_headers, "10.70.1.0/24")

    response = client.get(f"/api/v1/networks/{container['id']}/next-subnet?prefixlen=24",
                          headers=auth_headers)
    assert response.status_code == 409
