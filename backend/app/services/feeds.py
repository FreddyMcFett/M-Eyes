"""Builds FortiGate External Resource feed payloads."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BlocklistEntry, Feed, IPAddress, Network, Record, Tag
from app.services import audit


def build_entries(db: Session, feed: Feed) -> list[str]:
    if feed.kind == "networks":
        return [
            n.cidr
            for n in db.scalars(
                select(Network).where(Network.is_container.is_(False)).order_by(Network.cidr)
            ).all()
        ]
    if feed.kind == "tag":
        tag = db.get(Tag, feed.tag_id) if feed.tag_id else None
        if tag is None:
            return []
        entries = [n.cidr for n in db.scalars(select(Network)).all() if tag in n.tags]
        entries += [
            f"{ip.ip}/32" for ip in db.scalars(select(IPAddress)).all() if tag in ip.tags
        ]
        return sorted(set(entries))
    if feed.kind == "blocklist":
        return [e.value for e in db.scalars(select(BlocklistEntry).order_by(BlocklistEntry.value)).all()]
    if feed.kind == "fqdn":
        fqdns: set[str] = set()
        for record in db.scalars(select(Record).where(Record.type.in_(("A", "AAAA", "CNAME")))).all():
            zone_name = record.zone.name
            if record.zone.kind != "forward":
                continue
            fqdn = zone_name if record.name == "@" else f"{record.name}.{zone_name}"
            fqdns.add(fqdn)
        return sorted(fqdns)
    raise HTTPException(status_code=500, detail=f"Unknown feed kind {feed.kind!r}")


def feed_payload_json(db: Session, feed: Feed) -> dict:
    return {
        "feed": feed.slug,
        "version": audit.current_version(db),
        "entries": build_entries(db, feed),
    }


def fortigate_snippet(feed: Feed, base_url: str) -> str:
    resource_type = "domain" if feed.kind == "fqdn" else "address"
    return (
        "config system external-resource\n"
        f'    edit "meyes-{feed.slug}"\n'
        f"        set type {resource_type}\n"
        f'        set resource "{base_url}/feeds/{feed.slug}.txt"\n'
        '        set username "feed"\n'
        f"        set password {feed.token}\n"
        "        set refresh-rate 5\n"
        "        set status enable\n"
        "    next\n"
        "end"
    )
