from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class Event(Base):
    """Operational event log (the changelog stays config-only)."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)  # debug|info|warning|error
    category: Mapped[str] = mapped_column(String(32), index=True)  # auth|ipam|dns|dhcp|deploy|feeds|system
    message: Mapped[str] = mapped_column(String(1024))
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AppSetting(Base):
    """Key/value runtime settings editable from the UI (syslog, debug, log level)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), default="")
