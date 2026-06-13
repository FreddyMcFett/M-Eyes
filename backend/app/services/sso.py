"""SAML 2.0 Service Provider implementation.

M-Eyes is the SP; an external IdP (FortiAuthenticator, Microsoft Entra ID, Okta,
…) authenticates the user and POSTs a signed assertion back to the Assertion
Consumer Service. The signature is verified with ``signxml`` (pure-Python XML
DSig, no native xmlsec dependency); assertion conditions (validity window and
audience) are enforced before any identity is trusted.

The module degrades gracefully: building AuthnRequests and SP metadata needs only
``lxml``; only response verification pulls in ``signxml`` (imported lazily).
"""

from __future__ import annotations

import base64
import secrets
import zlib
from datetime import datetime, timedelta
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.api.deps import role_at_least
from app.models import SsoConfig, User
from app.models.base import utcnow
from app.models.user import ROLES
from app.security import create_access_token, hash_password
from app.services import events

SAML_NS = "urn:oasis:names:tc:SAML:2.0:assertion"
SAMLP_NS = "urn:oasis:names:tc:SAML:2.0:protocol"
NSMAP = {"saml": SAML_NS, "samlp": SAMLP_NS}


class SamlError(Exception):
    """Raised when a SAML exchange cannot be trusted or is malformed."""


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def get_config(db: Session) -> SsoConfig:
    cfg = db.get(SsoConfig, 1)
    if cfg is None:
        cfg = SsoConfig(id=1)
        db.add(cfg)
        db.flush()
    return cfg


def sp_entity_id(cfg: SsoConfig) -> str:
    return cfg.sp_entity_id.strip() or f"{_base(cfg)}/api/v1/sso/metadata"


def acs_url(cfg: SsoConfig) -> str:
    return f"{_base(cfg)}/api/v1/auth/sso/acs"


def _base(cfg: SsoConfig) -> str:
    return cfg.base_url.rstrip("/")


# --------------------------------------------------------------------------- #
# Certificate helpers
# --------------------------------------------------------------------------- #
def _normalize_cert(cert: str) -> str:
    """Accept a bare base64 blob (as found in IdP metadata) or full PEM; return PEM."""
    cert = (cert or "").strip()
    if not cert:
        raise SamlError("No IdP signing certificate configured")
    if "BEGIN CERTIFICATE" in cert:
        return cert
    body = "".join(cert.split())
    lines = "\n".join(body[i : i + 64] for i in range(0, len(body), 64))
    return f"-----BEGIN CERTIFICATE-----\n{lines}\n-----END CERTIFICATE-----\n"


def _cert_der_b64(cert_pem: str) -> str:
    """Single-line base64 DER for embedding in SP metadata <ds:X509Certificate>."""
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import Encoding

    loaded = x509.load_pem_x509_certificate(_normalize_cert(cert_pem).encode())
    return base64.b64encode(loaded.public_bytes(Encoding.DER)).decode()


