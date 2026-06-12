"""Live DHCP lease view, read from Kea via the Control Agent (lease4-get-all).

Same graceful contract as the deployers: an unreachable Control Agent yields
reachable=false and an empty list instead of an error.
"""

import json
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import DhcpSubnet

STATE_NAMES = {0: "active", 1: "declined", 2: "expired-reclaimed"}


def _cidr_by_kea_subnet_id(db: Session) -> dict[int, str]:
    """Kea subnet ids are assigned positionally by the config generator."""
    subnets = db.scalars(select(DhcpSubnet).where(DhcpSubnet.enabled)).all()
    return {index: subnet.network.cidr for index, subnet in enumerate(subnets, start=1)}


def list_leases(db: Session) -> dict:
    settings = get_settings()
    cidr_map = _cidr_by_kea_subnet_id(db)
    try:
        response = httpx.post(
            settings.kea_ca_url,
            json={"command": "lease4-get-all", "service": ["dhcp4"]},
            timeout=5,
        )
        body = response.json()
        result = body[0] if isinstance(body, list) and body else {}
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        return {"reachable": False, "detail": f"Kea Control Agent not reachable "
                                              f"({exc.__class__.__name__})", "leases": []}
    if result.get("result") not in (0, 3):  # 0 = ok, 3 = no leases
        return {"reachable": False,
                "detail": f"Kea rejected the command: {result.get('text', 'unknown error')}",
                "leases": []}

    leases = []
    for lease in result.get("arguments", {}).get("leases", []):
        cltt, valid_lft = lease.get("cltt"), lease.get("valid-lft")
        expires_at = None
        if cltt is not None and valid_lft is not None:
            expires_at = datetime.fromtimestamp(cltt + valid_lft, UTC).isoformat()
        leases.append({
            "ip": lease.get("ip-address", ""),
            "mac": lease.get("hw-address", ""),
            "hostname": lease.get("hostname", ""),
            "state": STATE_NAMES.get(lease.get("state", 0), f"state-{lease.get('state')}"),
            "expires_at": expires_at,
            "subnet": cidr_map.get(lease.get("subnet-id")),
        })
    leases.sort(key=lambda entry: entry["ip"])
    return {"reachable": True, "detail": f"{len(leases)} lease(s)", "leases": leases}
