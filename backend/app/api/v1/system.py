from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import Deployment, Event, Network, Record, User, Zone
from app.schemas.system import SettingsIn, SettingsOut
from app.services import app_settings, audit, certs, events
from app.version import __version__

router = APIRouter(prefix="/system", tags=["system"])


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
