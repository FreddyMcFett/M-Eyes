from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# block      -> NXDOMAIN (CNAME .)
# nodata     -> empty answer (CNAME *.)
# passthru   -> whitelist, exempt from the policy (CNAME rpz-passthru.)
# substitute -> answer with a replacement IP or CNAME target
RPZ_ACTIONS = ("block", "nodata", "passthru", "substitute")


class RpzRule(Base, TimestampMixin):
    """DNS firewall rule, published as a BIND Response Policy Zone entry.

    Each rule covers the domain itself and all its subdomains.
    """

    __tablename__ = "rpz_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    fqdn: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    action: Mapped[str] = mapped_column(String(16), default="block")
    substitute: Mapped[str] = mapped_column(String(255), default="")  # substitute action only
    comment: Mapped[str] = mapped_column(String(255), default="")
    enabled: Mapped[bool] = mapped_column(default=True)
