from pydantic import BaseModel

from app.schemas.common import TimestampedOut


class DhcpSubnetIn(BaseModel):
    network_id: int
    enabled: bool = True
    valid_lifetime: int | None = None
    max_valid_lifetime: int | None = None
    renew_timer: int | None = None
    rebind_timer: int | None = None
    next_server: str | None = None
    boot_file_name: str | None = None
    client_class: str | None = None


class DhcpSubnetUpdate(BaseModel):
    enabled: bool | None = None
    valid_lifetime: int | None = None
    max_valid_lifetime: int | None = None
    renew_timer: int | None = None
    rebind_timer: int | None = None
    next_server: str | None = None
    boot_file_name: str | None = None
    client_class: str | None = None


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
    valid_lifetime: int | None = None
    max_valid_lifetime: int | None = None
    renew_timer: int | None = None
    rebind_timer: int | None = None
    next_server: str | None = None
    boot_file_name: str | None = None
    client_class: str | None = None
    cidr: str = ""
    ranges: list[DhcpRangeOut] = []
    reservations: list[DhcpReservationOut] = []
    options: list[DhcpOptionOut] = []
