from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.ipam import Tag

ASSET_TYPES = (
    "server",
    "workstation",
    "laptop",
    "mobile",
    "network",      # switch/router/firewall
    "firewall",
    "iot",
    "printer",
    "virtual",
    "container",
    "other",
)

ASSET_STATUSES = ("in_service", "in_stock", "maintenance", "retired", "decommissioned")
ASSET_CRITICALITY = ("low", "medium", "high", "critical")

asset_tags = Table(
    "asset_tags",
    Base.metadata,
    Column("asset_id", ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Asset(Base, TimestampMixin):
    """A CMDB asset, cross-referenced to DDI data (IPs, MACs, hostnames).

    Assets are linked to the network fabric through their interfaces, so an
    operator can pivot from an IP address or DHCP lease straight to the owning
    device, its owner, location and lifecycle state.
    """

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    asset_type: Mapped[str] = mapped_column(String(32), default="server")
    status: Mapped[str] = mapped_column(String(32), default="in_service")
    criticality: Mapped[str] = mapped_column(String(16), default="medium")

    owner: Mapped[str] = mapped_column(String(128), default="")
    location: Mapped[str] = mapped_column(String(128), default="")
    department: Mapped[str] = mapped_column(String(128), default="")
    vendor: Mapped[str] = mapped_column(String(128), default="")
    model: Mapped[str] = mapped_column(String(128), default="")
    serial_number: Mapped[str] = mapped_column(String(128), default="")
    operating_system: Mapped[str] = mapped_column(String(128), default="")
    description: Mapped[str] = mapped_column(Text, default="")

    # Provenance: where this asset record came from (manual, discovery, an integration slug).
    source: Mapped[str] = mapped_column(String(64), default="manual")
    external_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tags: Mapped[list[Tag]] = relationship(secondary=asset_tags, lazy="selectin")
    interfaces: Mapped[list["AssetInterface"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", lazy="selectin"
    )


class AssetInterface(Base, TimestampMixin):
    """A network interface on an asset — the join between CMDB and DDI.

    `ip_id` links to a managed IPAM address when one exists; `ip` / `mac` keep the
    raw values so discovery and lease data can populate an interface before (or
    without) a formal IPAM allocation.
    """

    __tablename__ = "asset_interfaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64), default="")
    mac: Mapped[str] = mapped_column(String(32), default="", index=True)
    ip: Mapped[str] = mapped_column(String(64), default="", index=True)
    hostname: Mapped[str] = mapped_column(String(255), default="")
    ip_id: Mapped[int | None] = mapped_column(
        ForeignKey("ip_addresses.id", ondelete="SET NULL"), nullable=True
    )

    asset: Mapped[Asset] = relationship(back_populates="interfaces")
