from pydantic import BaseModel

from app.schemas.common import TimestampedOut


class FeedIn(BaseModel):
    slug: str
    name: str
    kind: str  # networks|tag|blocklist|fqdn
    tag_id: int | None = None
    enabled: bool = True


class FeedUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    tag_id: int | None = None


class FeedOut(TimestampedOut):
    slug: str
    name: str
    kind: str
    tag_id: int | None
    token: str
    enabled: bool
    entry_count: int = 0
    fortigate_snippet: str = ""


class BlocklistIn(BaseModel):
    value: str
    reason: str = ""


class BlocklistOut(TimestampedOut):
    value: str
    reason: str
    created_by: str
