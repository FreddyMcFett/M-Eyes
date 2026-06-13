"""User management with role-based access control (admin only)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.database import get_db
from app.models import User
from app.models.user import ROLES
from app.schemas.user import UserAdminOut, UserCreate, UserUpdate
from app.security import hash_password
from app.services import audit, events

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserAdminOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    return db.scalars(select(User).order_by(User.username)).all()


@router.get("/roles")
def roles(admin: User = Depends(require_role("admin"))):
    return {"roles": list(ROLES)}


@router.post("", response_model=UserAdminOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db),
                admin: User = Depends(require_role("admin"))):
    if payload.role not in ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role; allowed: {list(ROLES)}")
    if len(payload.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=409, detail=f"User {payload.username!r} already exists")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        email=payload.email,
        display_name=payload.display_name,
        auth_source="local",
    )
    db.add(user)
    db.flush()
    audit.record(db, admin.username, "create", "user", user.id, None,
                 {"username": user.username, "role": user.role}, summary=f"Created user {user.username}")
    events.emit(db, "info", "auth", f"User {user.username!r} created by {admin.username}")
    db.commit()
    return user


@router.patch("/{user_id}", response_model=UserAdminOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db),
                admin: User = Depends(require_role("admin"))):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role is not None and payload.role not in ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role; allowed: {list(ROLES)}")
    before = {"role": user.role, "is_active": user.is_active}
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        password = data.pop("password")
        if password:
            if len(password) < 6:
                raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
            user.password_hash = hash_password(password)
    if data.get("is_active") is False and user.id == admin.id:
        raise HTTPException(status_code=422, detail="You cannot disable your own account")
    for field, value in data.items():
        setattr(user, field, value)
    db.flush()
    audit.record(db, admin.username, "update", "user", user.id, before,
                 {"role": user.role, "is_active": user.is_active}, summary=f"Updated user {user.username}")
    db.commit()
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db),
                admin: User = Depends(require_role("admin"))):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=422, detail="You cannot delete your own account")
    username = user.username
    db.delete(user)
    db.flush()
    audit.record(db, admin.username, "delete", "user", user_id, {"username": username}, None,
                 summary=f"Deleted user {username}")
    events.emit(db, "info", "auth", f"User {username!r} deleted by {admin.username}")
    db.commit()
