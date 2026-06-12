"""Public FortiGate External Resource feeds.

Auth (per feed): HTTP Basic with username 'feed' and the feed token as password
(matches FortiOS external-resource auth), or a ?token= query parameter.
"""

import base64
import binascii
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Feed, Tag
from app.services import feeds as feeds_service

router = APIRouter(prefix="/feeds", tags=["fortinet-feeds"])


def _extract_token(request: Request) -> str | None:
    token = request.query_params.get("token")
    if token:
        return token
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("basic "):
        try:
            decoded = base64.b64decode(auth[6:]).decode()
            _, _, password = decoded.partition(":")
            return password or None
        except (binascii.Error, UnicodeDecodeError):
            return None
    return None


def _authorize(request: Request, feed: Feed | None) -> Feed:
    if feed is None or not feed.enabled:
        raise HTTPException(status_code=404, detail="Feed not found")
    token = _extract_token(request)
    if token is None or not secrets.compare_digest(token, feed.token):
        raise HTTPException(
            status_code=401,
            detail="Invalid feed token",
            headers={"WWW-Authenticate": 'Basic realm="m-eyes-feeds"'},
        )
    return feed


def _resolve(db: Session, slug: str) -> Feed | None:
    return db.scalar(select(Feed).where(Feed.slug == slug))


def _txt_response(entries: list[str]) -> PlainTextResponse:
    return PlainTextResponse(
        "\n".join(entries) + ("\n" if entries else ""),
        headers={"Cache-Control": "max-age=60"},
    )


@router.get("/{slug}.txt", response_class=PlainTextResponse)
def feed_txt(slug: str, request: Request, db: Session = Depends(get_db)):
    feed = _authorize(request, _resolve(db, slug))
    return _txt_response(feeds_service.build_entries(db, feed))


@router.get("/{slug}.json")
def feed_json(slug: str, request: Request, db: Session = Depends(get_db)):
    feed = _authorize(request, _resolve(db, slug))
    return feeds_service.feed_payload_json(db, feed)


@router.get("/tag/{tag_name}.txt", response_class=PlainTextResponse)
def tag_feed_txt(tag_name: str, request: Request, db: Session = Depends(get_db)):
    """Convenience per-tag feed; requires a feed of kind 'tag' bound to this tag."""
    tag = db.scalar(select(Tag).where(Tag.name == tag_name))
    feed = None
    if tag is not None:
        feed = db.scalar(select(Feed).where(Feed.kind == "tag", Feed.tag_id == tag.id))
    feed = _authorize(request, feed)
    return _txt_response(feeds_service.build_entries(db, feed))
