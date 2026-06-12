"""Network discovery: ICMP ping sweep over a managed network.

Responding addresses that are unknown to IPAM are recorded with status
'discovered' (Infoblox 'unmanaged'); already-allocated addresses get their
last_seen timestamp refreshed. A response from an address that IPAM holds
as 'reserved' is flagged as a conflict.
"""

import ipaddress
import subprocess
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IPAddress, Network
from app.models.base import utcnow
from app.services import audit, events

MAX_DISCOVERY_PREFIX = 22  # refuse sweeps over networks larger than a /22 (~1k hosts)
PING_WORKERS = 64


def _ping(ip: str) -> bool:
    try:
        proc = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            capture_output=True, timeout=3,
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def discover(db: Session, actor: str, network: Network) -> dict:
    net = ipaddress.ip_network(network.cidr)
    if net.version != 4:
        raise HTTPException(status_code=422, detail="Discovery is IPv4-only")
    if net.prefixlen < MAX_DISCOVERY_PREFIX:
        raise HTTPException(
            status_code=422,
            detail=f"Network too large to sweep (larger than /{MAX_DISCOVERY_PREFIX}); "
                   "discover a smaller subnet",
        )

    hosts = [str(host) for host in net.hosts()]
    with ThreadPoolExecutor(max_workers=PING_WORKERS) as pool:
        alive = {ip for ip, ok in zip(hosts, pool.map(_ping, hosts), strict=True) if ok}

    existing = {
        row.ip: row
        for row in db.scalars(select(IPAddress).where(IPAddress.network_id == network.id)).all()
    }
    now = utcnow()
    created = updated = conflicts = 0
    for ip in sorted(alive, key=lambda value: int(ipaddress.ip_address(value))):
        row = existing.get(ip)
        if row is None:
            row = IPAddress(network_id=network.id, ip=ip, status="discovered",
                            description="Discovered by ping sweep", last_seen=now)
            db.add(row)
            db.flush()
            audit.record(db, actor, "create", "ip_address", row.id, None, audit.snapshot(row),
                         summary=f"Discovered IP {ip}")
            created += 1
        else:
            row.last_seen = now
            updated += 1
            if row.status == "reserved":
                conflicts += 1
                events.emit(db, "warning", "ipam",
                            f"Discovery conflict: {ip} is reserved in IPAM but answered the sweep",
                            {"id": row.id})
    db.flush()
    events.emit(db, "info", "ipam",
                f"Discovery on {network.cidr}: {len(alive)} alive, {created} new, "
                f"{conflicts} conflict(s)", {"network_id": network.id})
    return {
        "cidr": network.cidr,
        "scanned": len(hosts),
        "alive": len(alive),
        "created": created,
        "updated": updated,
        "conflicts": conflicts,
    }
