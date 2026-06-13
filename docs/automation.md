# Automation & Autonomy

M-Eyes can run itself. The **automation engine** is a background scheduler that
executes **rules** on a cadence, so the platform keeps IPAM, assets, integrations
and engine config in step without anyone clicking a button. Every run is recorded
on the rule and in the event log, so the autonomy stays fully auditable.

Manage rules under **Enterprise → Automation**.

## Rule kinds

| Kind | What it does | Config |
|---|---|---|
| **Asset reconcile from IPAM** | Matches managed IPAM addresses (with MAC/hostname) into the asset inventory | — |
| **Discovery sweep + asset reconcile** | Ping-sweeps a network, records responders in IPAM, then reconciles assets | target network |
| **Run an integration sync** | Executes a configured Fortinet/Microsoft integration sync | integration |
| **Auto-deploy pending DNS/DHCP config** | Deploys BIND/Kea **only when** the live deployment lags the current config version (drift) | targets (bind/kea) |
| **Refresh DNS-firewall threat feeds** | Re-syncs threat feeds past their refresh interval | — |

## Scheduling

Each rule has an **interval** (5 minutes → weekly). The scheduler wakes every
minute, runs any rule whose next-run time has passed, records the outcome
(`ok` / `skipped` / `error`) and reschedules it. You can also **Run** any rule
immediately from the UI.

## Safety model

- **Auto-deploy is drift-gated.** It compares each engine's last deployed config
  version against the current version and **only deploys when behind** — it never
  redeploys identical config, and it goes through the same `named-checkzone`
  validation as a manual deploy.
- **Rules are isolated.** A failing rule is recorded as an error and never stops
  the scheduler or other rules.
- **Everything is attributed.** Runs are actioned as `automation:<rule name>` in
  the change log and event stream, so autonomous changes are as traceable as
  manual ones.

## Example: a self-driving branch network

1. **Discovery sweep** on `10.20.0.0/24` every 6 hours → new devices appear in
   IPAM and the asset inventory automatically.
2. **FortiGate sync** every 15 minutes (`integration_sync`) → interface subnets and
   DHCP leases stay current.
3. **Auto-deploy** hourly → any DNS/DHCP changes (manual or from the above) roll out
   to BIND/Kea once, when drift is detected.
4. **Threat-feed refresh** daily → DNS firewall blocklists stay fresh.

## Permissions

- **viewer / operator** — view rules; **operator** may run a rule on demand.
- **admin** — create, edit and delete rules.
