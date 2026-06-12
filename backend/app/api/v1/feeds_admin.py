from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Feed, User
from app.models.feed import generate_token
from app.schemas.feed import FeedIn, FeedOut, FeedUpdate
from app.services import audit, events
from app.services import feeds as feeds_service

router = APIRouter(prefix="/feeds", tags=["fortinet"])

FEED_KINDS = ("networks", "tag", "blocklist", "fqdn")


def _out(db: Session, feed: Feed, request: Request) -> FeedOut:
    out = FeedOut.model_validate(feed)
    out.entry_count = len(feeds_service.build_entries(db, feed))
    base_url = str(request.base_url).rstrip("/")
    out.fortigate_snippet = feeds_service.fortigate_snippet(feed, base_url)
    return out


def _get_or_404(db: Session, feed_id: int) -> Feed:
    feed = db.get(Feed, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")
    return feed


@router.get("", response_model=list[FeedOut])
def list_feeds(request: Request, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    return [_out(db, f, request) for f in db.scalars(select(Feed).order_by(Feed.slug)).all()]


@router.post("", response_model=FeedOut, status_code=201)
def create_feed(payload: FeedIn, request: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    if payload.kind not in FEED_KINDS:
        raise HTTPException(status_code=422, detail=f"kind must be one of {', '.join(FEED_KINDS)}")
    if payload.kind == "tag" and not payload.tag_id:
        raise HTTPException(status_code=422, detail="tag feeds require tag_id")
    if db.scalar(select(Feed).where(Feed.slug == payload.slug)):
        raise HTTPException(status_code=409, detail=f"Feed {payload.slug!r} already exists")
    feed = Feed(**payload.model_dump())
    db.add(feed)
    db.flush()
    audit.record(db, user.username, "create", "feed", feed.id, None, audit.snapshot(feed),
                 summary=f"Created feed {feed.slug}")
    events.emit(db, "info", "feeds", f"Feed {feed.slug} created")
    db.commit()
    return _out(db, feed, request)


@router.patch("/{feed_id}", response_model=FeedOut)
def update_feed(feed_id: int, payload: FeedUpdate, request: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    feed = _get_or_404(db, feed_id)
    before = audit.snapshot(feed)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(feed, key, value)
    db.flush()
    audit.record(db, user.username, "update", "feed", feed.id, before, audit.snapshot(feed),
                 summary=f"Updated feed {feed.slug}")
    db.commit()
    return _out(db, feed, request)


@router.post("/{feed_id}/regenerate-token", response_model=FeedOut)
def regenerate_token(feed_id: int, request: Request, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    feed = _get_or_404(db, feed_id)
    before = audit.snapshot(feed)
    feed.token = generate_token()
    db.flush()
    audit.record(db, user.username, "update", "feed", feed.id, before, audit.snapshot(feed),
                 summary=f"Regenerated token for feed {feed.slug}")
    events.emit(db, "warning", "feeds", f"Token regenerated for feed {feed.slug}")
    db.commit()
    return _out(db, feed, request)


@router.delete("/{feed_id}", status_code=204)
def delete_feed(feed_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    feed = _get_or_404(db, feed_id)
    before = audit.snapshot(feed)
    db.delete(feed)
    db.flush()
    audit.record(db, user.username, "delete", "feed", before["id"], before, None,
                 summary=f"Deleted feed {before['slug']}")
    events.emit(db, "info", "feeds", f"Feed {before['slug']} deleted")
    db.commit()
