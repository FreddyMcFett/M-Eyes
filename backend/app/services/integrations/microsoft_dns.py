"""Microsoft DNS connector.

Imports A records from a Microsoft DNS server via zone transfer (AXFR) and turns
them into asset records cross-referenced to their hostnames/IPs. Uses ``dig`` —
already present in the API image (bind9-dnsutils) and consistent with the ping
sweep discovery service. The Microsoft DNS server must permit a zone transfer to
the M-Eyes host.
"""

from __future__ import annotations

import subprocess

from sqlalchemy.orm import Session

from app.models import Integration
from app.services import assets, events
from app.services.integrations.base import ConfigField, Connector, ConnectorError, register


class MicrosoftDnsConnector(Connector):
    kind = "microsoft_dns"
    label = "Microsoft DNS"
    category = "microsoft"
    description = "Import host (A) records from Microsoft DNS zones via AXFR into the asset inventory."
    capabilities = ["import_assets", "test"]
    uses_base_url = True
    base_url_label = "DNS server"
    base_url_placeholder = "10.0.0.10"
    uses_secret = False
    fields = [
        ConfigField("zones", "Zones (comma-separated)", required=True,
                    placeholder="corp.example.com, ad.example.com"),
        ConfigField("create_assets", "Create assets from records", type="bool", default="true"),
    ]

    def _server(self, integration: Integration) -> str:
        server = integration.base_url.strip()
        if not server:
            raise ConnectorError("Microsoft DNS server is not configured")
        return server

    def _axfr(self, server: str, zone: str) -> list[tuple[str, str]]:
        """Return (hostname, ip) pairs for A records in the zone, via dig AXFR."""
        try:
            proc = subprocess.run(
                ["dig", f"@{server}", zone, "AXFR", "+nocomments", "+nostats", "+noquestion"],
                capture_output=True, text=True, timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise ConnectorError(f"dig AXFR failed: {exc}") from exc
        if "Transfer failed" in proc.stdout or proc.returncode != 0:
            raise ConnectorError(f"Zone transfer of {zone} refused by {server}")
        records: list[tuple[str, str]] = []
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[3] == "A":
                records.append((parts[0].rstrip("."), parts[4]))
        return records

    def test_connection(self, integration: Integration) -> tuple[bool, str]:
        try:
            server = self._server(integration)
            zones = [z.strip() for z in (integration.settings or {}).get("zones", "").split(",") if z.strip()]
            if not zones:
                return False, "No zones configured"
            records = self._axfr(server, zones[0])
            return True, f"Zone transfer of {zones[0]} succeeded ({len(records)} A records)"
        except ConnectorError as exc:
            return False, str(exc)

    def sync(self, db: Session, integration: Integration) -> dict:
        server = self._server(integration)
        zones = [z.strip() for z in (integration.settings or {}).get("zones", "").split(",") if z.strip()]
        create = str((integration.settings or {}).get("create_assets", "true")).lower() \
            in ("true", "1", "yes")
        created = linked = total = 0
        for zone in zones:
            for hostname, ip in self._axfr(server, zone):
                total += 1
                if not create:
                    continue
                _, outcome = assets.upsert_from_observation(
                    db, name=hostname, ip=ip, hostname=hostname,
                    source=integration.name, asset_type="server",
                )
                created += outcome == "created"
                linked += outcome == "linked"
        detail = f"{total} A record(s) across {len(zones)} zone(s): {created} new, {linked} linked"
        events.emit(db, "info", "integration", f"Microsoft DNS sync ({integration.name}): {detail}")
        return {"records": total, "created": created, "linked": linked, "detail": detail}


register(MicrosoftDnsConnector())
