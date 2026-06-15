import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DhcpOption, DhcpSubnet
from app.services import app_settings


def _int_setting(db: Session, key: str) -> int | None:
    """Parse a runtime integer setting; blank/invalid values mean 'unset'."""
    raw = (app_settings.get(db, key) or "").strip()
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


def _lease_timing(subnet: DhcpSubnet) -> dict:
    """Per-scope lease timers — only emitted when explicitly overridden so the
    server-level defaults apply otherwise."""
    timing: dict = {}
    if subnet.valid_lifetime is not None:
        timing["valid-lifetime"] = subnet.valid_lifetime
    if subnet.max_valid_lifetime is not None:
        timing["max-valid-lifetime"] = subnet.max_valid_lifetime
    if subnet.renew_timer is not None:
        timing["renew-timer"] = subnet.renew_timer
    if subnet.rebind_timer is not None:
        timing["rebind-timer"] = subnet.rebind_timer
    return timing


def build_kea_config(db: Session) -> dict:
    subnets = db.scalars(select(DhcpSubnet).where(DhcpSubnet.enabled)).all()
    global_options = db.scalars(select(DhcpOption).where(DhcpOption.subnet_id.is_(None))).all()

    subnet4 = []
    for index, subnet in enumerate(subnets, start=1):
        entry: dict = {
            "id": index,
            "subnet": subnet.network.cidr,
            "pools": [{"pool": f"{r.start_ip} - {r.end_ip}"} for r in subnet.ranges],
            "reservations": [
                {
                    "hw-address": res.mac,
                    "ip-address": res.ip,
                    **({"hostname": res.hostname} if res.hostname else {}),
                }
                for res in subnet.reservations
            ],
        }
        entry.update(_lease_timing(subnet))
        if subnet.next_server:
            entry["next-server"] = subnet.next_server
        if subnet.boot_file_name:
            entry["boot-file-name"] = subnet.boot_file_name
        if subnet.client_class:
            entry["client-class"] = subnet.client_class
        option_data = [{"name": o.name, "data": o.value} for o in subnet.options]
        if option_data:
            entry["option-data"] = option_data
        subnet4.append(entry)

    # Server-level lease defaults (configurable in System → Settings → Services).
    dhcp4: dict = {
        "interfaces-config": {"interfaces": ["*"]},
        "control-socket": {"socket-type": "unix", "socket-name": "/run/kea/kea4-ctrl-socket"},
        "lease-database": {"type": "memfile", "lfc-interval": 3600},
        "valid-lifetime": _int_setting(db, "dhcp_valid_lifetime") or 4000,
        "option-data": [{"name": o.name, "data": o.value} for o in global_options],
        "subnet4": subnet4,
        "loggers": [
            {
                "name": "kea-dhcp4",
                "output_options": [{"output": "stdout"}],
                "severity": "INFO",
            }
        ],
    }
    for key, kea_key in (
        ("dhcp_max_valid_lifetime", "max-valid-lifetime"),
        ("dhcp_renew_timer", "renew-timer"),
        ("dhcp_rebind_timer", "rebind-timer"),
    ):
        value = _int_setting(db, key)
        if value is not None:
            dhcp4[kea_key] = value

    return {"Dhcp4": dhcp4}


def render_kea_conf(db: Session) -> str:
    # Pure JSON (no comment header) so strict parsers can validate it; the
    # config version is tracked in the deployments table instead.
    return json.dumps(build_kea_config(db), indent=2) + "\n"
