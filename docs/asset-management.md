# Asset Management

M-Eyes includes a lightweight **CMDB** that is cross-referenced to your DDI data.
Where classic IPAM tells you *which IP is used*, the asset inventory tells you
*what device owns it*, who's responsible, where it lives and its lifecycle state —
and links the two together automatically.

## The model

```
Asset ─┬─ name, type, status, criticality
       ├─ owner, location, department
       ├─ vendor, model, serial, OS
       ├─ tags, source, last_seen
       └─ interfaces ──► (MAC, IP, hostname) ──► IPAM IPAddress
```

Each **interface** is the join between the CMDB and the network fabric. An
interface carries a MAC, an IP and a hostname; when its IP matches a managed IPAM
address, M-Eyes links them (`ip_id`) and shows a link icon in the Addresses
column. From there you can pivot between the address and its owning asset.

| Field | Values |
|---|---|
| **Type** | server, workstation, laptop, mobile, network, firewall, iot, printer, virtual, container, other |
| **Status** | in_service, in_stock, maintenance, retired, decommissioned |
| **Criticality** | low, medium, high, critical |

## Connecting assets to DDI

There are four ways assets get populated and linked:

1. **Manually** — create an asset on the **Network → Assets** page and add its
   interfaces.
2. **Reconcile from DDI** — the *Reconcile from DDI* button (and the
   `asset_reconcile` automation rule) walks managed IPAM addresses that carry a
   MAC or hostname and creates/links assets. Matching is **MAC first, then IP**,
   so re-running is idempotent.
3. **Network discovery** — a `discovery_sweep` automation rule ping-sweeps a
   network, records responders in IPAM, then reconciles them into assets.
4. **Integrations** — FortiGate DHCP leases, Microsoft DNS records and Microsoft
   Entra/Intune devices all upsert assets tagged with their source. See
   [Integrations](integrations.md).

Because matching is keyed on MAC/IP, the same physical device discovered by
several sources collapses into **one asset with multiple interfaces** rather than
duplicates.

## Provenance

Every asset records a **source** (`manual`, `discovery`, `ipam`, or an integration
name) and a `last_seen` timestamp, so you can tell stale records from live ones and
audit where an entry came from.

## Permissions

- **viewer** — read the inventory.
- **operator** — create/edit/delete assets and run reconciliation.
- **admin** — everything.

Asset changes are written to the **Change Log** with before/after diffs, like the
rest of the platform.
