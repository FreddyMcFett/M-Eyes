from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel, TagOut, TimestampedOut


class AssetInterfaceIn(BaseModel):
    name: str = ""
    mac: str = ""
    ip: str = ""
    hostname: str = ""
    ip_id: int | None = None


class AssetInterfaceOut(ORMModel):
    id: int
    name: str
    mac: str
    ip: str
    hostname: str
    ip_id: int | None


class AssetBase(BaseModel):
    name: str
    asset_type: str = "server"
    status: str = "in_service"
    criticality: str = "medium"
    owner: str = ""
    location: str = ""
    department: str = ""
    vendor: str = ""
    model: str = ""
    serial_number: str = ""
    operating_system: str = ""
    description: str = ""


class AssetIn(AssetBase):
    tag_ids: list[int] = []
    interfaces: list[AssetInterfaceIn] = []


class AssetUpdate(BaseModel):
    name: str | None = None
    asset_type: str | None = None
    status: str | None = None
    criticality: str | None = None
    owner: str | None = None
    location: str | None = None
    department: str | None = None
    vendor: str | None = None
    model: str | None = None
    serial_number: str | None = None
    operating_system: str | None = None
    description: str | None = None
    tag_ids: list[int] | None = None
    interfaces: list[AssetInterfaceIn] | None = None


class AssetOut(AssetBase, TimestampedOut):
    source: str
    external_id: str
    last_seen: datetime | None
    tags: list[TagOut]
    interfaces: list[AssetInterfaceOut]


class AssetSyncResult(BaseModel):
    created: int
    updated: int
    linked: int
    detail: str
