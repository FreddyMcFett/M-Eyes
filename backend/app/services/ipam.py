import ipaddress

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DhcpRange, DhcpSubnet, IPAddress, Network, Tag
from app.services import audit, events, extattrs

MAX_SCAN_PREFIX = 16  # refuse next-free-IP scans for networks larger than a /16


def parse_cidr(cidr: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
    try:
        return ipaddress.ip_network(cidr, strict=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid CIDR: {exc}") from exc


def find_parent(db: Session, cidr: str, exclude_id: int | None = None) -> Network | None:
    """Longest-prefix containing network becomes the parent."""
    target = parse_cidr(cidr)
    best: Network | None = None
    best_prefix = -1
    for network in db.scalars(select(Network)).all():
        if network.id == exclude_id:
            continue
        candidate = ipaddress.ip_network(network.cidr)
        if candidate.version != target.version:
            continue
        if candidate.prefixlen < target.prefixlen and target.subnet_of(candidate):
            if candidate.prefixlen > best_prefix:
                best = network
                best_prefix = candidate.prefixlen
    return best


def _reparent_children(db: Session, network: Network) -> None:
    """Existing networks contained in the new network become its children."""
    net = ipaddress.ip_network(network.cidr)
    for other in db.scalars(select(Network)).all():
        if other.id == network.id:
            continue
        other_net = ipaddress.ip_network(other.cidr)
        if other_net.version != net.version or other_net.prefixlen <= net.prefixlen:
            continue
        if other_net.subnet_of(net):
            current_parent_prefix = -1
            if other.parent_id:
                parent = db.get(Network, other.parent_id)
                if parent:
                    current_parent_prefix = ipaddress.ip_network(parent.cidr).prefixlen
            if net.prefixlen > current_parent_prefix:
                other.parent_id = network.id


def create_network(db: Session, actor: str, data: dict) -> Network:
    parse_cidr(data["cidr"])
    if db.scalar(select(Network).where(Network.cidr == data["cidr"])):
        raise HTTPException(status_code=409, detail=f"Network {data['cidr']} already exists")
    tag_ids = data.pop("tag_ids", None)
    network = Network(**data)
    parent = find_parent(db, network.cidr)
    network.parent_id = parent.id if parent else None
    if tag_ids is not None:
        network.tags = list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all())
    db.add(network)
    db.flush()
    _reparent_children(db, network)
    audit.record(db, actor, "create", "network", network.id, None, audit.snapshot(network),
                 summary=f"Created network {network.cidr}")
    events.emit(db, "info", "ipam", f"Network {network.cidr} created", {"id": network.id})
    return network


def update_network(db: Session, actor: str, network: Network, data: dict) -> Network:
    before = audit.snapshot(network)
    tag_ids = data.pop("tag_ids", None)
    if "cidr" in data and data["cidr"] != network.cidr:
        parse_cidr(data["cidr"])
        if db.scalar(select(Network).where(Network.cidr == data["cidr"], Network.id != network.id)):
            raise HTTPException(status_code=409, detail=f"Network {data['cidr']} already exists")
        parent = find_parent(db, data["cidr"], exclude_id=network.id)
        network.parent_id = parent.id if parent else None
    for key, value in data.items():
        setattr(network, key, value)
    if tag_ids is not None:
        network.tags = list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all())
    db.flush()
    audit.record(db, actor, "update", "network", network.id, before, audit.snapshot(network),
                 summary=f"Updated network {network.cidr}")
    events.emit(db, "info", "ipam", f"Network {network.cidr} updated", {"id": network.id})
    return network


def delete_network(db: Session, actor: str, network: Network) -> None:
    before = audit.snapshot(network)
    cidr = network.cidr
    for child in db.scalars(select(Network).where(Network.parent_id == network.id)).all():
        child.parent_id = network.parent_id
    for ip_row in network.ip_addresses:
        extattrs.purge(db, "ip_address", ip_row.id)
    extattrs.purge(db, "network", network.id)
    db.delete(network)
    db.flush()
    audit.record(db, actor, "delete", "network", before["id"], before, None,
                 summary=f"Deleted network {cidr}")
    events.emit(db, "info", "ipam", f"Network {cidr} deleted")


