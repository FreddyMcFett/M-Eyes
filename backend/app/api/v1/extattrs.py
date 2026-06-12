from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import ExtAttrDef, User
from app.schemas.extattr import (
    ExtAttrDefIn,
    ExtAttrDefOut,
    ExtAttrDefUpdate,
    ExtAttrValuesIn,
    ExtAttrValuesOut,
)
from app.services import extattrs as extattr_service

router = APIRouter(tags=["extattrs"])


def _out(db: Session, definition: ExtAttrDef) -> ExtAttrDefOut:
    out = ExtAttrDefOut.model_validate(definition)
    out.usage_count = extattr_service.usage_count(db, definition)
    return out


def _def_or_404(db: Session, def_id: int) -> ExtAttrDef:
    definition = db.get(ExtAttrDef, def_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="Extensible attribute not found")
    return definition


@router.get("/extattr-defs", response_model=list[ExtAttrDefOut])
def list_defs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    defs = db.scalars(select(ExtAttrDef).order_by(ExtAttrDef.name)).all()
    return [_out(db, d) for d in defs]


@router.post("/extattr-defs", response_model=ExtAttrDefOut, status_code=201)
def create_def(payload: ExtAttrDefIn, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    definition = extattr_service.create_def(db, user.username, payload.model_dump())
    db.commit()
    return _out(db, definition)


@router.patch("/extattr-defs/{def_id}", response_model=ExtAttrDefOut)
def update_def(def_id: int, payload: ExtAttrDefUpdate, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    definition = _def_or_404(db, def_id)
    definition = extattr_service.update_def(db, user.username, definition,
                                            payload.model_dump(exclude_unset=True))
    db.commit()
    return _out(db, definition)


@router.delete("/extattr-defs/{def_id}", status_code=204)
def delete_def(def_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    extattr_service.delete_def(db, user.username, _def_or_404(db, def_id))
    db.commit()


@router.get("/extattrs/{object_type}/{object_id}", response_model=ExtAttrValuesOut)
def get_values(object_type: str, object_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    values = extattr_service.get_for_object(db, object_type, object_id)
    return ExtAttrValuesOut(object_type=object_type, object_id=object_id, values=values)


@router.put("/extattrs/{object_type}/{object_id}", response_model=ExtAttrValuesOut)
def set_values(object_type: str, object_id: int, payload: ExtAttrValuesIn,
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    values = extattr_service.set_for_object(db, user.username, object_type, object_id,
                                            payload.values)
    db.commit()
    return ExtAttrValuesOut(object_type=object_type, object_id=object_id, values=values)
