"""FortiManager (JSON-RPC API) connector.

Pushes M-Eyes IPAM networks into a FortiManager ADOM as firewall address objects
so they can be referenced fabric-wide. Authenticates with a username/password and
a session token over the JSON-RPC endpoint.
"""

from __future__ import annotations

import ipaddress

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Integration, Network
from app.services import events
from app.services.integrations.base import ConfigField, Connector, ConnectorError, register


class FortiManagerConnector(Connector):
    kind = "fortimanager"
    label = "FortiManager"
    category = "fortinet"
    description = "Push IPAM networks into a FortiManager ADOM as firewall address objects."
    capabilities = ["push_networks", "test"]
    base_url_label = "FortiManager URL"
    base_url_placeholder = "https://fmg.example.com"
    uses_username = True
    username_label = "Admin user"
    secret_label = "Password"
    fields = [
        ConfigField("adom", "ADOM", default="root", required=True),
        ConfigField("object_prefix", "Address object prefix", default="meyes_", advanced=True),
    ]

    def _rpc(self, integration: Integration, method: str, params: list, session: str | None = None) -> dict:
        if not integration.base_url:
            raise ConnectorError("FortiManager URL is not configured")
        body = {"method": method, "params": params, "id": 1}
        if session:
            body["session"] = session
        with httpx.Client(verify=integration.verify_tls, timeout=20) as client:
            resp = client.post(f"{integration.base_url.rstrip('/')}/jsonrpc", json=body)
            resp.raise_for_status()
            return resp.json()

    def _login(self, integration: Integration) -> str:
        data = self._rpc(integration, "exec", [{
            "url": "/sys/login/user",
            "data": {"user": integration.username, "passwd": integration.secret},
        }])
        session = data.get("session")
        if not session:
            raise ConnectorError("FortiManager login failed (no session returned)")
        return session

    def test_connection(self, integration: Integration) -> tuple[bool, str]:
        try:
            session = self._login(integration)
            status = self._rpc(integration, "get", [{"url": "/sys/status"}], session)
            self._rpc(integration, "exec", [{"url": "/sys/logout"}], session)
            data = status.get("result", [{}])[0].get("data", {})
            return True, f"Connected to FortiManager {data.get('Version', '')}".strip()
        except (httpx.HTTPError, ConnectorError, ValueError, KeyError, IndexError) as exc:
            return False, f"{exc.__class__.__name__}: {exc}"

    def sync(self, db: Session, integration: Integration) -> dict:
        adom = (integration.settings or {}).get("adom", "root")
        prefix = (integration.settings or {}).get("object_prefix", "meyes_")
        session = self._login(integration)
        pushed = 0
        try:
            for net in db.scalars(select(Network).where(Network.is_container.is_(False))).all():
                try:
                    network = ipaddress.ip_network(net.cidr)
                except ValueError:
                    continue
                if network.version != 4:
                    continue
                obj = {
                    "name": f"{prefix}{net.cidr.replace('/', '_')}",
                    "type": "ipmask",
                    "subnet": [str(network.network_address), str(network.netmask)],
                    "comment": net.name or f"M-Eyes {net.cidr}",
                }
                self._rpc(integration, "set", [{
                    "url": f"/pm/config/adom/{adom}/obj/firewall/address",
                    "data": obj,
                }], session)
                pushed += 1
        finally:
            self._rpc(integration, "exec", [{"url": "/sys/logout"}], session)
        detail = f"Pushed {pushed} address object(s) to ADOM {adom}"
        events.emit(db, "info", "integration", f"FortiManager sync ({integration.name}): {detail}")
        return {"pushed": pushed, "detail": detail}


register(FortiManagerConnector())
