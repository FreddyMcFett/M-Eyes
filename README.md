# M-Eyes

**M-Eyes** is an open-source **DDI platform** — DNS, DHCP and IP Address Management in a
single control plane — built for the **Fortinet ecosystem**, with a FortiOS-style web UI,
automatic configuration versioning and self-generating documentation.

> Think "open Infoblox": M-Eyes models your networks, zones and scopes, generates
> engine-native configuration for **BIND9** and **Kea DHCP**, and publishes your address
> data as feeds that **FortiGates consume natively** as External Resources.

## Features

| Area | Highlights |
|---|---|
| **IPAM** | network containers & subnets, IP inventory, next-free-IP allocation, utilization, VLAN/site metadata, tags, **network discovery** (ping sweep with conflict detection) |
| **DNS** | forward & reverse zones, A/AAAA/CNAME/MX/TXT/NS/PTR/SRV, automatic PTR management, SOA serial handling, **split-horizon views** (match-clients ACLs), **DNSSEC** inline signing per zone, zone-file preview, one-click deploy to BIND9 (`named-checkzone` validated, `rndc` reload) |
| **DNS Firewall** | Infoblox-style RPZ: block / NXDOMAIN, NODATA, passthru and substitute rules per domain (subdomains included), generated as a BIND Response Policy Zone |
| **DHCP** | scopes mapped to IPAM networks, ranges, MAC reservations (mirrored into IPAM), options, deploy to Kea via Control Agent, **live lease viewer** |
| **Hosts** | composite create: IP + A + PTR + DHCP reservation in one call — and one delete to reverse it |
| **Extensible Attributes** | typed, admin-defined metadata (string / integer / email / URL / date / enum) attachable to networks, IPs, zones, records and hosts |
| **Search** | global search across networks, IPs, zones, records, hosts and firewall rules from the top bar |
| **Fortinet** | token-protected External Resource feeds (subnets / tagged objects / blocklist / FQDNs), per-feed FortiGate CLI snippets, token rotation, syslog forwarding to FortiAnalyzer or any collector |
| **Versioning** | immutable changelog with before/after diffs, global config version, one-click rollback, auto-generated Markdown runbook, deploy-drift display |
| **Operations** | live dashboard (SSE event stream + polling), event log with live tail, debug mode, engine connectivity tests, diagnostics bundle |

## Quick start (Docker)

```bash
docker compose up -d --build
```

- Web UI: **http://localhost:8080** — login `admin` / `admin`
- API & Swagger: http://localhost:8000/docs
- DNS (BIND9): `dig @localhost -p 5353 ns1.corp.m-eyes.local` (after deploying from the UI)

Demo data is seeded automatically (`MEYES_SEED_DEMO=false` to skip).

## Quick start (development)

```bash
# backend — http://localhost:8000
cd backend && pip install -e ".[dev]" && python -m app.scripts.seed && uvicorn app.main:app --reload

# frontend — http://localhost:5173
cd frontend && npm install && npm run dev

# tests
cd backend && pytest
```

No Docker needed: without the engines M-Eyes runs in management-only mode — config
generation and previews work; deploys report `unreachable`.

## FortiGate integration in 30 seconds

1. Open **Security Fabric → Fortinet Feeds**, copy the CLI snippet of a feed:

```text
config system external-resource
    edit "meyes-networks"
        set type address
        set resource "https://meyes.example.com/feeds/networks.txt"
        set username "feed"
        set password <token>
        set refresh-rate 5
        set status enable
    next
end
```

2. Use the external address object in firewall policies. Blocklist additions in M-Eyes
   propagate to every FortiGate on its next refresh.

Full guide: [docs/fortinet-integration.md](docs/fortinet-integration.md)

## Repository layout

```
backend/    FastAPI control plane (models, services, generators, tests)
frontend/   React + TypeScript SPA, FortiOS-style theme
deploy/     Dockerfiles, nginx, BIND9 + Kea engine assets
docs/       MkDocs documentation (auto-deployed, auto-generated API reference)
```

## Versioning

- **Configuration**: every change is recorded with a before/after diff and a global config
  version; anything can be rolled back from the Change Log page.
- **Software**: releases are fully automated with semantic-release — conventional commits
  on `main` produce the changelog, version bumps, tags and GitHub Releases.

## Production checklist

- Terminate TLS in front of M-Eyes (feeds use HTTP basic auth).
- Set `MEYES_JWT_SECRET`; change the admin password.
- Regenerate `deploy/bind9/rndc.key` (`rndc-confgen -a`) — the committed key is dev-only.
- Give the Kea container L2 access (`network_mode: host`) for real DHCP service.

## License

MIT
