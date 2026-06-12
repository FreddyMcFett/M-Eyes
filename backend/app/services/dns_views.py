"""Split-horizon DNS views: named match-clients ACLs that BIND evaluates in order.

The generated zones.conf wraps zones in `view` blocks whenever at least one view
exists; unassigned zones form the implicit trailing 'default' view (match-clients any).
"""

import ipaddress
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import View, Zone
from app.services import audit, events

ACL_KEYWORDS = {"any", "none", "localhost", "localnets"}
_VIEW_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]*$")
RESERVED_NAMES = {"default"}  # used for the implicit catch-all view


def normalize_match_clients(value: str) -> str:
    tokens = [t.strip() for t in value.replace(";", ",").split(",") if t.strip()]
    if not tokens:
        raise HTTPException(status_code=422, detail="match_clients cannot be empty")
    for token in tokens:
        bare = token[1:] if token.startswith("!") else token
        if bare in ACL_KEYWORDS:
            continue
        try:
            ipaddress.ip_network(bare, strict=False)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid match-clients element {token!r}: expected "
                       f"{'|'.join(sorted(ACL_KEYWORDS))} or an IP/CIDR (optionally !negated)",
            ) from None
    return ", ".join(tokens)


def zone_count(db: Session, view: View) -> int:
    return db.query(Zone).filter(Zone.view_id == view.id).count()


def create_view(db: Session, actor: str, data: dict) -> View:
    name = (data.get("name") or "").strip()
    if not _VIEW_NAME_RE.match(name):
        raise HTTPException(status_code=422, detail=f"Invalid view name {name!r}")
    if name.lower() in RESERVED_NAMES:
        raise HTTPException(status_code=422, detail=f"View name {name!r} is reserved")
    if db.scalar(select(View).where(View.name == name)):
        raise HTTPException(status_code=409, detail=f"View {name} already exists")
    data["name"] = name
    data["match_clients"] = normalize_match_clients(data.get("match_clients") or "any")
    view = View(**data)
    db.add(view)
    db.flush()
    audit.record(db, actor, "create", "dns_view", view.id, None, audit.snapshot(view),
                 summary=f"Created DNS view {view.name}")
    events.emit(db, "info", "dns", f"DNS view {view.name} created", {"id": view.id})
    return view


def update_view(db: Session, actor: str, view: View, data: dict) -> View:
    before = audit.snapshot(view)
    data.pop("name", None)  # renaming would break generated zone file names; delete + recreate
    if "match_clients" in data:
        data["match_clients"] = normalize_match_clients(data["match_clients"])
    for key, value in data.items():
        setattr(view, key, value)
    db.flush()
    audit.record(db, actor, "update", "dns_view", view.id, before, audit.snapshot(view),
                 summary=f"Updated DNS view {view.name}")
    events.emit(db, "info", "dns", f"DNS view {view.name} updated", {"id": view.id})
    return view


def delete_view(db: Session, actor: str, view: View) -> None:
    attached = zone_count(db, view)
    if attached:
        raise HTTPException(
            status_code=409,
            detail=f"View {view.name} still contains {attached} zone(s); move or delete them first",
        )
    before = audit.snapshot(view)
    name = view.name
    db.delete(view)
    db.flush()
    audit.record(db, actor, "delete", "dns_view", before["id"], before, None,
                 summary=f"Deleted DNS view {name}")
    events.emit(db, "info", "dns", f"DNS view {name} deleted")
