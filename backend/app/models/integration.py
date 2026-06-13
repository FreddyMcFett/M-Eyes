from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Integration(Base, TimestampMixin):
    """A connection to an external enterprise system (Fortinet or Microsoft).

    The connector identified by `kind` knows how to test connectivity and run a
    one-way or two-way sync. Credentials are stored here and never echoed back to
    the UI in full.
    """

    __tablename__ = "integrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(48), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    base_url: Mapped[str] = mapped_column(String(512), default="")
    username: Mapped[str] = mapped_column(String(255), default="")
    secret: Mapped[str] = mapped_column(Text, default="")  # API token / password / client secret
    verify_tls: Mapped[bool] = mapped_column(Boolean, default=True)

    # Connector-specific options (e.g. ADOM, tenant id, zones to import).
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str] = mapped_column(String(32), default="never")  # never|ok|error
    last_message: Mapped[str] = mapped_column(String(512), default="")
