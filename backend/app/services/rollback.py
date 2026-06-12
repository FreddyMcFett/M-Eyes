"""Rollback = a new forward change that restores a previous state. History is never rewritten."""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    BlocklistEntry,
    ChangeLog,
    DhcpOption,
    DhcpRange,
    DhcpReservation,
    DhcpSubnet,
    ExtAttrDef,
    Feed,
    Host,
    IPAddress,
    Network,
    Record,
    RpzRule,
    Tag,
    View,
    Zone,
)
from app.services import audit, events

OBJECT_TYPES = {
    "network": Network,
    "ip_address": IPAddress,
    "tag": Tag,
    "zone": Zone,
    "record": Record,
    "dhcp_subnet": DhcpSubnet,
    "dhcp_range": DhcpRange,
    "dhcp_reservation": DhcpReservation,
    "dhcp_option": DhcpOption,
    "host": Host,
    "feed": Feed,
    "blocklist_entry": BlocklistEntry,
    "dns_view": View,
    "rpz_rule": RpzRule,
    "extattr_def": ExtAttrDef,
}

_SKIP_FIELDS = {"created_at", "updated_at"}


def _apply_snapshot(obj, snap: dict) -> None:
    for key, value in snap.items():
        if key in _SKIP_FIELDS or key == "id":
            continue
        setattr(obj, key, value)


def rollback(db: Session, actor: str, entry: ChangeLog) -> ChangeLog:
    model = OBJECT_TYPES.get(entry.object_type)
    if model is None:
        raise HTTPException(status_code=422, detail=f"Cannot roll back objects of type {entry.object_type}")

    try:
        if entry.action in ("update", "rollback"):
            if not entry.before:
                raise HTTPException(status_code=422, detail="Entry has no previous state to restore")
            obj = db.get(model, entry.object_id)
            if obj is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"{entry.object_type} #{entry.object_id} no longer exists; "
                           "roll back its deletion first",
                )
            before = audit.snapshot(obj)
            _apply_snapshot(obj, entry.before)
            db.flush()
            after = audit.snapshot(obj)
        elif entry.action == "delete":
            if db.get(model, entry.object_id) is not None:
                raise HTTPException(status_code=409, detail="Object already exists; nothing to restore")
            data = {k: v for k, v in (entry.before or {}).items() if k not in _SKIP_FIELDS}
            obj = model(**data)
            db.add(obj)
            db.flush()
            before, after = None, audit.snapshot(obj)
        elif entry.action == "create":
            obj = db.get(model, entry.object_id)
            if obj is None:
                raise HTTPException(status_code=404, detail="Object already deleted")
            before = audit.snapshot(obj)
            db.delete(obj)
            db.flush()
            after = None
        else:
            raise HTTPException(status_code=422, detail=f"Cannot roll back action {entry.action!r}")
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Rollback violates referential integrity: {exc.orig}",
        ) from exc

    if after is not None:
        after = {**after, "_rollback_of": entry.id}
    result = audit.record(
        db, actor, "rollback", entry.object_type, entry.object_id, before, after,
        summary=f"Rolled back change #{entry.id} ({entry.action} {entry.object_type})",
    )
    events.emit(db, "warning", "system",
                f"Change #{entry.id} rolled back by {actor}", {"changelog_id": result.id})
    return result
