"""Global search (Infoblox-style): one query across every object family,
returning typed results with a UI deep link."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Host, IPAddress, Network, Record, RpzRule, Zone

PER_CATEGORY_LIMIT = 20


def search(db: Session, query: str) -> list[dict]:
    like = f"%{query}%"
    results: list[dict] = []

    for network in db.scalars(
        select(Network).where(
            or_(Network.cidr.ilike(like), Network.name.ilike(like),
                Network.description.ilike(like), Network.site.ilike(like))
        ).order_by(Network.cidr).limit(PER_CATEGORY_LIMIT)
    ).all():
        results.append({"type": "network", "id": network.id, "label": network.cidr,
                        "detail": network.name or network.description,
                        "url": f"/ipam/{network.id}"})

    for ip in db.scalars(
        select(IPAddress).where(
            or_(IPAddress.ip.ilike(like), IPAddress.hostname.ilike(like),
                IPAddress.mac.ilike(like), IPAddress.description.ilike(like))
        ).order_by(IPAddress.ip).limit(PER_CATEGORY_LIMIT)
    ).all():
        results.append({"type": "ip_address", "id": ip.id, "label": ip.ip,
                        "detail": ip.hostname or ip.status,
                        "url": f"/ipam/{ip.network_id}"})

    for zone in db.scalars(
        select(Zone).where(Zone.name.ilike(like)).order_by(Zone.name).limit(PER_CATEGORY_LIMIT)
    ).all():
        results.append({"type": "zone", "id": zone.id, "label": zone.name,
                        "detail": f"{zone.kind} zone"
                                  + (f" (view {zone.view.name})" if zone.view else ""),
                        "url": f"/dns/{zone.id}"})

    for record in db.scalars(
        select(Record).where(or_(Record.name.ilike(like), Record.value.ilike(like)))
        .order_by(Record.name).limit(PER_CATEGORY_LIMIT)
    ).all():
        fqdn = record.zone.name if record.name == "@" else f"{record.name}.{record.zone.name}"
        results.append({"type": "record", "id": record.id, "label": fqdn,
                        "detail": f"{record.type} {record.value}",
                        "url": f"/dns/{record.zone_id}"})

    for host in db.scalars(
        select(Host).where(Host.name.ilike(like)).order_by(Host.name).limit(PER_CATEGORY_LIMIT)
    ).all():
        results.append({"type": "host", "id": host.id, "label": host.name,
                        "detail": "composite host", "url": "/hosts"})

    for rule in db.scalars(
        select(RpzRule).where(RpzRule.fqdn.ilike(like)).order_by(RpzRule.fqdn)
        .limit(PER_CATEGORY_LIMIT)
    ).all():
        results.append({"type": "rpz_rule", "id": rule.id, "label": rule.fqdn,
                        "detail": f"DNS firewall: {rule.action}", "url": "/dnsfw"})

    return results
