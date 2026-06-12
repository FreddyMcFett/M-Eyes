def test_global_search(client, auth_headers):
    network = client.post("/api/v1/networks", json={"cidr": "10.80.0.0/24", "name": "web tier"},
                          headers=auth_headers).json()
    client.post(f"/api/v1/networks/{network['id']}/addresses",
                json={"ip": "10.80.0.10", "hostname": "web-01"}, headers=auth_headers)
    zone = client.post("/api/v1/zones", json={"name": "web.example.com"},
                       headers=auth_headers).json()
    client.post(f"/api/v1/zones/{zone['id']}/records",
                json={"name": "webmail", "type": "A", "value": "10.80.0.20"},
                headers=auth_headers)
    client.post("/api/v1/rpz/rules", json={"fqdn": "webtrap.example.net", "action": "block"},
                headers=auth_headers)

    response = client.get("/api/v1/search", params={"q": "web"}, headers=auth_headers)
    assert response.status_code == 200, response.text
    results = response.json()["results"]
    types = {entry["type"] for entry in results}
    assert {"network", "ip_address", "zone", "record", "rpz_rule"} <= types
    by_type = {entry["type"]: entry for entry in results}
    assert by_type["network"]["url"] == f"/ipam/{network['id']}"
    assert by_type["zone"]["url"] == f"/dns/{zone['id']}"

    # short terms are rejected
    assert client.get("/api/v1/search", params={"q": "w"},
                      headers=auth_headers).status_code == 422


def test_search_requires_auth(client):
    assert client.get("/api/v1/search", params={"q": "web"}).status_code == 401
