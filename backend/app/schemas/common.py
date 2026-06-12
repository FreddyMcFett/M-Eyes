from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TagOut(ORMModel):
    id: int
    name: str
    color: str


class TagIn(BaseModel):
    name: str
    color: str = "#4caf50"


class TimestampedOut(ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime
