"""Certificate lifecycle: self-signed, CSR -> sign -> import, CA import, activate."""

import datetime as dt

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

BASE = "/api/v1/system/certificates"


def _sign_csr(csr_pem: str, ca_key, ca_cert) -> str:
    """Act as a corporate CA: sign a submitted CSR and return the leaf PEM."""
    csr = x509.load_pem_x509_csr(csr_pem.encode())
    now = dt.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=1))
        .not_valid_after(now + dt.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def _make_ca():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Corp Root CA")])
    now = dt.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return key, cert


def test_self_signed_create_and_activate(client, auth_headers):
    resp = client.post(
        f"{BASE}/self-signed",
        json={
            "name": "Bootstrap",
            "subject": {"common_name": "ddi.example.com", "organization": "Example"},
            "sans": ["ddi.example.com", "10.0.0.5"],
            "activate": True,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["is_self_signed"] is True
    assert body["has_key"] is True
    assert "ddi.example.com" in body["san"]

    status = client.get(f"{BASE}/status", headers=auth_headers).json()
    assert status["https_ready"] is True
    assert status["active_certificate"]["name"] == "Bootstrap"


def test_csr_flow_sign_and_import(client, auth_headers):
    # 1. generate a key + CSR in M-Eyes
    resp = client.post(
        f"{BASE}/csr",
        json={
            "name": "Prod cert",
            "subject": {"common_name": "prod.example.com", "organization": "Example"},
            "sans": ["prod.example.com", "www.example.com"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    cert_id = resp.json()["id"]
    assert resp.json()["status"] == "pending_csr"
    assert resp.json()["has_csr"] is True

    # download the CSR PEM
    csr_pem = client.get(f"{BASE}/{cert_id}/download?part=csr", headers=auth_headers).text
    assert "BEGIN CERTIFICATE REQUEST" in csr_pem

    # 2. corporate CA signs it
    ca_key, ca_cert = _make_ca()
    leaf_pem = _sign_csr(csr_pem, ca_key, ca_cert)
    chain_pem = ca_cert.public_bytes(serialization.Encoding.PEM).decode()

    # 3. import the signed cert and activate
    resp = client.post(
        f"{BASE}/{cert_id}/import-cert",
        json={"cert_pem": leaf_pem, "chain_pem": chain_pem, "activate": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["has_chain"] is True
    assert body["is_self_signed"] is False


def test_import_cert_rejects_key_mismatch(client, auth_headers):
    resp = client.post(
        f"{BASE}/csr",
        json={"name": "Mismatch", "subject": {"common_name": "a.example.com"}},
        headers=auth_headers,
    )
    cert_id = resp.json()["id"]

    # sign a *different* key's CSR -> public key won't match the stored private key
    other_key, ca_cert = _make_ca()
    bogus = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "a.example.com")]))
        .issuer_name(ca_cert.subject)
        .public_key(other_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime.utcnow() - dt.timedelta(minutes=1))
        .not_valid_after(dt.datetime.utcnow() + dt.timedelta(days=1))
        .sign(other_key, hashes.SHA256())
        .public_bytes(serialization.Encoding.PEM)
        .decode()
    )
    resp = client.post(
        f"{BASE}/{cert_id}/import-cert", json={"cert_pem": bogus}, headers=auth_headers
    )
    assert resp.status_code == 422
    assert "does not match" in resp.json()["detail"]


def test_import_ca_and_bundle(client, auth_headers):
    _, ca_cert = _make_ca()
    ca_pem = ca_cert.public_bytes(serialization.Encoding.PEM).decode()
    resp = client.post(
        f"{BASE}/ca", json={"name": "Corp Root", "cert_pem": ca_pem}, headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["kind"] == "ca"
    assert resp.json()["status"] == "trusted"

    listing = client.get(BASE, headers=auth_headers).json()
    assert any(c["kind"] == "ca" and c["name"] == "Corp Root" for c in listing)


def test_cannot_delete_active(client, auth_headers):
    resp = client.post(
        f"{BASE}/self-signed",
        json={"name": "Active", "subject": {"common_name": "x.example.com"}, "activate": True},
        headers=auth_headers,
    )
    cert_id = resp.json()["id"]
    resp = client.delete(f"{BASE}/{cert_id}", headers=auth_headers)
    assert resp.status_code == 422
    assert "active" in resp.json()["detail"].lower()


def test_import_full_server_cert_rejects_bad_key(client, auth_headers):
    _, ca_cert = _make_ca()
    leaf_pem = ca_cert.public_bytes(serialization.Encoding.PEM).decode()
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_pem = wrong_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    resp = client.post(
        f"{BASE}/import-server",
        json={"name": "bad", "cert_pem": leaf_pem, "key_pem": key_pem},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_certs_require_auth(client):
    assert client.get(BASE).status_code == 401
