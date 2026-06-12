from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.generators.zonefile import render_zone
from app.models import User, Zone
from app.schemas.dns import ZoneIn, ZoneOut, ZoneUpdate
from app.services import dns as dns_service

router = APIRouter(prefix="/zones", tags=["dns"])


def _out(zone: Zone) -> ZoneOut:
    out = ZoneOut.model_validate(zone)
    out.record_count = len(zone.records)
    out.view_name = zone.view.name if zone.view else None
    return out


def _get_or_404(db: Session, zone_id: int) -> Zone:
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


@router.get("", response_model=list[ZoneOut])
def list_zones(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_out(z) for z in db.scalars(select(Zone).order_by(Zone.name)).all()]


@router.post("", response_model=ZoneOut, status_code=201)
def create_zone(payload: ZoneIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    zone = dns_service.create_zone(db, user.username, data)
    db.commit()
    return _out(zone)


@router.get("/{zone_id}", response_model=ZoneOut)
def get_zone(zone_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _out(_get_or_404(db, zone_id))


@router.patch("/{zone_id}", response_model=ZoneOut)
def update_zone(zone_id: int, payload: ZoneUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    zone = _get_or_404(db, zone_id)
    zone = dns_service.update_zone(db, user.username, zone, payload.model_dump(exclude_unset=True))
    db.commit()
    return _out(zone)


@router.delete("/{zone_id}", status_code=204)
def delete_zone(zone_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dns_service.delete_zone(db, user.username, _get_or_404(db, zone_id))
    db.commit()


@router.get("/{zone_id}/file")
def zone_file(zone_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    zone = _get_or_404(db, zone_id)
    return {"zone": zone.name, "content": render_zone(db, zone)}
