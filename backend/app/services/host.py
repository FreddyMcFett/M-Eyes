"""Composite host operations: one call allocates an IP, creates A + PTR records
and optionally a DHCP reservation - the Infoblox-style 'Host' object."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DhcpReservation, DhcpSubnet, Host, IPAddress, Network, Record
from app.services import audit, events, ipam
from app.services import dhcp as dhcp_service
from app.services import dns as dns_service


def create_host(
    db: Session,
    actor: str,
    name: str,
    network_id: int,
    ip: str | None = None,
    mac: str | None = None,
    create_reservation: bool = False,
    description: str = "",
) -> Host:
    name = name.rstrip(".").lower()
    if db.scalar(select(Host).where(Host.name == name)):
        raise HTTPException(status_code=409, detail=f"Host {name} already exists")
    network = db.get(Network, network_id)
    if network is None:
        raise HTTPException(status_code=404, detail="Network not found")
    forward = dns_service.find_forward_zone(db, name)
    if forward is None:
        raise HTTPException(status_code=422, detail=f"No forward zone matches {name}; create the zone first")
    zone, relative = forward
    if create_reservation and not mac:
        raise HTTPException(status_code=422, detail="MAC address required for a DHCP reservation")

    ip_row = ipam.create_ip(
        db, actor, network,
        {"ip": ip, "status": "used", "hostname": name, "mac": mac or "", "description": description},
    )
    a_record = dns_service.create_record(
        db, actor, zone, {"name": relative, "type": "A", "value": ip_row.ip}, auto_ptr=False
    )
    ptr_record = dns_service.ensure_ptr(db, actor, ip_row.ip, name)

    reservation = None
    if create_reservation:
        subnet = db.scalar(select(DhcpSubnet).where(DhcpSubnet.network_id == network.id))
        if subnet is None:
            raise HTTPException(status_code=422,
                                detail=f"No DHCP scope on {network.cidr}; enable DHCP first")
        reservation = dhcp_service.create_reservation(
            db, actor, subnet, {"mac": mac, "ip": ip_row.ip, "hostname": name}
        )

    host = Host(
        name=name,
        ip_address_id=ip_row.id,
        a_record_id=a_record.id,
        ptr_record_id=ptr_record.id if ptr_record else None,
        reservation_id=reservation.id if reservation else None,
    )
    db.add(host)
    db.flush()
    audit.record(db, actor, "create", "host", host.id, None, audit.snapshot(host),
                 summary=f"Created host {name} ({ip_row.ip})")
    events.emit(db, "info", "ipam", f"Host {name} created with IP {ip_row.ip}", {"id": host.id})
    return host


def delete_host(db: Session, actor: str, host: Host) -> None:
    before = audit.snapshot(host)
    name = host.name

    if host.reservation_id:
        reservation = db.get(DhcpReservation, host.reservation_id)
        if reservation is not None:
            dhcp_service.delete_reservation(db, actor, reservation)
    for record_id in (host.a_record_id, host.ptr_record_id):
        if record_id:
            record = db.get(Record, record_id)
            if record is not None:
                dns_service.delete_record(db, actor, record)
    if host.ip_address_id:
        ip_row = db.get(IPAddress, host.ip_address_id)
        if ip_row is not None:
            ipam.delete_ip(db, actor, ip_row)

    db.delete(host)
    db.flush()
    audit.record(db, actor, "delete", "host", before["id"], before, None,
                 summary=f"Deleted host {name}")
    events.emit(db, "info", "ipam", f"Host {name} deleted")
