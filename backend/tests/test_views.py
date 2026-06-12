def _create_view(client, headers, name="internal", match_clients="10.0.0.0/8"):
    response = client.post("/api/v1/views",
                           json={"name": name, "match_clients": match_clients},
                           headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_view_crud_and_validation(client, auth_headers):
    view = _create_view(client, auth_headers)
    assert view["match_clients"] == "10.0.0.0/8"

    # reserved & duplicate names
    assert client.post("/api/v1/views", json={"name": "default"},
                       headers=auth_headers).status_code == 422
    assert client.post("/api/v1/views", json={"name": "internal"},
                       headers=auth_headers).status_code == 409
    # invalid ACL element
    assert client.post("/api/v1/views",
                       json={"name": "x", "match_clients": "not-an-ip"},
                       headers=auth_headers).status_code == 422

    response = client.patch(f"/api/v1/views/{view['id']}",
                            json={"match_clients": "10.0.0.0/8; localnets"},
                            headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["match_clients"] == "10.0.0.0/8, localnets"

    assert client.delete(f"/api/v1/views/{view['id']}", headers=auth_headers).status_code == 204


def test_zone_per_view_uniqueness(client, auth_headers):
    view = _create_view(client, auth_headers)
    base = {"name": "corp.example.com", "kind": "forward"}

    assert client.post("/api/v1/zones", json=base, headers=auth_headers).status_code == 201
    # same name in the default view is a duplicate ...
    assert client.post("/api/v1/zones", json=base, headers=auth_headers).status_code == 409
    # ... but allowed inside a view
    response = client.post("/api/v1/zones", json={**base, "view_id": view["id"]},
                           headers=auth_headers)
    assert response.status_code == 201, response.text
    assert response.json()["view_name"] == "internal"
    # and duplicated again inside that view it conflicts
    assert client.post("/api/v1/zones", json={**base, "view_id": view["id"]},
                       headers=auth_headers).status_code == 409

    # a view with zones cannot be deleted
    assert client.delete(f"/api/v1/views/{view['id']}", headers=auth_headers).status_code == 409


def test_zones_conf_renders_views(client, auth_headers, db_session):
    from app.generators.named_conf import render_zones_conf

    view = _create_view(client, auth_headers, name="internal", match_clients="10.0.0.0/8")
    client.post("/api/v1/zones", json={"name": "corp.example.com"}, headers=auth_headers)
    client.post("/api/v1/zones",
                json={"name": "corp.example.com", "view_id": view["id"]},
                headers=auth_headers)

    conf = render_zones_conf(db_session)
    assert 'view "internal" {' in conf
    assert "match-clients { 10.0.0.0/8; };" in conf
    # unassigned zones land in the trailing catch-all view
    assert 'view "default" {' in conf
    assert "match-clients { any; };" in conf
    # per-view zone files are disambiguated by file name
    assert "db.internal.corp.example.com" in conf
    assert "/db.corp.example.com" in conf


def test_zones_conf_flat_without_views(client, auth_headers, db_session):
    from app.generators.named_conf import render_zones_conf

    client.post("/api/v1/zones", json={"name": "corp.example.com"}, headers=auth_headers)
    conf = render_zones_conf(db_session)
    assert "view " not in conf
    assert 'zone "corp.example.com" {' in conf


def test_dnssec_flag_renders_policy(client, auth_headers, db_session):
    from app.generators.named_conf import render_zones_conf

    response = client.post("/api/v1/zones",
                           json={"name": "secure.example.com", "dnssec_enabled": True},
                           headers=auth_headers)
    assert response.status_code == 201, response.text
    assert response.json()["dnssec_enabled"] is True

    conf = render_zones_conf(db_session)
    assert "dnssec-policy default;" in conf
    assert "inline-signing yes;" in conf

    # and it can be toggled off again
    zone_id = response.json()["id"]
    client.patch(f"/api/v1/zones/{zone_id}", json={"dnssec_enabled": False},
                 headers=auth_headers)
    assert "dnssec-policy" not in render_zones_conf(db_session)
