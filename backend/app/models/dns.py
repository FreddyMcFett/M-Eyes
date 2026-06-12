from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

RECORD_TYPES = ("A", "AAAA", "CNAME", "MX", "TXT", "NS", "PTR", "SRV")


class Zone(Base, TimestampMixin):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(16), default="forward")  # forward|reverse
    serial: Mapped[int] = mapped_column(Integer, default=1)
    default_ttl: Mapped[int] = mapped_column(Integer, default=3600)
    soa_mname: Mapped[str] = mapped_column(String(255), default="")
    soa_rname: Mapped[str] = mapped_column(String(255), default="")
    refresh: Mapped[int] = mapped_column(Integer, default=10800)
    retry: Mapped[int] = mapped_column(Integer, default=3600)
    expire: Mapped[int] = mapped_column(Integer, default=604800)
    minimum: Mapped[int] = mapped_column(Integer, default=3600)
    network_id: Mapped[int | None] = mapped_column(
        ForeignKey("networks.id", ondelete="SET NULL"), nullable=True
    )

    records: Mapped[list["Record"]] = relationship(back_populates="zone", cascade="all, delete-orphan")


class Record(Base, TimestampMixin):
    __tablename__ = "records"
    __table_args__ = (UniqueConstraint("zone_id", "name", "type", "value", name="uq_record"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))  # relative name, "@" for apex
    type: Mapped[str] = mapped_column(String(8))
    value: Mapped[str] = mapped_column(String(1024))
    ttl: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)  # MX / SRV
    ip_address_id: Mapped[int | None] = mapped_column(
        ForeignKey("ip_addresses.id", ondelete="SET NULL"), nullable=True
    )

    zone: Mapped[Zone] = relationship(back_populates="records")
