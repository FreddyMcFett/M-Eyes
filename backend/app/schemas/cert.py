from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CertOut(ORMModel):
    id: int
    name: str
    kind: str
    status: str
    subject: str
    issuer: str
    san: list[str] | None
    serial: str
    fingerprint_sha256: str
    key_type: str
    is_self_signed: bool
    not_before: datetime | None
    not_after: datetime | None
    has_key: bool = False
    has_csr: bool = False
    has_chain: bool = False
    created_at: datetime
    updated_at: datetime


class SubjectIn(BaseModel):
    common_name: str = Field(min_length=1, max_length=253)
    organization: str = ""
    organizational_unit: str = ""
    country: str = ""
    state: str = ""
    locality: str = ""
    email: str = ""


class SelfSignedIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    subject: SubjectIn
    sans: list[str] = []
    days: int = Field(default=825, ge=1, le=3650)
    key_type: str = "rsa"
    activate: bool = True


class CsrIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    subject: SubjectIn
    sans: list[str] = []
    key_type: str = "rsa"


class ImportSignedIn(BaseModel):
    cert_pem: str
    chain_pem: str | None = None
    activate: bool = True


class ImportServerIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    cert_pem: str
    key_pem: str
    chain_pem: str | None = None
    activate: bool = False


class ImportCaIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    cert_pem: str


class TlsStatusOut(BaseModel):
    https_ready: bool
    active_certificate: CertOut | None
    tls_dir: str
    settings: dict[str, str]
