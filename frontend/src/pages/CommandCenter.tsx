import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  Boxes,
  Cpu,
  Database,
  Globe,
  HardDrive,
  Network as NetworkIcon,
  Radio,
  Rss,
  Server,
  ShieldCheck,
  Signal,
  Zap,
} from 'lucide-react';
import { api } from '../api/client';
import { DashboardStats, SystemStatus } from '../api/types';
import Gauge from '../components/Gauge';
import { useClock } from '../hooks/useClock';
import { useEventStream } from '../hooks/useEventStream';
import { clockInZone, formatBytes, formatDuration } from '../lib/format';
import '../theme/command.css';

const SEV_COLOR: Record<string, string> = {
  error: 'var(--cc-red)',
  warning: 'var(--cc-amber)',
  info: 'var(--cc-cyan)',
  debug: 'var(--cc-muted)',
};

const ENGINE_COLOR: Record<string, string> = {
  success: 'var(--cc-green)',
  failed: 'var(--cc-red)',
  unreachable: 'var(--cc-amber)',
};

function StatTile({ icon, label, value, color }: { icon: JSX.Element; label: string; value: number | string; color: string }) {
  return (
    <div className="cc-stat">
      <div className="flex items-center justify-between">
        <span style={{ color }}>{icon}</span>
        <span className="text-[10px] tracking-[0.2em] uppercase" style={{ color: 'var(--cc-muted)' }}>{label}</span>
      </div>
      <div className="cc-stat-value text-3xl mt-3 cc-glow" style={{ color }}>{value}</div>
    </div>
  );
}

