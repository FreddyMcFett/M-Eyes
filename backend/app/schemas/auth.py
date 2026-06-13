from pydantic import BaseModel

from app.schemas.common import ORMModel


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: int
    username: str
    role: str
    email: str = ""
    display_name: str = ""
    auth_source: str = "local"
    is_active: bool = True


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str
