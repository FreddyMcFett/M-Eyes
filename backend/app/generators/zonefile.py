from sqlalchemy.orm import Session

from app.generators import jinja_env
from app.models import Record, Zone
from app.services import audit


def _rendered_value(record: Record) -> str:
    """Values that are domain names must be absolute (or made relative-safe)."""
    if record.type in ("CNAME", "NS", "PTR", "MX", "SRV"):
        value = record.value
        if not value.endswith("."):
            value += "."
        return value
    if record.type == "TXT":
        value = record.value
        if not (value.startswith('"') and value.endswith('"')):
            value = '"' + value.replace('"', '\\"') + '"'
        return value
    return record.value


def render_zone(db: Session, zone: Zone) -> str:
    records = sorted(zone.records, key=lambda r: (r.name != "@", r.name, r.type))
    rows = []
    for record in records:
        rows.append(
            {
                "name": record.name,
                "ttl": record.ttl,
                "type": record.type,
                "priority": record.priority,
                "rendered_value": _rendered_value(record),
            }
        )
    template = jinja_env.get_template("zone.db.j2")
    return template.render(zone=zone, records=rows, config_version=audit.current_version(db))
