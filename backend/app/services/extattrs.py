"""Extensible attributes: typed, admin-defined metadata attachable to any DDI object
(the Infoblox EA model). Values are validated against their definition's type."""

import re
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    DhcpSubnet,
    ExtAttrDef,
    ExtAttrValue,
    Host,
    IPAddress,
    Network,
    Record,
    Zone,
)
from app.models.extattr import EXTATTR_TYPES
from app.services import audit, events

OBJECT_MODELS = {
    "network": Network,
    "ip_address": IPAddress,
    "zone": Zone,
    "record": Record,
    "host": Host,
    "dhcp_subnet": DhcpSubnet,
}

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _\-]*$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_def(data: dict) -> None:
    name = data.get("name", "")
    if not _NAME_RE.match(name):
        raise HTTPException(status_code=422, detail=f"Invalid attribute name {name!r}")
    if data.get("type") not in EXTATTR_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported attribute type {data.get('type')!r}; one of {', '.join(EXTATTR_TYPES)}",
        )
    if data["type"] == "enum":
        values = data.get("allowed_values")
        if not values or not isinstance(values, list):
            raise HTTPException(status_code=422, detail="Enum attributes require allowed_values")
    else:
        data["allowed_values"] = None


def validate_value(definition: ExtAttrDef, value: str) -> None:
    detail = None
    if definition.type == "integer":
        try:
            int(value)
        except ValueError:
            detail = "an integer"
    elif definition.type == "email":
        if not _EMAIL_RE.match(value):
            detail = "an email address"
    elif definition.type == "url":
        if not value.startswith(("http://", "https://")):
            detail = "an http(s) URL"
    elif definition.type == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            detail = "an ISO date (YYYY-MM-DD)"
    elif definition.type == "enum":
        if value not in (definition.allowed_values or []):
            detail = f"one of {', '.join(definition.allowed_values or [])}"
    if detail:
        raise HTTPException(
            status_code=422,
            detail=f"Attribute {definition.name!r} requires {detail}, got {value!r}",
        )


def create_def(db: Session, actor: str, data: dict) -> ExtAttrDef:
    data.setdefault("type", "string")
    _validate_def(data)
    if db.scalar(select(ExtAttrDef).where(ExtAttrDef.name == data["name"])):
        raise HTTPException(status_code=409, detail=f"Attribute {data['name']} already exists")
    definition = ExtAttrDef(**data)
    db.add(definition)
    db.flush()
    audit.record(db, actor, "create", "extattr_def", definition.id, None, audit.snapshot(definition),
                 summary=f"Created extensible attribute {definition.name}")
    events.emit(db, "info", "system", f"Extensible attribute {definition.name} created",
                {"id": definition.id})
    return definition


def update_def(db: Session, actor: str, definition: ExtAttrDef, data: dict) -> ExtAttrDef:
    before = audit.snapshot(definition)
    data.pop("name", None)  # renaming would orphan values semantically; delete + recreate
    data.pop("type", None)  # type changes would invalidate existing values
    if "allowed_values" in data and definition.type != "enum":
        data.pop("allowed_values")
    for key, value in data.items():
        setattr(definition, key, value)
    db.flush()
    audit.record(db, actor, "update", "extattr_def", definition.id, before, audit.snapshot(definition),
                 summary=f"Updated extensible attribute {definition.name}")
    return definition


def delete_def(db: Session, actor: str, definition: ExtAttrDef) -> None:
    before = audit.snapshot(definition)
    name = definition.name
    db.delete(definition)  # values cascade
    db.flush()
    audit.record(db, actor, "delete", "extattr_def", before["id"], before, None,
                 summary=f"Deleted extensible attribute {name}")
    events.emit(db, "info", "system", f"Extensible attribute {name} deleted")


def _check_object(db: Session, object_type: str, object_id: int) -> None:
    model = OBJECT_MODELS.get(object_type)
    if model is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported object type {object_type!r}; one of {', '.join(OBJECT_MODELS)}",
        )
    if db.get(model, object_id) is None:
        raise HTTPException(status_code=404, detail=f"{object_type} #{object_id} not found")


def get_for_object(db: Session, object_type: str, object_id: int) -> dict[str, str]:
    _check_object(db, object_type, object_id)
    rows = db.scalars(
        select(ExtAttrValue).where(
            ExtAttrValue.object_type == object_type, ExtAttrValue.object_id == object_id
        )
    ).all()
    return {row.definition.name: row.value for row in rows}


def set_for_object(
    db: Session, actor: str, object_type: str, object_id: int, values: dict[str, str]
) -> dict[str, str]:
    """Full-replace semantics: attributes missing from `values` are removed."""
    _check_object(db, object_type, object_id)
    defs = {d.name: d for d in db.scalars(select(ExtAttrDef)).all()}
    for name, value in values.items():
        definition = defs.get(name)
        if definition is None:
            raise HTTPException(status_code=422, detail=f"Unknown extensible attribute {name!r}")
        validate_value(definition, str(value))

    before = get_for_object(db, object_type, object_id)
    existing = {
        row.definition.name: row
        for row in db.scalars(
            select(ExtAttrValue).where(
                ExtAttrValue.object_type == object_type, ExtAttrValue.object_id == object_id
            )
        ).all()
    }
    for name, row in existing.items():
        if name not in values:
            db.delete(row)
        elif row.value != str(values[name]):
            row.value = str(values[name])
    for name, value in values.items():
        if name not in existing:
            db.add(ExtAttrValue(def_id=defs[name].id, object_type=object_type,
                                object_id=object_id, value=str(value)))
    db.flush()
    after = dict(values)
    if before != after:
        audit.record(db, actor, "update", "extattrs", object_id, before, after,
                     summary=f"Set extensible attributes on {object_type} #{object_id}")
    return after


def purge(db: Session, object_type: str, object_id: int) -> None:
    """Drop attribute values when their owning object is deleted."""
    for row in db.scalars(
        select(ExtAttrValue).where(
            ExtAttrValue.object_type == object_type, ExtAttrValue.object_id == object_id
        )
    ).all():
        db.delete(row)
    db.flush()


def usage_count(db: Session, definition: ExtAttrDef) -> int:
    return db.query(ExtAttrValue).filter(ExtAttrValue.def_id == definition.id).count()
