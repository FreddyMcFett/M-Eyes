from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.generators.rpz_zone import render_rpz_zone
from app.models import RpzRule, RpzThreatFeed, User
from app.schemas.rpz import (
    RpzRuleIn,
    RpzRuleOut,
    RpzRuleUpdate,
    ThreatFeedIn,
    ThreatFeedOut,
    ThreatFeedUpdate,
)
from app.services import rpz as rpz_service
from app.services import threat_feeds as threat_feed_service

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


def _feed_or_404(db: Session, feed_id: int) -> RpzThreatFeed:
    feed = db.get(RpzThreatFeed, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Threat feed not found")
    return feed


@router.get("/threat-feeds", response_model=list[ThreatFeedOut])
def list_threat_feeds(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(RpzThreatFeed).order_by(RpzThreatFeed.name)).all()


@router.post("/threat-feeds", response_model=ThreatFeedOut, status_code=201)
def create_threat_feed(payload: ThreatFeedIn, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    feed = threat_feed_service.create_feed(db, user.username, payload.model_dump())
    db.commit()
    return feed


@router.patch("/threat-feeds/{feed_id}", response_model=ThreatFeedOut)
def update_threat_feed(feed_id: int, payload: ThreatFeedUpdate, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    feed = _feed_or_404(db, feed_id)
    feed = threat_feed_service.update_feed(db, user.username, feed,
                                           payload.model_dump(exclude_unset=True))
    db.commit()
    return feed


@router.delete("/threat-feeds/{feed_id}", status_code=204)
def delete_threat_feed(feed_id: int, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    threat_feed_service.delete_feed(db, user.username, _feed_or_404(db, feed_id))
    db.commit()


@router.post("/threat-feeds/{feed_id}/sync", response_model=ThreatFeedOut)
def sync_threat_feed(feed_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Fetch the feed now; deploy to BIND afterwards to activate new entries."""
    feed = threat_feed_service.sync_feed(db, _feed_or_404(db, feed_id))
    db.commit()
    return feed
