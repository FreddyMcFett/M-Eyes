# Enterprise Integrations

M-Eyes connects to your **Fortinet** and **Microsoft** estate through a pluggable
connector framework. Each connector can **test** its connection and **sync** data;
the [automation engine](automation.md) can run any sync on a schedule for
hands-off operation.

Manage them under **Enterprise → Integrations**. Adding one renders a form driven
by the connector's own field descriptors, with basic and **advanced** settings.
Secrets (API tokens, passwords, client secrets) are stored encrypted-at-rest in the
database and **never returned** to the UI — update a credential by typing a new one,
leave it blank to keep the stored value.

## Fortinet connectors

### FortiGate

Talks to the FortiOS REST API with an **API token** (System → Administrators →
REST API Admin).

- **Test** — reads `system/status` and reports FortiOS version/hostname.
- **Sync**:
  - imports **interface subnets** into IPAM (deduplicated against existing
    networks),
  - imports **DHCP leases** as assets (matched by MAC/IP).
- Options: VDOM, toggles for interface/lease import, an IPAM site tag (advanced).

### FortiManager

JSON-RPC API, authenticated with an admin **user/password**.

- **Test** — logs in and reads `sys/status`.
- **Sync** — **pushes** every non-container IPAM network into the chosen **ADOM**
  as a firewall **address object** (`<prefix><cidr>`), ready to reference fabric-wide.

### FortiAnalyzer

Centralises the M-Eyes event stream in FortiAnalyzer.

- **Test** — probes the syslog host/port (TCP connect or UDP send).
- **Sync** — enables M-Eyes syslog forwarding to the configured collector (the same
  forwarder as System → Settings → Advanced Logging).

### FortiAuthenticator

The recommended **SAML Identity Provider** for M-Eyes SSO. This connector verifies
portal reachability; the assertion exchange itself is configured under
**System → SSO / SAML** — see the [SAML SSO guide](saml-sso.md).

## Microsoft connectors

### Microsoft DNS

Imports host records from Microsoft DNS via **zone transfer (AXFR)** using `dig`
(bundled in the API image). The Microsoft DNS server must permit a zone transfer to
the M-Eyes host.

- **Test** — transfers the first configured zone and counts A records.
- **Sync** — imports A records across all configured zones as assets (matched by
  hostname/IP).
- Options: comma-separated **zones**, create-assets toggle.

### Microsoft Entra ID

Imports **Entra ID / Intune managed devices** as assets via the Microsoft Graph
API, using an app registration (**client credentials**).

- Provide **Tenant ID**, **Client ID** (as the username) and a **Client secret**.
  The app needs `Device.Read.All` / `DeviceManagementManagedDevices.Read.All`
  application permissions with admin consent.
- **Test** — obtains a token and lists devices.
- **Sync** — upserts devices as assets, enriching OS, model, vendor and serial.
  Handles Graph paging automatically.

## Running a sync

- **On demand** — the **Test** and **Sync** buttons on each row (operator+).
- **Scheduled** — create an `integration_sync` [automation rule](automation.md)
  pointing at the integration and pick a cadence.

Each run updates the integration's **last status / message / time** and writes an
event (`integration` category). A connector that can't reach its target fails
gracefully — it records the error and never affects the control plane.

## Permissions

- **viewer / operator** — view integrations; **operator** may run test/sync.
- **admin** — create, edit and delete integrations and their credentials.
