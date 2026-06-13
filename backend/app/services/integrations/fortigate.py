"""FortiGate (FortiOS REST API) connector.

Pulls interface subnets into IPAM and DHCP leases into the asset inventory, and
can be extended to push address objects. Authentication uses a FortiOS REST API
administrator token (``access_token``).
"""

from __future__ import annotations

import ipaddress

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Integration, Network
from app.services import assets, events, ipam
from app.services.integrations.base import ConfigField, Connector, ConnectorError, register


class FortiGateConnector(Connector):
    kind = "fortigate"
    label = "FortiGate"
    category = "fortinet"
    description = (
        "Sync FortiGate interface networks into IPAM and DHCP leases into the asset "
        "inventory over the FortiOS REST API."
    )
    capabilities = ["import_networks", "import_assets", "test"]
    base_url_label = "FortiGate URL"
    base_url_placeholder = "https://192.0.2.1"
    uses_secret = True
    secret_label = "REST API token"
    fields = [
        ConfigField("vdom", "VDOM", default="root", help="Virtual domain to query."),
        ConfigField("import_interfaces", "Import interface subnets into IPAM",
                    type="bool", default="true"),
        ConfigField("import_leases", "Import DHCP leases as assets", type="bool", default="true"),
        ConfigField("site", "IPAM site tag for imported networks", default="",
                    help="Optional site/name applied to networks created from interfaces.",
                    advanced=True),
    ]

    def _client(self, integration: Integration) -> httpx.Client:
        if not integration.base_url:
            raise ConnectorError("FortiGate URL is not configured")
        if not integration.secret:
            raise ConnectorError("FortiGate REST API token is not configured")
        return httpx.Client(
            base_url=integration.base_url.rstrip("/"),
            params={"access_token": integration.secret, "vdom": integration.settings.get("vdom", "root")},
            verify=integration.verify_tls,
            timeout=15,
        )

    def test_connection(self, integration: Integration) -> tuple[bool, str]:
        try:
            with self._client(integration) as client:
                resp = client.get("/api/v2/monitor/system/status")
                resp.raise_for_status()
                data = resp.json()
            version = data.get("version") or data.get("results", {}).get("version", "unknown")
            hostname = data.get("results", {}).get("hostname", "")
            return True, f"Connected to FortiGate {hostname} (FortiOS {version})".strip()
        except (httpx.HTTPError, ConnectorError, ValueError) as exc:
            return False, f"{exc.__class__.__name__}: {exc}"

    def sync(self, db: Session, integration: Integration) -> dict:
        settings = integration.settings or {}
        result = {"networks_created": 0, "assets_created": 0, "assets_linked": 0}
        with self._client(integration) as client:
            if str(settings.get("import_interfaces", "true")).lower() in ("true", "1", "yes"):
                result["networks_created"] += self._import_interfaces(db, integration, client)
            if str(settings.get("import_leases", "true")).lower() in ("true", "1", "yes"):
                created, linked = self._import_leases(db, integration, client)
                result["assets_created"] += created
                result["assets_linked"] += linked
        detail = (f"{result['networks_created']} network(s), "
                  f"{result['assets_created']} new asset(s), {result['assets_linked']} linked")
        result["detail"] = detail
        events.emit(db, "info", "integration", f"FortiGate sync ({integration.name}): {detail}")
        return result

    def _import_interfaces(self, db: Session, integration: Integration, client: httpx.Client) -> int:
        resp = client.get("/api/v2/cmdb/system/interface")
        resp.raise_for_status()
        created = 0
        site = (integration.settings or {}).get("site", "")
        for iface in resp.json().get("results", []):
            ip_mask = iface.get("ip", "")  # "10.0.0.1 255.255.255.0"
            if not ip_mask or ip_mask.startswith("0.0.0.0"):
                continue
            try:
                addr, mask = ip_mask.split()
                network = ipaddress.ip_network(f"{addr}/{mask}", strict=False)
            except (ValueError, IndexError):
                continue
            cidr = str(network)
            if db.scalar(select(Network).where(Network.cidr == cidr)):
                continue
            try:
                ipam.create_network(db, f"integration:{integration.name}", {
                    "cidr": cidr,
                    "name": iface.get("name", ""),
                    "description": f"Imported from FortiGate {integration.name}",
                    "site": site,
                })
                created += 1
            except HTTPException:
                continue  # overlapping/duplicate — leave the existing record untouched
        return created

    def _import_leases(self, db: Session, integration: Integration, client: httpx.Client) -> tuple[int, int]:
        resp = client.get("/api/v2/monitor/system/dhcp")
        resp.raise_for_status()
        created = linked = 0
        for lease in resp.json().get("results", []):
            ip = lease.get("ip", "")
            mac = lease.get("mac", "")
            if not ip and not mac:
                continue
            _, outcome = assets.upsert_from_observation(
                db,
                name=lease.get("hostname", "") or ip,
                ip=ip,
                mac=mac,
                hostname=lease.get("hostname", ""),
                source=integration.name,
                asset_type="other",
            )
            created += outcome == "created"
            linked += outcome == "linked"
        return created, linked


register(FortiGateConnector())
