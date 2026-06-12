"""Render zones, validate with named-checkzone, atomically publish, reload via rndc.

The reload step degrades gracefully: when BIND (or the rndc binary) is unreachable
the files are still written and the deployment is recorded as 'unreachable' -
management-only mode works by construction.
"""

import shutil
import subprocess
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.generators.named_conf import render_rpz_options, render_zones_conf, rpz_active, zone_filename
from app.generators.rpz_zone import render_rpz_zone
from app.generators.zonefile import render_zone
from app.models import Deployment, Zone
from app.services import audit, events


def preview(db: Session) -> dict:
    zones = db.scalars(select(Zone).order_by(Zone.name)).all()
    result = {
        "zones_conf": render_zones_conf(db),
        "rpz_options": render_rpz_options(db),
        # keyed by file name: the same zone name may exist in several views
        "zone_files": {zone_filename(zone): render_zone(db, zone) for zone in zones},
    }
    if rpz_active(db):
        result["zone_files"][f"db.{get_settings().rpz_zone_name}"] = render_rpz_zone(db)
    return result


def _checkzone(zone_name: str, path: Path) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["named-checkzone", zone_name, str(path)],
            capture_output=True, text=True, timeout=10,
        )
        return proc.returncode == 0, proc.stdout + proc.stderr
    except FileNotFoundError:
        return True, "named-checkzone not installed; skipped validation"
    except subprocess.TimeoutExpired:
        return False, "named-checkzone timed out"


def _rndc(args: list[str]) -> tuple[bool, str]:
    settings = get_settings()
    cmd = ["rndc", "-s", settings.rndc_host, "-p", str(settings.rndc_port),
           "-k", settings.rndc_key_file, *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return proc.returncode == 0, proc.stdout + proc.stderr
    except FileNotFoundError:
        return False, "rndc binary not found"
    except subprocess.TimeoutExpired:
        return False, "rndc timed out"


def deploy(db: Session, actor: str, debug: bool = False) -> dict:
    settings = get_settings()
    output_dir = Path(settings.bind_output_dir)
    staging = output_dir / "staging"
    staging.mkdir(parents=True, exist_ok=True)

    zones = db.scalars(select(Zone).order_by(Zone.name)).all()
    rendered = preview(db)
    version = audit.current_version(db)

    # 1. render to staging
    (staging / "zones.conf").write_text(rendered["zones_conf"])
    (staging / "rpz-options.conf").write_text(rendered["rpz_options"])
    to_check = [(zone.name, zone_filename(zone)) for zone in zones]
    if rpz_active(db):
        to_check.append((settings.rpz_zone_name, f"db.{settings.rpz_zone_name}"))
    for _zone_name, filename in to_check:
        (staging / filename).write_text(rendered["zone_files"][filename])

    # 2. validate
    check_output = []
    for zone_name, filename in to_check:
        ok, output = _checkzone(zone_name, staging / filename)
        check_output.append(f"{zone_name}: {output.strip()}")
        if not ok:
            message = f"Zone validation failed for {zone_name}: {output.strip()}"
            db.add(Deployment(target="bind", status="failed", message=message, config_version=version))
            db.flush()
            events.emit(db, "error", "deploy", message)
            return {"status": "failed", "detail": message,
                    **({"debug": check_output} if debug else {})}

    # 3. atomic publish
    for staged in staging.iterdir():
        shutil.move(str(staged), str(output_dir / staged.name))

    # 4. reload
    ok_reconfig, out1 = _rndc(["reconfig"])
    ok_reload, out2 = _rndc(["reload"]) if ok_reconfig else (False, "")
    raw = f"reconfig: {out1.strip() or 'ok'} | reload: {out2.strip() or 'ok'}"

    if ok_reconfig and ok_reload:
        db.add(Deployment(target="bind", status="success",
                          message=f"{len(zones)} zone(s) deployed", config_version=version))
        db.flush()
        events.emit(db, "info", "deploy", f"BIND deployment succeeded ({len(zones)} zones, v{version})")
        return {"status": "success", "detail": f"{len(zones)} zone(s) deployed",
                "config_version": version, **({"debug": raw} if debug else {})}

    message = f"Config written; BIND not reachable ({(out1 + out2).strip()})"
    db.add(Deployment(target="bind", status="unreachable", message=message, config_version=version))
    db.flush()
    events.emit(db, "warning", "deploy", message)
    return {"status": "unreachable", "detail": message, "config_version": version,
            **({"debug": raw} if debug else {})}


def ping() -> dict:
    ok, output = _rndc(["status"])
    return {"reachable": ok, "detail": output.strip()[:500]}
