"""Configuration change log: every mutation records an immutable before/after entry.

`ChangeLog.id` is the global, monotonically increasing config version.
"""

from datetime import date, datetime

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChangeLog


def snapshot(obj) -> dict:
    """JSON-safe dict of an ORM object's column values."""
    result = {}
    for column in sa_inspect(obj).mapper.columns:
        value = getattr(obj, column.key)
        if isinstance(value, datetime | date):
            value = value.isoformat()
        result[column.key] = value
    return result


def record(
    db: Session,
    actor: str,
    action: str,
    object_type: str,
    object_id: int,
    before: dict | None,
    after: dict | None,
    summary: str = "",
) -> ChangeLog:
    entry = ChangeLog(
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=object_id,
        before=before,
        after=after,
        summary=summary,
    )
    db.add(entry)
    db.flush()
    return entry


def current_version(db: Session) -> int:
    latest = db.scalar(select(ChangeLog.id).order_by(ChangeLog.id.desc()).limit(1))
    return latest or 0
