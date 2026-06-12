"""Render kea-dhcp4.conf, sanity-check, atomically publish, reload via Control Agent.

Same graceful contract as the BIND deployer: config is always written; an
unreachable Control Agent records an 'unreachable' deployment.
"""

import json
import time
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.generators.kea_conf import render_kea_conf
from app.models import Deployment
from app.services import audit, events


def preview(db: Session) -> dict:
    return {"kea_dhcp4_conf": render_kea_conf(db)}


def deploy(db: Session, actor: str, debug: bool = False) -> dict:
    settings = get_settings()
    output_dir = Path(settings.kea_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    version = audit.current_version(db)

    rendered = render_kea_conf(db)
    parsed = json.loads(rendered)  # structural sanity check
    subnet_count = len(parsed["Dhcp4"]["subnet4"])

    tmp = output_dir / "kea-dhcp4.conf.tmp"
    tmp.write_text(rendered)
    tmp.replace(output_dir / "kea-dhcp4.conf")

    try:
        response = httpx.post(
            settings.kea_ca_url,
            json={"command": "config-reload", "service": ["dhcp4"]},
            timeout=5,
        )
        body = response.json()
        result = body[0] if isinstance(body, list) and body else {}
        raw = json.dumps(result)[:1000]
        if result.get("result") == 0:
            db.add(Deployment(target="kea", status="success",
                              message=f"{subnet_count} subnet(s) deployed", config_version=version))
            db.flush()
            events.emit(db, "info", "deploy",
                        f"Kea deployment succeeded ({subnet_count} subnets, v{version})")
            return {"status": "success", "detail": f"{subnet_count} subnet(s) deployed",
                    "config_version": version, **({"debug": raw} if debug else {})}
        message = f"Kea rejected the config: {result.get('text', 'unknown error')}"
        db.add(Deployment(target="kea", status="failed", message=message, config_version=version))
        db.flush()
        events.emit(db, "error", "deploy", message)
        return {"status": "failed", "detail": message, **({"debug": raw} if debug else {})}
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError) as exc:
        message = f"Config written; Kea Control Agent not reachable ({exc.__class__.__name__})"
        db.add(Deployment(target="kea", status="unreachable", message=message, config_version=version))
        db.flush()
        events.emit(db, "warning", "deploy", message)
        return {"status": "unreachable", "detail": message, "config_version": version}


def ping() -> dict:
    settings = get_settings()
    start = time.monotonic()
    try:
        response = httpx.post(settings.kea_ca_url, json={"command": "status-get", "service": ["dhcp4"]},
                              timeout=3)
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        body = response.json()
        result = body[0] if isinstance(body, list) and body else {}
        return {"reachable": result.get("result") == 0, "latency_ms": latency_ms,
                "detail": json.dumps(result.get("arguments", {}))[:500]}
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        return {"reachable": False, "detail": exc.__class__.__name__}
