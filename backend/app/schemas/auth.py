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


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str
