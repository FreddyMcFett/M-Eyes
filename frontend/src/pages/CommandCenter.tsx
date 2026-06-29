import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Waypoints } from 'lucide-react';
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
import ThreatFabricMap, { FabricSource } from '../components/ThreatFabricMap';
import '../theme/command.css';

/* --------------------------------------------------------------------------
   The Command Center is intentionally minimal: a single centerpiece — the
   security "exposure fabric" map — on the dark SOC surface. Everything else
   (greeting, clock, metric strip, posture ring, panels, footer) lives on the
   operational /dashboard, so this view stays a calm, focused exposure board.
   -------------------------------------------------------------------------- */

function isFailed(status?: string | null): boolean {
  const v = (status ?? '').toLowerCase();
  return v.includes('err') || v.includes('fail') || v.includes('unreach');
}

export default function CommandCenter() {
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

  return (
    <div className="cc-root cc-root--minimal p-5 md:p-6">
      {/* Exposure fabric map — the sole centerpiece, framed in a recessed 3D stage. */}
      <div className="cc-stage">
        <span className="cc-corner cc-corner--tl" />
        <span className="cc-corner cc-corner--tr" />
        <span className="cc-corner cc-corner--bl" />
        <span className="cc-corner cc-corner--br" />
        <header className="cc-panel-title cc-stage__bar">
          <Waypoints size={14} style={{ color: 'var(--cc-cyan)' }} />
          <span className="cc-tt">Exposure Fabric</span>
          <span className="ml-auto inline-flex items-center gap-1.5 text-[10px] tracking-[0.2em] uppercase" style={{ color: 'var(--cc-muted)' }}>
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
