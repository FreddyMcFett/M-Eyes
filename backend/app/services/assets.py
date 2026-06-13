"""Asset (CMDB) service: CRUD plus reconciliation against live DDI data.

DDI reconciliation matches asset interfaces to IPAM addresses by MAC first, then
IP, and can mint new assets from discovered/managed addresses and DHCP leases so
the inventory stays in step with what is actually on the network.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, AssetInterface, IPAddress, Tag
from app.models.base import utcnow
from app.services import audit, events


def _norm_mac(mac: str) -> str:
    return mac.replace("-", ":").lower().strip()


def list_assets(db: Session) -> list[Asset]:
    return list(db.scalars(select(Asset).order_by(Asset.name)).all())


def get(db: Session, asset_id: int) -> Asset | None:
    return db.get(Asset, asset_id)


def _apply_tags(db: Session, asset: Asset, tag_ids: list[int]) -> None:
    asset.tags = list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all()) if tag_ids else []


def _link_interface(db: Session, iface: AssetInterface) -> bool:
    """Resolve iface.ip_id from its IP, refreshing IPAM hostname/mac. Returns True if linked."""
    if not iface.ip:
        return False
    ip_row = db.scalar(select(IPAddress).where(IPAddress.ip == iface.ip))
    if ip_row is None:
        return False
    iface.ip_id = ip_row.id
    if iface.mac and not ip_row.mac:
        ip_row.mac = iface.mac
    if iface.hostname and not ip_row.hostname:
        ip_row.hostname = iface.hostname
    return True


def create(db: Session, actor: str, data: dict, interfaces: list[dict], tag_ids: list[int]) -> Asset:
    asset = Asset(**data)
    db.add(asset)
    db.flush()
    _apply_tags(db, asset, tag_ids)
    for spec in interfaces:
        iface = AssetInterface(asset_id=asset.id, **spec)
        iface.mac = _norm_mac(iface.mac)
        db.add(iface)
        db.flush()
        _link_interface(db, iface)
    db.flush()
    audit.record(db, actor, "create", "asset", asset.id, None, audit.snapshot(asset),
                 summary=f"Created asset {asset.name}")
    events.emit(db, "info", "asset", f"Asset {asset.name!r} created by {actor}", {"id": asset.id})
    return asset


def update(db: Session, actor: str, asset: Asset, changes: dict,
           interfaces: list[dict] | None, tag_ids: list[int] | None) -> Asset:
    before = audit.snapshot(asset)
    for field, value in changes.items():
        setattr(asset, field, value)
    if tag_ids is not None:
        _apply_tags(db, asset, tag_ids)
    if interfaces is not None:
        asset.interfaces.clear()
        db.flush()
        for spec in interfaces:
            iface = AssetInterface(asset_id=asset.id, **spec)
            iface.mac = _norm_mac(iface.mac)
            db.add(iface)
            db.flush()
            _link_interface(db, iface)
    db.flush()
    audit.record(db, actor, "update", "asset", asset.id, before, audit.snapshot(asset),
                 summary=f"Updated asset {asset.name}")
    return asset


def delete(db: Session, actor: str, asset: Asset) -> None:
    name = asset.name
    asset_id = asset.id
    db.delete(asset)
    db.flush()
    audit.record(db, actor, "delete", "asset", asset_id, {"name": name}, None,
                 summary=f"Deleted asset {name}")
    events.emit(db, "info", "asset", f"Asset {name!r} deleted by {actor}")


def _find_asset_for(db: Session, mac: str, ip: str) -> Asset | None:
    """Locate an existing asset by interface MAC (preferred) or IP."""
    mac = _norm_mac(mac)
    if mac:
        iface = db.scalar(select(AssetInterface).where(AssetInterface.mac == mac))
        if iface is not None:
            return iface.asset
    if ip:
        iface = db.scalar(select(AssetInterface).where(AssetInterface.ip == ip))
        if iface is not None:
            return iface.asset
    return None


def upsert_from_observation(
    db: Session,
    *,
    name: str,
    ip: str = "",
    mac: str = "",
    hostname: str = "",
    source: str = "discovery",
    asset_type: str = "other",
    external_id: str = "",
    extra: dict | None = None,
) -> tuple[Asset, str]:
    """Create or update an asset from a single network observation.

    Returns (asset, outcome) where outcome is 'created', 'updated' or 'linked'.
    """
    mac = _norm_mac(mac)
    asset = _find_asset_for(db, mac, ip)
    outcome = "updated"
    if asset is None:
        asset = Asset(name=name or hostname or ip or mac or "unknown",
                      asset_type=asset_type, source=source, external_id=external_id)
        db.add(asset)
        db.flush()
        outcome = "created"
    for field, value in (extra or {}).items():
        if value and not getattr(asset, field, None):
            setattr(asset, field, value)
    asset.last_seen = utcnow()

    iface = None
    for existing in asset.interfaces:
        if (mac and existing.mac == mac) or (ip and existing.ip == ip):
            iface = existing
            break
    if iface is None:
        iface = AssetInterface(asset_id=asset.id)
        asset.interfaces.append(iface)
        if outcome != "created":
            outcome = "linked"
    iface.mac = mac or iface.mac
    iface.ip = ip or iface.ip
    iface.hostname = hostname or iface.hostname
    db.flush()
    if _link_interface(db, iface) and outcome == "updated":
        outcome = "linked"
    db.flush()
    return asset, outcome


def sync_from_ipam(db: Session, actor: str = "system") -> dict:
    """Reconcile assets against managed/discovered IPAM addresses that carry a MAC."""
    created = updated = linked = 0
    rows = db.scalars(
        select(IPAddress).where((IPAddress.mac != "") | (IPAddress.hostname != ""))
    ).all()
    for row in rows:
        if not row.mac and not row.hostname:
            continue
        _, outcome = upsert_from_observation(
            db,
            name=row.hostname or row.ip,
            ip=row.ip,
            mac=row.mac,
            hostname=row.hostname,
            source="ipam",
        )
        created += outcome == "created"
        updated += outcome == "updated"
        linked += outcome == "linked"
    detail = f"IPAM reconciliation: {created} new, {linked} linked, {updated} refreshed"
    events.emit(db, "info", "asset", detail)
    return {"created": created, "updated": updated, "linked": linked, "detail": detail}
