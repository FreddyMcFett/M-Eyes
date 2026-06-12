# Fortinet Integration

M-Eyes publishes its IPAM/DNS data as **External Resource feeds** that FortiGates (and
FortiManager) consume natively — no agent, no scripting on the firewall.

## Feed types

| Feed kind | Content | FortiOS resource type |
|---|---|---|
| `networks` | every non-container subnet as a CIDR list | `address` |
| `tag` | subnets + IPs (as /32) carrying a chosen tag | `address` |
| `blocklist` | the M-Eyes blocklist (IPs / CIDRs) | `address` |
| `fqdn` | unique FQDNs from A/AAAA/CNAME records | `domain` |

Every feed is served as `text/plain`, one entry per line, at
`/feeds/<slug>.txt`, plus a JSON variant at `/feeds/<slug>.json` that carries the
config version. Responses send `Cache-Control: max-age=60`.

## Authentication

Each feed has its own random token, rotatable from the UI. Two ways to present it:

- **HTTP Basic** — username `feed`, password = token (matches the FortiOS
  `external-resource` username/password fields). Recommended.
- Query parameter — `?token=<token>` (curl/testing).

## FortiGate configuration

The Feeds page generates a ready-to-paste snippet per feed:

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

The resulting external address object can be used directly in firewall policies. Domain
feeds (`set type domain`) plug into DNS filter profiles.

!!! warning
    Use HTTPS in production — the token travels as basic auth. Put a TLS-terminating
    proxy in front of M-Eyes.

## Typical workflows

- **Block a C2 IP**: add it on the Blocklist page → FortiGates pull the updated feed within
  their refresh interval → the policy referencing the external address blocks it.
- **Segment guest networks**: tag guest subnets with `guest-wifi`, create a tag feed, and
  reference it in policies on every FortiGate in the fabric.
- **DNS visibility**: the FQDN feed gives web/DNS filters the full list of names M-Eyes
  is authoritative for.

## Syslog to FortiAnalyzer

Under *System → Settings → Advanced Logging*, point syslog forwarding at a FortiAnalyzer
(or any collector). All M-Eyes events — logins, configuration changes, deploys, feed
token rotations — are forwarded as RFC 3164 syslog over UDP or TCP with a configurable
facility and minimum severity.
