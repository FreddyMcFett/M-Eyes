from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.generators import jinja_env
from app.models import RpzRule, RpzThreatFeed, View, Zone
from app.services import audit


def zone_filename(zone: Zone) -> str:
    """Zone file name; prefixed with the view so the same zone name can exist per view."""
    prefix = f"{zone.view.name}." if zone.view is not None else ""
    return f"db.{prefix}{zone.name}"


def rpz_active(db: Session) -> bool:
    if db.scalar(select(RpzRule.id).where(RpzRule.enabled).limit(1)) is not None:
        return True
    return db.scalar(
        select(RpzThreatFeed.id)
        .where(RpzThreatFeed.enabled, RpzThreatFeed.entry_count > 0)
        .limit(1)
    ) is not None


def _acl_clause(value: str | None) -> str | None:
    """Render a comma/semicolon-separated ACL into a BIND address-match list
    (``{ a; b; }``). Returns ``None`` when nothing is configured so the engine
    default applies and no empty clause is emitted."""
    tokens = [t.strip() for t in (value or "").replace(";", ",").split(",") if t.strip()]
    return "{ " + " ".join(f"{token};" for token in tokens) + " }" if tokens else None


def _zone_entry(zone: Zone) -> dict:
    return {
        "name": zone.name,
        "filename": zone_filename(zone),
        "dnssec": zone.dnssec_enabled,
        "role": zone.role,
        "primaries": [ip for ip in zone.primaries.split(",") if ip],
        "allow_query": _acl_clause(getattr(zone, "allow_query", "")),
        "allow_transfer": _acl_clause(getattr(zone, "allow_transfer", "")),
        "allow_update": _acl_clause(getattr(zone, "allow_update", "")),
        "also_notify": _acl_clause(getattr(zone, "also_notify", "")),
        "forward_first": getattr(zone, "forward_first", False),
    }


def _match_clients_clause(match_clients: str) -> str:
    tokens = [t.strip() for t in match_clients.replace(";", ",").split(",") if t.strip()]
    return " ".join(f"{token};" for token in tokens) or "any;"


def render_zones_conf(db: Session) -> str:
    settings = get_settings()
    zones = db.scalars(select(Zone).order_by(Zone.name)).all()
    views = db.scalars(select(View).order_by(View.position, View.id)).all()

    default_zones = [_zone_entry(z) for z in zones if z.view_id is None]
    view_blocks = [
        {
            "name": view.name,
            "match_clients": _match_clients_clause(view.match_clients),
            "zones": [_zone_entry(z) for z in zones if z.view_id == view.id],
        }
        for view in views
    ]
    if views:
        # BIND requires every zone to live in a view once views are used: unassigned
        # zones form the catch-all default view, evaluated last.
        view_blocks.append({"name": "default", "match_clients": "any;", "zones": default_zones})

    rpz = None
    if rpz_active(db):
        rpz = {"name": settings.rpz_zone_name, "filename": f"db.{settings.rpz_zone_name}",
               "dnssec": False, "role": "primary", "primaries": [],
               "allow_query": None, "allow_transfer": None, "allow_update": None,
               "also_notify": None, "forward_first": False}

    template = jinja_env.get_template("zones.conf.j2")
    return template.render(
        use_views=bool(views),
        views=view_blocks,
        default_zones=default_zones,
        rpz=rpz,
        zone_dir=settings.bind_zone_dir,
        config_version=audit.current_version(db),
    )


def render_rpz_options(db: Session) -> str:
    """Generated include for the BIND options block: enables the response policy
    only while at least one rule is enabled (the option is global; with views the
    policy is instead emitted per view inside zones.conf)."""
    settings = get_settings()
    has_views = db.scalar(select(View.id).limit(1)) is not None
    if not rpz_active(db) or has_views:
        return "// M-Eyes DNS firewall: no global response policy active\n"
    return (
        "// M-Eyes generated DNS firewall configuration - do not edit by hand\n"
        f'response-policy {{ zone "{settings.rpz_zone_name}"; }} '
        "qname-wait-recurse no break-dnssec yes;\n"
    )
