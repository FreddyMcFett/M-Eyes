"""FortiAuthenticator connector.

FortiAuthenticator is the recommended SAML Identity Provider for M-Eyes single
sign-on (configured under System → SSO / SAML). This connector verifies that the
FortiAuthenticator portal is reachable and acts as the registry entry that ties
the Fortinet IdP to the SSO configuration; the assertion exchange itself is
handled by app.services.sso.
"""

from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from app.models import Integration
from app.services.integrations.base import ConfigField, Connector, register


class FortiAuthenticatorConnector(Connector):
    kind = "fortiauthenticator"
    label = "FortiAuthenticator (SAML IdP)"
    category = "fortinet"
    description = (
        "Recommended SAML Identity Provider for M-Eyes SSO. Verifies portal "
        "reachability; configure the assertion exchange under System → SSO."
    )
    capabilities = ["saml_idp", "test"]
    base_url_label = "FortiAuthenticator URL"
    base_url_placeholder = "https://fac.example.com"
    uses_secret = False
    fields = [
        ConfigField("idp_portal_path", "IdP portal path", default="/saml-idp/",
                    advanced=True, help="Login portal path used for the reachability probe."),
    ]

    def test_connection(self, integration: Integration) -> tuple[bool, str]:
        if not integration.base_url:
            return False, "FortiAuthenticator URL is not configured"
        path = (integration.settings or {}).get("idp_portal_path", "/saml-idp/")
        url = f"{integration.base_url.rstrip('/')}{path}"
        try:
            with httpx.Client(verify=integration.verify_tls, timeout=10, follow_redirects=True) as client:
                resp = client.get(url)
            if resp.status_code < 500:
                return True, f"FortiAuthenticator reachable (HTTP {resp.status_code})"
            return False, f"FortiAuthenticator returned HTTP {resp.status_code}"
        except httpx.HTTPError as exc:
            return False, f"{exc.__class__.__name__}: {exc}"

    def sync(self, db: Session, integration: Integration) -> dict:
        return {"detail": "Configure the SAML assertion exchange under System → SSO / SAML."}


register(FortiAuthenticatorConnector())
