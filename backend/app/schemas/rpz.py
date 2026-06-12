from pydantic import BaseModel

from app.schemas.common import TimestampedOut


class RpzRuleIn(BaseModel):
    fqdn: str
    action: str = "block"
    substitute: str = ""
    comment: str = ""
    enabled: bool = True


class RpzRuleUpdate(BaseModel):
    action: str | None = None
    substitute: str | None = None
    comment: str | None = None
    enabled: bool | None = None


class RpzRuleOut(TimestampedOut):
    fqdn: str
    action: str
    substitute: str
    comment: str
    enabled: bool
