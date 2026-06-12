from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import ApiKey, User
from app.models.base import utcnow
from app.schemas.apikey import ApiKeyCreated, ApiKeyIn, ApiKeyOut
from app.security import generate_api_key, hash_api_key
from app.services import audit, events

router = APIRouter(prefix="/apikeys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyOut])
def list_keys(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(ApiKey).order_by(ApiKey.name)).all()


@router.post("", response_model=ApiKeyCreated, status_code=201)
def create_key(payload: ApiKeyIn, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Key name is required")
    if db.scalar(select(ApiKey).where(ApiKey.name == name)):
        raise HTTPException(status_code=409, detail=f"An API key named {name!r} already exists")
    key = generate_api_key()
    api_key = ApiKey(
        name=name,
        prefix=key[:12],
        key_hash=hash_api_key(key),
        role=payload.role,
        expires_at=(utcnow() + timedelta(days=payload.expires_in_days)
                    if payload.expires_in_days else None),
    )
    db.add(api_key)
    db.flush()
    audit.record(db, user.username, "create", "api_key", api_key.id, None,
                 {"id": api_key.id, "name": name, "role": api_key.role},
                 summary=f"Created API key {name}")
    events.emit(db, "info", "auth", f"API key {name} created by {user.username}", {"id": api_key.id})
    db.commit()
    out = ApiKeyCreated.model_validate(api_key, from_attributes=True)
    out.key = key
    return out


@router.delete("/{key_id}", status_code=204)
def delete_key(key_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    api_key = db.get(ApiKey, key_id)
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    name = api_key.name
    db.delete(api_key)
    db.flush()
    audit.record(db, user.username, "delete", "api_key", key_id,
                 {"id": key_id, "name": name}, None, summary=f"Revoked API key {name}")
    events.emit(db, "info", "auth", f"API key {name} revoked by {user.username}")
    db.commit()
