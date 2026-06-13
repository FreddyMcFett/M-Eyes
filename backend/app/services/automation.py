"""Autonomy engine: a scheduler that runs AutomationRules on their cadence.

Each rule kind maps to a handler. The background loop (started in app.main) wakes
periodically, runs every due rule in its own transaction, records the outcome on
the rule and in the event log, and reschedules it. Handlers are defensive: a
failing rule is recorded as an error and never stops the loop or other rules.
"""

from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AutomationRule, Integration, Network
from app.models.base import utcnow
from app.services import assets, audit, events, integration_admin
from app.services.deploy import bind as bind_deploy
from app.services.deploy import kea as kea_deploy

SCHEDULER_TICK_SECONDS = 60  # how often the loop checks for due rules


# --------------------------------------------------------------------------- #
# Handlers — each returns a (status, message) tuple. status in {ok, error, skipped}
# --------------------------------------------------------------------------- #
def _handle_discovery_sweep(db: Session, rule: AutomationRule) -> tuple[str, str]:
    from app.services import discovery

    network_id = (rule.config or {}).get("network_id")
    network = db.get(Network, network_id) if network_id else None
    if network is None:
        return "skipped", "No target network configured"
    summary = discovery.discover(db, f"automation:{rule.name}", network)
    recon = assets.sync_from_ipam(db, f"automation:{rule.name}")
    return "ok", (f"Swept {summary['cidr']}: {summary['alive']} alive, {summary['created']} new IP(s); "
                  f"assets +{recon['created']}/~{recon['linked']}")


def _handle_asset_reconcile(db: Session, rule: AutomationRule) -> tuple[str, str]:
    recon = assets.sync_from_ipam(db, f"automation:{rule.name}")
    return "ok", recon["detail"]


def _handle_integration_sync(db: Session, rule: AutomationRule) -> tuple[str, str]:
    integration_id = (rule.config or {}).get("integration_id")
    integration = db.get(Integration, integration_id) if integration_id else None
    if integration is None:
        return "skipped", "No target integration configured"
    result = integration_admin.run_sync(db, integration)
    return ("ok" if result.get("ok") else "error",
            result.get("detail") or result.get("message", "sync finished"))


def _handle_auto_deploy(db: Session, rule: AutomationRule) -> tuple[str, str]:
    """Deploy pending BIND/Kea config only when the live deployment lags the config version."""
    from app.models import Deployment

    current = audit.current_version(db)
    targets = (rule.config or {}).get("targets", ["bind", "kea"])
    messages = []
    deployed_any = False
    for target in targets:
        last = db.scalar(
            select(Deployment).where(Deployment.target == target).order_by(Deployment.id.desc()).limit(1)
        )
        deployed_version = last.config_version if last else -1
        if deployed_version >= current:
            messages.append(f"{target}: up to date (v{deployed_version})")
            continue
        deployer = bind_deploy if target == "bind" else kea_deploy
        result = deployer.deploy(db, f"automation:{rule.name}")
        deployed_any = True
        messages.append(f"{target}: {result['status']}")
    status = "ok" if deployed_any or messages else "skipped"
    return status, "; ".join(messages)


def _handle_threat_feed_sync(db: Session, rule: AutomationRule) -> tuple[str, str]:
    from app.services import threat_feeds

    count = 0
    for feed in threat_feeds.feeds_due(db):
        threat_feeds.sync_feed(db, feed)
        count += 1
    return "ok", f"Synced {count} due threat feed(s)"


HANDLERS: dict[str, Callable[[Session, AutomationRule], tuple[str, str]]] = {
    "discovery_sweep": _handle_discovery_sweep,
    "asset_reconcile": _handle_asset_reconcile,
    "integration_sync": _handle_integration_sync,
    "auto_deploy": _handle_auto_deploy,
    "threat_feed_sync": _handle_threat_feed_sync,
}


# --------------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------------- #
def run_rule(db: Session, rule: AutomationRule) -> dict:
    """Execute a single rule, recording the outcome. Safe to call manually."""
    handler = HANDLERS.get(rule.kind)
    now = utcnow()
    if handler is None:
        status, message = "error", f"Unknown automation kind {rule.kind!r}"
    else:
        try:
            status, message = handler(db, rule)
        except Exception as exc:  # noqa: BLE001 - a rule must never crash the scheduler
            status, message = "error", f"{exc.__class__.__name__}: {exc}"
            events.emit(db, "error", "automation", f"Automation {rule.name!r} failed: {exc}")
    rule.last_run_at = now
    rule.last_status = status
    rule.last_message = message[:512]
    rule.run_count += 1
    rule.next_run_at = now + timedelta(seconds=max(rule.interval_seconds, 60))
    db.flush()
    severity = {"ok": "info", "skipped": "info", "error": "warning"}.get(status, "info")
    events.emit(db, severity, "automation", f"Automation {rule.name!r} {status}: {message}")
    return {"status": status, "message": message}


def due_rules(db: Session) -> list[AutomationRule]:
    now = utcnow()
    rules = db.scalars(select(AutomationRule).where(AutomationRule.enabled.is_(True))).all()
    return [r for r in rules if r.next_run_at is None or r.next_run_at <= now]


def run_due(db: Session) -> int:
    ran = 0
    for rule in due_rules(db):
        run_rule(db, rule)
        db.commit()
        ran += 1
    return ran
