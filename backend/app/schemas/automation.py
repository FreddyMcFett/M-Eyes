from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import TimestampedOut


class AutomationRuleBase(BaseModel):
    name: str
    kind: str
    enabled: bool = True
    interval_seconds: int = 3600
    config: dict = {}


class AutomationRuleIn(AutomationRuleBase):
    pass


class AutomationRuleUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    interval_seconds: int | None = None
    config: dict | None = None


class AutomationRuleOut(AutomationRuleBase, TimestampedOut):
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    last_status: str = "pending"
    last_message: str = ""
    run_count: int = 0


class AutomationRunResult(BaseModel):
    status: str
    message: str
