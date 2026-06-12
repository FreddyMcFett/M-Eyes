"""Operational event log with optional syslog forwarding and live SSE broadcast."""

import logging
import logging.handlers
import socket
import threading

from sqlalchemy.orm import Session

from app.models import Event
from app.services import app_settings
from app.services.broker import broker

SEVERITY_ORDER = {"debug": 0, "info": 1, "warning": 2, "error": 3}

_SYSLOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

_lock = threading.Lock()
_syslog_logger: logging.Logger | None = None
_syslog_config: tuple | None = None


def _build_syslog_logger(host: str, port: int, protocol: str, facility: str) -> logging.Logger:
    logger = logging.getLogger("meyes.syslog")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    socktype = socket.SOCK_STREAM if protocol == "tcp" else socket.SOCK_DGRAM
    facility_code = logging.handlers.SysLogHandler.facility_names.get(facility, 16)
    handler = logging.handlers.SysLogHandler(address=(host, port), facility=facility_code, socktype=socktype)
    handler.setFormatter(logging.Formatter("m-eyes[%(name)s]: %(message)s"))
    logger.addHandler(handler)
    return logger


def reset_syslog() -> None:
    """Force the forwarder to be rebuilt on next emit (called after settings change)."""
    global _syslog_logger, _syslog_config
    with _lock:
        _syslog_logger = None
        _syslog_config = None


def _forward_to_syslog(db: Session, severity: str, category: str, message: str) -> None:
    global _syslog_logger, _syslog_config
    settings = app_settings.get_all(db)
    if settings["syslog_enabled"].lower() not in ("true", "1", "yes"):
        return
    if SEVERITY_ORDER.get(severity, 1) < SEVERITY_ORDER.get(settings["syslog_min_severity"], 1):
        return
    host = settings["syslog_host"]
    if not host:
        return
    config = (host, int(settings["syslog_port"] or 514), settings["syslog_protocol"],
              settings["syslog_facility"])
    try:
        with _lock:
            if _syslog_logger is None or _syslog_config != config:
                _syslog_logger = _build_syslog_logger(*config)
                _syslog_config = config
            _syslog_logger.log(_SYSLOG_LEVELS.get(severity, logging.INFO), "[%s] %s", category, message)
    except OSError:
        logging.getLogger("meyes").warning("syslog forwarding failed (host=%s)", host)


def emit(
    db: Session,
    severity: str,
    category: str,
    message: str,
    data: dict | None = None,
) -> Event:
    event = Event(severity=severity, category=category, message=message, data=data)
    db.add(event)
    db.flush()
    _forward_to_syslog(db, severity, category, message)
    broker.publish(
        "event",
        {
            "id": event.id,
            "ts": event.ts,
            "severity": severity,
            "category": category,
            "message": message,
        },
    )
    return event
