"""Runtime key/value settings editable from the UI without restart."""

from sqlalchemy.orm import Session

from app.models import AppSetting

DEFAULTS: dict[str, str] = {
    "syslog_enabled": "false",
    "syslog_host": "",
    "syslog_port": "514",
    "syslog_protocol": "udp",  # udp|tcp
    "syslog_facility": "local0",
    "syslog_min_severity": "info",  # debug|info|warning|error
    "debug_mode": "false",
    "log_level": "info",
}


def get_all(db: Session) -> dict[str, str]:
    values = dict(DEFAULTS)
    for row in db.query(AppSetting).all():
        if row.key in values:
            values[row.key] = row.value
    return values


def get(db: Session, key: str) -> str:
    row = db.get(AppSetting, key)
    if row is not None:
        return row.value
    return DEFAULTS.get(key, "")


def get_bool(db: Session, key: str) -> bool:
    return get(db, key).lower() in ("true", "1", "yes")


def set_many(db: Session, values: dict[str, str]) -> dict[str, str]:
    for key, value in values.items():
        if key not in DEFAULTS:
            continue
        row = db.get(AppSetting, key)
        if row is None:
            db.add(AppSetting(key=key, value=str(value)))
        else:
            row.value = str(value)
    db.flush()
    return get_all(db)
