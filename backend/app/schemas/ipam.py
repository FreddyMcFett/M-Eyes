from pydantic import BaseModel

from app.schemas.common import TagOut, TimestampedOut


class NetworkIn(BaseModel):
    cidr: str
    name: str = ""
    description: str = ""
    is_container: bool = False
    vlan: int | None = None
    site: str = ""
    tag_ids: list[int] | None = None


class SubnetAllocateIn(BaseModel):
    prefixlen: int
    name: str = ""
    description: str = ""
    is_container: bool = False
    vlan: int | None = None
    site: str = ""
    tag_ids: list[int] | None = None


class NetworkUpdate(BaseModel):
    cidr: str | None = None
    name: str | None = None
    description: str | None = None
    is_container: bool | None = None
    vlan: int | None = None
    site: str | None = None
    tag_ids: list[int] | None = None


class UtilizationOut(BaseModel):
    total: int
    used: int
    dhcp_range: int
    free: int
    percent: float


class NetworkOut(TimestampedOut):
    cidr: str
    name: str
    description: str
    is_container: bool
    vlan: int | None
    site: str
    parent_id: int | None
    tags: list[TagOut] = []
    utilization: UtilizationOut | None = None


class IPAddressIn(BaseModel):
    ip: str | None = None  # omit to auto-allocate
    status: str = "used"
    hostname: str = ""
    mac: str = ""
    description: str = ""
    tag_ids: list[int] | None = None


class IPAddressUpdate(BaseModel):
    status: str | None = None
    hostname: str | None = None
    mac: str | None = None
    description: str | None = None
    tag_ids: list[int] | None = None


class IPAddressOut(TimestampedOut):
    network_id: int
    ip: str
    status: str
    hostname: str
    mac: str
    description: str
    tags: list[TagOut] = []
