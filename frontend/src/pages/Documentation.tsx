import { ReactNode, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  ArrowRight,
  BookOpen,
  Boxes,
  Cpu,
  ExternalLink,
  Globe,
  History,
  KeyRound,
  Layers,
  LayoutDashboard,
  List,
  ListChecks,
  Plug,
  Rss,
  Search,
  Server,
  Settings as SettingsIcon,
  Shield,
  ShieldBan,
  ShieldOff,
  Tags,
  UploadCloud,
  Users as UsersIcon,
} from 'lucide-react';

interface Feature {
  id: string;
  title: string;
  icon: ReactNode;
  /** Route this feature lives at, so the doc can deep-link into the app. */
  route?: string;
  what: string;
  useCases: string[];
  configure: string[];
  tips?: string[];
}

interface Section {
  label: string;
  features: Feature[];
}

const SECTIONS: Section[] = [
  {
    label: 'Overview',
    features: [
      {
        id: 'dashboard',
        title: 'Dashboard',
        icon: <LayoutDashboard size={16} />,
        route: '/',
        what: 'The landing page summarising the whole platform: object counts (networks, IPs, zones, records, DHCP scopes, feeds), top network utilisation, BIND/Kea engine status, a live event feed and the most recent configuration changes.',
        useCases: [
          'Get an at-a-glance health check of DNS/DHCP/IPAM in one screen.',
          'Spot configuration drift — see when an engine is behind the current config version.',
          'Jump straight to the area you need: every stat card is clickable.',
        ],
        configure: [
          'No configuration required — it reads live data from the API.',
          'Click any stat card (e.g. "Networks") to open the matching page (IPAM, DNS, DHCP, Feeds).',
          'Use the Deploy buttons in the Engines panel to push pending config to BIND9 or Kea.',
        ],
        tips: ['Counts and engine status auto-refresh every 5 seconds; live events stream over Server-Sent Events.'],
      },
      {
        id: 'search',
        title: 'Global Search',
        icon: <Search size={16} />,
        what: 'The "Search everything…" box in the top bar performs an Infoblox-style search across every object family — networks, IP addresses, zones, records, hosts and DNS-firewall rules — and links straight to the matching detail page.',
        useCases: [
          'Find an IP, hostname or subnet without remembering which page it lives on.',
          'Jump to a DNS record or zone by name during an incident.',
        ],
        configure: [
          'Type at least 2 characters; results appear after a short debounce.',
          'Click a result to navigate to it. No setup required.',
        ],
      },
    ],
  },
  {
    label: 'Network (DDI)',
    features: [
      {
        id: 'ipam',
        title: 'IPAM',
        icon: <List size={16} />,
        route: '/ipam',
        what: 'IP Address Management: a hierarchy of network containers and subnets, an IP inventory with per-address status, next-free-IP allocation, utilisation tracking and tags.',
        useCases: [
          'Model your address plan as containers (10.0.0.0/8) and leaf subnets (10.10.1.0/24).',
          'Track which addresses are used / reserved / discovered and find the next free IP.',
          'Tag subnets (e.g. guest-wifi, servers) to drive Fortinet feeds and reporting.',
        ],
        configure: [
          'Open IPAM and click New Network. Enter the CIDR, name, optional VLAN and site.',
          'Mark a network as a container when it only holds smaller subnets.',
          'Open a network to manage its IP inventory, allocate the next free IP, or run Discover.',
          'Attach Extensible Attributes (Owner, Environment, …) from the detail page.',
        ],
        tips: ['The Discover button ping-sweeps the subnet (up to /22) and records responders as IPs.'],
      },
      {
        id: 'dns',
        title: 'DNS (Zones & Records)',
        icon: <Globe size={16} />,
        route: '/dns',
        what: 'Authoritative forward and reverse zones with all common record types, automatic PTR management, SOA serial handling, optional DNSSEC, and deployment to BIND9.',
        useCases: [
          'Host internal forward zones (corp.example.com) and reverse zones for PTR.',
          'Keep A and PTR records in sync automatically when you create hosts.',
          'Sign a zone with DNSSEC using BIND-managed keys.',
        ],
        configure: [
          'Open DNS → New Zone. Choose forward or reverse; for reverse, link the IPAM network.',
          'Open a zone to add records (A, AAAA, CNAME, MX, TXT, NS, SRV, PTR …).',
          'Toggle DNSSEC on the zone to add dnssec-policy default; pull the DS record for your registrar.',
          'Deploy from the Dashboard or via an auto-deploy automation rule to push to BIND9.',
        ],
      },
      {
        id: 'dns-views',
        title: 'DNS Views (split-horizon)',
        icon: <Layers size={16} />,
        route: '/dns-views',
        what: 'Named match-clients ACLs that let the same zone resolve differently for different clients (internal vs external). Views are evaluated in order; unassigned zones fall through to the implicit default view.',
        useCases: [
          'Serve an internal IP for corp.example.com to staff and a public IP to the internet.',
          'Segment resolution by source network without running multiple DNS servers.',
        ],
        configure: [
          'Open DNS Views → New View. Define the match-clients ACL (any, none, localnets, CIDRs, !negations).',
          'Order views; the first match wins, default always matches last.',
          'Assign zones to a view from the zone detail page.',
        ],
        tips: ['Generated zone files are prefixed with the view name to keep them apart on disk.'],
      },
      {
        id: 'dhcp',
        title: 'DHCP (Scopes)',
        icon: <Server size={16} />,
        route: '/dhcp',
        what: 'DHCP scopes mapped 1:1 to IPAM networks, with address ranges, MAC reservations (mirrored into IPAM), and DHCP options, deployed to Kea DHCPv4.',
        useCases: [
          'Hand out addresses on a client subnet from a defined range.',
          'Pin a printer or server to a fixed IP by MAC reservation.',
          'Push gateway, DNS and domain-name options to clients.',
        ],
        configure: [
          'Open DHCP → create a scope on an existing IPAM network.',
          'Add one or more ranges (start/end IP) inside the subnet.',
          'Set options (routers, domain-name-servers, domain-name) at scope or global level.',
          'Add reservations by MAC → IP; they appear in IPAM too. Deploy to Kea.',
        ],
      },
      {
        id: 'leases',
        title: 'Leases',
        icon: <ListChecks size={16} />,
        route: '/leases',
        what: 'A live view of the Kea lease table read through the Kea Control Agent (lease4-get-all), with Kea subnet ids mapped back to IPAM networks.',
        useCases: [
          'See which devices currently hold a DHCP lease and on which subnet.',
          'Troubleshoot address exhaustion or unexpected clients.',
        ],
        configure: [
          'No configuration — the page reads live data. Requires the Kea Control Agent to be reachable.',
          'If the Control Agent is down the page degrades gracefully instead of erroring.',
        ],
      },
      {
        id: 'hosts',
        title: 'Hosts',
        icon: <Activity size={16} />,
        route: '/hosts',
        what: 'Infoblox-style composite objects: a single create call allocates the IP, writes the A and PTR records, and optionally a DHCP reservation — keeping IPAM and DNS consistent in one step.',
        useCases: [
          'Onboard a new server with IP + DNS + DHCP in one action.',
          'Avoid forgetting the PTR record or leaving stale IPAM entries.',
        ],
        configure: [
          'Open Hosts → New Host. Enter the FQDN, pick the network and the IP (or take next-free).',
          'Optionally add a MAC to also create a DHCP reservation.',
          'Deleting the host cleans up the IP, A and PTR together.',
        ],
      },
      {
        id: 'assets',
        title: 'Assets (CMDB)',
        icon: <Boxes size={16} />,
        route: '/assets',
        what: 'A lightweight CMDB cross-referenced to your DDI data. Where IPAM tells you which IP is used, the asset inventory tells you what device owns it, who is responsible, where it lives and its lifecycle state.',
        useCases: [
          'Keep an owner/location/criticality record for every device.',
          'Pivot from an IP address to the asset that owns it (and back).',
          'Collapse a device discovered by several sources into one asset with multiple interfaces.',
        ],
        configure: [
          'Open Assets → New Asset, set type/status/criticality and add interfaces (MAC, IP, hostname).',
          'Or use Reconcile from DDI to build assets from managed IPAM addresses (matches MAC first, then IP).',
          'Populate automatically via discovery sweeps or integrations (FortiGate, Microsoft DNS, Entra/Intune).',
        ],
        tips: ['Every asset records a source (manual/discovery/ipam/integration) and a last_seen timestamp.'],
      },
    ],
  },
  {
    label: 'Security Fabric',
    features: [
      {
        id: 'feeds',
        title: 'Fortinet Feeds',
        icon: <Rss size={16} />,
        route: '/feeds',
        what: 'Token-protected HTTP External Resource feeds that FortiGates and FortiManager consume natively — no agent. Feed kinds: networks (subnets), tag (tagged subnets/IPs), blocklist (IPs/CIDRs) and fqdn (domains).',
        useCases: [
          'Reference live M-Eyes subnets in FortiGate firewall policies.',
          'Distribute a guest-network address group across the whole fabric via a tag feed.',
          'Feed authoritative FQDNs into DNS/web filter profiles.',
        ],
        configure: [
          'Open Feeds, pick a feed and copy the generated config system external-resource snippet.',
          'Authenticate with HTTP Basic (username feed, password = the feed token) — rotate the token from the UI.',
          'Paste the snippet into FortiOS; set the refresh-rate. Use HTTPS in production.',
        ],
        tips: ['Each feed is served at /feeds/<slug>.txt (plain) and /feeds/<slug>.json (with config version).'],
      },
      {
        id: 'blocklist',
        title: 'Blocklist',
        icon: <ShieldBan size={16} />,
        route: '/blocklist',
        what: 'A managed list of bad IPs and CIDRs that is published through the blocklist Fortinet feed for use as an external address object in firewall policies.',
        useCases: [
          'Block a known C2 / scanning IP fabric-wide within the feed refresh interval.',
          'Maintain a curated deny list with reasons and attribution.',
        ],
        configure: [
          'Open Blocklist → add an entry (IP or CIDR) with a reason.',
          'Reference the blocklist feed in your FortiGate policies; updates propagate on refresh.',
        ],
      },
      {
        id: 'dnsfw',
        title: 'DNS Firewall (RPZ)',
        icon: <ShieldOff size={16} />,
        route: '/dnsfw',
        what: 'Response Policy Zone rules that act on DNS answers BIND returns to clients. Each rule covers a domain and its subdomains and supports block (NXDOMAIN), nodata, passthru (whitelist) and substitute (walled-garden redirect).',
        useCases: [
          'Block malware/phishing domains at the resolver.',
          'Redirect a tracker domain to a walled-garden page (substitute).',
          'Exempt a domain that would otherwise be caught (passthru).',
        ],
        configure: [
          'Open DNS Firewall → New Rule. Enter the FQDN and pick the action.',
          'For substitute, provide the replacement A/AAAA/CNAME target.',
          'Deploy BIND — while any rule is enabled, the rpz.m-eyes zone and response-policy are published.',
        ],
        tips: ['Point your clients at BIND for the firewall to take effect — RPZ acts on resolver responses.'],
      },
    ],
  },
  {
    label: 'Enterprise',
    features: [
      {
        id: 'integrations',
        title: 'Integrations',
        icon: <Plug size={16} />,
        route: '/integrations',
        what: 'A pluggable connector framework for the Fortinet and Microsoft estate. Each connector can Test its connection and Sync data; secrets are stored encrypted-at-rest and never returned to the UI. Connectors: FortiGate, FortiManager, FortiAnalyzer, FortiAuthenticator, Microsoft DNS, Microsoft Entra ID.',
        useCases: [
          'Import FortiGate interface subnets into IPAM and DHCP leases as assets.',
          'Push IPAM networks into FortiManager as address objects.',
          'Import Microsoft DNS A records or Entra/Intune devices as assets.',
        ],
        configure: [
          'Open Integrations → Add, pick the connector, fill the form (the fields are driven by the connector).',
          'Provide credentials (API token, user/password, or client-credentials). Click Test to verify.',
          'Run Sync on demand, or schedule it with an integration_sync automation rule.',
        ],
        tips: ['Leave a credential field blank when editing to keep the stored secret unchanged.'],
      },
      {
        id: 'automation',
        title: 'Automation & Autonomy',
        icon: <Cpu size={16} />,
        route: '/automation',
        what: 'A background scheduler that runs rules on a cadence so the platform keeps IPAM, assets, integrations and engine config in step automatically. Rule kinds include asset reconcile, discovery sweep, integration sync, drift-gated auto-deploy and threat-feed refresh.',
        useCases: [
          'Auto-deploy DNS/DHCP only when an engine drifts behind the current config version.',
          'Discover a branch network and reconcile assets every few hours, hands-off.',
          'Keep DNS-firewall threat feeds fresh on a daily schedule.',
        ],
        configure: [
          'Open Automation → New Rule. Pick the kind and its target (network / integration / engines).',
          'Choose an interval (5 minutes → weekly). The scheduler wakes every minute and runs due rules.',
          'Use Run to execute a rule immediately. Outcomes (ok/skipped/error) are logged per run.',
        ],
        tips: ['Auto-deploy is drift-gated: it only deploys when an engine is behind, and goes through the same validation as a manual deploy.'],
      },
    ],
  },
  {
    label: 'Log & Report',
    features: [
      {
        id: 'changelog',
        title: 'Change Log & Rollback',
        icon: <History size={16} />,
        route: '/changelog',
        what: 'Automatic config versioning: every change is recorded with a before/after diff, a global config version and one-click rollback. Autonomous changes are attributed to the automation rule that made them.',
        useCases: [
          'Audit who changed what, when, with a precise diff.',
          'Roll back a bad change to a previous config version.',
        ],
        configure: [
          'No setup — every create/update/delete is recorded automatically.',
          'Open the Change Log, inspect a diff, and use Rollback to restore.',
        ],
      },
      {
        id: 'events',
        title: 'Events',
        icon: <Activity size={16} />,
        route: '/events',
        what: 'An operational event log with severities and categories (logins, config changes, deploys, feed token rotations, integration runs), with optional syslog forwarding and a live SSE stream.',
        useCases: [
          'Watch deployments and integration runs in real time.',
          'Forward all events to FortiAnalyzer or any syslog collector.',
        ],
        configure: [
          'View and filter events on the Events page.',
          'Configure syslog forwarding (UDP/TCP, facility, min severity) under Settings → Advanced Logging.',
        ],
      },
      {
        id: 'runbook',
        title: 'Runbook',
        icon: <BookOpen size={16} />,
        route: '/runbook',
        what: 'An auto-generated Markdown runbook describing the current state of the platform — networks, zones, scopes and engine config — kept in step with the config version.',
        useCases: [
          'Hand operators an always-current operational reference.',
          'Export a snapshot of the environment for documentation or audit.',
        ],
        configure: ['No setup — the runbook regenerates from the live configuration.'],
      },
    ],
  },
  {
    label: 'System',
    features: [
      {
        id: 'extattrs',
        title: 'Extensible Attributes',
        icon: <Tags size={16} />,
        route: '/extattrs',
        what: 'Infoblox-style typed metadata. Admins define attributes (string, integer, email, URL, date or enum) that can be attached to networks, IPs, zones, records and hosts and are validated against the definition.',
        useCases: [
          'Record Owner, Environment (prod/staging/dev) or Location on any object.',
          'Drive reporting and filtering with consistent, validated metadata.',
        ],
        configure: [
          'Open Extensible Attrs → define an attribute and its type (and allowed values for enum).',
          'Set values from any object detail page; they are audited and cleaned up on delete.',
        ],
      },
      {
        id: 'users',
        title: 'Users & Roles',
        icon: <UsersIcon size={16} />,
        route: '/users',
        what: 'Local user accounts with role-based access control. Roles: viewer (read), operator (run syncs/deploys/edits where allowed) and admin (full control).',
        useCases: [
          'Give operators day-to-day access without full admin rights.',
          'Restrict credential and rule management to admins.',
        ],
        configure: [
          'Open Users & Roles → add a user and assign a role.',
          'Change the default admin password immediately on first login.',
        ],
      },
      {
        id: 'sso',
        title: 'SSO / SAML',
        icon: <KeyRound size={16} />,
        route: '/sso',
        what: 'SAML 2.0 single sign-on, with FortiAuthenticator as the recommended Identity Provider. Users authenticate against your IdP and are mapped to M-Eyes roles.',
        useCases: [
          'Centralise authentication through your corporate IdP.',
          'Avoid managing local passwords for every operator.',
        ],
        configure: [
          'Open SSO / SAML → configure the IdP metadata / entity id, SSO URL and certificate.',
          'Map IdP groups/attributes to M-Eyes roles. Test the assertion exchange before enforcing.',
        ],
      },
      {
        id: 'settings',
        title: 'Settings',
        icon: <SettingsIcon size={16} />,
        route: '/settings',
        what: 'Platform-wide configuration: engine endpoints, advanced logging (syslog forwarding), and other operational defaults.',
        useCases: [
          'Point M-Eyes at your BIND/Kea control endpoints.',
          'Enable syslog forwarding to a SIEM or FortiAnalyzer.',
        ],
        configure: [
          'Open Settings, adjust the relevant section and save.',
          'Use Advanced Logging to set the syslog host, transport, facility and minimum severity.',
        ],
      },
      {
        id: 'deploy',
        title: 'Deployment (BIND & Kea)',
        icon: <UploadCloud size={16} />,
        what: 'M-Eyes is the management plane: it renders engine-native config (BIND zone files, Kea JSON) and reloads the engines over their native control channels (rndc, Kea Control Agent). When engines are down it keeps working in management-only mode and reports unreachable.',
        useCases: [
          'Push pending DNS/DHCP changes to the live engines safely.',
          'Operate management-only when engines are offline; deploy later.',
        ],
        configure: [
          'Use the Deploy buttons on the Dashboard Engines panel, or an auto-deploy automation rule.',
          'Deploys run validation (e.g. named-checkzone) before reloading the engine.',
        ],
      },
    ],
  },
];

