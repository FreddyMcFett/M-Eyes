import platform
import socket
import time
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, available_timezones

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.config import get_settings
from app.database import get_db
from app.models import Deployment, Event, Network, Record, User, Zone
from app.schemas.system import SettingsIn, SettingsOut, UpdateTrigger
from app.services import app_settings, audit, backup, certs, events, system_metrics, updater
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


def _valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
        return True
    except (KeyError, ValueError, OSError):
        return False


def _resolve_timezone(db: Session) -> tuple[str, ZoneInfo]:
    """The configured IANA zone, falling back to UTC if unset or invalid."""
    name = app_settings.get(db, "timezone") or "UTC"
    try:
        return name, ZoneInfo(name)
    except (KeyError, ValueError, OSError):
        return "UTC", ZoneInfo("UTC")


@router.get("/info")
def info(db: Session = Depends(get_db)):
    return {"name": "M-Eyes", "version": __version__, "config_version": audit.current_version(db)}


@router.get("/timezones")
def timezones(user: User = Depends(get_current_user)):
    """Sorted list of IANA time-zone names for the settings picker."""
    return {"timezones": sorted(available_timezones())}


@router.get("/status")
def system_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Live operational snapshot for the dashboards: version, time, host and
    resource usage. Deliberately does no network I/O so it can be polled often;
    the software-update check lives on its own (cached) endpoint."""
    tz_name, tz = _resolve_timezone(db)
    now = datetime.now(tz)

    def last_deploy(target: str):
        row = db.scalar(select(Deployment).where(Deployment.target == target)
                        .order_by(Deployment.id.desc()).limit(1))
        return {"status": row.status, "ts": row.ts.isoformat(), "message": row.message,
                "config_version": row.config_version} if row else None

    return {
        "name": "M-Eyes",
        "version": __version__,
        "config_version": audit.current_version(db),
        "timezone": tz_name,
        "server_time": now.isoformat(),
        "utc_offset": now.strftime("%z"),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "in_app_update": updater.is_supported(),
        "resources": system_metrics.snapshot(),
        "engines": {"bind": last_deploy("bind"), "kea": last_deploy("kea")},
    }


@router.get("/settings", response_model=SettingsOut)
def get_app_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return SettingsOut(values=app_settings.get_all(db))


@router.put("/settings", response_model=SettingsOut)
def update_app_settings(payload: SettingsIn, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    tz = payload.values.get("timezone")
    if tz and not _valid_timezone(tz):
        raise HTTPException(status_code=422, detail=f"Unknown time zone: {tz!r}")
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


def _compute_update_status(force: bool = False) -> dict:
    """Compare the running version against the latest published release (cached 1h).

    Never raises: any failure to reach the release server (offline / air-gapped
    appliance, DNS failure, timeout, rate-limit, malformed response) is captured
    in the ``error`` field so the endpoint always returns 200 with the installed
    version. A short, bounded timeout keeps the request snappy even when the
    upstream silently drops packets, so the UI never hangs on "checking…"."""
    now = time.monotonic()
    if force or _update_cache["result"] is None or now - _update_cache["ts"] > _UPDATE_CACHE_TTL:
        result = {"current_version": __version__, "latest_version": None,
                  "update_available": False, "release_url": RELEASES_URL, "error": None}
        try:
            # Explicit, tight timeouts (connect/read) so a blocked egress fails
            # fast instead of tying up the worker — the browser never waits long
            # enough to surface a "Failed to fetch".
            response = httpx.get(
                RELEASES_API,
                timeout=httpx.Timeout(connect=3.0, read=4.0, write=4.0, pool=4.0),
                headers={"Accept": "application/vnd.github+json"},
            )
            response.raise_for_status()
            release = response.json()
            latest = (release.get("tag_name") or "").lstrip("v")
            result["latest_version"] = latest or None
            result["release_url"] = release.get("html_url") or RELEASES_URL
            if latest:
                result["update_available"] = _version_tuple(latest) > _version_tuple(__version__)
        except httpx.HTTPError:
            result["error"] = ("Could not reach the update server — check this "
                               "system's outbound network access.")
        except Exception:  # noqa: BLE001 - update checks must never break the page
            result["error"] = "Could not determine the latest version."
        _update_cache.update(ts=now, result=result)
    return dict(_update_cache["result"])


@router.get("/update-check")
def update_check(force: bool = False, user: User = Depends(get_current_user)):
    """Compare the running version against the latest GitHub release (cached 1h).

    Pass ``force=true`` to bypass the cache (used by the "Check now" button).
    ``in_app_update`` reports whether this deployment can update itself from the
    UI (the privileged ``updater`` sidecar is wired up).
    """
    result = _compute_update_status(force=force)
    result["in_app_update"] = updater.is_supported()
    return result


@router.post("/update")
def trigger_update(payload: UpdateTrigger | None = Body(default=None),
                   db: Session = Depends(get_db),
                   user: User = Depends(require_role("admin"))):
    """Pull the latest images and restart the M-Eyes services in place. Admin only.

    Hands the work to the privileged ``updater`` sidecar; the API itself never
    touches Docker. Poll ``/update/status`` for progress (the API restarts as
    part of the update, so expect a brief window where it is unreachable)."""
    if not updater.is_supported():
        raise HTTPException(
            status_code=400,
            detail="In-app update is not available on this deployment. Upgrade on the host "
                   "with 'docker compose pull && docker compose up -d'.",
        )
    if updater.is_active():
        raise HTTPException(status_code=409, detail="An update is already in progress")

    target = payload.target_version if payload else None
    if not target:
        check = _compute_update_status()
        if not check.get("update_available"):
            raise HTTPException(status_code=400, detail="M-Eyes is already up to date")
        target = check.get("latest_version")
    if not updater.valid_version(target):
        raise HTTPException(status_code=422, detail=f"Invalid target version: {target!r}")

    try:
        status = updater.request_update(target, user.username)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    events.emit(db, "warning", "system",
                f"In-app update to v{target} started by {user.username}",
                {"target_version": target})
    db.commit()
    return status


@router.get("/update/status")
def update_status(user: User = Depends(get_current_user)):
    """Progress of an in-app update, written by the updater sidecar.

    ``current_version`` is the version of the API answering this request, so the
    UI knows the update finished once it equals the requested target."""
    status = updater.read_status()
    status["current_version"] = __version__
    status["in_app_update"] = updater.is_supported()
    status["log_tail"] = updater.read_log_tail()
    return status


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
