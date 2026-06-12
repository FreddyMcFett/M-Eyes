import base64


def create_feed(client, headers, slug="nets", kind="networks", **kwargs):
    response = client.post("/api/v1/feeds",
                           json={"slug": slug, "name": slug, "kind": kind, **kwargs},
                           headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def basic_auth(token):
    return {"Authorization": "Basic " + base64.b64encode(f"feed:{token}".encode()).decode()}


def test_networks_feed_with_query_token(client, auth_headers):
    client.post("/api/v1/networks", json={"cidr": "10.80.0.0/24"}, headers=auth_headers)
    client.post("/api/v1/networks", json={"cidr": "10.0.0.0/8", "is_container": True},
                headers=auth_headers)
    feed = create_feed(client, auth_headers)
    response = client.get(f"/feeds/nets.txt?token={feed['token']}")
    assert response.status_code == 200
    lines = response.text.strip().splitlines()
    assert "10.80.0.0/24" in lines
    assert "10.0.0.0/8" not in lines  # containers excluded
    assert response.headers["cache-control"] == "max-age=60"


def test_feed_basic_auth(client, auth_headers):
    feed = create_feed(client, auth_headers, slug="basic")
    response = client.get("/feeds/basic.txt", headers=basic_auth(feed["token"]))
    assert response.status_code == 200


def test_feed_auth_failures(client, auth_headers):
    create_feed(client, auth_headers, slug="locked")
    assert client.get("/feeds/locked.txt").status_code == 401
    assert client.get("/feeds/locked.txt?token=wrong").status_code == 401
    assert client.get("/feeds/locked.txt", headers=basic_auth("wrong")).status_code == 401
    assert client.get("/feeds/missing.txt?token=x").status_code == 404


def test_disabled_feed_404(client, auth_headers):
    feed = create_feed(client, auth_headers, slug="off")
    client.patch(f"/api/v1/feeds/{feed['id']}", json={"enabled": False}, headers=auth_headers)
    assert client.get(f"/feeds/off.txt?token={feed['token']}").status_code == 404


def test_blocklist_feed(client, auth_headers):
    client.post("/api/v1/blocklist", json={"value": "203.0.113.7", "reason": "c2"},
                headers=auth_headers)
    client.post("/api/v1/blocklist", json={"value": "198.51.100.0/24", "reason": "scanning"},
                headers=auth_headers)
    feed = create_feed(client, auth_headers, slug="block", kind="blocklist")
    response = client.get(f"/feeds/block.txt?token={feed['token']}")
    lines = response.text.strip().splitlines()
    assert "203.0.113.7" in lines and "198.51.100.0/24" in lines


def test_fqdn_feed(client, auth_headers):
    zone = client.post("/api/v1/zones", json={"name": "feed.example"}, headers=auth_headers).json()
    client.post(f"/api/v1/zones/{zone['id']}/records",
                json={"name": "www", "type": "A", "value": "192.0.2.1"}, headers=auth_headers)
    feed = create_feed(client, auth_headers, slug="domains", kind="fqdn")
    response = client.get(f"/feeds/domains.txt?token={feed['token']}")
    assert "www.feed.example" in response.text.splitlines()


def test_tag_feed(client, auth_headers):
    tag = client.post("/api/v1/tags", json={"name": "fortinet-sync"}, headers=auth_headers).json()
    client.post("/api/v1/networks", json={"cidr": "10.81.0.0/24", "tag_ids": [tag["id"]]},
                headers=auth_headers)
    client.post("/api/v1/networks", json={"cidr": "10.82.0.0/24"}, headers=auth_headers)
    feed = create_feed(client, auth_headers, slug="tagged", kind="tag", tag_id=tag["id"])

    response = client.get(f"/feeds/tagged.txt?token={feed['token']}")
    lines = response.text.strip().splitlines()
    assert lines == ["10.81.0.0/24"]

    # the /feeds/tag/{name}.txt alias resolves the same feed
    alias = client.get(f"/feeds/tag/fortinet-sync.txt?token={feed['token']}")
    assert alias.text == response.text


def test_json_variant_carries_version(client, auth_headers):
    client.post("/api/v1/networks", json={"cidr": "10.83.0.0/24"}, headers=auth_headers)
    feed = create_feed(client, auth_headers, slug="jsonfeed")
    body = client.get(f"/feeds/jsonfeed.json?token={feed['token']}").json()
    assert body["feed"] == "jsonfeed"
    assert body["version"] > 0
    assert "10.83.0.0/24" in body["entries"]


def test_token_regeneration_invalidates_old(client, auth_headers):
    feed = create_feed(client, auth_headers, slug="rotate")
    old_token = feed["token"]
    rotated = client.post(f"/api/v1/feeds/{feed['id']}/regenerate-token",
                          headers=auth_headers).json()
    assert rotated["token"] != old_token
    assert client.get(f"/feeds/rotate.txt?token={old_token}").status_code == 401
    assert client.get(f"/feeds/rotate.txt?token={rotated['token']}").status_code == 200


def test_fortigate_snippet_present(client, auth_headers):
    feed = create_feed(client, auth_headers, slug="snippet")
    assert "config system external-resource" in feed["fortigate_snippet"]
    assert feed["token"] in feed["fortigate_snippet"]
