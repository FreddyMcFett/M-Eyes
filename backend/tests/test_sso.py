"""SAML SSO: configuration API, metadata/AuthnRequest building, and a full
signed-assertion round trip through the Assertion Consumer Service."""

import base64
from datetime import timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.models import SsoConfig
from app.models.base import utcnow
from app.services import sso

SAML_NS = "urn:oasis:names:tc:SAML:2.0:assertion"
SAMLP_NS = "urn:oasis:names:tc:SAML:2.0:protocol"
BASE_URL = "https://meyes.example.com"


@pytest.fixture
def idp_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-idp")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(utcnow() - timedelta(days=1))
        .not_valid_after(utcnow() + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    return key_pem, cert_pem


def _signed_response(key_pem: str, cert_pem: str, *, username="alice@example.com",
                     groups=("meyes-admins",), audience=None) -> str:
    from lxml import etree
    from signxml import XMLSigner

    audience = audience or f"{BASE_URL}/api/v1/sso/metadata"
    now = utcnow()
    nb = (now - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    na = (now + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

    response = etree.Element(f"{{{SAMLP_NS}}}Response", nsmap={"samlp": SAMLP_NS, "saml": SAML_NS},
                             ID="_resp1", Version="2.0", IssueInstant=nb)
    etree.SubElement(response, f"{{{SAML_NS}}}Issuer").text = "https://idp.example.com"
    assertion = etree.SubElement(response, f"{{{SAML_NS}}}Assertion", ID="_assert1",
                                 Version="2.0", IssueInstant=nb)
    etree.SubElement(assertion, f"{{{SAML_NS}}}Issuer").text = "https://idp.example.com"
    subject = etree.SubElement(assertion, f"{{{SAML_NS}}}Subject")
    etree.SubElement(subject, f"{{{SAML_NS}}}NameID").text = username
    conditions = etree.SubElement(assertion, f"{{{SAML_NS}}}Conditions",
                                  NotBefore=nb, NotOnOrAfter=na)
    ar = etree.SubElement(conditions, f"{{{SAML_NS}}}AudienceRestriction")
    etree.SubElement(ar, f"{{{SAML_NS}}}Audience").text = audience
    stmt = etree.SubElement(assertion, f"{{{SAML_NS}}}AttributeStatement")
    grp = etree.SubElement(stmt, f"{{{SAML_NS}}}Attribute", Name="groups")
    for g in groups:
        etree.SubElement(grp, f"{{{SAML_NS}}}AttributeValue").text = g

    signed_assertion = XMLSigner(
        signature_algorithm="rsa-sha256", digest_algorithm="sha256",
    ).sign(assertion, key=key_pem, cert=cert_pem, reference_uri="_assert1")
    # Replace the unsigned assertion with the signed one.
    response.replace(assertion, signed_assertion)
    return base64.b64encode(etree.tostring(response)).decode()


def _configure(db, cert_pem, **overrides):
    cfg = sso.get_config(db)
    cfg.enabled = True
    cfg.base_url = BASE_URL
    cfg.idp_sso_url = "https://idp.example.com/sso"
    cfg.idp_x509_cert = cert_pem
    cfg.attr_groups = "groups"
    cfg.role_mappings = {"meyes-admins": "admin", "meyes-ops": "operator"}
    cfg.default_role = "viewer"
    for key, value in overrides.items():
        setattr(cfg, key, value)
    db.flush()
    return cfg


# --------------------------------------------------------------------------- #
def test_status_default_disabled(client):
    resp = client.get("/api/v1/sso/status")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


def test_config_requires_admin(client, db_session, auth_headers):
    resp = client.get("/api/v1/sso/config", headers=auth_headers)
    assert resp.status_code == 200
    body = client.put("/api/v1/sso/config", headers=auth_headers, json={
        "enabled": True, "base_url": BASE_URL, "idp_sso_url": "https://idp/sso",
        "role_mappings": {"g": "operator"},
    })
    assert body.status_code == 200
    assert body.json()["acs_url"] == f"{BASE_URL}/api/v1/auth/sso/acs"


def test_metadata_xml(client, db_session):
    sso.get_config(db_session)
    db_session.query(SsoConfig).update({"base_url": BASE_URL})
    db_session.commit()
    resp = client.get("/api/v1/sso/metadata")
    assert resp.status_code == 200
    assert "EntityDescriptor" in resp.text
    assert "AssertionConsumerService" in resp.text


def test_authn_request_redirect(db_session):
    cfg = sso.get_config(db_session)
    cfg.base_url = BASE_URL
    cfg.idp_sso_url = "https://idp.example.com/sso"
    url = sso.build_authn_request_redirect(cfg)
    assert url.startswith("https://idp.example.com/sso?")
    assert "SAMLRequest=" in url


def test_role_mapping_highest_wins(db_session, idp_keypair):
    _, cert_pem = idp_keypair
    cfg = _configure(db_session, cert_pem)
    assert sso.map_role(cfg, ["meyes-ops", "meyes-admins"]) == "admin"
    assert sso.map_role(cfg, ["meyes-ops"]) == "operator"
    assert sso.map_role(cfg, ["unknown"]) == "viewer"


def test_acs_roundtrip_provisions_user(client, db_session, idp_keypair):
    key_pem, cert_pem = idp_keypair
    _configure(db_session, cert_pem)
    db_session.commit()
    saml_response = _signed_response(key_pem, cert_pem, username="alice@example.com")
    resp = client.post("/api/v1/auth/sso/acs", data={"SAMLResponse": saml_response},
                       follow_redirects=False)
    assert resp.status_code == 302, resp.text
    assert "token=" in resp.headers["location"]

    from sqlalchemy import select

    from app.models import User
    user = db_session.scalar(select(User).where(User.username == "alice@example.com"))
    assert user is not None
    assert user.role == "admin"
    assert user.auth_source == "saml"


def test_acs_rejects_tampered_signature(client, db_session, idp_keypair):
    key_pem, cert_pem = idp_keypair
    _configure(db_session, cert_pem)
    db_session.commit()
    saml_response = _signed_response(key_pem, cert_pem)
    raw = base64.b64decode(saml_response).replace(b"alice@example.com", b"evil@example.com")
    resp = client.post("/api/v1/auth/sso/acs",
                       data={"SAMLResponse": base64.b64encode(raw).decode()},
                       follow_redirects=False)
    assert resp.status_code == 400


def test_acs_rejects_wrong_audience(client, db_session, idp_keypair):
    key_pem, cert_pem = idp_keypair
    _configure(db_session, cert_pem)
    db_session.commit()
    saml_response = _signed_response(key_pem, cert_pem, audience="https://wrong.example.com")
    resp = client.post("/api/v1/auth/sso/acs", data={"SAMLResponse": saml_response},
                       follow_redirects=False)
    assert resp.status_code == 400
