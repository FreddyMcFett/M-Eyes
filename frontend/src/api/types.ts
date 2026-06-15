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
  allow_query: string;
  allow_transfer: string;
  allow_update: string;
  also_notify: string;
  forward_first: boolean;
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
  valid_lifetime: number | null;
  max_valid_lifetime: number | null;
  renew_timer: number | null;
  rebind_timer: number | null;
  next_server: string | null;
  boot_file_name: string | null;
  client_class: string | null;
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

export interface ResourceMetric {
  total: number;
  used: number;
  available?: number;
  free?: number;
  percent: number;
}

export interface SystemResources {
  cpu_percent: number | null;
  cpu_count: number;
  load_average: number[] | null;
  memory: ResourceMetric | null;
  disk: ResourceMetric | null;
  host_uptime_seconds: number | null;
  process_uptime_seconds: number | null;
}

export interface SystemStatus {
  name: string;
  version: string;
  config_version: number;
  timezone: string;
  server_time: string;
  utc_offset: string;
  hostname: string;
  platform: string;
  python_version: string;
  in_app_update: boolean;
  resources: SystemResources;
  engines: Record<string, { status: string; ts: string; message: string; config_version: number } | null>;
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
  in_app_update?: boolean;
}

export interface UpdateProgress {
  phase: 'idle' | 'requested' | 'pulling' | 'recreating' | 'done' | 'error';
  message: string;
  target_version: string | null;
  current_version?: string;
  in_app_update?: boolean;
  log_tail?: string;
  processed_id?: string | null;
  returncode?: number | null;
  started_at?: string | null;
  updated_at?: string | null;
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

export interface AssetInterface {
  id?: number;
  name: string;
  mac: string;
  ip: string;
  hostname: string;
  ip_id: number | null;
}

export interface Asset {
  id: number;
  name: string;
  asset_type: string;
  status: string;
  criticality: string;
  owner: string;
  location: string;
  department: string;
  vendor: string;
  model: string;
  serial_number: string;
  operating_system: string;
  description: string;
  source: string;
  external_id: string;
  last_seen: string | null;
  tags: Tag[];
  interfaces: AssetInterface[];
  created_at: string;
  updated_at: string;
}

export interface AssetMeta {
  types: string[];
  statuses: string[];
  criticality: string[];
}

export interface ConnectorField {
  key: string;
  label: string;
  type: string;
  required: boolean;
  help: string;
  placeholder: string;
  default: string;
  advanced: boolean;
}

export interface ConnectorDescriptor {
  kind: string;
  label: string;
  category: string;
  description: string;
  capabilities: string[];
  uses_base_url: boolean;
  base_url_label: string;
  base_url_placeholder: string;
  uses_username: boolean;
  username_label: string;
  uses_secret: boolean;
  secret_label: string;
  fields: ConnectorField[];
}

export interface Integration {
  id: number;
  name: string;
  kind: string;
  enabled: boolean;
  base_url: string;
  username: string;
  verify_tls: boolean;
  settings: Record<string, string>;
  secret_set: boolean;
  last_sync_at: string | null;
  last_status: string;
  last_message: string;
  created_at: string;
  updated_at: string;
}

export interface AutomationRule {
  id: number;
  name: string;
  kind: string;
  enabled: boolean;
  interval_seconds: number;
  config: Record<string, unknown>;
  last_run_at: string | null;
  next_run_at: string | null;
  last_status: string;
  last_message: string;
  run_count: number;
  created_at: string;
  updated_at: string;
}

export interface SsoConfig {
  enabled: boolean;
  button_label: string;
  idp_entity_id: string;
  idp_sso_url: string;
  idp_slo_url: string;
  idp_x509_cert: string;
  sp_entity_id: string;
  base_url: string;
  attr_username: string;
  attr_email: string;
  attr_display_name: string;
  attr_groups: string;
  role_mappings: Record<string, string>;
  default_role: string;
  allow_jit_provisioning: boolean;
  name_id_format: string;
  sign_authn_requests: boolean;
  want_assertions_signed: boolean;
  want_response_signed: boolean;
  force_authn: boolean;
  allowed_clock_skew_seconds: number;
  signature_algorithm: string;
  sp_metadata_url: string;
  acs_url: string;
  sp_entity_id_effective: string;
  sp_signing_configured: boolean;
}

export interface SsoStatus {
  enabled: boolean;
  button_label: string;
  login_url: string;
}

export interface ManagedUser {
  id: number;
  username: string;
  role: string;
  email: string;
  display_name: string;
  auth_source: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}
