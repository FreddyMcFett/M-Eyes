from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.generators.rpz_zone import render_rpz_zone
from app.models import RpzRule, User
from app.schemas.rpz import RpzRuleIn, RpzRuleOut, RpzRuleUpdate
from app.services import rpz as rpz_service

router = APIRouter(prefix="/rpz", tags=["dns-firewall"])


def _get_or_404(db: Session, rule_id: int) -> RpzRule:
    rule = db.get(RpzRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="DNS firewall rule not found")
    return rule


@router.get("/rules", response_model=list[RpzRuleOut])
def list_rules(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(RpzRule).order_by(RpzRule.fqdn)).all()


@router.post("/rules", response_model=RpzRuleOut, status_code=201)
def create_rule(payload: RpzRuleIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    rule = rpz_service.create_rule(db, user.username, payload.model_dump())
    db.commit()
    return rule


@router.patch("/rules/{rule_id}", response_model=RpzRuleOut)
def update_rule(rule_id: int, payload: RpzRuleUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    rule = _get_or_404(db, rule_id)
    rule = rpz_service.update_rule(db, user.username, rule, payload.model_dump(exclude_unset=True))
    db.commit()
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    rpz_service.delete_rule(db, user.username, _get_or_404(db, rule_id))
    db.commit()


@router.get("/preview")
def preview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"zone": get_settings().rpz_zone_name, "content": render_rpz_zone(db)}
