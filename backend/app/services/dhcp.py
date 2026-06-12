import ipaddress
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DhcpOption, DhcpRange, DhcpReservation, DhcpSubnet, IPAddress, Network
from app.services import audit, events

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")

KNOWN_OPTIONS = ("routers", "domain-name-servers", "domain-name", "ntp-servers", "time-servers")


def normalize_mac(mac: str) -> str:
    if not _MAC_RE.match(mac):
        raise HTTPException(status_code=422, detail=f"Invalid MAC address {mac!r}")
    return mac.replace("-", ":").lower()


def _ip_in_network(ip: str, network: Network) -> None:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid IP: {exc}") from exc
    if addr not in ipaddress.ip_network(network.cidr):
        raise HTTPException(status_code=422, detail=f"{ip} is not inside {network.cidr}")


def create_subnet(db: Session, actor: str, data: dict) -> DhcpSubnet:
    network = db.get(Network, data["network_id"])
    if network is None:
        raise HTTPException(status_code=404, detail="Network not found")
    if network.is_container:
        raise HTTPException(status_code=422, detail="DHCP cannot be enabled on a container network")
    if db.scalar(select(DhcpSubnet).where(DhcpSubnet.network_id == network.id)):
        raise HTTPException(status_code=409, detail=f"DHCP already enabled on {network.cidr}")
    subnet = DhcpSubnet(**data)
    db.add(subnet)
    db.flush()
    audit.record(db, actor, "create", "dhcp_subnet", subnet.id, None, audit.snapshot(subnet),
                 summary=f"Enabled DHCP on {network.cidr}")
    events.emit(db, "info", "dhcp", f"DHCP scope created for {network.cidr}", {"id": subnet.id})
    return subnet


def update_subnet(db: Session, actor: str, subnet: DhcpSubnet, data: dict) -> DhcpSubnet:
    before = audit.snapshot(subnet)
    data.pop("network_id", None)
    for key, value in data.items():
        setattr(subnet, key, value)
    db.flush()
    audit.record(db, actor, "update", "dhcp_subnet", subnet.id, before, audit.snapshot(subnet),
                 summary=f"Updated DHCP scope on {subnet.network.cidr}")
    return subnet


def delete_subnet(db: Session, actor: str, subnet: DhcpSubnet) -> None:
    before = audit.snapshot(subnet)
    cidr = subnet.network.cidr
    db.delete(subnet)
    db.flush()
    audit.record(db, actor, "delete", "dhcp_subnet", before["id"], before, None,
                 summary=f"Disabled DHCP on {cidr}")
    events.emit(db, "info", "dhcp", f"DHCP scope removed from {cidr}")


def create_range(db: Session, actor: str, subnet: DhcpSubnet, data: dict) -> DhcpRange:
    _ip_in_network(data["start_ip"], subnet.network)
    _ip_in_network(data["end_ip"], subnet.network)
    if int(ipaddress.ip_address(data["start_ip"])) > int(ipaddress.ip_address(data["end_ip"])):
        raise HTTPException(status_code=422, detail="Range start must be <= end")
    rng = DhcpRange(subnet_id=subnet.id, **data)
    db.add(rng)
    db.flush()
    audit.record(db, actor, "create", "dhcp_range", rng.id, None, audit.snapshot(rng),
                 summary=f"Added range {rng.start_ip}-{rng.end_ip}")
    events.emit(db, "info", "dhcp", f"Range {rng.start_ip}-{rng.end_ip} added to {subnet.network.cidr}")
    return rng


def delete_range(db: Session, actor: str, rng: DhcpRange) -> None:
    before = audit.snapshot(rng)
    db.delete(rng)
    db.flush()
    audit.record(db, actor, "delete", "dhcp_range", before["id"], before, None,
                 summary=f"Removed range {before['start_ip']}-{before['end_ip']}")


def create_reservation(db: Session, actor: str, subnet: DhcpSubnet, data: dict) -> DhcpReservation:
    data["mac"] = normalize_mac(data["mac"])
    _ip_in_network(data["ip"], subnet.network)
    if db.scalar(select(DhcpReservation).where(DhcpReservation.subnet_id == subnet.id,
                                               DhcpReservation.mac == data["mac"])):
        raise HTTPException(status_code=409, detail=f"Reservation for {data['mac']} already exists")
    # Reserve the IP in IPAM too (upsert)
    ip_row = db.scalar(select(IPAddress).where(IPAddress.network_id == subnet.network_id,
                                               IPAddress.ip == data["ip"]))
    if ip_row is None:
        ip_row = IPAddress(network_id=subnet.network_id, ip=data["ip"], status="reserved",
                           hostname=data.get("hostname", ""), mac=data["mac"],
                           description="DHCP reservation")
        db.add(ip_row)
        db.flush()
        audit.record(db, actor, "create", "ip_address", ip_row.id, None, audit.snapshot(ip_row),
                     summary=f"Reserved IP {ip_row.ip} for DHCP")
    reservation = DhcpReservation(subnet_id=subnet.id, ip_address_id=ip_row.id, **data)
    db.add(reservation)
    db.flush()
    audit.record(db, actor, "create", "dhcp_reservation", reservation.id, None,
                 audit.snapshot(reservation),
                 summary=f"Reserved {reservation.ip} for {reservation.mac}")
    events.emit(db, "info", "dhcp", f"Reservation {reservation.mac} -> {reservation.ip}",
                {"id": reservation.id})
    return reservation


def delete_reservation(db: Session, actor: str, reservation: DhcpReservation) -> None:
    before = audit.snapshot(reservation)
    if reservation.ip_address_id:
        ip_row = db.get(IPAddress, reservation.ip_address_id)
        if ip_row is not None and ip_row.status == "reserved":
            ip_before = audit.snapshot(ip_row)
            db.delete(ip_row)
            db.flush()
            audit.record(db, actor, "delete", "ip_address", ip_before["id"], ip_before, None,
                         summary=f"Released reserved IP {ip_before['ip']}")
    db.delete(reservation)
    db.flush()
    audit.record(db, actor, "delete", "dhcp_reservation", before["id"], before, None,
                 summary=f"Removed reservation {before['mac']}")
    events.emit(db, "info", "dhcp", f"Reservation {before['mac']} removed")


def set_option(db: Session, actor: str, data: dict, subnet: DhcpSubnet | None = None) -> DhcpOption:
    if data["name"] not in KNOWN_OPTIONS:
        raise HTTPException(status_code=422, detail=f"Unsupported option {data['name']!r}; "
                                                    f"supported: {', '.join(KNOWN_OPTIONS)}")
    subnet_id = subnet.id if subnet else None
    existing = db.scalar(select(DhcpOption).where(DhcpOption.subnet_id == subnet_id,
                                                  DhcpOption.name == data["name"]))
    if existing:
        before = audit.snapshot(existing)
        existing.value = data["value"]
        db.flush()
        audit.record(db, actor, "update", "dhcp_option", existing.id, before, audit.snapshot(existing),
                     summary=f"Updated option {existing.name}")
        return existing
    option = DhcpOption(subnet_id=subnet_id, **data)
    db.add(option)
    db.flush()
    audit.record(db, actor, "create", "dhcp_option", option.id, None, audit.snapshot(option),
                 summary=f"Set option {option.name}")
    return option


def delete_option(db: Session, actor: str, option: DhcpOption) -> None:
    before = audit.snapshot(option)
    db.delete(option)
    db.flush()
    audit.record(db, actor, "delete", "dhcp_option", before["id"], before, None,
                 summary=f"Removed option {before['name']}")
