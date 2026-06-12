from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Host(Base, TimestampMixin):
    """Composite Infoblox-style object: one host = IP allocation + A + PTR + DHCP reservation."""

    __tablename__ = "hosts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # FQDN
    ip_address_id: Mapped[int | None] = mapped_column(
        ForeignKey("ip_addresses.id", ondelete="SET NULL"), nullable=True
    )
    a_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("records.id", ondelete="SET NULL"), nullable=True
    )
    ptr_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("records.id", ondelete="SET NULL"), nullable=True
    )
    reservation_id: Mapped[int | None] = mapped_column(
        ForeignKey("dhcp_reservations.id", ondelete="SET NULL"), nullable=True
    )
