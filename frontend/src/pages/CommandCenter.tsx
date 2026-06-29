import { ReactNode, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity, Boxes, Radar, ShieldCheck, Waypoints, Workflow, Zap } from 'lucide-react';
import { api } from '../api/client';
import {
  Asset,
  AutomationRule,
  BlocklistEntry,
  Feed,
  Integration,
  ThreatFeed,
} from '../api/types';
import { LiveEvent } from '../hooks/useEventStream';
import { useClock } from '../hooks/useClock';
import { useCountUp } from '../hooks/useCountUp';
import { formatCompact } from '../lib/format';
import ThreatFabricMap, { FabricSource } from '../components/ThreatFabricMap';
import '../theme/command.css';

/* --------------------------------------------------------------------------
   The Command Center is a full operations cockpit on the dark SOC surface: an
   animated deep-space backdrop, a hero header with a live mission clock and an
   overall posture readout, a strip of HUD posture tiles, and — the hero — the
   security "exposure fabric" map framed in a recessed 3D stage.
   -------------------------------------------------------------------------- */

function isFailed(status?: string | null): boolean {
  const v = (status ?? '').toLowerCase();
  return v.includes('err') || v.includes('fail') || v.includes('unreach');
}

/** A HUD posture tile with a counting-up value and a charging underline. */
function HudStat({
  icon,
  value,
  label,
  color,
}: {
  icon: ReactNode;
  value: number;
  label: string;
  color: string;
}) {
  const v = useCountUp(value);
  return (
    <div className="cc-stat" style={{ color }}>
      <div className="flex items-start justify-between gap-2">
        <span className="grid place-items-center w-8 h-8 rounded-lg" style={{ background: 'rgba(255,255,255,0.05)', color }}>
          {icon}
        </span>
        <span className="cc-dot cc-pulse mt-1" style={{ background: color, color }} />
      </div>
      <div className="cc-stat-value cc-glow mt-3 text-[26px]" style={{ color }}>
        {formatCompact(v)}
      </div>
      <div className="text-[10px] uppercase tracking-[0.16em] mt-1" style={{ color: 'var(--cc-muted)' }}>
        {label}
      </div>
      <span className="cc-stat-bar" />
    </div>
  );
}

