"""Host resource metrics (CPU, memory, disk, load) without third-party deps.

Reads Linux ``/proc`` and ``os.statvfs`` directly so the appliance needs no
``psutil``. Every probe degrades gracefully to ``None`` on non-Linux hosts or
when ``/proc`` is unavailable, so callers can always render *something*.
"""

import os
import time
from threading import Lock

_PROC_STAT = "/proc/stat"
_PROC_MEMINFO = "/proc/meminfo"
_PROC_UPTIME = "/proc/uptime"

# When the module is imported the API process has effectively just started, so
# this doubles as a process-uptime baseline that survives across requests.
_PROCESS_START = time.time()

_cpu_lock = Lock()
_cpu_prev: tuple[int, int] | None = None  # (idle_jiffies, total_jiffies)


def _read_cpu_sample() -> tuple[int, int] | None:
    """Aggregate (idle, total) jiffies from the first ``cpu`` line of /proc/stat."""
    try:
        with open(_PROC_STAT) as fh:
            for line in fh:
                if line.startswith("cpu "):
                    parts = [int(value) for value in line.split()[1:]]
                    if len(parts) < 4:
                        return None
                    idle = parts[3] + (parts[4] if len(parts) > 4 else 0)  # idle + iowait
                    return idle, sum(parts)
    except (OSError, ValueError):
        return None
    return None


def cpu_percent() -> float | None:
    """System-wide CPU utilisation as a 0–100 percentage.

    Computed from the delta between successive /proc/stat reads, so repeated
    polling is cheap and accurate. The first call (no stored baseline) takes a
    short inline sample so it still returns a real number instead of ``None``.
    """
    global _cpu_prev
    sample = _read_cpu_sample()
    if sample is None:
        return None

    with _cpu_lock:
        prev, _cpu_prev = _cpu_prev, sample

    if prev is None or sample[1] <= prev[1]:
        # No usable baseline (first call, or counters were reset) — measure a
        # fresh short window inline.
        time.sleep(0.1)
        nxt = _read_cpu_sample()
        if nxt is None:
            return None
        with _cpu_lock:
            _cpu_prev = nxt
        prev, sample = sample, nxt

    idle_delta = sample[0] - prev[0]
    total_delta = sample[1] - prev[1]
    if total_delta <= 0:
        return None
    usage = (1.0 - idle_delta / total_delta) * 100.0
    return round(max(0.0, min(100.0, usage)), 1)


def memory() -> dict | None:
    """Physical memory usage in bytes from /proc/meminfo."""
    info: dict[str, int] = {}
    try:
        with open(_PROC_MEMINFO) as fh:
            for line in fh:
                key, _, rest = line.partition(":")
                fields = rest.split()
                if fields:
                    info[key.strip()] = int(fields[0]) * 1024  # kB -> bytes
    except (OSError, ValueError):
        return None

    total = info.get("MemTotal")
    if not total:
        return None
    available = info.get("MemAvailable")
    if available is None:
        available = info.get("MemFree", 0) + info.get("Cached", 0) + info.get("Buffers", 0)
    available = min(available, total)
    used = total - available
    return {
        "total": total,
        "used": used,
        "available": available,
        "percent": round(used / total * 100, 1),
    }


def disk(path: str = "/") -> dict | None:
    """Filesystem usage in bytes for the volume backing ``path``."""
    try:
        st = os.statvfs(path)
    except (OSError, AttributeError):
        return None
    total = st.f_blocks * st.f_frsize
    if total <= 0:
        return None
    free = st.f_bavail * st.f_frsize
    used = total - st.f_bfree * st.f_frsize
    return {
        "total": total,
        "used": used,
        "free": free,
        "percent": round(used / total * 100, 1),
    }


def load_average() -> list[float] | None:
    """1/5/15-minute load averages, or ``None`` where unsupported."""
    try:
        return [round(value, 2) for value in os.getloadavg()]
    except (OSError, AttributeError):
        return None


def host_uptime_seconds() -> float | None:
    try:
        with open(_PROC_UPTIME) as fh:
            return round(float(fh.read().split()[0]), 0)
    except (OSError, ValueError, IndexError):
        return None


def cpu_count() -> int:
    return os.cpu_count() or 1


def snapshot() -> dict:
    """A single bundle of every metric, with ``None`` for anything unavailable."""
    return {
        "cpu_percent": cpu_percent(),
        "cpu_count": cpu_count(),
        "load_average": load_average(),
        "memory": memory(),
        "disk": disk(),
        "host_uptime_seconds": host_uptime_seconds(),
        "process_uptime_seconds": round(time.time() - _PROCESS_START, 0),
    }