export default function Documentation() {
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();

  const sections = useMemo(() => {
    if (!q) return SECTIONS;
    return SECTIONS.map((s) => ({
      ...s,
      features: s.features.filter((f) =>
        [f.title, f.what, ...f.useCases, ...f.configure, ...(f.tips ?? [])]
          .join(' ')
          .toLowerCase()
          .includes(q),
      ),
    })).filter((s) => s.features.length > 0);
  }, [q]);

  const allFeatures = sections.flatMap((s) => s.features);

  return (
    <div className="space-y-4">
      <div className="f-card p-5">
        <div className="flex items-start gap-3">
          <BookOpen size={26} className="text-accent shrink-0 mt-0.5" />
          <div>
            <h1 className="text-lg font-semibold">M-Eyes Documentation</h1>
            <p className="text-table text-muted mt-1 max-w-3xl">
              An open-source DDI platform — DNS, DHCP and IP Address Management in one control plane —
              with first-class Fortinet ecosystem integration. Every feature below documents{' '}
              <strong>what it does</strong>, its <strong>use cases</strong> and{' '}
              <strong>how to configure it</strong>. Click a card title to open that area of the app.
            </p>
          </div>
        </div>
        <div className="relative mt-4 max-w-md">
          <Search size={15} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
          <input
            className="f-input !pl-9"
            placeholder="Filter features…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-4">
        {/* Table of contents */}
        <nav className="f-card p-3 h-max lg:sticky lg:top-0 hidden lg:block">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted mb-2">Contents</div>
          <div className="space-y-3">
            {sections.map((s) => (
              <div key={s.label}>
                <div className="text-xs font-semibold text-slate-600 mb-1">{s.label}</div>
                <ul className="space-y-0.5">
                  {s.features.map((f) => (
                    <li key={f.id}>
                      <a
                        href={`#${f.id}`}
                        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-accent"
                      >
                        <span className="text-muted">{f.icon}</span>
                        {f.title}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </nav>

        {/* Feature articles */}
        <div className="space-y-4 min-w-0">
          {allFeatures.length === 0 && (
            <div className="f-card p-6 text-center text-muted text-table">No features match “{query}”.</div>
          )}
          {sections.map((s) => (
            <section key={s.label} className="space-y-4">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">{s.label}</h2>
              {s.features.map((f) => (
                <article key={f.id} id={f.id} className="f-card p-5 scroll-mt-4">
                  <div className="flex items-center gap-2.5 mb-3">
                    <span className="text-accent">{f.icon}</span>
                    <h3 className="font-semibold">{f.title}</h3>
                    {f.route && (
                      <Link
                        to={f.route}
                        className="ml-auto inline-flex items-center gap-1 text-xs text-accent hover:underline"
                      >
                        Open <ExternalLink size={12} />
                      </Link>
                    )}
                  </div>

                  <p className="text-table text-slate-700">{f.what}</p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                    <div>
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted mb-1.5">
                        Use cases
                      </div>
                      <ul className="space-y-1">
                        {f.useCases.map((u, i) => (
                          <li key={i} className="flex items-start gap-1.5 text-table text-slate-700">
                            <ArrowRight size={13} className="text-accent shrink-0 mt-0.5" />
                            <span>{u}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted mb-1.5">
                        How to configure
                      </div>
                      <ol className="space-y-1 list-decimal list-inside marker:text-muted">
                        {f.configure.map((c, i) => (
                          <li key={i} className="text-table text-slate-700">
                            {c}
                          </li>
                        ))}
                      </ol>
                    </div>
                  </div>

                  {f.tips && f.tips.length > 0 && (
                    <div className="mt-3 rounded border border-line bg-slate-50 px-3 py-2">
                      {f.tips.map((t, i) => (
                        <div key={i} className="flex items-start gap-1.5 text-xs text-slate-600">
                          <Shield size={12} className="text-accent shrink-0 mt-0.5" />
                          <span>{t}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </article>
              ))}
            </section>
          ))}

          <div className="f-card p-4 text-xs text-muted">
            Looking for deeper reference material (architecture, API, upgrade and SAML guides)? See the full
            documentation site published from the <code>docs/</code> folder of the repository.
          </div>
        </div>
      </div>
    </div>
  );
}
