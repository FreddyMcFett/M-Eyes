from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class ChangeLog(Base):
    """Append-only configuration change log. `id` is the global config version."""

    __tablename__ = "changelog"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    action: Mapped[str] = mapped_column(String(16))  # create|update|delete|rollback
    object_type: Mapped[str] = mapped_column(String(64), index=True)
    object_id: Mapped[int] = mapped_column(Integer, index=True)
    summary: Mapped[str] = mapped_column(String(255), default="")
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    target: Mapped[str] = mapped_column(String(16))  # bind|kea
    status: Mapped[str] = mapped_column(String(16))  # success|failed|unreachable
    message: Mapped[str] = mapped_column(String(4096), default="")
    config_version: Mapped[int] = mapped_column(Integer, default=0)
