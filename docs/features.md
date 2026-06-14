# Feature Reference

Every M-Eyes feature, with **what it does**, its **use cases** and **how to
configure** it. The same reference is available **inside the app** — click the
**?** (help) button in the top-right of any page, or open
[`/docs`](#) after signing in.

!!! tip "Interactive dashboard"
    The Dashboard stat cards are clickable — selecting **Networks** opens IPAM,
    **DNS Zones** opens DNS, and so on. Use the help button (top-right **?**) to
    reach this documentation at any time.

## Overview

### Dashboard

- **What it does** — Landing page summarising the platform: object counts,
  top network utilisation, BIND/Kea engine status, a live event feed and recent
  configuration changes.
- **Use cases** — At-a-glance health check; spotting config drift; quick
  navigation (every stat card is a link).
- **Configure** — No setup. Click a stat card (e.g. *Networks*) to open that
  area; use the Deploy buttons in the Engines panel to push pending config.

### Global Search

- **What it does** — Top-bar "Search everything…" box that searches networks,
  IPs, zones, records, hosts and DNS-firewall rules and links to the match.
- **Use cases** — Find an object without knowing which page it lives on.
- **Configure** — Type ≥ 2 characters and click a result. No setup.

## Network (DDI)

### IPAM

- **What it does** — Network containers and subnets, IP inventory with status,
  next-free-IP allocation, utilisation tracking and tags.
- **Use cases** — Model the address plan; track used/reserved/discovered IPs;
  tag subnets to drive feeds.
- **Configure** — *IPAM → New Network* (CIDR, name, VLAN, site). Mark containers
  for parent ranges. Open a network to manage IPs, allocate next-free or
  **Discover** responders.

### DNS (Zones & Records)

- **What it does** — Forward/reverse zones, all common record types, automatic
  PTR, SOA serials, optional DNSSEC, deployment to BIND9.
- **Use cases** — Internal authoritative DNS; synced A/PTR; DNSSEC signing.
- **Configure** — *DNS → New Zone* (forward, or reverse linked to an IPAM
  network); add records; toggle DNSSEC; Deploy to BIND9.

### DNS Views (split-horizon)

- **What it does** — Named `match-clients` ACLs so one zone resolves differently
  per client; evaluated in order, with an implicit catch-all default view.
- **Use cases** — Internal vs external answers for the same name.
- **Configure** — *DNS Views → New View* (ACL), order the views, assign zones
  from the zone detail page.

### DHCP (Scopes)

- **What it does** — Scopes mapped 1:1 to IPAM networks, address ranges, MAC
  reservations (mirrored into IPAM) and options, deployed to Kea DHCPv4.
- **Use cases** — Lease addresses on a subnet; pin devices by MAC; push
  gateway/DNS/domain options.
- **Configure** — *DHCP → create scope on a network*, add ranges, set options,
  add reservations, Deploy to Kea.

### Leases

- **What it does** — Live Kea lease table via the Control Agent
  (`lease4-get-all`), mapped back to IPAM networks.
- **Use cases** — See current leases; troubleshoot exhaustion.
- **Configure** — None; requires the Kea Control Agent reachable (degrades
  gracefully otherwise).

### Hosts

- **What it does** — Composite objects: one create allocates the IP and writes
  A + PTR (and optionally a DHCP reservation).
- **Use cases** — Onboard a device with IP + DNS + DHCP in one step.
- **Configure** — *Hosts → New Host* (FQDN, network, IP, optional MAC). Delete
  cleans up IP/A/PTR together.

### Assets (CMDB)

- **What it does** — Lightweight CMDB cross-referenced to DDI: owner, location,
  criticality, lifecycle and interfaces linked to IPAM addresses.
- **Use cases** — Know which device owns an IP; collapse multi-source discoveries
  into one asset.
- **Configure** — *Assets → New Asset* with interfaces, or **Reconcile from
  DDI**, or populate via discovery sweeps / integrations.

## Security Fabric

### Fortinet Feeds

- **What it does** — Token-protected External Resource feeds (networks, tag,
  blocklist, fqdn) FortiGates consume natively.
- **Use cases** — Reference live subnets in policies; distribute tagged groups;
  feed FQDNs into filters.
- **Configure** — *Feeds*, copy the generated `external-resource` snippet,
  authenticate with HTTP Basic (`feed` / token), set refresh-rate, use HTTPS.

### Blocklist

- **What it does** — Managed list of bad IPs/CIDRs published via the blocklist
  feed.
- **Use cases** — Block a C2/scanning IP fabric-wide.
- **Configure** — *Blocklist → add entry* (IP/CIDR + reason); reference the feed
  in policies.

### DNS Firewall (RPZ)

- **What it does** — RPZ rules acting on resolver responses: block, nodata,
  passthru, substitute (walled garden).
- **Use cases** — Block malware/phishing; redirect trackers; exempt domains.
- **Configure** — *DNS Firewall → New Rule* (FQDN + action; target for
  substitute); Deploy BIND. Point clients at BIND.

## Enterprise

### Integrations

- **What it does** — Pluggable Fortinet/Microsoft connectors (FortiGate,
  FortiManager, FortiAnalyzer, FortiAuthenticator, Microsoft DNS, Entra ID) that
  Test and Sync; secrets stored encrypted-at-rest.
- **Use cases** — Import FortiGate subnets/leases; push networks to
  FortiManager; import Microsoft DNS/Entra devices as assets.
- **Configure** — *Integrations → Add*, fill the connector form, provide
  credentials, **Test**, then **Sync** on demand or on a schedule.

### Automation & Autonomy

- **What it does** — Background scheduler running rules (asset reconcile,
  discovery sweep, integration sync, drift-gated auto-deploy, threat-feed
  refresh) on a cadence.
- **Use cases** — Self-driving networks; drift-gated deploys; fresh threat feeds.
- **Configure** — *Automation → New Rule* (kind, target, interval); **Run** on
  demand. Auto-deploy only fires when an engine is behind.

## Log & Report

### Change Log & Rollback

- **What it does** — Automatic config versioning with before/after diffs, a
  global config version and one-click rollback.
- **Use cases** — Audit changes; revert a bad change.
- **Configure** — None; inspect diffs and use **Rollback**.

### Events

- **What it does** — Operational event log (severities/categories) with optional
  syslog forwarding and a live SSE stream.
- **Use cases** — Watch deploys/integrations live; forward to a SIEM.
- **Configure** — View/filter events; set syslog under *Settings → Advanced
  Logging*.

### Runbook

- **What it does** — Auto-generated Markdown runbook of current platform state.
- **Use cases** — Always-current operational reference; audit snapshot.
- **Configure** — None; regenerates from live config.

## System

### Extensible Attributes

- **What it does** — Typed metadata (string, integer, email, URL, date, enum)
  attachable to networks, IPs, zones, records and hosts, validated on input.
- **Use cases** — Record Owner/Environment/Location; consistent reporting.
- **Configure** — *Extensible Attrs → define*, then set values on detail pages.

### Users & Roles

- **What it does** — Local accounts with RBAC: viewer, operator, admin.
- **Use cases** — Grant operators limited access; reserve admin actions.
- **Configure** — *Users & Roles → add user*; assign a role; change the default
  admin password.

### SSO / SAML

- **What it does** — SAML 2.0 SSO (FortiAuthenticator recommended IdP) mapping
  IdP identities to M-Eyes roles.
- **Use cases** — Central authentication; no local passwords.
- **Configure** — *SSO / SAML*: IdP metadata/entity id, SSO URL, certificate;
  map groups to roles; test before enforcing.

### Settings

- **What it does** — Platform configuration: engine endpoints, advanced logging,
  HTTPS/TLS and operational defaults.
- **Use cases** — Point at BIND/Kea control endpoints; enable syslog forwarding.
- **Configure** — *Settings*: adjust the relevant section and save.

### Deployment (BIND & Kea)

- **What it does** — Renders engine-native config and reloads via native control
  channels (`rndc`, Kea Control Agent); management-only when engines are down.
- **Use cases** — Push pending DNS/DHCP safely; operate offline and deploy later.
- **Configure** — Use the Dashboard Deploy buttons or an auto-deploy rule;
  deploys validate before reloading.
