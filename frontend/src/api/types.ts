export interface Tag {
  id: number;
  name: string;
  color: string;
}

export interface Utilization {
  total: number;
  used: number;
  dhcp_range: number;
  free: number;
  percent: number;
}

export interface Network {
  id: number;
  cidr: string;
  name: string;
  description: string;
  is_container: boolean;
  vlan: number | null;
  site: string;
  parent_id: number | null;
  tags: Tag[];
  utilization: Utilization | null;
}

export interface IPAddress {
  id: number;
  network_id: number;
  ip: string;
  status: string;
  hostname: string;
  mac: string;
  description: string;
  last_seen: string | null;
  tags: Tag[];
}

export interface DnsView {
  id: number;
  name: string;
  match_clients: string;
  description: string;
  position: number;
  zone_count: number;
}

export interface Zone {
  id: number;
  name: string;
  kind: string;
  serial: number;
  default_ttl: number;
  soa_mname: string;
  soa_rname: string;
  refresh: number;
  retry: number;
  expire: number;
  minimum: number;
  network_id: number | null;
  view_id: number | null;
  view_name: string | null;
  dnssec_enabled: boolean;
  role: string;
  primaries: string;
  record_count: number;
}

export interface DnsRecord {
  id: number;
  zone_id: number;
  name: string;
  type: string;
  value: string;
  ttl: number | null;
  priority: number | null;
  ip_address_id: number | null;
}

export interface DhcpRange {
  id: number;
  subnet_id: number;
  start_ip: string;
  end_ip: string;
}

export interface DhcpReservation {
  id: number;
  subnet_id: number;
  mac: string;
  ip: string;
  hostname: string;
}

export interface DhcpOption {
  id: number;
  subnet_id: number | null;
  name: string;
  value: string;
}

export interface DhcpSubnet {
  id: number;
  network_id: number;
  enabled: boolean;
  cidr: string;
  ranges: DhcpRange[];
  reservations: DhcpReservation[];
  options: DhcpOption[];
}

export interface Host {
  id: number;
  name: string;
  ip: string | null;
  zone_name: string | null;
  ip_address_id: number | null;
  a_record_id: number | null;
  ptr_record_id: number | null;
  reservation_id: number | null;
}

export interface Feed {
  id: number;
  slug: string;
  name: string;
  kind: string;
  tag_id: number | null;
  token: string;
  enabled: boolean;
  entry_count: number;
  fortigate_snippet: string;
}

export interface BlocklistEntry {
  id: number;
  value: string;
  reason: string;
  created_by: string;
  created_at: string;
}

export interface ChangeLogEntry {
  id: number;
  ts: string;
  actor: string;
  action: string;
  object_type: string;
  object_id: number;
  summary: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
}

export interface AppEvent {
  id: number;
  ts: string;
  severity: string;
  category: string;
  message: string;
  data: Record<string, unknown> | null;
}

export interface DashboardStats {
  config_version: number;
  counts: Record<string, number>;
  top_networks: ({ id: number; cidr: string; name: string } & Utilization)[];
  recent_changes: { id: number; ts: string; actor: string; action: string; object_type: string; summary: string }[];
  engines: Record<string, { status: string; ts: string; config_version: number } | null>;
}

export interface EngineStatus {
  bind: { last_status: string | null; last_message: string | null; deployed_version: number | null };
  kea: { last_status: string | null; last_message: string | null; deployed_version: number | null };
}

export interface Deployment {
  id: number;
  ts: string;
  target: string;
  status: string;
  message: string;
  config_version: number;
}

export interface RpzRule {
  id: number;
  fqdn: string;
  action: string;
  substitute: string;
  comment: string;
  enabled: boolean;
}

export interface ThreatFeed {
  id: number;
  name: string;
  url: string;
  action: string;
  enabled: boolean;
  refresh_hours: number;
  last_synced: string | null;
  last_status: string;
  entry_count: number;
}

export interface ApiKey {
  id: number;
  name: string;
  prefix: string;
  role: string;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
  key?: string; // present only in the create response
}

export interface UpdateStatus {
  current_version: string;
  latest_version: string | null;
  update_available: boolean;
  release_url: string;
  error: string | null;
}

export interface ExtAttrDef {
  id: number;
  name: string;
  type: string;
  comment: string;
  allowed_values: string[] | null;
  usage_count: number;
}

export interface ExtAttrValues {
  object_type: string;
  object_id: number;
  values: Record<string, string>;
}

export interface DhcpLease {
  ip: string;
  mac: string;
  hostname: string;
  state: string;
  expires_at: string | null;
  subnet: string | null;
}

export interface LeasesResponse {
  reachable: boolean;
  detail: string;
  leases: DhcpLease[];
}

export interface SearchResult {
  type: string;
  id: number;
  label: string;
  detail: string;
  url: string;
}

export interface DiscoveryResult {
  cidr: string;
  scanned: number;
  alive: number;
  created: number;
  updated: number;
  conflicts: number;
}

export interface Certificate {
  id: number;
  name: string;
  kind: 'server' | 'ca';
  status: string;
  subject: string;
  issuer: string;
  san: string[] | null;
  serial: string;
  fingerprint_sha256: string;
  key_type: string;
  is_self_signed: boolean;
  not_before: string | null;
  not_after: string | null;
  has_key: boolean;
  has_csr: boolean;
  has_chain: boolean;
  created_at: string;
  updated_at: string;
}

export interface TlsStatus {
  https_ready: boolean;
  active_certificate: Certificate | null;
  tls_dir: string;
  settings: Record<string, string>;
}
