from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# Role hierarchy, lowest to highest privilege. Higher roles inherit the rights
# of every role below them (see app.api.deps.role_at_least).
ROLES = ("viewer", "operator", "admin")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32), default="admin")

    # Enterprise identity / SSO fields
    email: Mapped[str] = mapped_column(String(255), default="")
    display_name: Mapped[str] = mapped_column(String(128), default="")
    auth_source: Mapped[str] = mapped_column(String(16), default="local")  # local|saml
    external_id: Mapped[str] = mapped_column(String(255), default="")  # IdP NameID for SSO users
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
