import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DhcpOption, DhcpSubnet


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
        option_data = [{"name": o.name, "data": o.value} for o in subnet.options]
        if option_data:
            entry["option-data"] = option_data
        subnet4.append(entry)

    return {
        "Dhcp4": {
            "interfaces-config": {"interfaces": ["*"]},
            "control-socket": {"socket-type": "unix", "socket-name": "/run/kea/kea4-ctrl-socket"},
            "lease-database": {"type": "memfile", "lfc-interval": 3600},
            "valid-lifetime": 4000,
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
    }


def render_kea_conf(db: Session) -> str:
    # Pure JSON (no comment header) so strict parsers can validate it; the
    # config version is tracked in the deployments table instead.
    return json.dumps(build_kea_config(db), indent=2) + "\n"
