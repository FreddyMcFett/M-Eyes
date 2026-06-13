"""X.509 certificate lifecycle for HTTPS, managed from the UI.

The service wraps :mod:`cryptography` to provide the operations an enterprise
admin expects: generate a self-signed bootstrap certificate, generate a private
key + CSR for signing by a corporate CA, import the signed certificate back,
import full key+certificate bundles, import trusted CA certificates, activate a
server certificate and publish (materialize) the active material to the TLS
directory consumed by the terminating proxy.

Private key material never leaves the backend in API responses; only public
certificates, CSRs and metadata are returned.
"""

from __future__ import annotations

import datetime as dt
import os
import tempfile
from dataclasses import dataclass

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtensionOID, NameOID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Certificate
from app.services import app_settings

_NAME_OIDS = {
    "CN": NameOID.COMMON_NAME,
    "O": NameOID.ORGANIZATION_NAME,
    "OU": NameOID.ORGANIZATIONAL_UNIT_NAME,
    "C": NameOID.COUNTRY_NAME,
    "ST": NameOID.STATE_OR_PROVINCE_NAME,
    "L": NameOID.LOCALITY_NAME,
    "emailAddress": NameOID.EMAIL_ADDRESS,
}


class CertError(ValueError):
    """Raised for invalid certificate input or illegal lifecycle transitions."""


@dataclass
class SubjectFields:
    common_name: str
    organization: str = ""
    organizational_unit: str = ""
    country: str = ""
    state: str = ""
    locality: str = ""
    email: str = ""

    def to_x509_name(self) -> x509.Name:
        attrs = []
        mapping = [
            (NameOID.COMMON_NAME, self.common_name),
            (NameOID.ORGANIZATION_NAME, self.organization),
            (NameOID.ORGANIZATIONAL_UNIT_NAME, self.organizational_unit),
            (NameOID.COUNTRY_NAME, self.country),
            (NameOID.STATE_OR_PROVINCE_NAME, self.state),
            (NameOID.LOCALITY_NAME, self.locality),
            (NameOID.EMAIL_ADDRESS, self.email),
        ]
        for oid, value in mapping:
            if value:
                attrs.append(x509.NameAttribute(oid, value))
        if not attrs:
            raise CertError("A common name is required")
        return x509.Name(attrs)


# --------------------------------------------------------------------------- #
# Parsing / metadata helpers
# --------------------------------------------------------------------------- #
def _san_list(values: list[str] | None) -> list[x509.GeneralName]:
    names: list[x509.GeneralName] = []
    for raw in values or []:
        value = raw.strip()
        if not value:
            continue
        try:
            names.append(x509.IPAddress(_ip(value)))
        except ValueError:
            names.append(x509.DNSName(value))
    return names


def _ip(value: str):
    import ipaddress

    return ipaddress.ip_address(value)


def load_cert(pem: str) -> x509.Certificate:
    try:
        return x509.load_pem_x509_certificate(pem.encode())
    except Exception as exc:  # noqa: BLE001
        raise CertError(f"Not a valid PEM certificate: {exc}") from exc


def _key_type(public_key) -> str:
    if isinstance(public_key, rsa.RSAPublicKey):
        return f"RSA {public_key.key_size}"
    if isinstance(public_key, ec.EllipticCurvePublicKey):
        return f"EC {public_key.curve.name}"
    return public_key.__class__.__name__


def _sans_from_cert(cert: x509.Certificate) -> list[str]:
    try:
        ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
    except x509.ExtensionNotFound:
        return []
    result: list[str] = []
    for name in ext.value:
        if isinstance(name, x509.DNSName):
            result.append(name.value)
        elif isinstance(name, x509.IPAddress):
            result.append(str(name.value))
    return result


def _apply_cert_metadata(row: Certificate, cert: x509.Certificate) -> None:
    row.subject = cert.subject.rfc4514_string()
    row.issuer = cert.issuer.rfc4514_string()
    row.san = _sans_from_cert(cert)
    row.serial = format(cert.serial_number, "x")
    row.fingerprint_sha256 = cert.fingerprint(hashes.SHA256()).hex(":")
    row.key_type = _key_type(cert.public_key())
    # Store naive UTC to match the rest of the schema; the *_utc accessors are
    # the non-deprecated way to read these (the bare properties return naive
    # datetimes and emit a CryptographyDeprecationWarning).
    row.not_before = cert.not_valid_before_utc.replace(tzinfo=None)
    row.not_after = cert.not_valid_after_utc.replace(tzinfo=None)
    row.is_self_signed = cert.issuer == cert.subject


