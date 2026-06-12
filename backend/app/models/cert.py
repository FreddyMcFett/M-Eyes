from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class Certificate(Base):
    """X.509 material managed from the UI.

    A single table holds three kinds of object, distinguished by ``kind``:

    * ``server`` — a TLS server certificate (with private key) used to terminate
      HTTPS. Exactly one server certificate may be ``active`` at a time.
    * ``ca`` — a trusted CA / trust-anchor certificate (no private key) added to
      the trust bundle that is published to clients.

    Server certificates move through ``status``: ``pending_csr`` (a key and CSR
    were generated and we are waiting for the signed certificate), ``inactive``
    (a complete key+certificate that is not currently serving) and ``active``.
    """

    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="server", index=True)  # server|ca
    status: Mapped[str] = mapped_column(String(16), default="inactive", index=True)

    subject: Mapped[str] = mapped_column(String(512), default="")
    issuer: Mapped[str] = mapped_column(String(512), default="")
    san: Mapped[list | None] = mapped_column(JSON, nullable=True)

    serial: Mapped[str] = mapped_column(String(128), default="")
    fingerprint_sha256: Mapped[str] = mapped_column(String(128), default="")
    key_type: Mapped[str] = mapped_column(String(32), default="")
    is_self_signed: Mapped[bool] = mapped_column(Boolean, default=False)

    not_before: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    not_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    private_key_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    csr_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    cert_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    chain_pem: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
