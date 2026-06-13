"""CRUD and orchestration for enterprise integrations (test / sync)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Integration
from app.models.base import utcnow
from app.services import audit, events
from app.services.integrations import get_connector
from app.services.integrations.base import ConnectorError

_SECRET_KEYS = {"secret"}


def list_integrations(db: Session) -> list[Integration]:
    return list(db.scalars(select(Integration).order_by(Integration.kind, Integration.name)).all())


def get(db: Session, integration_id: int) -> Integration | None:
    return db.get(Integration, integration_id)


def create(db: Session, actor: str, data: dict) -> Integration:
    get_connector(data["kind"])  # validates the kind
    integration = Integration(**data)
    db.add(integration)
    db.flush()
    audit.record(db, actor, "create", "integration", integration.id, None,
                 _redact(audit.snapshot(integration)), summary=f"Created integration {integration.name}")
    events.emit(db, "info", "integration",
                f"Integration {integration.name!r} ({integration.kind}) created by {actor}")
    return integration


def update(db: Session, actor: str, integration: Integration, changes: dict) -> Integration:
    before = _redact(audit.snapshot(integration))
    for field, value in changes.items():
        if field in _SECRET_KEYS and not value:
            continue  # blank secret keeps the stored value
        setattr(integration, field, value)
    db.flush()
    audit.record(db, actor, "update", "integration", integration.id, before,
                 _redact(audit.snapshot(integration)), summary=f"Updated integration {integration.name}")
    return integration


def delete(db: Session, actor: str, integration: Integration) -> None:
    name = integration.name
    iid = integration.id
    db.delete(integration)
    db.flush()
    audit.record(db, actor, "delete", "integration", iid, {"name": name}, None,
                 summary=f"Deleted integration {name}")
    events.emit(db, "info", "integration", f"Integration {name!r} deleted by {actor}")


def test(db: Session, integration: Integration) -> dict:
    connector = get_connector(integration.kind)
    try:
        ok, message = connector.test_connection(integration)
    except ConnectorError as exc:
        ok, message = False, str(exc)
    integration.last_status = "ok" if ok else "error"
    integration.last_message = message[:512]
    db.flush()
    events.emit(db, "info" if ok else "warning", "integration",
                f"Integration {integration.name!r} test: {message}")
    return {"ok": ok, "message": message}


def run_sync(db: Session, integration: Integration) -> dict:
    if not integration.enabled:
        return {"ok": False, "message": "Integration is disabled", "detail": ""}
    connector = get_connector(integration.kind)
    try:
        result = connector.sync(db, integration)
        integration.last_status = "ok"
        integration.last_message = result.get("detail", "Sync completed")[:512]
        integration.last_sync_at = utcnow()
        db.flush()
        return {"ok": True, **result}
    except Exception as exc:  # noqa: BLE001 - a connector must never crash the loop
        integration.last_status = "error"
        integration.last_message = f"{exc.__class__.__name__}: {exc}"[:512]
        integration.last_sync_at = utcnow()
        db.flush()
        events.emit(db, "error", "integration",
                    f"Integration {integration.name!r} sync failed: {exc}")
        return {"ok": False, "message": str(exc)}


def _redact(snapshot: dict) -> dict:
    return {k: ("***" if k in _SECRET_KEYS and v else v) for k, v in snapshot.items()}
