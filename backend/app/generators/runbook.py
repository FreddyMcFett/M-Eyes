from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.generators import jinja_env
from app.models import DhcpSubnet, Feed, Host, IPAddress, Network, Record, Zone
from app.services import audit, ipam


def render_runbook(db: Session) -> dict:
    networks = []
    for network in db.scalars(select(Network).order_by(Network.cidr)).all():
        util = ipam.utilization(db, network)
        networks.append(
            {
                "cidr": network.cidr,
                "name": network.name,
                "is_container": network.is_container,
                "vlan": network.vlan,
                "site": network.site,
                "utilization": util["percent"],
            }
        )

    zones = []
    for zone in db.scalars(select(Zone).order_by(Zone.name)).all():
        zones.append(
            {"name": zone.name, "kind": zone.kind, "serial": zone.serial,
             "record_count": len(zone.records)}
        )

    dhcp_subnets = []
    for subnet in db.scalars(select(DhcpSubnet)).all():
        dhcp_subnets.append(
            {
                "cidr": subnet.network.cidr,
                "enabled": subnet.enabled,
                "ranges": [f"{r.start_ip}-{r.end_ip}" for r in subnet.ranges],
                "reservation_count": len(subnet.reservations),
            }
        )

    feeds = db.scalars(select(Feed).order_by(Feed.slug)).all()
    config_version = audit.current_version(db)
    markdown = jinja_env.get_template("runbook.md.j2").render(
        config_version=config_version,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        networks=networks,
        zones=zones,
        dhcp_subnets=dhcp_subnets,
        feeds=feeds,
        ip_count=db.scalar(select(func.count(IPAddress.id))) or 0,
        record_count=db.scalar(select(func.count(Record.id))) or 0,
        host_count=db.scalar(select(func.count(Host.id))) or 0,
    )
    return {
        "markdown": markdown,
        "config_version": config_version,
        "generated_at": datetime.now(UTC).isoformat(),
    }
