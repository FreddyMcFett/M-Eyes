"""Microsoft Entra ID (Azure AD) connector.

Imports managed devices from Microsoft Entra ID / Intune into the asset inventory
through the Microsoft Graph API using OAuth2 client-credentials (app registration).
Provide the tenant ID, the application's client ID (as the username) and a client
secret.
"""

from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from app.models import Integration
from app.services import assets, events
from app.services.integrations.base import ConfigField, Connector, ConnectorError, register

GRAPH = "https://graph.microsoft.com/v1.0"
LOGIN = "https://login.microsoftonline.com"


class EntraConnector(Connector):
    kind = "microsoft_entra"
    label = "Microsoft Entra ID"
    category = "microsoft"
    description = "Import Entra ID / Intune managed devices as assets via the Microsoft Graph API."
    capabilities = ["import_assets", "test"]
    uses_base_url = False
    uses_username = True
    username_label = "Client ID"
    secret_label = "Client secret"
    fields = [
        ConfigField("tenant_id", "Tenant ID", required=True,
                    placeholder="00000000-0000-0000-0000-000000000000"),
        ConfigField("source", "Device source", default="all", advanced=True,
                    help="all | entra | intune — which device collection to import."),
    ]

    def _token(self, integration: Integration) -> str:
        tenant = (integration.settings or {}).get("tenant_id", "")
        if not tenant or not integration.username or not integration.secret:
            raise ConnectorError("Tenant ID, client ID and client secret are all required")
        try:
            with httpx.Client(timeout=20, verify=integration.verify_tls) as client:
                resp = client.post(
                    f"{LOGIN}/{tenant}/oauth2/v2.0/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": integration.username,
                        "client_secret": integration.secret,
                        "scope": "https://graph.microsoft.com/.default",
                    },
                )
                resp.raise_for_status()
                return resp.json()["access_token"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ConnectorError(f"Entra token request failed: {exc}") from exc

    def test_connection(self, integration: Integration) -> tuple[bool, str]:
        try:
            token = self._token(integration)
            with httpx.Client(timeout=20, verify=integration.verify_tls) as client:
                resp = client.get(f"{GRAPH}/devices?$top=1",
                                  headers={"Authorization": f"Bearer {token}"})
                resp.raise_for_status()
            return True, "Authenticated to Microsoft Graph and listed devices"
        except (httpx.HTTPError, ConnectorError) as exc:
            return False, f"{exc.__class__.__name__}: {exc}"

    def sync(self, db: Session, integration: Integration) -> dict:
        token = self._token(integration)
        source = (integration.settings or {}).get("source", "all")
        endpoints = []
        if source in ("all", "entra"):
            endpoints.append(("entra", f"{GRAPH}/devices"))
        if source in ("all", "intune"):
            endpoints.append(("intune", f"{GRAPH}/deviceManagement/managedDevices"))
        created = updated = 0
        headers = {"Authorization": f"Bearer {token}"}
        with httpx.Client(timeout=30, verify=integration.verify_tls) as client:
            for _label, url in endpoints:
                while url:
                    resp = client.get(url, headers=headers)
                    resp.raise_for_status()
                    body = resp.json()
                    for dev in body.get("value", []):
                        name = (dev.get("displayName") or dev.get("deviceName") or "").strip()
                        if not name:
                            continue
                        _, outcome = assets.upsert_from_observation(
                            db,
                            name=name,
                            hostname=name,
                            source=integration.name,
                            asset_type="workstation",
                            external_id=dev.get("id", ""),
                            extra={
                                "operating_system": dev.get("operatingSystem", ""),
                                "model": dev.get("model", ""),
                                "vendor": dev.get("manufacturer", ""),
                                "serial_number": dev.get("serialNumber", ""),
                            },
                        )
                        created += outcome == "created"
                        updated += outcome != "created"
                    url = body.get("@odata.nextLink")
        detail = f"{created} new device(s), {updated} updated"
        events.emit(db, "info", "integration", f"Entra ID sync ({integration.name}): {detail}")
        return {"created": created, "updated": updated, "detail": detail}


register(EntraConnector())
