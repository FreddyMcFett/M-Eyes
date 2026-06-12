from pydantic import BaseModel

from app.schemas.common import TimestampedOut


class ZoneIn(BaseModel):
    name: str = ""
    kind: str = "forward"
    network_id: int | None = None  # reverse zones can derive their name from a network
    default_ttl: int | None = None
    soa_mname: str | None = None
    soa_rname: str | None = None


class ZoneUpdate(BaseModel):
    default_ttl: int | None = None
    soa_mname: str | None = None
    soa_rname: str | None = None
    refresh: int | None = None
    retry: int | None = None
    expire: int | None = None
    minimum: int | None = None


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
