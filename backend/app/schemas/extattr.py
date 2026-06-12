from pydantic import BaseModel

from app.schemas.common import TimestampedOut


class ExtAttrDefIn(BaseModel):
    name: str
    type: str = "string"
    comment: str = ""
    allowed_values: list[str] | None = None


class ExtAttrDefUpdate(BaseModel):
    comment: str | None = None
    allowed_values: list[str] | None = None


class ExtAttrDefOut(TimestampedOut):
    name: str
    type: str
    comment: str
    allowed_values: list[str] | None
    usage_count: int = 0


class ExtAttrValuesIn(BaseModel):
    values: dict[str, str]


class ExtAttrValuesOut(BaseModel):
    object_type: str
    object_id: int
    values: dict[str, str]
