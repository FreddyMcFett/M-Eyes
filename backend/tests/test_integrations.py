from app.services.integrations import REGISTRY, connector_catalog, get_connector


def test_registry_has_all_connectors():
    for kind in ("fortigate", "fortimanager", "fortianalyzer", "fortiauthenticator",
                 "microsoft_dns", "microsoft_entra"):
        assert kind in REGISTRY


def test_catalog_endpoint(client, auth_headers):
    resp = client.get("/api/v1/integrations/catalog", headers=auth_headers)
    assert resp.status_code == 200
    kinds = {c["kind"] for c in resp.json()}
    assert "fortigate" in kinds and "microsoft_entra" in kinds
    fg = next(c for c in resp.json() if c["kind"] == "fortigate")
    assert fg["category"] == "fortinet"
    assert any(f["key"] == "vdom" for f in fg["fields"])


def test_crud_and_secret_masking(client, auth_headers):
    created = client.post("/api/v1/integrations", headers=auth_headers, json={
        "name": "edge-fw", "kind": "fortigate", "base_url": "https://192.0.2.1",
        "secret": "supersecrettoken", "settings": {"vdom": "root"},
    })
    assert created.status_code == 201, created.text
    body = created.json()
    assert "secret" not in body  # never echoed
    assert body["secret_set"] is True
    iid = body["id"]

    # Updating without a secret keeps the stored one.
    patched = client.patch(f"/api/v1/integrations/{iid}", headers=auth_headers,
                           json={"enabled": False})
    assert patched.status_code == 200 and patched.json()["secret_set"] is True

    assert client.delete(f"/api/v1/integrations/{iid}", headers=auth_headers).status_code == 204


def test_unknown_kind_rejected(client, auth_headers):
    resp = client.post("/api/v1/integrations", headers=auth_headers,
                       json={"name": "bad", "kind": "nonexistent"})
    assert resp.status_code == 422


def test_test_connection_degrades_gracefully(client, auth_headers):
    created = client.post("/api/v1/integrations", headers=auth_headers, json={
        "name": "unreachable", "kind": "fortigate",
        "base_url": "https://10.255.255.1", "secret": "tok",
    })
    iid = created.json()["id"]
    resp = client.post(f"/api/v1/integrations/{iid}/test", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is False  # cannot reach a bogus host, but no crash


def test_descriptor_shape():
    descriptors = connector_catalog()
    assert all({"kind", "label", "category", "fields"} <= set(d) for d in descriptors)
    assert get_connector("fortigate").label == "FortiGate"
