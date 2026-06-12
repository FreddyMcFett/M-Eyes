def make_zone(client, headers, name, kind="forward", **kwargs):
    response = client.post("/api/v1/zones", json={"name": name, "kind": kind, **kwargs},
                           headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def add_record(client, headers, zone_id, **record):
    response = client.post(f"/api/v1/zones/{zone_id}/records", json=record, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_zone_create_with_apex_ns(client, auth_headers):
    zone = make_zone(client, auth_headers, "example.com")
    records = client.get(f"/api/v1/zones/{zone['id']}/records", headers=auth_headers).json()
    assert any(r["type"] == "NS" and r["name"] == "@" for r in records)


def test_serial_bumps_on_record_change(client, auth_headers):
    zone = make_zone(client, auth_headers, "serial.test")
    initial = client.get(f"/api/v1/zones/{zone['id']}", headers=auth_headers).json()["serial"]
    add_record(client, auth_headers, zone["id"], name="www", type="A", value="192.0.2.1")
    after = client.get(f"/api/v1/zones/{zone['id']}", headers=auth_headers).json()["serial"]
    assert after == initial + 1


def test_record_validation(client, auth_headers):
    zone = make_zone(client, auth_headers, "valid.test")
    bad_a = client.post(f"/api/v1/zones/{zone['id']}/records",
                        json={"name": "x", "type": "A", "value": "not-an-ip"}, headers=auth_headers)
    assert bad_a.status_code == 422
    bad_type = client.post(f"/api/v1/zones/{zone['id']}/records",
                           json={"name": "x", "type": "BOGUS", "value": "y"}, headers=auth_headers)
    assert bad_type.status_code == 422


def test_duplicate_record_rejected(client, auth_headers):
    zone = make_zone(client, auth_headers, "dup.test")
    add_record(client, auth_headers, zone["id"], name="www", type="A", value="192.0.2.1")
    response = client.post(f"/api/v1/zones/{zone['id']}/records",
                           json={"name": "www", "type": "A", "value": "192.0.2.1"},
                           headers=auth_headers)
    assert response.status_code == 409


def test_auto_ptr(client, auth_headers):
    client.post("/api/v1/networks", json={"cidr": "192.0.2.0/24"}, headers=auth_headers)
    reverse = make_zone(client, auth_headers, "2.0.192.in-addr.arpa", kind="reverse")
    forward = make_zone(client, auth_headers, "ptr.test")
    add_record(client, auth_headers, forward["id"], name="host1", type="A", value="192.0.2.10",
               auto_ptr=True)
    records = client.get(f"/api/v1/zones/{reverse['id']}/records", headers=auth_headers).json()
    ptrs = [r for r in records if r["type"] == "PTR"]
    assert len(ptrs) == 1
    assert ptrs[0]["name"] == "10"
    assert ptrs[0]["value"] == "host1.ptr.test."


def test_auto_ptr_without_reverse_zone_is_noop(client, auth_headers):
    zone = make_zone(client, auth_headers, "orphan.test")
    add_record(client, auth_headers, zone["id"], name="a", type="A", value="198.51.100.5",
               auto_ptr=True)
    # no reverse zone exists; the A record is still created
    records = client.get(f"/api/v1/zones/{zone['id']}/records", headers=auth_headers).json()
    assert any(r["type"] == "A" for r in records)


def test_reverse_zone_derived_from_network(client, auth_headers):
    network = client.post("/api/v1/networks", json={"cidr": "10.55.3.0/24"},
                          headers=auth_headers).json()
    zone = make_zone(client, auth_headers, "", kind="reverse", network_id=network["id"])
    assert zone["name"] == "3.55.10.in-addr.arpa"


def test_zone_file_rendering(client, auth_headers):
    zone = make_zone(client, auth_headers, "render.test")
    add_record(client, auth_headers, zone["id"], name="www", type="A", value="192.0.2.1")
    add_record(client, auth_headers, zone["id"], name="@", type="MX", value="mail.render.test",
               priority=10)
    add_record(client, auth_headers, zone["id"], name="@", type="TXT", value="v=spf1 -all")
    add_record(client, auth_headers, zone["id"], name="alias", type="CNAME", value="www.render.test")

    content = client.get(f"/api/v1/zones/{zone['id']}/file", headers=auth_headers).json()["content"]
    assert "IN  SOA" in content
    assert "www" in content and "192.0.2.1" in content
    assert "10 mail.render.test." in content  # MX priority + absolute name
    assert '"v=spf1 -all"' in content  # TXT quoted
    assert "alias" in content and "www.render.test." in content
    current_serial = client.get(f"/api/v1/zones/{zone['id']}", headers=auth_headers).json()["serial"]
    assert str(current_serial) in content
