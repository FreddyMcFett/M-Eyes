# Architecture

```
                  ┌────────────────────────────────────────────┐
                  │                 Browser (SPA)              │
                  │   React 18 + TS, FortiOS-style UI          │
                  └───────────────┬────────────────────────────┘
                                  │ /api /feeds  (nginx in compose, vite proxy in dev)
                  ┌───────────────▼────────────────────────────┐
                  │             M-Eyes API (FastAPI)           │
                  │  routers → services → models (SQLAlchemy)  │
                  │  audit/changelog · events/syslog · SSE     │
                  └──────┬──────────────┬──────────────┬───────┘
                         │              │              │
                  PostgreSQL     zone files +     kea-dhcp4.conf
                  (SQLite dev)   zones.conf            │
                         │              │              │
                         │       ┌──────▼─────┐  ┌─────▼─────────────┐
                         │       │   BIND9    │  │ Kea DHCP4 + CtrlA │
                         │       │ rndc reload│  │ config-reload API │
                         │       └────────────┘  └───────────────────┘
                         │
                  FortiGate(s) pull /feeds/*.txt as External Resources
```

## Control plane / engine split

M-Eyes never speaks DNS or DHCP itself. It renders **engine-native configuration** and
triggers reloads over native control channels:

### BIND9 deployment

1. Render every zone (Jinja2 → standard zone file) plus `zones.conf` into a staging dir.
2. Validate each zone with `named-checkzone`. A validation failure aborts the deploy —
   nothing is published.
3. Atomically move the staged files into the shared volume.
4. `rndc reconfig` + `rndc reload` against the BIND container.

### Kea deployment

1. Render the complete `kea-dhcp4.conf` (subnets, pools, reservations, options).
2. Parse the result as JSON as a structural sanity check.
3. Atomic write into the shared volume.
4. `config-reload` command via the Kea Control Agent REST API.

### Management-only mode

Both deployers treat an unreachable engine as a **degraded success**: the configuration is
written, the deployment is recorded with status `unreachable`, and the UI shows the drift
between deployed and current config version. You can run M-Eyes entirely without engines
and use it as a pure IPAM/modeling tool.

## Data model highlights

- `changelog.id` **is** the global config version — a single monotonically increasing
  sequence with no separate counter to race on.
- Free IPs are computed, never materialized — only allocated/reserved IPs have rows.
- DHCP reservations upsert a linked `reserved` IPAM entry, so the IP grid always tells
  the truth.
- `hosts` is a composite object holding foreign keys to the IP, A record, PTR record and
  reservation it created; deleting the host reverses all of them.

## Live updates

State-changing operations publish to an in-process async broker; `GET
/api/v1/events/stream` exposes it as **Server-Sent Events**. The dashboard combines the
stream (event ticker) with 5-second polling (counters, engine status).
