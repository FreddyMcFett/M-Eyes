def _rule(client, headers, **overrides):
    payload = {"fqdn": "bad.example.com", "action": "block", **overrides}
    return client.post("/api/v1/rpz/rules", json=payload, headers=headers)


def test_rule_crud_and_validation(client, auth_headers):
    response = _rule(client, auth_headers)
    assert response.status_code == 201, response.text
    rule_id = response.json()["id"]

    assert _rule(client, auth_headers).status_code == 409  # duplicate fqdn
    assert _rule(client, auth_headers, fqdn="*.evil.com").status_code == 422  # explicit wildcard
    assert _rule(client, auth_headers, fqdn="not a domain").status_code == 422
    assert _rule(client, auth_headers, fqdn="x.example.com",
                 action="teleport").status_code == 422
    assert _rule(client, auth_headers, fqdn="y.example.com",
                 action="substitute").status_code == 422  # missing substitute value

    response = client.patch(f"/api/v1/rpz/rules/{rule_id}", json={"enabled": False},
                            headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    assert client.delete(f"/api/v1/rpz/rules/{rule_id}", headers=auth_headers).status_code == 204
    assert client.get("/api/v1/rpz/rules", headers=auth_headers).json() == []


def test_rpz_zone_rendering(client, auth_headers, db_session):
    from app.generators.rpz_zone import render_rpz_zone

    _rule(client, auth_headers)  # block bad.example.com
    _rule(client, auth_headers, fqdn="ok.example.com", action="passthru")
    _rule(client, auth_headers, fqdn="empty.example.com", action="nodata")
    _rule(client, auth_headers, fqdn="redirect.example.com", action="substitute",
          substitute="10.0.0.80")
    _rule(client, auth_headers, fqdn="alias.example.com", action="substitute",
          substitute="landing.example.org")
    _rule(client, auth_headers, fqdn="disabled.example.com", enabled=False)

    content = client.get("/api/v1/rpz/preview", headers=auth_headers).json()["content"]
    assert content == render_rpz_zone(db_session)

    assert "bad.example.com" in content and "CNAME  ." in content
    assert "*.bad.example.com" in content  # subdomains are covered automatically
    assert "rpz-passthru." in content
    assert "CNAME  *." in content
    assert "A      10.0.0.80" in content
    assert "CNAME  landing.example.org." in content
    assert "disabled.example.com" not in content


def test_rpz_appears_in_bind_config_only_when_active(client, auth_headers, db_session):
    from app.generators.named_conf import render_rpz_options, render_zones_conf

    # no rules -> no zone, no policy
    assert "rpz" not in render_zones_conf(db_session)
    assert "response-policy" not in render_rpz_options(db_session)

    response = _rule(client, auth_headers)
    conf = render_zones_conf(db_session)
    assert 'zone "rpz.m-eyes" {' in conf
    assert 'response-policy { zone "rpz.m-eyes"; }' in render_rpz_options(db_session)

    # disabling the only rule turns the firewall back off
    client.patch(f"/api/v1/rpz/rules/{response.json()['id']}", json={"enabled": False},
                 headers=auth_headers)
    assert "rpz" not in render_zones_conf(db_session)
    assert "response-policy" not in render_rpz_options(db_session)


def test_rpz_policy_moves_into_views(client, auth_headers, db_session):
    from app.generators.named_conf import render_rpz_options, render_zones_conf

    _rule(client, auth_headers)
    client.post("/api/v1/views", json={"name": "internal", "match_clients": "10.0.0.0/8"},
                headers=auth_headers)
    conf = render_zones_conf(db_session)
    # with views, the policy is emitted per view instead of globally
    assert conf.count('response-policy { zone "rpz.m-eyes"; }') == 2  # internal + default
    assert "response-policy" not in render_rpz_options(db_session)
