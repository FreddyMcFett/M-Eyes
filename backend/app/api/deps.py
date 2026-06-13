from collections.abc import Callable

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiKey, User
from app.models.base import utcnow
from app.models.user import ROLES
from app.security import decode_access_token, hash_api_key

bearer = HTTPBearer(auto_error=False)


def role_at_least(role: str, minimum: str) -> bool:
    """True when `role` is at least as privileged as `minimum` in the ROLES hierarchy."""
    try:
        return ROLES.index(role) >= ROLES.index(minimum)
    except ValueError:
        # Unknown role (e.g. a legacy value): only grant if it matches exactly.
        return role == minimum


def _user_from_api_key(db: Session, key: str) -> User:
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == hash_api_key(key)))
    if api_key is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if api_key.expires_at is not None and api_key.expires_at < utcnow():
        raise HTTPException(status_code=401, detail="API key has expired")
    api_key.last_used_at = utcnow()
    db.commit()
    # synthetic, non-persisted identity so audit entries name the key
    return User(username=f"apikey:{api_key.name}", password_hash="", role=api_key.role)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None and x_api_key:
        return _user_from_api_key(db, x_api_key)
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    username = decode_access_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")
    return user


def require_role(minimum: str) -> Callable[[User], User]:
    """Dependency factory: require the caller to hold at least `minimum` role.

    Usage: `user: User = Depends(require_role("operator"))`.
    """

    def checker(user: User = Depends(get_current_user)) -> User:
        if not role_at_least(user.role, minimum):
            raise HTTPException(
                status_code=403,
                detail=f"This action requires the '{minimum}' role or higher",
            )
        return user

    return checker
