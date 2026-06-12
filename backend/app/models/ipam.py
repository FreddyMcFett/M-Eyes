from sqlalchemy import Column, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

network_tags = Table(
    "network_tags",
    Base.metadata,
    Column("network_id", ForeignKey("networks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

ip_tags = Table(
    "ip_tags",
    Base.metadata,
    Column("ip_id", ForeignKey("ip_addresses.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base, TimestampMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    color: Mapped[str] = mapped_column(String(16), default="#4caf50")


class Network(Base, TimestampMixin):
    __tablename__ = "networks"

    id: Mapped[int] = mapped_column(primary_key=True)
    cidr: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    description: Mapped[str] = mapped_column(String(255), default="")
    is_container: Mapped[bool] = mapped_column(default=False)
    vlan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    site: Mapped[str] = mapped_column(String(128), default="")
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("networks.id", ondelete="SET NULL"), nullable=True
    )

    parent: Mapped["Network | None"] = relationship(remote_side=[id], backref="children")
    tags: Mapped[list[Tag]] = relationship(secondary=network_tags, lazy="selectin")
    ip_addresses: Mapped[list["IPAddress"]] = relationship(
        back_populates="network", cascade="all, delete-orphan"
    )


class IPAddress(Base, TimestampMixin):
    __tablename__ = "ip_addresses"
    __table_args__ = (UniqueConstraint("network_id", "ip", name="uq_network_ip"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    network_id: Mapped[int] = mapped_column(ForeignKey("networks.id", ondelete="CASCADE"))
    ip: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), default="used")  # used|reserved|dhcp
    hostname: Mapped[str] = mapped_column(String(255), default="")
    mac: Mapped[str] = mapped_column(String(32), default="")
    description: Mapped[str] = mapped_column(String(255), default="")

    network: Mapped[Network] = relationship(back_populates="ip_addresses")
    tags: Mapped[list[Tag]] = relationship(secondary=ip_tags, lazy="selectin")
