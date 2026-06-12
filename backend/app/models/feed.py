import secrets

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


def generate_token() -> str:
    return secrets.token_hex(16)


class Feed(Base, TimestampMixin):
    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(16))  # networks|tag|blocklist|fqdn
    tag_id: Mapped[int | None] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), nullable=True)
    token: Mapped[str] = mapped_column(String(64), default=generate_token)
    enabled: Mapped[bool] = mapped_column(default=True)

    tag = relationship("Tag", lazy="joined")


class BlocklistEntry(Base, TimestampMixin):
    __tablename__ = "blocklist_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(String(64), unique=True)  # IP or CIDR
    reason: Mapped[str] = mapped_column(String(255), default="")
    created_by: Mapped[str] = mapped_column(String(64), default="")
