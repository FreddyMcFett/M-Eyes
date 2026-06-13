from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# Autonomous rule kinds handled by app.services.automation.
AUTOMATION_KINDS = (
    "discovery_sweep",     # ping-sweep a network and reconcile assets
    "asset_reconcile",     # match IPAM data into the asset inventory
    "integration_sync",    # run an enterprise integration sync
    "auto_deploy",         # deploy pending DNS/DHCP config when drift is detected
    "threat_feed_sync",    # refresh due DNS-firewall threat feeds
)


class AutomationRule(Base, TimestampMixin):
    """A scheduled, autonomous task evaluated by the background scheduler.

    `interval_seconds` defines the cadence; `config` holds kind-specific options
    (e.g. the target network or integration id). Runs are recorded on the rule and
    in the event log so the autonomy is fully auditable.
    """

    __tablename__ = "automation_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(48), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=3600)
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|ok|error|skipped
    last_message: Mapped[str] = mapped_column(String(512), default="")
    run_count: Mapped[int] = mapped_column(Integer, default=0)
