from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ChangeLogOut(ORMModel):
    id: int
    ts: datetime
    actor: str
    action: str
    object_type: str
    object_id: int
    summary: str
    before: dict | None
    after: dict | None


class DeploymentOut(ORMModel):
    id: int
    ts: datetime
    target: str
    status: str
    message: str
    config_version: int


class EventOut(ORMModel):
    id: int
    ts: datetime
    severity: str
    category: str
    message: str
    data: dict | None


class SettingsOut(BaseModel):
    values: dict[str, str]


class SettingsIn(BaseModel):
    values: dict[str, str]
