from pydantic import BaseModel

from app.schemas.common import TimestampedOut


class ViewIn(BaseModel):
    name: str
    match_clients: str = "any"
    description: str = ""
    position: int = 0


class ViewUpdate(BaseModel):
    match_clients: str | None = None
    description: str | None = None
    position: int | None = None


class ViewOut(TimestampedOut):
    name: str
    match_clients: str
    description: str
    position: int
    zone_count: int = 0


class ZoneIn(BaseModel):
    name: str = ""
    kind: str = "forward"
    network_id: int | None = None  # reverse zones can derive their name from a network
    view_id: int | None = None  # None = default view
    dnssec_enabled: bool = False
    role: str = "primary"  # primary|secondary|forward
    primaries: str = ""  # masters (secondary) or forwarders (forward), comma-separated
    default_ttl: int | None = None
    soa_mname: str | None = None
    soa_rname: str | None = None
    # Advanced DNS options
    allow_query: str = ""
    allow_transfer: str = ""
    allow_update: str = ""
    also_notify: str = ""
    forward_first: bool = False


class ZoneUpdate(BaseModel):
    view_id: int | None = None
    dnssec_enabled: bool | None = None
    role: str | None = None
    primaries: str | None = None
    default_ttl: int | None = None
    soa_mname: str | None = None
    soa_rname: str | None = None
    refresh: int | None = None
    retry: int | None = None
    expire: int | None = None
    minimum: int | None = None
    allow_query: str | None = None
    allow_transfer: str | None = None
    allow_update: str | None = None
    also_notify: str | None = None
    forward_first: bool | None = None


class ZoneOut(TimestampedOut):
    name: str
    kind: str
    serial: int
    default_ttl: int
    soa_mname: str
    soa_rname: str
    refresh: int
    retry: int
    expire: int
    minimum: int
    network_id: int | None
    view_id: int | None
    view_name: str | None = None
    dnssec_enabled: bool
    role: str
    primaries: str
    allow_query: str
    allow_transfer: str
    allow_update: str
    also_notify: str
    forward_first: bool
    record_count: int = 0


class RecordIn(BaseModel):
    name: str = "@"
    type: str
    value: str
    ttl: int | None = None
    priority: int | None = None
    auto_ptr: bool = False


class RecordUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    value: str | None = None
    ttl: int | None = None
    priority: int | None = None


class RecordOut(TimestampedOut):
    zone_id: int
    name: str
    type: str
    value: str
    ttl: int | None
    priority: int | None
    ip_address_id: int | None
