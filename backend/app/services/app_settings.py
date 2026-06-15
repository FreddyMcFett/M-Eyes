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
    # System identity
    "system_hostname": "",          # FQDN clients use to reach M-Eyes (default CSR/cert CN)
    "organization_name": "M-Eyes",  # used as default O in generated CSRs
    # HTTPS / TLS (applied by the TLS-terminating proxy on save)
    "https_redirect": "true",       # 301 redirect plain HTTP to HTTPS
    "hsts_enabled": "false",        # emit Strict-Transport-Security header
    "hsts_max_age": "31536000",
    "tls_min_version": "TLSv1.2",   # TLSv1.2|TLSv1.3
    # DHCP service defaults — applied to every scope that does not override them.
    # Lease lifetimes are in seconds; empty timers are omitted (the engine then
    # derives sensible defaults from the valid lifetime).
    "dhcp_valid_lifetime": "4000",  # default lease time
    "dhcp_max_valid_lifetime": "",  # cap on client-requested lease times
    "dhcp_renew_timer": "",         # T1 — when clients start renewing
    "dhcp_rebind_timer": "",        # T2 — when clients start rebinding
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
