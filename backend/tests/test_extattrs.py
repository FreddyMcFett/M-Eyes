def _create_network(client, headers, cidr="10.50.0.0/24"):
    response = client.post("/api/v1/networks", json={"cidr": cidr, "name": "test"},
                           headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_def_crud_and_validation(client, auth_headers):
    response = client.post("/api/v1/extattr-defs",
                           json={"name": "Owner", "type": "string", "comment": "team"},
                           headers=auth_headers)
    assert response.status_code == 201, response.text
    def_id = response.json()["id"]

    # duplicate name
    response = client.post("/api/v1/extattr-defs", json={"name": "Owner"}, headers=auth_headers)
    assert response.status_code == 409

    # enum requires allowed_values
    response = client.post("/api/v1/extattr-defs", json={"name": "Env", "type": "enum"},
                           headers=auth_headers)
    assert response.status_code == 422

    # bad type
    response = client.post("/api/v1/extattr-defs", json={"name": "X", "type": "float"},
                           headers=auth_headers)
    assert response.status_code == 422

    response = client.patch(f"/api/v1/extattr-defs/{def_id}", json={"comment": "updated"},
                            headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["comment"] == "updated"

    response = client.delete(f"/api/v1/extattr-defs/{def_id}", headers=auth_headers)
    assert response.status_code == 204
    assert client.get("/api/v1/extattr-defs", headers=auth_headers).json() == []


def test_set_and_get_values(client, auth_headers):
    network = _create_network(client, auth_headers)
    for payload in ({"name": "Owner", "type": "string"},
                    {"name": "Environment", "type": "enum",
                     "allowed_values": ["prod", "dev"]},
                    {"name": "Capacity", "type": "integer"}):
        assert client.post("/api/v1/extattr-defs", json=payload,
                           headers=auth_headers).status_code == 201

    url = f"/api/v1/extattrs/network/{network['id']}"
    response = client.put(url, json={"values": {"Owner": "netops", "Environment": "prod"}},
                          headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["values"] == {"Owner": "netops", "Environment": "prod"}

    # typed validation
    assert client.put(url, json={"values": {"Environment": "qa"}},
                      headers=auth_headers).status_code == 422
    assert client.put(url, json={"values": {"Capacity": "not-a-number"}},
                      headers=auth_headers).status_code == 422
    assert client.put(url, json={"values": {"Unknown": "x"}},
                      headers=auth_headers).status_code == 422

    # full-replace semantics: Environment disappears
    response = client.put(url, json={"values": {"Owner": "security"}}, headers=auth_headers)
    assert response.json()["values"] == {"Owner": "security"}
    assert client.get(url, headers=auth_headers).json()["values"] == {"Owner": "security"}

    # usage counting
    defs = {d["name"]: d for d in client.get("/api/v1/extattr-defs", headers=auth_headers).json()}
    assert defs["Owner"]["usage_count"] == 1
    assert defs["Environment"]["usage_count"] == 0


def test_values_purged_with_object(client, auth_headers):
    network = _create_network(client, auth_headers, cidr="10.51.0.0/24")
    assert client.post("/api/v1/extattr-defs", json={"name": "Owner"},
                       headers=auth_headers).status_code == 201
    url = f"/api/v1/extattrs/network/{network['id']}"
    client.put(url, json={"values": {"Owner": "netops"}}, headers=auth_headers)

    assert client.delete(f"/api/v1/networks/{network['id']}",
                         headers=auth_headers).status_code == 204
    assert client.get(url, headers=auth_headers).status_code == 404
    defs = client.get("/api/v1/extattr-defs", headers=auth_headers).json()
    assert defs[0]["usage_count"] == 0


def test_bad_object_type_and_missing_object(client, auth_headers):
    assert client.get("/api/v1/extattrs/spaceship/1", headers=auth_headers).status_code == 422
    assert client.get("/api/v1/extattrs/network/999", headers=auth_headers).status_code == 404
