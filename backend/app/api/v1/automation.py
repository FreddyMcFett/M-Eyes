from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models import AutomationRule, User
from app.models.automation import AUTOMATION_KINDS
from app.schemas.automation import (
    AutomationRuleIn,
    AutomationRuleOut,
    AutomationRuleUpdate,
    AutomationRunResult,
)
from app.services import audit, automation, events

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("/kinds")
def kinds(user: User = Depends(get_current_user)):
    return {"kinds": list(AUTOMATION_KINDS)}


@router.get("", response_model=list[AutomationRuleOut])
def list_rules(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(AutomationRule).order_by(AutomationRule.name)).all()


@router.post("", response_model=AutomationRuleOut, status_code=201)
def create_rule(payload: AutomationRuleIn, db: Session = Depends(get_db),
                user: User = Depends(require_role("admin"))):
    if payload.kind not in AUTOMATION_KINDS:
        raise HTTPException(status_code=422, detail=f"Invalid kind; allowed: {list(AUTOMATION_KINDS)}")
    if db.scalar(select(AutomationRule).where(AutomationRule.name == payload.name)):
        raise HTTPException(status_code=409, detail=f"A rule named {payload.name!r} already exists")
    rule = AutomationRule(**payload.model_dump())
    db.add(rule)
    db.flush()
    audit.record(db, user.username, "create", "automation_rule", rule.id, None,
                 audit.snapshot(rule), summary=f"Created automation rule {rule.name}")
    events.emit(db, "info", "automation", f"Automation rule {rule.name!r} created by {user.username}")
    db.commit()
    return rule


@router.patch("/{rule_id}", response_model=AutomationRuleOut)
def update_rule(rule_id: int, payload: AutomationRuleUpdate, db: Session = Depends(get_db),
                user: User = Depends(require_role("admin"))):
    rule = db.get(AutomationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    before = audit.snapshot(rule)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.flush()
    audit.record(db, user.username, "update", "automation_rule", rule.id, before,
                 audit.snapshot(rule), summary=f"Updated automation rule {rule.name}")
    db.commit()
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db),
                user: User = Depends(require_role("admin"))):
    rule = db.get(AutomationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    name = rule.name
    db.delete(rule)
    db.flush()
    audit.record(db, user.username, "delete", "automation_rule", rule_id, {"name": name}, None,
                 summary=f"Deleted automation rule {name}")
    events.emit(db, "info", "automation", f"Automation rule {name!r} deleted by {user.username}")
    db.commit()


@router.post("/{rule_id}/run", response_model=AutomationRunResult)
def run_now(rule_id: int, db: Session = Depends(get_db),
            user: User = Depends(require_role("operator"))):
    rule = db.get(AutomationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    result = automation.run_rule(db, rule)
    db.commit()
    return AutomationRunResult(**result)
