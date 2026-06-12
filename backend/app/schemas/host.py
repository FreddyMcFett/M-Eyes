from pydantic import BaseModel

from app.schemas.common import TimestampedOut


class HostIn(BaseModel):
    name: str
    network_id: int
    ip: str | None = None  # omit to auto-allocate
    mac: str | None = None
    create_reservation: bool = False
    description: str = ""


class HostOut(TimestampedOut):
    name: str
    ip_address_id: int | None
    a_record_id: int | None
    ptr_record_id: int | None
    reservation_id: int | None
    ip: str | None = None
    zone_name: str | None = None
