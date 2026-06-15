"""Advanced DNS zone ACLs / forwarding and DHCP lease-timing, boot and class
options surface correctly in the generated engine configuration."""
import json


def _network(client, headers, cidr):
    return client.post("/api/v1/networks", json={"cidr": cidr}, headers=headers).json()


def test_subnet_advanced_options_in_dhcp_config(client, auth_headers):
    network = _network(client, auth_headers, "10.60.0.0/24")
    subnet = client.post(
        "/api/v1/dhcp/subnets",
        json={
            "network_id": network["id"],
            "valid_lifetime": 7200,
            "renew_timer": 1800,
            "rebind_timer": 3150,
            "next_server": "10.60.0.2",
            "boot_file_name": "pxelinux.0",
            "client_class": "voip",
        },
        headers=auth_headers,
    ).json()
    assert subnet["valid_lifetime"] == 7200
    assert subnet["next_server"] == "10.60.0.2"

    preview = client.get("/api/v1/deploy/kea/preview", headers=auth_headers).json()
    config = json.loads(preview["kea_dhcp4_conf"])
    entry = next(s for s in config["Dhcp4"]["subnet4"] if s["subnet"] == "10.60.0.0/24")
    assert entry["valid-lifetime"] == 7200
    assert entry["renew-timer"] == 1800
    assert entry["rebind-timer"] == 3150
    assert entry["next-server"] == "10.60.0.2"
    assert entry["boot-file-name"] == "pxelinux.0"
    assert entry["client-class"] == "voip"


def test_subnet_without_overrides_inherits_defaults(client, auth_headers):
    network = _network(client, auth_headers, "10.61.0.0/24")
    client.post("/api/v1/dhcp/subnets", json={"network_id": network["id"]}, headers=auth_headers)
    preview = client.get("/api/v1/deploy/kea/preview", headers=auth_headers).json()
    entry = next(s for s in json.loads(preview["kea_dhcp4_conf"])["Dhcp4"]["subnet4"]
                 if s["subnet"] == "10.61.0.0/24")
    # No per-scope timing keys when nothing is overridden — the server default applies.
    assert "valid-lifetime" not in entry
    assert "next-server" not in entry


def test_global_dhcp_lease_defaults_configurable(client, auth_headers):
    client.put("/api/v1/system/settings",
               json={"values": {"dhcp_valid_lifetime": "9000", "dhcp_renew_timer": "2000",
                                "dhcp_rebind_timer": "4000"}},
               headers=auth_headers)
    network = _network(client, auth_headers, "10.62.0.0/24")
    client.post("/api/v1/dhcp/subnets", json={"network_id": network["id"]}, headers=auth_headers)
    config = json.loads(
        client.get("/api/v1/deploy/kea/preview", headers=auth_headers).json()["kea_dhcp4_conf"]
    )
    dhcp4 = config["Dhcp4"]
    assert dhcp4["valid-lifetime"] == 9000
    assert dhcp4["renew-timer"] == 2000
    assert dhcp4["rebind-timer"] == 4000


def test_negative_lease_timer_rejected(client, auth_headers):
    network = _network(client, auth_headers, "10.63.0.0/24")
    response = client.post("/api/v1/dhcp/subnets",
                           json={"network_id": network["id"], "valid_lifetime": -5},
                           headers=auth_headers)
    assert response.status_code == 422


def test_zone_acls_rendered(client, auth_headers, db_session):
    from app.generators.named_conf import render_zones_conf

    client.post(
        "/api/v1/zones",
        json={
            "name": "secure.example.com",
            "allow_query": "10.0.0.0/8, localhost",
            "allow_transfer": "192.0.2.53",
            "allow_update": "none",
            "also_notify": "192.0.2.53; 192.0.2.54",
        },
        headers=auth_headers,
    )
    conf = render_zones_conf(db_session)
    assert "allow-query { 10.0.0.0/8; localhost; };" in conf
    assert "allow-transfer { 192.0.2.53; };" in conf
    assert "allow-update { none; };" in conf
    assert "also-notify { 192.0.2.53; 192.0.2.54; };" in conf


def test_forward_first_zone_rendered(client, auth_headers, db_session):
    from app.generators.named_conf import render_zones_conf

    client.post("/api/v1/zones",
                json={"name": "fwd.example.com", "role": "forward",
                      "primaries": "198.51.100.1", "forward_first": True},
                headers=auth_headers)
    conf = render_zones_conf(db_session)
    assert "forward first;" in conf


def test_zone_without_acls_emits_no_clause(client, auth_headers, db_session):
    from app.generators.named_conf import render_zones_conf

    client.post("/api/v1/zones", json={"name": "plain.example.com"}, headers=auth_headers)
    conf = render_zones_conf(db_session)
    assert "allow-query" not in conf
    assert "allow-transfer" not in conf