export default function CommandCenter() {
  const now = useClock(1000);
  const { data: stats } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get<DashboardStats>('/api/v1/dashboard/stats'),
    refetchInterval: 5000,
  });
  const { data: status } = useQuery({
    queryKey: ['system-status'],
    queryFn: () => api.get<SystemStatus>('/api/v1/system/status'),
    refetchInterval: 3000,
  });
  const liveEvents = useEventStream(40);

  const counts = stats?.counts ?? {};
  const res = status?.resources;
  const tz = status?.timezone ?? 'UTC';
  const clock = useMemo(() => clockInZone(tz, now), [tz, now]);

  const tiles = [
    { icon: <NetworkIcon size={18} />, label: 'Networks', value: counts.networks ?? '—', color: 'var(--cc-cyan)' },
    { icon: <Activity size={18} />, label: 'IP Addrs', value: counts.ip_addresses ?? '—', color: 'var(--cc-green)' },
    { icon: <Globe size={18} />, label: 'DNS Zones', value: counts.zones ?? '—', color: 'var(--cc-violet)' },
    { icon: <Globe size={18} />, label: 'Records', value: counts.records ?? '—', color: 'var(--cc-cyan)' },
    { icon: <Server size={18} />, label: 'Scopes', value: counts.dhcp_subnets ?? '—', color: 'var(--cc-amber)' },
    { icon: <Boxes size={18} />, label: 'Hosts', value: counts.hosts ?? '—', color: 'var(--cc-green)' },
    { icon: <Rss size={18} />, label: 'Feeds', value: counts.feeds ?? '—', color: 'var(--cc-violet)' },
  ];

  const topNetworks = stats?.top_networks ?? [];
  const loadPerCore =
    res?.load_average && res.cpu_count ? (res.load_average[0] / res.cpu_count) * 100 : null;

  return (
    <div className="cc-root p-5 md:p-6 space-y-5">
      {/* Hero ------------------------------------------------------------ */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[11px] tracking-[0.3em] uppercase" style={{ color: 'var(--cc-muted)' }}>
            <Signal size={13} className="cc-pulse" style={{ color: 'var(--cc-green)' }} /> M-Eyes · DDI Control Plane
          </div>
          <h1 className="cc-title text-4xl md:text-5xl mt-1">COMMAND CENTER</h1>
          <div className="flex items-center gap-3 mt-2 text-xs" style={{ color: 'var(--cc-muted)' }}>
            <span className="inline-flex items-center gap-1.5">
              <span className="cc-dot cc-pulse" style={{ background: 'var(--cc-green)', color: 'var(--cc-green)' }} />
              All systems online
            </span>
            <span>·</span>
            <span>v{status?.version ?? '…'}</span>
            <span>·</span>
            <span className="font-mono">config v{stats?.config_version ?? status?.config_version ?? 0}</span>
          </div>
        </div>

        {/* Live clock */}
        <div className="cc-panel px-5 py-3 text-right">
          <div className="text-4xl md:text-5xl font-bold tracking-widest font-mono cc-glow" style={{ color: 'var(--cc-cyan)' }}>
            {clock.time}
          </div>
          <div className="text-[11px] tracking-wider mt-1" style={{ color: 'var(--cc-muted)' }}>
            {clock.date} · {clock.zone} {status?.utc_offset ? `(UTC${status.utc_offset.replace(/(\d{2})(\d{2})/, '$1:$2')})` : ''}
          </div>
        </div>
      </div>

      {/* Stat tiles ------------------------------------------------------ */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3">
        {tiles.map((t) => (
          <StatTile key={t.label} {...t} />
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Resource telemetry ------------------------------------------- */}
        <div className="cc-panel p-4 xl:col-span-2">
          <div className="cc-panel-title mb-4">
            <Cpu size={14} style={{ color: 'var(--cc-cyan)' }} /> Resource Telemetry
          </div>
          <div className="grid grid-cols-3 gap-3 place-items-center">
            <Gauge
              percent={res?.cpu_percent ?? null}
              label="CPU"
              sub={`${res?.cpu_count ?? '—'} cores`}
            />
            <Gauge
              percent={res?.memory?.percent ?? null}
              label="Memory"
              sub={res?.memory ? `${formatBytes(res.memory.used)} / ${formatBytes(res.memory.total)}` : undefined}
            />
            <Gauge
              percent={res?.disk?.percent ?? null}
              label="Disk"
              sub={res?.disk ? `${formatBytes(res.disk.used)} / ${formatBytes(res.disk.total)}` : undefined}
            />
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 text-center">
            <Metric icon={<Zap size={14} />} label="Load (1m)" value={res?.load_average ? res.load_average[0].toFixed(2) : '—'}
                    accent={loadPerCore !== null && loadPerCore > 100 ? 'var(--cc-amber)' : 'var(--cc-green)'} />
            <Metric icon={<HardDrive size={14} />} label="Mem free" value={formatBytes(res?.memory?.available)} accent="var(--cc-cyan)" />
            <Metric icon={<Database size={14} />} label="Disk free" value={formatBytes(res?.disk?.free)} accent="var(--cc-violet)" />
            <Metric icon={<Activity size={14} />} label="Uptime" value={formatDuration(res?.host_uptime_seconds ?? res?.process_uptime_seconds)} accent="var(--cc-green)" />
          </div>
        </div>

        {/* Live feed ---------------------------------------------------- */}
        <div className="cc-panel p-4 flex flex-col">
          <div className="cc-panel-title mb-3">
            <Radio size={14} style={{ color: 'var(--cc-green)' }} /> Live Event Stream
            <span className="cc-dot cc-pulse ml-auto" style={{ background: 'var(--cc-green)', color: 'var(--cc-green)' }} />
          </div>
          <div className="cc-feed cc-scroll space-y-0.5 overflow-y-auto" style={{ maxHeight: 280 }}>
            {liveEvents.length === 0 && (
              <div style={{ color: 'var(--cc-muted)' }}>// awaiting telemetry…</div>
            )}
            {liveEvents.map((e) => (
              <div key={e.id} className="cc-feed-row">
                <span className="cc-dot mt-1 shrink-0" style={{ background: SEV_COLOR[e.severity] ?? 'var(--cc-cyan)', color: SEV_COLOR[e.severity] ?? 'var(--cc-cyan)' }} />
                <span className="shrink-0" style={{ color: 'var(--cc-muted)' }}>
                  {new Date(e.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <span style={{ color: 'var(--cc-text)' }}>{e.message}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Network utilisation ------------------------------------------ */}
        <div className="cc-panel p-4 xl:col-span-2">
          <div className="cc-panel-title mb-4">
            <NetworkIcon size={14} style={{ color: 'var(--cc-cyan)' }} /> Network Utilisation
          </div>
          <div className="space-y-3">
            {topNetworks.length === 0 && (
              <div className="text-xs" style={{ color: 'var(--cc-muted)' }}>No subnets yet</div>
            )}
            {topNetworks.map((n) => {
              const color = n.percent > 90 ? 'var(--cc-red)' : n.percent > 70 ? 'var(--cc-amber)' : 'var(--cc-green)';
              return (
                <div key={n.id}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-mono" style={{ color: 'var(--cc-text)' }}>{n.cidr}</span>
                    <span style={{ color }}>{n.percent}% · {n.used}/{n.total}</span>
                  </div>
                  <div className="cc-track">
                    <span style={{ width: `${Math.min(100, n.percent)}%`, background: color, boxShadow: `0 0 10px ${color}` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Engine nodes ------------------------------------------------- */}
        <div className="cc-panel p-4">
          <div className="cc-panel-title mb-4">
            <ShieldCheck size={14} style={{ color: 'var(--cc-violet)' }} /> Engine Status
          </div>
          <div className="space-y-3">
            {(['bind', 'kea'] as const).map((target) => {
              const engine = status?.engines?.[target] ?? stats?.engines?.[target] ?? null;
              const st = engine?.status ?? null;
              const color = st ? ENGINE_COLOR[st] ?? 'var(--cc-muted)' : 'var(--cc-muted)';
              return (
                <div key={target} className="flex items-center gap-3 p-3 rounded-lg" style={{ border: '1px solid var(--cc-line)', background: 'rgba(8,15,30,0.5)' }}>
                  <span className="cc-dot cc-pulse" style={{ background: color, color }} />
                  <div className="flex-1">
                    <div className="text-sm font-semibold tracking-wide" style={{ color: 'var(--cc-text)' }}>
                      {target === 'bind' ? 'DNS · BIND9' : 'DHCP · Kea'}
                    </div>
                    <div className="text-[11px]" style={{ color: 'var(--cc-muted)' }}>
                      {engine ? `${st} · deployed v${engine.config_version}` : 'never deployed'}
                    </div>
                  </div>
                  <span className="text-[11px] uppercase tracking-wider font-mono" style={{ color }}>
                    {st ?? 'idle'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function Metric({ icon, label, value, accent }: { icon: JSX.Element; label: string; value: string; accent: string }) {
  return (
    <div className="rounded-lg py-2 px-2" style={{ border: '1px solid var(--cc-line)', background: 'rgba(8,15,30,0.45)' }}>
      <div className="flex items-center justify-center gap-1.5 text-[10px] uppercase tracking-wider" style={{ color: 'var(--cc-muted)' }}>
        <span style={{ color: accent }}>{icon}</span> {label}
      </div>
      <div className="text-sm font-semibold font-mono mt-1" style={{ color: 'var(--cc-text)' }}>{value}</div>
    </div>
  );
}
