"""External threat-intelligence domain feeds for the DNS firewall.

A feed is a URL serving a domain list - one domain per line, comments with
'#' or ';', hosts-file format ("0.0.0.0 bad.example") also accepted. Synced
entries are cached in the database and merged into the generated RPZ zone
after the manual rules, so explicit passthru rules always take precedence.
"""

import re

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RpzThreatFeed
from app.models.base import utcnow
from app.models.threatfeed import THREAT_FEED_ACTIONS
from app.services import audit, events

_FQDN_RE = re.compile(r"^([a-z0-9_]([a-z0-9_\-]*[a-z0-9_])?\.)+[a-z]{2,}$")
_HOSTFILE_IPS = {"0.0.0.0", "127.0.0.1", "::", "::1"}
MAX_ENTRIES = 200_000
FETCH_TIMEOUT = 30.0


def _validate(data: dict) -> None:
    if not (data.get("name") or "").strip():
        raise HTTPException(status_code=422, detail="Feed name is required")
    url = (data.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="Feed URL must start with http:// or https://")
    data["url"] = url
    if data.get("action") not in THREAT_FEED_ACTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported action {data.get('action')!r}; one of {', '.join(THREAT_FEED_ACTIONS)}",
        )
    if not 1 <= int(data.get("refresh_hours") or 24) <= 168:
        raise HTTPException(status_code=422, detail="Refresh interval must be 1-168 hours")


def create_feed(db: Session, actor: str, data: dict) -> RpzThreatFeed:
    data.setdefault("action", "block")
    _validate(data)
    if db.scalar(select(RpzThreatFeed).where(RpzThreatFeed.name == data["name"])):
        raise HTTPException(status_code=409, detail=f"A feed named {data['name']!r} already exists")
    feed = RpzThreatFeed(**data)
    db.add(feed)
    db.flush()
    audit.record(db, actor, "create", "rpz_threat_feed", feed.id, None, _snapshot(feed),
                 summary=f"Created threat feed {feed.name}")
    events.emit(db, "info", "dns", f"Threat feed {feed.name} created", {"id": feed.id})
    return feed


def update_feed(db: Session, actor: str, feed: RpzThreatFeed, data: dict) -> RpzThreatFeed:
    before = _snapshot(feed)
    merged = {
        "name": data.get("name", feed.name),
        "url": data.get("url", feed.url),
        "action": data.get("action", feed.action),
        "refresh_hours": data.get("refresh_hours", feed.refresh_hours),
    }
    _validate(merged)
    data.update({k: merged[k] for k in merged if k in data})
    for key, value in data.items():
        setattr(feed, key, value)
    db.flush()
    audit.record(db, actor, "update", "rpz_threat_feed", feed.id, before, _snapshot(feed),
                 summary=f"Updated threat feed {feed.name}")
    return feed


def delete_feed(db: Session, actor: str, feed: RpzThreatFeed) -> None:
    before = _snapshot(feed)
    name = feed.name
    db.delete(feed)
    db.flush()
    audit.record(db, actor, "delete", "rpz_threat_feed", before["id"], before, None,
                 summary=f"Deleted threat feed {name}")
    events.emit(db, "info", "dns", f"Threat feed {name} deleted")


def _snapshot(feed: RpzThreatFeed) -> dict:
    snap = audit.snapshot(feed)
    snap.pop("domains", None)  # too large for the changelog
    return snap


def parse_domains(text: str) -> list[str]:
    """Extract valid domains from a plain list or hosts-file formatted feed."""
    domains: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].split(";", 1)[0].strip().lower()
        if not line:
            continue
        parts = line.split()
        if len(parts) == 2 and parts[0] in _HOSTFILE_IPS:
            candidate = parts[1]
        elif len(parts) == 1:
            candidate = parts[0]
        else:
            continue
        candidate = candidate.rstrip(".")
        if candidate.startswith("*."):
            candidate = candidate[2:]  # rule rows add the wildcard themselves
        if candidate not in seen and _FQDN_RE.match(candidate):
            seen.add(candidate)
            domains.append(candidate)
            if len(domains) >= MAX_ENTRIES:
                break
    return domains


def sync_feed(db: Session, feed: RpzThreatFeed) -> RpzThreatFeed:
    """Fetch and cache the feed's domain list; failures keep the previous entries."""
    feed.last_synced = utcnow()
    try:
        response = httpx.get(feed.url, timeout=FETCH_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        feed.last_status = f"fetch failed: {exc}"[:255]
        db.flush()
        events.emit(db, "warning", "dns", f"Threat feed {feed.name} sync failed", {"error": str(exc)})
        return feed
    domains = parse_domains(response.text)
    feed.domains = "\n".join(domains)
    feed.entry_count = len(domains)
    feed.last_status = f"ok: {len(domains)} domains"
    db.flush()
    events.emit(db, "info", "dns", f"Threat feed {feed.name} synced ({len(domains)} domains)",
                {"id": feed.id})
    return feed


def enabled_feeds(db: Session) -> list[RpzThreatFeed]:
    return db.scalars(
        select(RpzThreatFeed).where(RpzThreatFeed.enabled).order_by(RpzThreatFeed.name)
    ).all()


def feeds_due(db: Session) -> list[RpzThreatFeed]:
    """Enabled feeds whose cache is older than their refresh interval."""
    due = []
    now = utcnow()
    for feed in enabled_feeds(db):
        if feed.last_synced is None:
            due.append(feed)
        elif (now - feed.last_synced).total_seconds() >= feed.refresh_hours * 3600:
            due.append(feed)
    return due
