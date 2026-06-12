from sqlalchemy import JSON, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

EXTATTR_TYPES = ("string", "integer", "email", "url", "date", "enum")

# Object types that can carry extensible attributes.
EXTATTR_OBJECT_TYPES = ("network", "ip_address", "zone", "record", "host", "dhcp_subnet")


class ExtAttrDef(Base, TimestampMixin):
    """Infoblox-style extensible attribute definition: a typed, named metadata field
    that can be attached to any DDI object."""

    __tablename__ = "extattr_defs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(16), default="string")
    comment: Mapped[str] = mapped_column(String(255), default="")
    allowed_values: Mapped[list | None] = mapped_column(JSON, nullable=True)  # enum only

    values: Mapped[list["ExtAttrValue"]] = relationship(
        back_populates="definition", cascade="all, delete-orphan"
    )


class ExtAttrValue(Base, TimestampMixin):
    __tablename__ = "extattr_values"
    __table_args__ = (
        UniqueConstraint("def_id", "object_type", "object_id", name="uq_extattr_object"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    def_id: Mapped[int] = mapped_column(ForeignKey("extattr_defs.id", ondelete="CASCADE"))
    object_type: Mapped[str] = mapped_column(String(32), index=True)
    object_id: Mapped[int] = mapped_column(Integer, index=True)
    value: Mapped[str] = mapped_column(String(255))

    definition: Mapped[ExtAttrDef] = relationship(back_populates="values", lazy="joined")
