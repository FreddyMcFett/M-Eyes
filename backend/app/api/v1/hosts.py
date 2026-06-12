from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Host, IPAddress, Record, User
from app.schemas.host import HostIn, HostOut
from app.services import host as host_service

router = APIRouter(prefix="/hosts", tags=["hosts"])


def _out(db: Session, host: Host) -> HostOut:
    out = HostOut.model_validate(host)
    if host.ip_address_id:
        ip_row = db.get(IPAddress, host.ip_address_id)
        out.ip = ip_row.ip if ip_row else None
    if host.a_record_id:
        record = db.get(Record, host.a_record_id)
        out.zone_name = record.zone.name if record else None
    return out


@router.get("", response_model=list[HostOut])
def list_hosts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_out(db, h) for h in db.scalars(select(Host).order_by(Host.name)).all()]


@router.post("", response_model=HostOut, status_code=201)
def create_host(payload: HostIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    host = host_service.create_host(
        db,
        user.username,
        name=payload.name,
        network_id=payload.network_id,
        ip=payload.ip,
        mac=payload.mac,
        create_reservation=payload.create_reservation,
        description=payload.description,
    )
    db.commit()
    return _out(db, host)


@router.delete("/{host_id}", status_code=204)
def delete_host(host_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    host_service.delete_host(db, user.username, host)
    db.commit()