# --------------------------------------------------------------------------- #
# Key / certificate generation
# --------------------------------------------------------------------------- #
def _new_key(key_type: str):
    if key_type.lower().startswith("ec"):
        return ec.generate_private_key(ec.SECP256R1())
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _key_to_pem(key) -> str:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL
        if isinstance(key, rsa.RSAPrivateKey)
        else serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _cert_to_pem(cert: x509.Certificate) -> str:
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def generate_self_signed(
    db: Session,
    name: str,
    subject: SubjectFields,
    sans: list[str] | None = None,
    days: int = 825,
    key_type: str = "rsa",
    activate_now: bool = True,
) -> Certificate:
    key = _new_key(key_type)
    x509_subject = subject.to_x509_name()
    san_names = _san_list(sans or [subject.common_name])
    now = dt.datetime.now(dt.UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509_subject)
        .issuer_name(x509_subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName(san_names), critical=False)
    )
    cert = builder.sign(key, hashes.SHA256())
    row = Certificate(
        name=name,
        kind="server",
        status="inactive",
        private_key_pem=_key_to_pem(key),
        cert_pem=_cert_to_pem(cert),
    )
    _apply_cert_metadata(row, cert)
    db.add(row)
    db.flush()
    if activate_now:
        activate(db, row.id)
    return row


def generate_csr(
    db: Session,
    name: str,
    subject: SubjectFields,
    sans: list[str] | None = None,
    key_type: str = "rsa",
) -> Certificate:
    key = _new_key(key_type)
    san_names = _san_list(sans or [subject.common_name])
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(subject.to_x509_name())
        .add_extension(x509.SubjectAlternativeName(san_names), critical=False)
        .sign(key, hashes.SHA256())
    )
    row = Certificate(
        name=name,
        kind="server",
        status="pending_csr",
        subject=csr.subject.rfc4514_string(),
        san=[s for s in (sans or [subject.common_name]) if s],
        key_type=_key_type(key.public_key()),
        private_key_pem=_key_to_pem(key),
        csr_pem=csr.public_bytes(serialization.Encoding.PEM).decode(),
    )
    db.add(row)
    db.flush()
    return row


# --------------------------------------------------------------------------- #
# Imports
# --------------------------------------------------------------------------- #
def _public_numbers_match(key_pem: str, cert: x509.Certificate) -> bool:
    key = serialization.load_pem_private_key(key_pem.encode(), password=None)
    return key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    ) == cert.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )


def import_signed_cert(
    db: Session, cert_id: int, cert_pem: str, chain_pem: str | None = None,
    activate_now: bool = True,
) -> Certificate:
    row = db.get(Certificate, cert_id)
    if row is None or row.kind != "server":
        raise CertError("Unknown server certificate")
    if not row.private_key_pem:
        raise CertError("This entry has no private key to match against")
    cert = load_cert(cert_pem)
    if not _public_numbers_match(row.private_key_pem, cert):
        raise CertError("The certificate does not match this entry's private key / CSR")
    row.cert_pem = _cert_to_pem(cert)
    row.chain_pem = (chain_pem or "").strip() or None
    row.csr_pem = None
    row.status = "inactive"
    _apply_cert_metadata(row, cert)
    db.flush()
    if activate_now:
        activate(db, row.id)
    return row


def import_server_cert(
    db: Session, name: str, cert_pem: str, key_pem: str, chain_pem: str | None = None,
    activate_now: bool = False,
) -> Certificate:
    cert = load_cert(cert_pem)
    try:
        serialization.load_pem_private_key(key_pem.encode(), password=None)
    except Exception as exc:  # noqa: BLE001
        raise CertError(f"Not a valid private key: {exc}") from exc
    if not _public_numbers_match(key_pem, cert):
        raise CertError("The private key does not match the certificate")
    row = Certificate(
        name=name,
        kind="server",
        status="inactive",
        private_key_pem=key_pem.strip() + "\n",
        cert_pem=_cert_to_pem(cert),
        chain_pem=(chain_pem or "").strip() or None,
    )
    _apply_cert_metadata(row, cert)
    db.add(row)
    db.flush()
    if activate_now:
        activate(db, row.id)
    return row


def import_ca(db: Session, name: str, cert_pem: str) -> Certificate:
    cert = load_cert(cert_pem)
    row = Certificate(name=name, kind="ca", status="trusted", cert_pem=_cert_to_pem(cert))
    _apply_cert_metadata(row, cert)
    db.add(row)
    db.flush()
    return row


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #
def activate(db: Session, cert_id: int) -> Certificate:
    row = db.get(Certificate, cert_id)
    if row is None or row.kind != "server":
        raise CertError("Unknown server certificate")
    if not (row.cert_pem and row.private_key_pem):
        raise CertError("Certificate is incomplete (missing signed certificate or key)")
    for other in db.scalars(
        select(Certificate).where(Certificate.kind == "server", Certificate.status == "active")
    ).all():
        if other.id != row.id:
            other.status = "inactive"
    row.status = "active"
    db.flush()
    materialize(db)
    return row


