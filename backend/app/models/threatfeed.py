from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# Feeds can only block or return an empty answer; substitution needs a per-rule value.
THREAT_FEED_ACTIONS = ("block", "nodata")


class RpzThreatFeed(Base, TimestampMixin):
    """External threat-intelligence domain feed merged into the DNS firewall RPZ.

    The feed URL is fetched (plain domain list or hosts-file format), validated
    and cached in `domains`; every entry is published with the feed's action,
    after the manual rules so explicit passthru rules always win.
    """

    __tablename__ = "rpz_threat_feeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(512))
    action: Mapped[str] = mapped_column(String(16), default="block")
    enabled: Mapped[bool] = mapped_column(default=True)
    refresh_hours: Mapped[int] = mapped_column(Integer, default=24)
    last_synced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str] = mapped_column(String(255), default="")
    entry_count: Mapped[int] = mapped_column(Integer, default=0)
    domains: Mapped[str] = mapped_column(Text, default="")  # newline-separated, validated
