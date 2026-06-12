import time
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import Deployment, Event, Network, Record, User, Zone
from app.schemas.system import SettingsIn, SettingsOut
from app.services import app_settings, audit, backup, certs, events
from app.version import __version__

router = APIRouter(prefix="/system", tags=["system"])

RELEASES_API = "https://api.github.com/repos/FreddyMcFett/M-Eyes/releases/latest"
RELEASES_URL = "https://github.com/FreddyMcFett/M-Eyes/releases"
_UPDATE_CACHE_TTL = 3600.0
_update_cache: dict = {"ts": 0.0, "result": None}


def _version_tuple(version: str) -> tuple[int, ...]:
    parts = version.lstrip("v").split("-")[0].split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return (0,)


@router.get("/info")
def info(db: Session = Depends(get_db)):
    return {"name": "M-Eyes", "version": __version__, "config_version": audit.current_version(db)}


@router.get("/settings", response_model=SettingsOut)
def get_app_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return SettingsOut(values=app_settings.get_all(db))


@router.put("/settings", response_model=SettingsOut)
def update_app_settings(payload: SettingsIn, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    values = app_settings.set_many(db, payload.values)
    events.reset_syslog()
    # Republish TLS/proxy snippets when an HTTPS-affecting setting changed.
    if any(k in payload.values for k in
           ("https_redirect", "hsts_enabled", "hsts_max_age", "tls_min_version")):
        certs.materialize(db)
    events.emit(db, "info", "system", f"Settings updated by {user.username}",
                {"keys": sorted(payload.values.keys())})
    db.commit()
    return SettingsOut(values=values)


@router.post("/syslog-test")
def syslog_test(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = events.emit(db, "info", "system",
                        f"M-Eyes syslog test message (triggered by {user.username})")
    db.commit()
    enabled = app_settings.get_bool(db, "syslog_enabled")
    return {
        "status": "sent" if enabled else "logged-only",
        "detail": "Test event emitted"
                  + ("" if enabled else "; syslog forwarding is disabled in settings"),
        "event_id": event.id,
    }


@router.get("/update-check")
def update_check(user: User = Depends(get_current_user)):
    """Compare the running version against the latest GitHub release (cached 1h)."""
    now = time.monotonic()
    if _update_cache["result"] is None or now - _update_cache["ts"] > _UPDATE_CACHE_TTL:
        result = {"current_version": __version__, "latest_version": None,
                  "update_available": False, "release_url": RELEASES_URL, "error": None}
        try:
            response = httpx.get(RELEASES_API, timeout=5.0,
                                 headers={"Accept": "application/vnd.github+json"})
            response.raise_for_status()
            release = response.json()
            latest = (release.get("tag_name") or "").lstrip("v")
            result["latest_version"] = latest or None
            result["release_url"] = release.get("html_url") or RELEASES_URL
            if latest:
                result["update_available"] = _version_tuple(latest) > _version_tuple(__version__)
        except (httpx.HTTPError, ValueError) as exc:
            result["error"] = f"Update check failed: {exc}"[:255]
        _update_cache.update(ts=now, result=result)
    return _update_cache["result"]


@router.get("/backup")
def download_backup(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Full configuration export (excludes user accounts and TLS private keys)."""
    return backup.export_config(db)


@router.post("/restore")
def restore_backup(data: dict = Body(...), db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Replace the entire configuration with the uploaded backup. Admin only."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can restore a backup")
    result = backup.restore_config(db, user.username, data)
    db.commit()
    return result


@router.get("/diagnostics")
def diagnostics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    settings = get_settings()
    recent_errors = db.scalars(
        select(Event).where(Event.severity == "error").order_by(Event.id.desc()).limit(20)
    ).all()
    last_deployments = db.scalars(select(Deployment).order_by(Deployment.id.desc()).limit(10)).all()
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "version": __version__,
        "config_version": audit.current_version(db),
        "settings": {
            "database": settings.database_url.split("://")[0],
            "bind_output_dir": settings.bind_output_dir,
            "kea_output_dir": settings.kea_output_dir,
            "rndc_host": settings.rndc_host,
            "kea_ca_url": settings.kea_ca_url,
        },
        "runtime_settings": app_settings.get_all(db),
        "db_stats": {
            "networks": db.scalar(select(func.count(Network.id))) or 0,
            "zones": db.scalar(select(func.count(Zone.id))) or 0,
            "records": db.scalar(select(func.count(Record.id))) or 0,
            "events": db.scalar(select(func.count(Event.id))) or 0,
        },
        "last_deployments": [
            {"target": d.target, "status": d.status, "ts": d.ts.isoformat(),
             "config_version": d.config_version}
            for d in last_deployments
        ],
        "recent_errors": [
            {"ts": e.ts.isoformat(), "category": e.category, "message": e.message}
            for e in recent_errors
        ],
    }
