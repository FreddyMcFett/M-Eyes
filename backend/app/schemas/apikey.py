from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import TimestampedOut


class ApiKeyIn(BaseModel):
    name: str
    role: str = "admin"
    expires_in_days: int | None = None  # None = never expires


class ApiKeyOut(TimestampedOut):
    name: str
    prefix: str
    role: str
    expires_at: datetime | None
    last_used_at: datetime | None


class ApiKeyCreated(ApiKeyOut):
    key: str = ""  # full key, shown exactly once