# --------------------------------------------------------------------------- #
# SP metadata
# --------------------------------------------------------------------------- #
def sp_metadata_xml(cfg: SsoConfig) -> str:
    from lxml import etree

    md = "urn:oasis:names:tc:SAML:2.0:metadata"
    ds = "http://www.w3.org/2000/09/xmldsig#"
    ed = etree.Element(f"{{{md}}}EntityDescriptor", entityID=sp_entity_id(cfg), nsmap={None: md, "ds": ds})
    spsso = etree.SubElement(
        ed,
        f"{{{md}}}SPSSODescriptor",
        AuthnRequestsSigned="true" if cfg.sign_authn_requests else "false",
        WantAssertionsSigned="true" if cfg.want_assertions_signed else "false",
        protocolSupportEnumeration=SAMLP_NS,
    )
    if cfg.sp_x509_cert.strip():
        kd = etree.SubElement(spsso, f"{{{md}}}KeyDescriptor", use="signing")
        ki = etree.SubElement(kd, f"{{{ds}}}KeyInfo")
        data = etree.SubElement(ki, f"{{{ds}}}X509Data")
        etree.SubElement(data, f"{{{ds}}}X509Certificate").text = _cert_der_b64(cfg.sp_x509_cert)
    etree.SubElement(spsso, f"{{{md}}}NameIDFormat").text = cfg.name_id_format
    etree.SubElement(
        spsso,
        f"{{{md}}}AssertionConsumerService",
        Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
        Location=acs_url(cfg),
        index="0",
        isDefault="true",
    )
    if cfg.idp_slo_url.strip():
        etree.SubElement(
            spsso,
            f"{{{md}}}SingleLogoutService",
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            Location=f"{_base(cfg)}/api/v1/auth/sso/sls",
        )
    return etree.tostring(ed, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode()


# --------------------------------------------------------------------------- #
# AuthnRequest (SP-initiated SSO, HTTP-Redirect binding)
# --------------------------------------------------------------------------- #
def build_authn_request_redirect(cfg: SsoConfig, relay_state: str | None = None) -> str:
    from lxml import etree

    if not cfg.idp_sso_url.strip():
        raise SamlError("IdP Single Sign-On URL is not configured")
    request_id = "_" + secrets.token_hex(20)
    issue_instant = utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    root = etree.Element(
        f"{{{SAMLP_NS}}}AuthnRequest",
        nsmap=NSMAP,
        ID=request_id,
        Version="2.0",
        IssueInstant=issue_instant,
        Destination=cfg.idp_sso_url,
        ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
        AssertionConsumerServiceURL=acs_url(cfg),
    )
    if cfg.force_authn:
        root.set("ForceAuthn", "true")
    etree.SubElement(root, f"{{{SAML_NS}}}Issuer").text = sp_entity_id(cfg)
    if cfg.name_id_format:
        etree.SubElement(
            root,
            f"{{{SAMLP_NS}}}NameIDPolicy",
            Format=cfg.name_id_format,
            AllowCreate="true",
        )

    xml = etree.tostring(root, xml_declaration=False, encoding="UTF-8")
    deflated = zlib.compress(xml)[2:-4]  # raw DEFLATE for the HTTP-Redirect binding
    params = {"SAMLRequest": base64.b64encode(deflated).decode()}
    if relay_state:
        params["RelayState"] = relay_state
    sep = "&" if "?" in cfg.idp_sso_url else "?"
    return f"{cfg.idp_sso_url}{sep}{urlencode(params)}"


# --------------------------------------------------------------------------- #
# Response processing (Assertion Consumer Service)
# --------------------------------------------------------------------------- #
def _parse_instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _verify_signature(xml_bytes: bytes, cert_pem: str):
    """Verify the XML signature and return the signed (trusted) element."""
    from lxml import etree
    from signxml import XMLVerifier

    try:
        result = XMLVerifier().verify(xml_bytes, x509_cert=_normalize_cert(cert_pem))
    except Exception as exc:  # noqa: BLE001 - any failure means we cannot trust the response
        raise SamlError(f"SAML signature verification failed: {exc}") from exc
    if isinstance(result, list):
        result = result[0]
    signed = result.signed_xml
    if signed is None:
        raise SamlError("SAML response is not signed")
    # Re-root so XPath on the trusted subtree is unambiguous.
    return etree.fromstring(etree.tostring(signed))


def process_response(db: Session, cfg: SsoConfig, saml_response_b64: str) -> User:
    if not cfg.enabled:
        raise SamlError("SAML SSO is not enabled")
    try:
        xml_bytes = base64.b64decode(saml_response_b64)
    except Exception as exc:  # noqa: BLE001
        raise SamlError("SAMLResponse is not valid base64") from exc

    trusted = _verify_signature(xml_bytes, cfg.idp_x509_cert)
    tag = trusted.tag.split("}")[-1]
    if tag == "Response":
        if cfg.want_response_signed:
            pass  # the Response itself carried the verified signature
        assertion = trusted.find(f"{{{SAML_NS}}}Assertion")
        if assertion is None:
            raise SamlError("Signed Response contains no Assertion")
    elif tag == "Assertion":
        if cfg.want_response_signed:
            raise SamlError("Configuration requires a signed Response, but only the Assertion was signed")
        assertion = trusted
    else:
        raise SamlError(f"Unexpected signed element <{tag}>")

    _validate_conditions(cfg, assertion)
    return _provision_user(db, cfg, assertion)


def _validate_conditions(cfg: SsoConfig, assertion) -> None:
    skew = timedelta(seconds=cfg.allowed_clock_skew_seconds)
    now = utcnow()
    conditions = assertion.find(f"{{{SAML_NS}}}Conditions")
    if conditions is not None:
        nb = conditions.get("NotBefore")
        na = conditions.get("NotOnOrAfter")
        if nb and now + skew < _parse_instant(nb):
            raise SamlError("Assertion is not yet valid (NotBefore)")
        if na and now - skew >= _parse_instant(na):
            raise SamlError("Assertion has expired (NotOnOrAfter)")
        audiences = [
            a.text.strip()
            for a in conditions.iter(f"{{{SAML_NS}}}Audience")
            if a.text
        ]
        if audiences and sp_entity_id(cfg) not in audiences:
            raise SamlError("Assertion audience does not match this SP's entity ID")


def _attr_values(assertion, name: str) -> list[str]:
    if not name:
        return []
    values: list[str] = []
    for attr in assertion.iter(f"{{{SAML_NS}}}Attribute"):
        if attr.get("Name") == name or attr.get("FriendlyName") == name:
            for val in attr.iter(f"{{{SAML_NS}}}AttributeValue"):
                if val.text:
                    values.append(val.text.strip())
    return values


def _first(values: list[str]) -> str:
    return values[0] if values else ""


def map_role(cfg: SsoConfig, groups: list[str]) -> str:
    """Resolve the highest-privilege role any of the user's groups maps to."""
    best: str | None = None
    mappings = cfg.role_mappings or {}
    for group in groups:
        role = mappings.get(group)
        if role and role in ROLES:
            if best is None or role_at_least(role, best):
                best = role
    return best or (cfg.default_role if cfg.default_role in ROLES else "viewer")


def _provision_user(db: Session, cfg: SsoConfig, assertion) -> User:
    name_id_el = assertion.find(f"{{{SAML_NS}}}Subject/{{{SAML_NS}}}NameID")
    name_id = (name_id_el.text or "").strip() if name_id_el is not None else ""

    username = _first(_attr_values(assertion, cfg.attr_username)) or name_id
    if not username:
        raise SamlError("Could not determine a username from the assertion (NameID/attribute empty)")
    email = _first(_attr_values(assertion, cfg.attr_email))
    display_name = _first(_attr_values(assertion, cfg.attr_display_name))
    groups = _attr_values(assertion, cfg.attr_groups)
    role = map_role(cfg, groups)

    from sqlalchemy import select

    user = db.scalar(select(User).where(User.username == username))
    if user is None and name_id:
        user = db.scalar(select(User).where(User.external_id == name_id))
    if user is None:
        if not cfg.allow_jit_provisioning:
            raise SamlError(f"No M-Eyes account for {username!r} and just-in-time provisioning is off")
        user = User(
            username=username,
            password_hash=hash_password(secrets.token_urlsafe(32)),  # unusable local password
            role=role,
            auth_source="saml",
            external_id=name_id,
        )
        db.add(user)
        events.emit(db, "info", "auth", f"SSO provisioned new user {username!r} with role {role}")
    else:
        # Keep SSO-managed users in sync; never downgrade a local admin via SSO mapping.
        if user.auth_source == "saml":
            user.role = role
    user.email = email or user.email
    user.display_name = display_name or user.display_name
    user.external_id = name_id or user.external_id
    user.last_login_at = utcnow()
    db.flush()
    events.emit(db, "info", "auth", f"User {username!r} signed in via SAML SSO")
    return user


def issue_token(user: User) -> str:
    return create_access_token(user.username)
