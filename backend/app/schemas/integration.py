from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import TimestampedOut


class IntegrationBase(BaseModel):
    name: str
    kind: str
    enabled: bool = True
    base_url: str = ""
    username: str = ""
    verify_tls: bool = True
    settings: dict = {}


class IntegrationIn(IntegrationBase):
    secret: str = ""


class IntegrationUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    base_url: str | None = None
    username: str | None = None
    secret: str | None = None  # blank keeps the stored secret
    verify_tls: bool | None = None
    settings: dict | None = None


class IntegrationOut(IntegrationBase, TimestampedOut):
    secret_set: bool = False
    last_sync_at: datetime | None = None
    last_status: str = "never"
    last_message: str = ""


class IntegrationTestResult(BaseModel):
    ok: bool
    message: str


class IntegrationSyncResult(BaseModel):
    ok: bool
    detail: str = ""
    message: str = ""
