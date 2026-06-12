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
  tags: Tag[];
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
