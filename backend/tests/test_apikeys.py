def test_create_list_and_use_api_key(client, auth_headers):
    response = client.post("/api/v1/apikeys", json={"name": "terraform"}, headers=auth_headers)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["key"].startswith("meyes_")
    assert created["prefix"] == created["key"][:12]

    listed = client.get("/api/v1/apikeys", headers=auth_headers).json()
    assert len(listed) == 1
    assert "key" not in listed[0]  # the full key is never returned again

    # the key authenticates without a bearer token
    response = client.get("/api/v1/networks", headers={"X-API-Key": created["key"]})
    assert response.status_code == 200

    # actions performed with the key are attributed to it in the changelog
    response = client.post("/api/v1/networks", json={"cidr": "10.99.0.0/24"},
                           headers={"X-API-Key": created["key"]})
    assert response.status_code == 201
    changes = client.get("/api/v1/changelog", headers=auth_headers).json()
    entries = changes if isinstance(changes, list) else changes.get("items", [])
    assert any(e.get("actor") == "apikey:terraform" for e in entries)


def test_invalid_and_revoked_keys_rejected(client, auth_headers):
    assert client.get("/api/v1/networks", headers={"X-API-Key": "meyes_bogus"}).status_code == 401

    created = client.post("/api/v1/apikeys", json={"name": "ci"}, headers=auth_headers).json()
    assert client.get("/api/v1/networks", headers={"X-API-Key": created["key"]}).status_code == 200

    response = client.delete(f"/api/v1/apikeys/{created['id']}", headers=auth_headers)
    assert response.status_code == 204
    assert client.get("/api/v1/networks", headers={"X-API-Key": created["key"]}).status_code == 401


def test_expired_key_rejected(client, auth_headers, db_session):
    from datetime import timedelta

    from app.models import ApiKey
    from app.models.base import utcnow

    created = client.post("/api/v1/apikeys", json={"name": "old", "expires_in_days": 30},
                          headers=auth_headers).json()
    key_row = db_session.get(ApiKey, created["id"])
    key_row.expires_at = utcnow() - timedelta(days=1)
    db_session.commit()

    response = client.get("/api/v1/networks", headers={"X-API-Key": created["key"]})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]


def test_duplicate_name_rejected(client, auth_headers):
    assert client.post("/api/v1/apikeys", json={"name": "dup"},
                       headers=auth_headers).status_code == 201
    assert client.post("/api/v1/apikeys", json={"name": "dup"},
                       headers=auth_headers).status_code == 409
