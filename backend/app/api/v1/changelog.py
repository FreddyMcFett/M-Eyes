from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import ChangeLog, User
from app.schemas.system import ChangeLogOut
from app.services import audit
from app.services import rollback as rollback_service

router = APIRouter(prefix="/changelog", tags=["versioning"])


@router.get("", response_model=list[ChangeLogOut])
def list_changes(
    object_type: str | None = None,
    object_id: int | None = None,
    actor: str | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(ChangeLog).order_by(ChangeLog.id.desc())
    if object_type:
        query = query.where(ChangeLog.object_type == object_type)
    if object_id is not None:
        query = query.where(ChangeLog.object_id == object_id)
    if actor:
        query = query.where(ChangeLog.actor == actor)
    return db.scalars(query.limit(limit).offset(offset)).all()


@router.get("/version")
def version(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"config_version": audit.current_version(db)}


@router.get("/{entry_id}", response_model=ChangeLogOut)
def get_change(entry_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    entry = db.get(ChangeLog, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Change not found")
    return entry


@router.post("/{entry_id}/rollback", response_model=ChangeLogOut)
def rollback(entry_id: int, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    entry = db.get(ChangeLog, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Change not found")
    result = rollback_service.rollback(db, user.username, entry)
    db.commit()
    return result