def dhcp_range_members(db: Session, network: Network) -> set[str]:
    """All IPs covered by DHCP ranges configured on this network's scope."""
    members: set[str] = set()
    subnet = db.scalar(select(DhcpSubnet).where(DhcpSubnet.network_id == network.id))
    if not subnet:
        return members
    for r in db.scalars(select(DhcpRange).where(DhcpRange.subnet_id == subnet.id)).all():
        start = int(ipaddress.ip_address(r.start_ip))
        end = int(ipaddress.ip_address(r.end_ip))
        for value in range(start, end + 1):
            members.add(str(ipaddress.ip_address(value)))
    return members


def next_available_ip(db: Session, network: Network) -> str:
    net = ipaddress.ip_network(network.cidr)
    if net.version == 6:
        raise HTTPException(status_code=422, detail="Automatic allocation is IPv4-only; assign IPv6 manually")
    if net.prefixlen < MAX_SCAN_PREFIX:
        raise HTTPException(
            status_code=422,
            detail=f"Network too large to scan (>{MAX_SCAN_PREFIX}); allocate from a smaller subnet",
        )
    taken = {row.ip for row in db.scalars(select(IPAddress).where(IPAddress.network_id == network.id))}
    taken |= dhcp_range_members(db, network)
    for host in net.hosts():
        ip = str(host)
        if ip not in taken:
            return ip
    raise HTTPException(status_code=409, detail=f"No free addresses left in {network.cidr}")


def utilization(db: Session, network: Network) -> dict:
    net = ipaddress.ip_network(network.cidr)
    if net.version == 6:
        total = 0
    elif net.prefixlen >= 31:
        total = net.num_addresses
    else:
        total = net.num_addresses - 2  # network + broadcast
    used = db.query(IPAddress).filter(IPAddress.network_id == network.id).count()
    dhcp_count = len(dhcp_range_members(db, network)) if net.version == 4 else 0
    occupied = used + dhcp_count
    return {
        "total": total,
        "used": used,
        "dhcp_range": dhcp_count,
        "free": max(total - occupied, 0),
        "percent": round(occupied / total * 100, 1) if total else 0.0,
    }


def create_ip(db: Session, actor: str, network: Network, data: dict) -> IPAddress:
    ip_value = data.get("ip") or next_available_ip(db, network)
    addr = ipaddress.ip_address(ip_value)
    if addr not in ipaddress.ip_network(network.cidr):
        raise HTTPException(status_code=422, detail=f"{ip_value} is not inside {network.cidr}")
    if db.scalar(select(IPAddress).where(IPAddress.network_id == network.id, IPAddress.ip == ip_value)):
        raise HTTPException(status_code=409, detail=f"{ip_value} is already allocated")
    tag_ids = data.pop("tag_ids", None)
    data["ip"] = ip_value
    record = IPAddress(network_id=network.id, **data)
    if tag_ids is not None:
        record.tags = list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all())
    db.add(record)
    db.flush()
    audit.record(db, actor, "create", "ip_address", record.id, None, audit.snapshot(record),
                 summary=f"Allocated IP {ip_value}")
    events.emit(db, "info", "ipam", f"IP {ip_value} allocated in {network.cidr}", {"id": record.id})
    return record


def update_ip(db: Session, actor: str, record: IPAddress, data: dict) -> IPAddress:
    before = audit.snapshot(record)
    tag_ids = data.pop("tag_ids", None)
    data.pop("ip", None)  # the address itself is immutable; delete + recreate to move
    for key, value in data.items():
        setattr(record, key, value)
    if tag_ids is not None:
        record.tags = list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all())
    db.flush()
    audit.record(db, actor, "update", "ip_address", record.id, before, audit.snapshot(record),
                 summary=f"Updated IP {record.ip}")
    return record


def delete_ip(db: Session, actor: str, record: IPAddress) -> None:
    before = audit.snapshot(record)
    ip_value = record.ip
    extattrs.purge(db, "ip_address", record.id)
    db.delete(record)
    db.flush()
    audit.record(db, actor, "delete", "ip_address", before["id"], before, None,
                 summary=f"Released IP {ip_value}")
    events.emit(db, "info", "ipam", f"IP {ip_value} released")