export default function CommandCenter() {
  const now = useClock(1000);
  const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  const date = now.toLocaleDateString([], { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' });
  const hour = now.getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  // Security-fabric data sources feeding the exposure map.
  const { data: blocklist } = useQuery({
    queryKey: ['cc-blocklist'],
    queryFn: () => api.get<BlocklistEntry[]>('/api/v1/blocklist'),
    refetchInterval: 20000,
  });
  const { data: threatFeeds } = useQuery({
    queryKey: ['cc-threatfeeds'],
    queryFn: () => api.get<ThreatFeed[]>('/api/v1/rpz/threat-feeds'),
    refetchInterval: 15000,
  });
  const { data: feeds } = useQuery({
    queryKey: ['cc-feeds'],
    queryFn: () => api.get<Feed[]>('/api/v1/feeds'),
    refetchInterval: 20000,
  });
  const { data: events } = useQuery({
    queryKey: ['cc-events'],
    queryFn: () => api.get<LiveEvent[]>('/api/v1/events?limit=250'),
    refetchInterval: 8000,
  });
  const { data: assets } = useQuery({
    queryKey: ['cc-assets'],
    queryFn: () => api.get<Asset[]>('/api/v1/assets'),
    refetchInterval: 30000,
  });
  const { data: integrations } = useQuery({
    queryKey: ['cc-integrations'],
    queryFn: () => api.get<Integration[]>('/api/v1/integrations'),
    refetchInterval: 15000,
  });
  const { data: automation } = useQuery({
    queryKey: ['cc-automation'],
    queryFn: () => api.get<AutomationRule[]>('/api/v1/automation'),
    refetchInterval: 15000,
  });

  const tfList = useMemo(() => threatFeeds ?? [], [threatFeeds]);
  const feedList = useMemo(() => feeds ?? [], [feeds]);
  const assetList = useMemo(() => assets ?? [], [assets]);
  const intList = useMemo(() => integrations ?? [], [integrations]);
  const autoList = useMemo(() => automation ?? [], [automation]);

  const blockCount = blocklist?.length ?? 0;
  const tfIocs = tfList.reduce((sum, f) => sum + (f.entry_count ?? 0), 0);
  const feedEntries = feedList.reduce((sum, f) => sum + (f.entry_count ?? 0), 0);
  const indicatorsBlocked = blockCount + tfIocs + feedEntries;
  const sourcesOnline = intList.filter((i) => i.enabled && !isFailed(i.last_status)).length;
  const playbooksArmed = autoList.filter((a) => a.enabled).length;

  const sev = useMemo(() => {
    const evs = events ?? [];
    let error = 0;
    let warning = 0;
    for (const e of evs) {
      if (e.severity === 'error') error += 1;
      else if (e.severity === 'warning') warning += 1;
    }
    return { error, warning, total: evs.length };
  }, [events]);

  // Overall posture readout for the hero status pill.
  const posture =
    sev.error > 0
      ? { label: 'ELEVATED', color: 'var(--cc-red)' }
      : sev.warning > 0
        ? { label: 'GUARDED', color: 'var(--cc-amber)' }
        : { label: 'NOMINAL', color: 'var(--cc-green)' };

  // Left source nodes: intel/distribution feeds + the manual blocklist, ranked
  // by how many indicators each contributes, capped to 6.
  const fabricSources = useMemo<FabricSource[]>(() => {
    const tf = tfList.map((f) => ({
      id: `tf-${f.id}`,
      name: f.name,
      value: f.entry_count ?? 0,
      color: !f.enabled ? 'var(--cc-muted)' : isFailed(f.last_status) ? 'var(--cc-red)' : 'var(--cc-teal)',
    }));
    const df = feedList.map((f) => ({
      id: `df-${f.id}`,
      name: f.name,
      value: f.entry_count ?? 0,
      color: f.enabled ? 'var(--cc-cyan)' : 'var(--cc-muted)',
    }));
    const bl =
      blockCount > 0 ? [{ id: 'blocklist', name: 'Manual Blocklist', value: blockCount, color: 'var(--cc-violet)' }] : [];
    const all = [...tf, ...df, ...bl].sort((a, b) => b.value - a.value).slice(0, 6);
    return all.length ? all : [{ id: 'none', name: 'No intel sources', value: 0, color: 'var(--cc-muted)' }];
  }, [tfList, feedList, blockCount]);

  const fabricMetrics = [
    { id: 'ind', value: indicatorsBlocked, label: 'THREAT INDICATORS', color: 'var(--cc-cyan)' },
    { id: 'assets', value: assetList.length, label: 'PROTECTED ASSETS', color: 'var(--cc-teal)' },
    { id: 'events', value: sev.total, label: 'EVENTS ANALYSED', color: 'var(--cc-green)' },
  ];

  const activeBranch = {
    id: 'active',
    label: 'ACTIVE SIGNALS',
    total: sev.error + sev.warning,
    color: 'var(--cc-red)',
    cards: [
      { id: 'req', value: sev.error, label: 'Require Attention', color: 'var(--cc-red)' },
      { id: 'prog', value: sev.warning, label: 'In Progress', color: 'var(--cc-amber)' },
    ],
  };

  const resolvedBranch = {
    id: 'resolved',
    label: 'DEFENCES',
    total: sourcesOnline + playbooksArmed,
    color: 'var(--cc-teal)',
    cards: [
      { id: 'src', value: sourcesOnline, label: 'Sources Online', color: 'var(--cc-green)' },
      { id: 'pb', value: playbooksArmed, label: 'Playbooks Armed', color: 'var(--cc-teal)' },
    ],
  };

  const stats = [
    { icon: <Zap size={16} />, value: indicatorsBlocked, label: 'Threat Indicators', color: 'var(--cc-cyan)' },
    { icon: <Boxes size={16} />, value: assetList.length, label: 'Protected Assets', color: 'var(--cc-teal)' },
    { icon: <Activity size={16} />, value: sev.total, label: 'Events Analysed', color: 'var(--cc-green)' },
    { icon: <Radar size={16} />, value: sev.error + sev.warning, label: 'Active Signals', color: 'var(--cc-red)' },
    { icon: <ShieldCheck size={16} />, value: sourcesOnline, label: 'Sources Online', color: 'var(--cc-violet)' },
    { icon: <Workflow size={16} />, value: playbooksArmed, label: 'Playbooks Armed', color: 'var(--cc-amber)' },
  ];

  return (
    <div className="cc-root p-5 md:p-7 flex flex-col gap-6 min-h-full">
      {/* Animated backdrop layers */}
      <div className="cc-grid" aria-hidden />
      <div className="cc-stars" aria-hidden />
      <div className="cc-scan" aria-hidden />

      {/* Hero header --------------------------------------------------------- */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="cc-greeting text-[15px]">{greeting}, Operator</div>
          <h1 className="cc-title text-3xl md:text-[34px] leading-tight mt-0.5">Command Center</h1>
          <p className="text-[12px] mt-1.5 tracking-wide" style={{ color: 'var(--cc-muted)' }}>
            Live security exposure &amp; defence posture across the DDI control plane
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="font-mono text-2xl font-bold tabular-nums" style={{ color: 'var(--cc-text)' }}>
              {time}
            </div>
            <div className="text-[11px] tracking-wide" style={{ color: 'var(--cc-muted)' }}>
              {date}
            </div>
          </div>
          <div className="cc-status-pill" style={{ color: posture.color }}>
            <span className="cc-dot cc-pulse" style={{ background: posture.color, color: posture.color }} />
            <span className="font-semibold tracking-[0.18em] text-[11px]">{posture.label}</span>
          </div>
        </div>
      </header>

      {/* Posture stat strip -------------------------------------------------- */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
        {stats.map((s) => (
          <HudStat key={s.label} icon={s.icon} value={s.value} label={s.label} color={s.color} />
        ))}
      </div>

      {/* Exposure fabric map — the hero, in a recessed 3D stage -------------- */}
      <div className="cc-stage">
        <span className="cc-corner cc-corner--tl" />
        <span className="cc-corner cc-corner--tr" />
        <span className="cc-corner cc-corner--bl" />
        <span className="cc-corner cc-corner--br" />
        <header className="cc-panel-title cc-stage__bar">
          <Waypoints size={14} style={{ color: 'var(--cc-cyan)' }} />
          <span className="cc-tt">Exposure Fabric</span>
          <span
            className="ml-auto inline-flex items-center gap-1.5 text-[10px] tracking-[0.2em] uppercase"
            style={{ color: 'var(--cc-muted)' }}
          >
            <span className="cc-dot cc-pulse" style={{ background: 'var(--cc-green)', color: 'var(--cc-green)' }} /> live
          </span>
        </header>
        <div className="cc-stage__screen">
          <ThreatFabricMap sources={fabricSources} metrics={fabricMetrics} active={activeBranch} resolved={resolvedBranch} />
        </div>
      </div>
    </div>
  );
}
