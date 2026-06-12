"""DNS firewall rules, published to BIND as a Response Policy Zone (RPZ).

Every rule covers the domain itself plus all subdomains (a wildcard row is
generated alongside the exact name). The RPZ zone and the response-policy
directive only appear in the generated BIND config while at least one rule
is enabled.
"""

import ipaddress
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RpzRule
from app.models.rpz import RPZ_ACTIONS
from app.services import audit, events

_FQDN_RE = re.compile(r"^([a-z0-9_]([a-z0-9_\-]*[a-z0-9_])?\.)+[a-z]{2,}$")


def _validate(data: dict) -> None:
    fqdn = (data.get("fqdn") or "").rstrip(".").lower()
    if fqdn.startswith("*."):
        raise HTTPException(
            status_code=422,
            detail="Wildcards are implicit: a rule always covers the domain and its subdomains",
        )
    if not _FQDN_RE.match(fqdn):
        raise HTTPException(status_code=422, detail=f"Invalid domain name {fqdn!r}")
    data["fqdn"] = fqdn
    if data.get("action") not in RPZ_ACTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported action {data.get('action')!r}; one of {', '.join(RPZ_ACTIONS)}",
        )
    if data["action"] == "substitute":
        if not data.get("substitute"):
            raise HTTPException(status_code=422,
                                detail="The substitute action requires a substitute IP or FQDN")
    else:
        data["substitute"] = ""


def create_rule(db: Session, actor: str, data: dict) -> RpzRule:
    data.setdefault("action", "block")
    _validate(data)
    if db.scalar(select(RpzRule).where(RpzRule.fqdn == data["fqdn"])):
        raise HTTPException(status_code=409, detail=f"A rule for {data['fqdn']} already exists")
    rule = RpzRule(**data)
    db.add(rule)
    db.flush()
    audit.record(db, actor, "create", "rpz_rule", rule.id, None, audit.snapshot(rule),
                 summary=f"Created DNS firewall rule {rule.action} {rule.fqdn}")
    events.emit(db, "info", "dns", f"DNS firewall: {rule.action} {rule.fqdn}", {"id": rule.id})
    return rule


def update_rule(db: Session, actor: str, rule: RpzRule, data: dict) -> RpzRule:
    before = audit.snapshot(rule)
    merged = {
        "fqdn": rule.fqdn,
        "action": data.get("action", rule.action),
        "substitute": data.get("substitute", rule.substitute),
    }
    _validate(merged)
    data["action"], data["substitute"] = merged["action"], merged["substitute"]
    data.pop("fqdn", None)
    for key, value in data.items():
        setattr(rule, key, value)
    db.flush()
    audit.record(db, actor, "update", "rpz_rule", rule.id, before, audit.snapshot(rule),
                 summary=f"Updated DNS firewall rule for {rule.fqdn}")
    events.emit(db, "info", "dns", f"DNS firewall rule for {rule.fqdn} updated", {"id": rule.id})
    return rule


def delete_rule(db: Session, actor: str, rule: RpzRule) -> None:
    before = audit.snapshot(rule)
    fqdn = rule.fqdn
    db.delete(rule)
    db.flush()
    audit.record(db, actor, "delete", "rpz_rule", before["id"], before, None,
                 summary=f"Deleted DNS firewall rule for {fqdn}")
    events.emit(db, "info", "dns", f"DNS firewall rule for {fqdn} deleted")


def rule_rows(rule: RpzRule) -> list[dict]:
    """RPZ zone file rows for one rule (exact name + subdomain wildcard)."""
    if rule.action == "block":
        rtype, value = "CNAME", "."
    elif rule.action == "nodata":
        rtype, value = "CNAME", "*."
    elif rule.action == "passthru":
        rtype, value = "CNAME", "rpz-passthru."
    else:  # substitute
        try:
            version = ipaddress.ip_address(rule.substitute).version
            rtype, value = ("A", rule.substitute) if version == 4 else ("AAAA", rule.substitute)
        except ValueError:
            rtype, value = "CNAME", rule.substitute.rstrip(".") + "."
    return [
        {"name": rule.fqdn, "type": rtype, "value": value},
        {"name": f"*.{rule.fqdn}", "type": rtype, "value": value},
    ]


def enabled_rules(db: Session) -> list[RpzRule]:
    return db.scalars(select(RpzRule).where(RpzRule.enabled).order_by(RpzRule.fqdn)).all()
