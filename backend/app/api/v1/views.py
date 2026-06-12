from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import User, View
from app.schemas.dns import ViewIn, ViewOut, ViewUpdate
from app.services import dns_views

router = APIRouter(prefix="/views", tags=["dns"])


def _out(db: Session, view: View) -> ViewOut:
    out = ViewOut.model_validate(view)
    out.zone_count = dns_views.zone_count(db, view)
    return out


def _get_or_404(db: Session, view_id: int) -> View:
    view = db.get(View, view_id)
    if view is None:
        raise HTTPException(status_code=404, detail="DNS view not found")
    return view


@router.get("", response_model=list[ViewOut])
def list_views(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    views = db.scalars(select(View).order_by(View.position, View.id)).all()
    return [_out(db, v) for v in views]


@router.post("", response_model=ViewOut, status_code=201)
def create_view(payload: ViewIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    view = dns_views.create_view(db, user.username, payload.model_dump())
    db.commit()
    return _out(db, view)


@router.patch("/{view_id}", response_model=ViewOut)
def update_view(view_id: int, payload: ViewUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    view = _get_or_404(db, view_id)
    view = dns_views.update_view(db, user.username, view, payload.model_dump(exclude_unset=True))
    db.commit()
    return _out(db, view)


@router.delete("/{view_id}", status_code=204)
def delete_view(view_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    dns_views.delete_view(db, user.username, _get_or_404(db, view_id))
    db.commit()
