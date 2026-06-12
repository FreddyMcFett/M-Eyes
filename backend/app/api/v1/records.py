from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Record, User, Zone
from app.schemas.dns import RecordIn, RecordOut, RecordUpdate
from app.services import dns as dns_service

router = APIRouter(tags=["dns"])


@router.get("/zones/{zone_id}/records", response_model=list[RecordOut])
def list_records(zone_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    if db.get(Zone, zone_id) is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    return db.scalars(
        select(Record).where(Record.zone_id == zone_id).order_by(Record.name, Record.type)
    ).all()


@router.post("/zones/{zone_id}/records", response_model=RecordOut, status_code=201)
def create_record(zone_id: int, payload: RecordIn, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    data = payload.model_dump()
    auto_ptr = data.pop("auto_ptr", False)
    record = dns_service.create_record(db, user.username, zone, data, auto_ptr=auto_ptr)
    db.commit()
    return record


@router.patch("/records/{record_id}", response_model=RecordOut)
def update_record(record_id: int, payload: RecordUpdate, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    record = db.get(Record, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    record = dns_service.update_record(db, user.username, record, payload.model_dump(exclude_unset=True))
    db.commit()
    return record


@router.delete("/records/{record_id}", status_code=204)
def delete_record(record_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    record = db.get(Record, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    dns_service.delete_record(db, user.username, record)
    db.commit()
