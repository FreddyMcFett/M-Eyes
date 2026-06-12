from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.auth import LoginIn, PasswordChangeIn, TokenOut, UserOut
from app.security import create_access_token, hash_password, verify_password
from app.services import events

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        events.emit(db, "warning", "auth", f"Failed login for {payload.username!r}")
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    events.emit(db, "info", "auth", f"User {user.username} logged in")
    db.commit()
    return TokenOut(access_token=create_access_token(user.username))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password")
def change_password(
    payload: PasswordChangeIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=403, detail="Current password is incorrect")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=422, detail="New password must be at least 6 characters")
    db_user = db.scalar(select(User).where(User.username == user.username))
    db_user.password_hash = hash_password(payload.new_password)
    events.emit(db, "info", "auth", f"User {user.username} changed their password")
    db.commit()
    return {"status": "ok"}
