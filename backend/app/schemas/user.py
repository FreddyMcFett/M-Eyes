from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class UserAdminOut(ORMModel):
    id: int
    username: str
    role: str
    email: str = ""
    display_name: str = ""
    auth_source: str = "local"
    is_active: bool = True
    last_login_at: datetime | None = None
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"
    email: str = ""
    display_name: str = ""


class UserUpdate(BaseModel):
    role: str | None = None
    email: str | None = None
    display_name: str | None = None
    is_active: bool | None = None
    password: str | None = None
