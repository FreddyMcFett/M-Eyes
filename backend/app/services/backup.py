"""Full configuration backup & restore.

The backup is a single JSON document containing every configuration table
(networks, zones, records, DHCP, hosts, firewall rules, feeds, settings and
the change log). Restoring replaces the current configuration wholesale -
primary keys are preserved so cross-references stay intact.

Users and TLS certificates are deliberately excluded: credentials and private
keys never leave the database through this channel.
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import Table, select
from sqlalchemy.orm import Session

from app.models import (
    AppSetting,
    Base,
    BlocklistEntry,
    ChangeLog,
    DhcpOption,
    DhcpRange,
    DhcpReservation,
    DhcpSubnet,
    ExtAttrDef,
    ExtAttrValue,
    Feed,
    Host,
    IPAddress,
    Network,
    Record,
    RpzRule,
    RpzThreatFeed,
    Tag,
    View,
    Zone,
)
from app.models.base import utcnow
from app.services import events
from app.version import __version__

BACKUP_FORMAT = "m-eyes-backup"
BACKUP_FORMAT_VERSION = 1

# Insert order respects foreign-key dependencies; deletes run in reverse.
_ORDERED_TABLES: list[Table] = [
    Tag.__table__,
    Network.__table__,
    IPAddress.__table__,
    Base.metadata.tables["network_tags"],
    Base.metadata.tables["ip_tags"],
    View.__table__,
    Zone.__table__,
    Record.__table__,
    DhcpSubnet.__table__,
    DhcpRange.__table__,
    DhcpReservation.__table__,
    DhcpOption.__table__,
    Host.__table__,
    ExtAttrDef.__table__,
    ExtAttrValue.__table__,
    RpzRule.__table__,
    RpzThreatFeed.__table__,
    Feed.__table__,
    BlocklistEntry.__table__,
    AppSetting.__table__,
    ChangeLog.__table__,
]


def export_config(db: Session) -> dict:
    tables: dict[str, list[dict]] = {}
    for table in _ORDERED_TABLES:
        rows = []
        for row in db.execute(select(table)).mappings():
            rows.append({
                key: value.isoformat() if isinstance(value, datetime) else value
                for key, value in row.items()
            })
        tables[table.name] = rows
    return {
        "format": BACKUP_FORMAT,
        "format_version": BACKUP_FORMAT_VERSION,
        "app_version": __version__,
        "created_at": utcnow().isoformat(),
        "tables": tables,
    }


def _coerce_row(table: Table, row: dict) -> dict:
    coerced = {}
    for column in table.columns:
        if column.name not in row:
            continue
        value = row[column.name]
        try:
            py_type = column.type.python_type
        except NotImplementedError:
            py_type = None
        if py_type is datetime and isinstance(value, str):
            value = datetime.fromisoformat(value)
        coerced[column.name] = value
    return coerced


def _reset_sequences(db: Session) -> None:
    """Postgres: realign the id sequences after inserting rows with explicit PKs."""
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    from sqlalchemy import text
    for table in _ORDERED_TABLES:
        pk_columns = list(table.primary_key.columns)
        if len(pk_columns) != 1 or not pk_columns[0].name == "id":
            continue
        db.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table.name}), 0) + 1, false)"
        ))


def restore_config(db: Session, actor: str, data: dict) -> dict:
    if data.get("format") != BACKUP_FORMAT:
        raise HTTPException(status_code=422, detail="Not an M-Eyes backup file")
    if data.get("format_version", 0) > BACKUP_FORMAT_VERSION:
        raise HTTPException(
            status_code=422,
            detail="Backup was created by a newer M-Eyes version; upgrade first, then restore",
        )
    tables = data.get("tables")
    if not isinstance(tables, dict):
        raise HTTPException(status_code=422, detail="Backup file is missing the tables section")

    counts: dict[str, int] = {}
    for table in reversed(_ORDERED_TABLES):
        db.execute(table.delete())
    for table in _ORDERED_TABLES:
        rows = tables.get(table.name, [])
        for row in rows:
            db.execute(table.insert().values(**_coerce_row(table, row)))
        counts[table.name] = len(rows)
    _reset_sequences(db)
    db.flush()
    events.emit(db, "info", "system",
                f"Configuration restored by {actor} from backup "
                f"(created {data.get('created_at', 'unknown')}, app {data.get('app_version', '?')})")
    return {
        "status": "restored",
        "created_at": data.get("created_at"),
        "app_version": data.get("app_version"),
        "tables": counts,
    }
