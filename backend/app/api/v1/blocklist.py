import ipaddress

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import BlocklistEntry, User
from app.schemas.feed import BlocklistIn, BlocklistOut
from app.services import audit, events

router = APIRouter(prefix="/blocklist", tags=["fortinet"])


@router.get("", response_model=list[BlocklistOut])
def list_entries(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(BlocklistEntry).order_by(BlocklistEntry.value)).all()


@router.post("", response_model=BlocklistOut, status_code=201)
def create_entry(payload: BlocklistIn, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    value = payload.value.strip()
    try:
        if "/" in value:
            ipaddress.ip_network(value, strict=False)
        else:
            ipaddress.ip_address(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid IP or CIDR: {exc}") from exc
    if db.scalar(select(BlocklistEntry).where(BlocklistEntry.value == value)):
        raise HTTPException(status_code=409, detail=f"{value} is already blocklisted")
    entry = BlocklistEntry(value=value, reason=payload.reason, created_by=user.username)
    db.add(entry)
    db.flush()
    audit.record(db, user.username, "create", "blocklist_entry", entry.id, None,
                 audit.snapshot(entry), summary=f"Blocklisted {value}")
    events.emit(db, "warning", "feeds", f"{value} added to blocklist", {"reason": payload.reason})
    db.commit()
    return entry


@router.delete("/{entry_id}", status_code=204)
def delete_entry(entry_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    entry = db.get(BlocklistEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    before = audit.snapshot(entry)
    db.delete(entry)
    db.flush()
    audit.record(db, user.username, "delete", "blocklist_entry", before["id"], before, None,
                 summary=f"Removed {before['value']} from blocklist")
    events.emit(db, "info", "feeds", f"{before['value']} removed from blocklist")
    db.commit()
