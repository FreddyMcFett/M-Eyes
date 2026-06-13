from pydantic import BaseModel

from app.schemas.common import ORMModel


class SsoConfigBase(BaseModel):
    enabled: bool = False
    button_label: str = "Sign in with SSO"
    idp_entity_id: str = ""
    idp_sso_url: str = ""
    idp_slo_url: str = ""
    idp_x509_cert: str = ""
    sp_entity_id: str = ""
    base_url: str = ""
    attr_username: str = ""
    attr_email: str = ""
    attr_display_name: str = ""
    attr_groups: str = ""
    role_mappings: dict[str, str] = {}
    default_role: str = "viewer"
    allow_jit_provisioning: bool = True
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    sign_authn_requests: bool = False
    want_assertions_signed: bool = True
    want_response_signed: bool = False
    force_authn: bool = False
    allowed_clock_skew_seconds: int = 120
    signature_algorithm: str = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"


class SsoConfigIn(SsoConfigBase):
    # Write-only signing material; omitted/blank leaves the stored value untouched.
    sp_private_key: str | None = None
    sp_x509_cert: str | None = None


class SsoConfigOut(SsoConfigBase, ORMModel):
    # Derived, read-only values to copy into the IdP.
    sp_metadata_url: str = ""
    acs_url: str = ""
    sp_entity_id_effective: str = ""
    sp_signing_configured: bool = False


class SsoStatusOut(BaseModel):
    enabled: bool
    button_label: str
    login_url: str
