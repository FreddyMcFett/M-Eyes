from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Tag, User
from app.schemas.common import TagIn, TagOut
from app.services import audit

router = APIRouter(prefix="/tags", tags=["ipam"])


@router.get("", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(Tag).order_by(Tag.name)).all()


@router.post("", response_model=TagOut, status_code=201)
def create_tag(payload: TagIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if db.scalar(select(Tag).where(Tag.name == payload.name)):
        raise HTTPException(status_code=409, detail=f"Tag {payload.name!r} already exists")
    tag = Tag(**payload.model_dump())
    db.add(tag)
    db.flush()
    audit.record(db, user.username, "create", "tag", tag.id, None, audit.snapshot(tag),
                 summary=f"Created tag {tag.name}")
    db.commit()
    return tag


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    before = audit.snapshot(tag)
    db.delete(tag)
    db.flush()
    audit.record(db, user.username, "delete", "tag", before["id"], before, None,
                 summary=f"Deleted tag {before['name']}")
    db.commit()
