"""In-app software update orchestration.

The API never controls Docker itself. Instead it drops an update *request*
into a shared volume; a tiny privileged sidecar (the ``updater`` service — the
only container with access to the Docker socket) watches that volume, runs
``docker compose pull`` + ``docker compose up -d`` for the M-Eyes app services
and reports progress back into the same volume.

This mirrors the existing TLS hot-reload pattern (a marker file the frontend
sidecar watches) and deliberately keeps Docker/host privileges out of the
internet-facing API container: the API can only ever request an update for a
validated version string, never run arbitrary commands.

On-disk contract inside :func:`_dir` (all JSON):

``request.json``  written by the API   ``{id, target_version, requested_by, requested_at}``
``status.json``   written by both       ``{phase, message, target_version, processed_id, ...}``
``update.log``    written by the sidecar  raw ``docker compose`` output (tailed by the API)
"""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from datetime import UTC, datetime

from app.config import get_settings

REQUEST_FILE = "request.json"
STATUS_FILE = "status.json"
LOG_FILE = "update.log"

# Phases that mean "an update is mid-flight" — used to reject a second request.
ACTIVE_PHASES = {"requested", "pulling", "recreating"}
# An "active" status older than this is treated as stale (e.g. the sidecar
# crashed mid-update) so a stuck status can never permanently block updates.
ACTIVE_STALE_SECONDS = 900

# Tags published by the release pipeline look like ``1.5.0`` (optionally with a
# pre-release suffix). Validating here means the sidecar only ever interpolates
# a known-safe string into the image tag / shell command.
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-.][0-9A-Za-z.]+)?$")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _dir() -> str:
    return get_settings().update_dir


def valid_version(version: str | None) -> bool:
    return bool(version and _VERSION_RE.match(version))


def is_supported() -> bool:
    """True when in-app update is wired up (the shared volume is writable).

    In the Docker compose stack the ``updater`` sidecar mounts the same volume;
    in a bare dev checkout the directory is still creatable, so the capability
    is reported honestly only when the directory can actually be written to.
    """
    directory = _dir()
    try:
        os.makedirs(directory, exist_ok=True)
        return os.access(directory, os.W_OK)
    except OSError:
        return False


def _atomic_write(path: str, content: str) -> None:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _idle_status() -> dict:
    return {
        "phase": "idle",
        "message": "",
        "target_version": None,
        "processed_id": None,
        "started_at": None,
        "updated_at": None,
    }


def read_status() -> dict:
    path = os.path.join(_dir(), STATUS_FILE)
    try:
        with open(path) as fh:
            data = json.load(fh)
        if isinstance(data, dict) and data.get("phase"):
            return data
    except (OSError, ValueError):
        pass
    return _idle_status()


def read_log_tail(max_chars: int = 6000) -> str:
    path = os.path.join(_dir(), LOG_FILE)
    try:
        with open(path) as fh:
            return fh.read()[-max_chars:]
    except OSError:
        return ""


def is_active(status: dict | None = None) -> bool:
    status = status if status is not None else read_status()
    if status.get("phase") not in ACTIVE_PHASES:
        return False
    # A mid-flight status that has not been touched for a long time means the
    # sidecar died; don't let it lock out future updates forever.
    try:
        updated = datetime.fromisoformat(status["updated_at"])
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=UTC)
        return (datetime.now(UTC) - updated).total_seconds() < ACTIVE_STALE_SECONDS
    except (KeyError, TypeError, ValueError):
        return False


def request_update(target_version: str, requested_by: str) -> dict:
    """Drop an update request for the sidecar and seed an initial status.

    Raises ``RuntimeError`` if in-app update is unavailable and ``ValueError``
    for an invalid version string.
    """
    if not is_supported():
        raise RuntimeError("In-app update is not available on this deployment")
    if not valid_version(target_version):
        raise ValueError(f"Invalid target version: {target_version!r}")

    request_id = secrets.token_hex(8)
    request = {
        "id": request_id,
        "target_version": target_version,
        "requested_by": requested_by,
        "requested_at": _now(),
    }
    status = {
        "phase": "requested",
        "message": f"Update to v{target_version} queued; waiting for the updater service.",
        "target_version": target_version,
        "processed_id": None,
        "request_id": request_id,
        "returncode": None,
        "started_at": _now(),
        "updated_at": _now(),
    }
    directory = _dir()
    # Seed status first so a reader never sees the request without a status.
    _atomic_write(os.path.join(directory, STATUS_FILE), json.dumps(status, separators=(",", ":")))
    _atomic_write(os.path.join(directory, REQUEST_FILE), json.dumps(request, separators=(",", ":")))
    return status
