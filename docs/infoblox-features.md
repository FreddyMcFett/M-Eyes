# Infoblox-style features

M-Eyes positions itself as an "open Infoblox". This page maps the signature
Infoblox NIOS capabilities to their M-Eyes equivalents and explains how each one
works.

## Feature parity matrix

| Infoblox NIOS | M-Eyes | Where |
|---|---|---|
| IPAM (containers, networks, next-available IP) | ✅ | **Network → IPAM** |
| DNS zones & records, automatic PTR | ✅ | **Network → DNS** |
| DHCP scopes, ranges, fixed addresses | ✅ | **Network → DHCP** |
| Host records (composite objects) | ✅ | **Network → Hosts** |
| Extensible Attributes | ✅ | **System → Extensible Attrs** + every detail page |
| DNS Views (split-horizon) | ✅ | **Network → DNS Views** |
| DNSSEC zone signing | ✅ | per-zone toggle (BIND `dnssec-policy default`) |
| RPZ / DNS Firewall | ✅ | **Security Fabric → DNS Firewall** |
| DHCP lease viewer | ✅ | **Network → Leases** (live from Kea) |
| Network discovery | ✅ | **Discover** button on every network detail page |
| Global search | ✅ | search box in the top bar |
| Audit log & restore | ✅ | **Log & Report → Change Log** (rollback) |
| Grid (multi-member HA), Reporting server, DTC | ❌ roadmap | — |

## Extensible attributes

Admins define typed attributes (string, integer, email, URL, date or enum with a
fixed value list) under **System → Extensible Attrs**. Values can then be attached
to networks, IP addresses, zones, records and hosts from their detail pages and are
validated against the definition. Values are stored separately from the objects, are
audited in the change log, and are cleaned up automatically when the owning object
is deleted.

API: `GET/POST /api/v1/extattr-defs`, `GET/PUT /api/v1/extattrs/{object_type}/{object_id}`.

## DNS views (split-horizon)

A view is a named `match-clients` ACL (`any`, `none`, `localhost`, `localnets`,
CIDRs, `!`-negated elements). BIND evaluates views in their configured order; zones
that are not assigned to a view are served from the implicit catch-all **default**
view, which always matches last. The same zone name may exist once per view, so
`corp.example.com` can resolve differently for internal and external clients.

Generated zone files are prefixed with the view name (`db.internal.corp.example.com`)
to keep them apart on disk.

## DNSSEC

Enabling DNSSEC on a zone adds `dnssec-policy default; inline-signing yes;` to the
generated declaration — BIND 9.16+ creates and rotates the keys automatically in its
working directory. Pull the DS record from the signed zone for your registrar.

## DNS firewall (RPZ)

Rules live under **Security Fabric → DNS Firewall**. Each rule covers a domain and
all of its subdomains and supports the standard RPZ actions:

| Action | RPZ encoding | Effect |
|---|---|---|
| `block` | `CNAME .` | NXDOMAIN |
| `nodata` | `CNAME *.` | empty answer |
| `passthru` | `CNAME rpz-passthru.` | whitelist / exempt |
| `substitute` | `A`/`AAAA`/`CNAME` | walled garden redirect |

While at least one rule is enabled, deploys publish the `rpz.m-eyes` zone and a
`response-policy` directive (globally via the generated `rpz-options.conf` include,
or per view when views are in use). Note that response policies act on responses a
resolver returns to clients — point your clients at BIND for the firewall to bite.

## DHCP leases

**Network → Leases** reads the live lease table from Kea through the Control Agent
(`lease4-get-all`) and maps Kea subnet ids back to IPAM networks. If the Control
Agent is unreachable the page degrades gracefully instead of failing.

## Network discovery

The **Discover** button on a network detail page runs a concurrent ICMP ping sweep
(networks up to /22). Responding addresses unknown to IPAM are recorded with status
`discovered`; known addresses get their *last seen* timestamp refreshed; responses
from addresses marked `reserved` are flagged as conflicts in the event log.
