import ipaddress
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Network, Record, View, Zone
from app.models.dns import RECORD_TYPES, ZONE_ROLES
from app.services import audit, events, extattrs

_NAME_RE = re.compile(r"^(@|\*|[A-Za-z0-9_]([A-Za-z0-9_\-\.\*]*[A-Za-z0-9_])?)$")
# Control characters (incl. newlines) must never reach the generated zone file:
# a newline in a record value or zone name would let an authenticated user inject
# arbitrary BIND directives or extra resource records.
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
# Host name used as a zone name or as the value of a name-typed record. Allows an
# optional leading wildcard label and an optional trailing dot (absolute name).
_HOSTNAME_RE = re.compile(
    r"^(\*\.)?([A-Za-z0-9_](?:[A-Za-z0-9_\-]*[A-Za-z0-9_])?\.)*"
    r"[A-Za-z0-9_](?:[A-Za-z0-9_\-]*[A-Za-z0-9_])?\.?$"
)
_NAME_VALUE_TYPES = ("CNAME", "NS", "PTR", "MX", "SRV")


def bump_serial(db: Session, zone: Zone) -> None:
    zone.serial = (zone.serial or 0) + 1
    db.flush()


def reverse_zone_name(cidr: str) -> str:
    """in-addr.arpa zone name for an octet-boundary IPv4 network (/8, /16, /24)."""
    net = ipaddress.ip_network(cidr)
    if net.version != 4 or net.prefixlen not in (8, 16, 24):
        raise HTTPException(
            status_code=422,
            detail="Reverse zones can only be derived from /8, /16 or /24 IPv4 networks",
        )
    octets = str(net.network_address).split(".")[: net.prefixlen // 8]
    return ".".join(reversed(octets)) + ".in-addr.arpa"


def find_reverse_zone(db: Session, ip: str) -> Zone | None:
    """Longest-matching reverse zone for an IPv4 address."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if addr.version != 4:
        return None
    octets = str(addr).split(".")
    candidates = [
        ".".join(reversed(octets[:3])) + ".in-addr.arpa",  # /24
        ".".join(reversed(octets[:2])) + ".in-addr.arpa",  # /16
        octets[0] + ".in-addr.arpa",  # /8
    ]
    for name in candidates:
        # the same zone name may exist in several views; prefer the default view
        zones = db.scalars(select(Zone).where(Zone.name == name)).all()
        if zones:
            return min(zones, key=lambda z: (z.view_id is not None, z.id))
    return None


def ptr_name_in_zone(zone: Zone, ip: str) -> str:
    """Relative PTR owner name for an IP inside the given reverse zone."""
    octets = ip.split(".")
    zone_octets = zone.name.removesuffix(".in-addr.arpa").split(".")
    host_part = octets[len(zone_octets):]
    return ".".join(reversed(host_part))


def find_forward_zone(db: Session, fqdn: str) -> tuple[Zone, str] | None:
    """Longest-suffix forward zone match; returns (zone, relative_name)."""
    fqdn = fqdn.rstrip(".").lower()
    best: Zone | None = None
    for zone in db.scalars(select(Zone).where(Zone.kind == "forward")).all():
        zname = zone.name.rstrip(".").lower()
        if fqdn == zname or fqdn.endswith("." + zname):
            # longest suffix wins; on a tie prefer the default view over named views
            if best is None or (len(zname), zone.view_id is None) > (
                len(best.name.rstrip(".")), best.view_id is None
            ):
                best = zone
    if best is None:
        return None
    zname = best.name.rstrip(".").lower()
    relative = "@" if fqdn == zname else fqdn[: -(len(zname) + 1)]
    return best, relative


def _check_view_and_duplicate(db: Session, name: str, view_id: int | None,
                              exclude_id: int | None = None) -> None:
    if view_id is not None and db.get(View, view_id) is None:
        raise HTTPException(status_code=404, detail="DNS view not found")
    query = select(Zone).where(Zone.name == name, Zone.view_id == view_id)
    if exclude_id is not None:
        query = query.where(Zone.id != exclude_id)
    if db.scalar(query):
        where = "the default view" if view_id is None else "this view"
        raise HTTPException(status_code=409, detail=f"Zone {name} already exists in {where}")


def _validate_role(data: dict) -> None:
    role = data.setdefault("role", "primary")
    if role not in ZONE_ROLES:
        raise HTTPException(status_code=422,
                            detail=f"Unsupported zone role {role!r}; one of {', '.join(ZONE_ROLES)}")
    if role == "primary":
        data["primaries"] = ""
        return
    servers = [token.strip() for token in (data.get("primaries") or "").split(",") if token.strip()]
    label = "primary servers" if role == "secondary" else "forwarders"
    if not servers:
        raise HTTPException(status_code=422, detail=f"A {role} zone requires at least one IP in {label}")
    for server in servers:
        try:
            ipaddress.ip_address(server)
        except ValueError:
            raise HTTPException(status_code=422,
                                detail=f"Invalid IP {server!r} in {label}") from None
    data["primaries"] = ",".join(servers)


def create_zone(db: Session, actor: str, data: dict) -> Zone:
    settings = get_settings()
    if data.get("kind") == "reverse" and data.get("network_id") and not data.get("name"):
        network = db.get(Network, data["network_id"])
        if network is None:
            raise HTTPException(status_code=404, detail="Network not found")
        data["name"] = reverse_zone_name(network.cidr)
    name = (data.get("name") or "").rstrip(".").lower()
    if not name:
        raise HTTPException(status_code=422, detail="Zone name is required")
    if len(name) > 253 or not _HOSTNAME_RE.match(name):
        # the zone name becomes part of the on-disk zone file name, so reject
        # anything that is not a plain DNS name (no slashes, no path traversal)
        raise HTTPException(status_code=422, detail=f"Invalid zone name {name!r}")
    data["name"] = name
    _check_view_and_duplicate(db, name, data.get("view_id"))
    _validate_role(data)
    data.setdefault("soa_mname", settings.dns_default_soa_mname)
    data.setdefault("soa_rname", settings.dns_default_soa_rname)
    data.setdefault("default_ttl", settings.dns_default_ttl)
    zone = Zone(**data)
    db.add(zone)
    db.flush()
    if zone.role == "primary":
        # apex NS record so the generated zone file is loadable by BIND
        db.add(Record(zone_id=zone.id, name="@", type="NS", value=zone.soa_mname))
        db.flush()
    audit.record(db, actor, "create", "zone", zone.id, None, audit.snapshot(zone),
                 summary=f"Created zone {zone.name}")
    events.emit(db, "info", "dns", f"Zone {zone.name} created", {"id": zone.id})
    return zone


def update_zone(db: Session, actor: str, zone: Zone, data: dict) -> Zone:
    before = audit.snapshot(zone)
    data.pop("name", None)  # renaming a zone is delete + recreate
    data.pop("serial", None)
    if "role" in data or "primaries" in data:
        merged = {"role": data.get("role", zone.role),
                  "primaries": data.get("primaries", zone.primaries)}
        _validate_role(merged)
        data["role"], data["primaries"] = merged["role"], merged["primaries"]
    if "view_id" in data and data["view_id"] != zone.view_id:
        _check_view_and_duplicate(db, zone.name, data["view_id"], exclude_id=zone.id)
    for key, value in data.items():
        setattr(zone, key, value)
    bump_serial(db, zone)
    audit.record(db, actor, "update", "zone", zone.id, before, audit.snapshot(zone),
                 summary=f"Updated zone {zone.name}")
    events.emit(db, "info", "dns", f"Zone {zone.name} updated", {"id": zone.id})
    return zone


def delete_zone(db: Session, actor: str, zone: Zone) -> None:
    before = audit.snapshot(zone)
    name = zone.name
    for record in zone.records:
        extattrs.purge(db, "record", record.id)
    extattrs.purge(db, "zone", zone.id)
    db.delete(zone)
    db.flush()
    audit.record(db, actor, "delete", "zone", before["id"], before, None, summary=f"Deleted zone {name}")
    events.emit(db, "info", "dns", f"Zone {name} deleted")


def _validate_record(data: dict) -> None:
    if data["type"] not in RECORD_TYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported record type {data['type']}")
    if not _NAME_RE.match(data["name"]):
        raise HTTPException(status_code=422, detail=f"Invalid record name {data['name']!r}")
    rtype, value = data["type"], data["value"]
    if not isinstance(value, str) or _CONTROL_RE.search(value):
        raise HTTPException(status_code=422,
                            detail="Record value contains forbidden control characters")
    if len(value) > 1024:
        raise HTTPException(status_code=422, detail="Record value is too long (max 1024 chars)")
    if rtype in _NAME_VALUE_TYPES and not _HOSTNAME_RE.match(value):
        raise HTTPException(status_code=422,
                            detail=f"{rtype} record value must be a valid host name, got {value!r}")
    if rtype == "A":
        try:
            if ipaddress.ip_address(value).version != 4:
                raise ValueError
        except ValueError:
            raise HTTPException(
                status_code=422, detail=f"A record requires an IPv4 address, got {value!r}"
            ) from None
    elif rtype == "AAAA":
        try:
            if ipaddress.ip_address(value).version != 6:
                raise ValueError
        except ValueError:
            raise HTTPException(
                status_code=422, detail=f"AAAA record requires an IPv6 address, got {value!r}"
            ) from None
    elif rtype in ("MX", "SRV") and data.get("priority") is None:
        data["priority"] = 10


def create_record(db: Session, actor: str, zone: Zone, data: dict, auto_ptr: bool = False) -> Record:
    if zone.role != "primary":
        raise HTTPException(
            status_code=422,
            detail=f"Records can only be managed on primary zones ({zone.name} is {zone.role})",
        )
    data["name"] = data["name"].strip() or "@"
    _validate_record(data)
    duplicate = db.scalar(
        select(Record).where(
            Record.zone_id == zone.id,
            Record.name == data["name"],
            Record.type == data["type"],
            Record.value == data["value"],
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Identical record already exists")
    record = Record(zone_id=zone.id, **data)
    db.add(record)
    db.flush()
    bump_serial(db, zone)
    audit.record(db, actor, "create", "record", record.id, None, audit.snapshot(record),
                 summary=f"Created {record.type} record {record.name} in {zone.name}")
    events.emit(db, "info", "dns", f"{record.type} {record.name}.{zone.name} -> {record.value}",
                {"id": record.id})
    if auto_ptr and record.type == "A":
        fqdn = zone.name if record.name == "@" else f"{record.name}.{zone.name}"
        ensure_ptr(db, actor, record.value, fqdn)
    return record


def ensure_ptr(db: Session, actor: str, ip: str, fqdn: str) -> Record | None:
    zone = find_reverse_zone(db, ip)
    if zone is None:
        events.emit(db, "warning", "dns", f"No reverse zone covers {ip}; PTR for {fqdn} not created")
        return None
    name = ptr_name_in_zone(zone, ip)
    value = fqdn.rstrip(".") + "."
    existing = db.scalar(select(Record).where(Record.zone_id == zone.id, Record.name == name,
                                              Record.type == "PTR"))
    if existing:
        if existing.value == value:
            return existing
        before = audit.snapshot(existing)
        existing.value = value
        db.flush()
        bump_serial(db, zone)
        audit.record(db, actor, "update", "record", existing.id, before, audit.snapshot(existing),
                     summary=f"Updated PTR {name} in {zone.name}")
        return existing
    record = Record(zone_id=zone.id, name=name, type="PTR", value=value)
    db.add(record)
    db.flush()
    bump_serial(db, zone)
    audit.record(db, actor, "create", "record", record.id, None, audit.snapshot(record),
                 summary=f"Created PTR {name} in {zone.name}")
    return record


def update_record(db: Session, actor: str, record: Record, data: dict) -> Record:
    before = audit.snapshot(record)
    merged = {
        "name": data.get("name", record.name),
        "type": data.get("type", record.type),
        "value": data.get("value", record.value),
        "priority": data.get("priority", record.priority),
    }
    _validate_record(merged)
    for key in ("name", "type", "value", "ttl", "priority"):
        if key in data:
            setattr(record, key, data[key])
    db.flush()
    bump_serial(db, record.zone)
    audit.record(db, actor, "update", "record", record.id, before, audit.snapshot(record),
                 summary=f"Updated {record.type} record {record.name}")
    return record


def delete_record(db: Session, actor: str, record: Record) -> None:
    before = audit.snapshot(record)
    zone = record.zone
    extattrs.purge(db, "record", record.id)
    db.delete(record)
    db.flush()
    bump_serial(db, zone)
    audit.record(db, actor, "delete", "record", before["id"], before, None,
                 summary=f"Deleted {before['type']} record {before['name']} in {zone.name}")
    events.emit(db, "info", "dns", f"Record {before['name']} ({before['type']}) deleted from {zone.name}")
