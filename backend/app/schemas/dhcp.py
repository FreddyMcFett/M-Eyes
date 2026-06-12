from pydantic import BaseModel

from app.schemas.common import TimestampedOut


class DhcpSubnetIn(BaseModel):
    network_id: int
    enabled: bool = True


class DhcpSubnetUpdate(BaseModel):
    enabled: bool | None = None


class DhcpRangeIn(BaseModel):
    start_ip: str
    end_ip: str


class DhcpRangeOut(TimestampedOut):
    subnet_id: int
    start_ip: str
    end_ip: str


class DhcpReservationIn(BaseModel):
    mac: str
    ip: str
    hostname: str = ""


class DhcpReservationOut(TimestampedOut):
    subnet_id: int
    mac: str
    ip: str
    hostname: str
    ip_address_id: int | None


class DhcpOptionIn(BaseModel):
    name: str
    value: str


class DhcpOptionOut(TimestampedOut):
    subnet_id: int | None
    name: str
    value: str


class DhcpSubnetOut(TimestampedOut):
    network_id: int
    enabled: bool
    cidr: str = ""
    ranges: list[DhcpRangeOut] = []
    reservations: list[DhcpReservationOut] = []
    options: list[DhcpOptionOut] = []
