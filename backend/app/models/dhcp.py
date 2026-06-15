from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DhcpSubnet(Base, TimestampMixin):
    __tablename__ = "dhcp_subnets"

    id: Mapped[int] = mapped_column(primary_key=True)
    network_id: Mapped[int] = mapped_column(ForeignKey("networks.id", ondelete="CASCADE"), unique=True)
    enabled: Mapped[bool] = mapped_column(default=True)

    # Advanced lease timing (seconds). NULL means "inherit the global default".
    valid_lifetime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_valid_lifetime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    renew_timer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rebind_timer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # PXE / network boot and client classification (NULL/"" = not set).
    next_server: Mapped[str | None] = mapped_column(String(64), nullable=True)
    boot_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_class: Mapped[str | None] = mapped_column(String(128), nullable=True)

    network = relationship("Network", lazy="joined")
    ranges: Mapped[list["DhcpRange"]] = relationship(back_populates="subnet", cascade="all, delete-orphan")
    reservations: Mapped[list["DhcpReservation"]] = relationship(
        back_populates="subnet", cascade="all, delete-orphan"
    )
    options: Mapped[list["DhcpOption"]] = relationship(back_populates="subnet", cascade="all, delete-orphan")


class DhcpRange(Base, TimestampMixin):
    __tablename__ = "dhcp_ranges"

    id: Mapped[int] = mapped_column(primary_key=True)
    subnet_id: Mapped[int] = mapped_column(ForeignKey("dhcp_subnets.id", ondelete="CASCADE"))
    start_ip: Mapped[str] = mapped_column(String(64))
    end_ip: Mapped[str] = mapped_column(String(64))

    subnet: Mapped[DhcpSubnet] = relationship(back_populates="ranges")


class DhcpReservation(Base, TimestampMixin):
    __tablename__ = "dhcp_reservations"
    __table_args__ = (UniqueConstraint("subnet_id", "mac", name="uq_subnet_mac"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subnet_id: Mapped[int] = mapped_column(ForeignKey("dhcp_subnets.id", ondelete="CASCADE"))
    mac: Mapped[str] = mapped_column(String(32))
    ip: Mapped[str] = mapped_column(String(64))
    hostname: Mapped[str] = mapped_column(String(255), default="")
    ip_address_id: Mapped[int | None] = mapped_column(
        ForeignKey("ip_addresses.id", ondelete="SET NULL"), nullable=True
    )

    subnet: Mapped[DhcpSubnet] = relationship(back_populates="reservations")


class DhcpOption(Base, TimestampMixin):
    __tablename__ = "dhcp_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    # NULL subnet_id means a global option
    subnet_id: Mapped[int | None] = mapped_column(
        ForeignKey("dhcp_subnets.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(64))  # routers, domain-name-servers, domain-name, ...
    value: Mapped[str] = mapped_column(String(255))

    subnet: Mapped[DhcpSubnet | None] = relationship(back_populates="options")
