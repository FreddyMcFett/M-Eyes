from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import TimestampedOut


class RpzRuleIn(BaseModel):
    fqdn: str
    action: str = "block"
    substitute: str = ""
    comment: str = ""
    enabled: bool = True


class RpzRuleUpdate(BaseModel):
    action: str | None = None
    substitute: str | None = None
    comment: str | None = None
    enabled: bool | None = None


class RpzRuleOut(TimestampedOut):
    fqdn: str
    action: str
    substitute: str
    comment: str
    enabled: bool


class ThreatFeedIn(BaseModel):
    name: str
    url: str
    action: str = "block"
    enabled: bool = True
    refresh_hours: int = 24


class ThreatFeedUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    action: str | None = None
    enabled: bool | None = None
    refresh_hours: int | None = None


class ThreatFeedOut(TimestampedOut):
    name: str
    url: str
    action: str
    enabled: bool
    refresh_hours: int
    last_synced: datetime | None
    last_status: str
    entry_count: int
