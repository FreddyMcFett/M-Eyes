import httpx

from app.services import leases as lease_service


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


def test_leases_mapped_from_kea(client, auth_headers, monkeypatch):
    network = client.post("/api/v1/networks", json={"cidr": "10.10.20.0/24"},
                          headers=auth_headers).json()
    client.post("/api/v1/dhcp/subnets", json={"network_id": network["id"]},
                headers=auth_headers)

    body = [{
        "result": 0,
        "arguments": {"leases": [{
            "ip-address": "10.10.20.101",
            "hw-address": "00:09:0f:aa:bb:02",
            "hostname": "laptop-01",
            "state": 0,
            "cltt": 1_700_000_000,
            "valid-lft": 4000,
            "subnet-id": 1,
        }]},
    }]
    monkeypatch.setattr(lease_service.httpx, "post",
                        lambda *args, **kwargs: _FakeResponse(body))

    response = client.get("/api/v1/dhcp/leases", headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["reachable"] is True
    lease = data["leases"][0]
    assert lease["ip"] == "10.10.20.101"
    assert lease["mac"] == "00:09:0f:aa:bb:02"
    assert lease["state"] == "active"
    assert lease["subnet"] == "10.10.20.0/24"
    assert lease["expires_at"] is not None


def test_leases_unreachable_is_graceful(client, auth_headers, monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("no kea here")

    monkeypatch.setattr(lease_service.httpx, "post", boom)
    response = client.get("/api/v1/dhcp/leases", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"reachable": False,
                               "detail": "Kea Control Agent not reachable (ConnectError)",
                               "leases": []}