def delete(db: Session, cert_id: int) -> None:
    row = db.get(Certificate, cert_id)
    if row is None:
        raise CertError("Not found")
    if row.kind == "server" and row.status == "active":
        raise CertError("Cannot delete the active certificate; activate another one first")
    db.delete(row)
    db.flush()
    if row.kind == "ca":
        materialize(db)


def active_server_cert(db: Session) -> Certificate | None:
    return db.scalar(
        select(Certificate).where(Certificate.kind == "server", Certificate.status == "active")
    )


# --------------------------------------------------------------------------- #
# Materialization — publish active material for the TLS-terminating proxy
# --------------------------------------------------------------------------- #
def _atomic_write(path: str, content: str, mode: int = 0o644) -> None:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _options_snippet(db: Session) -> str:
    values = app_settings.get_all(db)
    min_version = values.get("tls_min_version", "TLSv1.2")
    protocols = "TLSv1.2 TLSv1.3" if min_version == "TLSv1.2" else "TLSv1.3"
    lines = [
        f"ssl_protocols {protocols};",
        "ssl_prefer_server_ciphers on;",
        "ssl_session_cache shared:MEyesTLS:10m;",
        "ssl_session_timeout 1d;",
    ]
    if app_settings.get_bool(db, "hsts_enabled"):
        try:
            max_age = int(values.get("hsts_max_age", "31536000"))
        except ValueError:
            max_age = 31536000
        lines.append(
            f'add_header Strict-Transport-Security "max-age={max_age}; includeSubDomains" always;'
        )
    return "\n".join(lines) + "\n"


def _redirect_snippet(db: Session) -> str:
    if app_settings.get_bool(db, "https_redirect"):
        return "return 301 https://$host$request_uri;\n"
    return "# HTTP-to-HTTPS redirect disabled in System settings\n"


def materialize(db: Session) -> dict:
    """Write the active server certificate, key, trust bundle and proxy snippets.

    Safe to call any time; missing pieces are simply skipped. Returns a summary
    used by the diagnostics / status endpoints. Never raises on I/O problems so
    that a settings save cannot be blocked by a read-only TLS directory.
    """
    tls_dir = get_settings().tls_dir
    written: list[str] = []
    try:
        os.makedirs(tls_dir, exist_ok=True)
        active = active_server_cert(db)
        if active and active.cert_pem and active.private_key_pem:
            fullchain = active.cert_pem.strip() + "\n"
            if active.chain_pem:
                fullchain += active.chain_pem.strip() + "\n"
            _atomic_write(os.path.join(tls_dir, "server.crt"), fullchain)
            _atomic_write(os.path.join(tls_dir, "server.key"), active.private_key_pem, mode=0o600)
            written += ["server.crt", "server.key"]

        cas = db.scalars(select(Certificate).where(Certificate.kind == "ca")).all()
        bundle = "".join((c.cert_pem or "").strip() + "\n" for c in cas if c.cert_pem)
        _atomic_write(os.path.join(tls_dir, "ca-bundle.crt"), bundle)
        _atomic_write(os.path.join(tls_dir, "options.conf"), _options_snippet(db))
        _atomic_write(os.path.join(tls_dir, "http-redirect.conf"), _redirect_snippet(db))
        # Touch a reload marker the proxy sidecar watches to trigger `nginx -s reload`.
        _atomic_write(
            os.path.join(tls_dir, "reload"), dt.datetime.now(dt.UTC).isoformat() + "\n"
        )
        written += ["ca-bundle.crt", "options.conf", "http-redirect.conf"]
        return {"tls_dir": tls_dir, "written": written, "ok": True}
    except OSError as exc:
        return {"tls_dir": tls_dir, "written": written, "ok": False, "error": str(exc)}


def ensure_bootstrap(db: Session) -> Certificate | None:
    """On startup guarantee an active server certificate exists.

    If none is configured, generate a self-signed certificate for the configured
    hostname so HTTPS works out of the box, then publish it. Best-effort: any
    failure is swallowed so it can never block application start-up.
    """
    try:
        if active_server_cert(db) is not None:
            materialize(db)
            return None
        settings = get_settings()
        hostname = app_settings.get(db, "system_hostname") or settings.tls_default_hostname
        org = app_settings.get(db, "organization_name") or "M-Eyes"
        sans = [hostname, "localhost"]
        cert = generate_self_signed(
            db,
            name=f"Self-signed ({hostname})",
            subject=SubjectFields(common_name=hostname, organization=org),
            sans=sans,
            activate_now=True,
        )
        db.commit()
        return cert
    except Exception:  # noqa: BLE001
        db.rollback()
        return None
