import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  AlertTriangle,
  Boxes,
  Bug,
  Crosshair,
  Flame,
  Plug,
  Radar,
  Radio,
  ScanLine,
  Server,
  Shield,
  ShieldAlert,
  ShieldOff,
  Signal,
  Waypoints,
  Workflow,
} from 'lucide-react';
import { api } from '../api/client';
import {
  Asset,
  AutomationRule,
  BlocklistEntry,
  Feed,
  Integration,
  RpzRule,
  ThreatFeed,
} from '../api/types';
import { useClock } from '../hooks/useClock';
import { LiveEvent, useEventStream } from '../hooks/useEventStream';
import '../theme/command.css';

/* --------------------------------------------------------------------------
   The Command Center is a Cortex-style Security Operations console. It is
   deliberately NOT a re-skin of /dashboard: instead of infra counts and host
   resource gauges, it surfaces the security fabric — threat indicators blocked,
   the DNS firewall, threat-intel feeds, event analytics, data-source health and
   automation playbooks — rendered as an animated HUD.
   -------------------------------------------------------------------------- */

const SEV_COLOR: Record<string, string> = {
  error: 'var(--cc-red)',
  warning: 'var(--cc-amber)',
  info: 'var(--cc-cyan)',
  debug: 'var(--cc-muted)',
};

const SEV_LABEL: Record<string, string> = {
  error: 'CRITICAL',
  warning: 'WARNING',
  info: 'INFO',
  debug: 'TRACE',
};

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

/** Animates a number from its previous value to `target` with an ease-out cubic. */
function useCountUp(target: number, ms = 1100): number {
  const [val, setVal] = useState(0);
  const fromRef = useRef(0);
  const rafRef = useRef<number>();

  useEffect(() => {
    if (prefersReducedMotion()) {
      fromRef.current = target;
      setVal(target);
      return;
    }
    const from = fromRef.current;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(from + (target - from) * eased);
      if (p < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = target;
      }
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [target, ms]);

  return val;
}

function Counter({ value, className, style }: { value: number; className?: string; style?: React.CSSProperties }) {
  const v = useCountUp(value);
  return (
    <span className={className} style={style}>
      {Math.round(v).toLocaleString()}
    </span>
  );
}

/** Compact "3m ago" style relative timestamp. */
function relTime(iso?: string | null): string {
  if (!iso) return 'never';
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return '—';
  const s = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}

function isHealthy(status?: string | null): boolean {
  const v = (status ?? '').toLowerCase();
  return v.includes('ok') || v.includes('success') || v.includes('synced') || v.includes('connect') || v === 'active';
}
function isFailed(status?: string | null): boolean {
  const v = (status ?? '').toLowerCase();
  return v.includes('err') || v.includes('fail') || v.includes('unreach');
}

/* --- Layout primitives ---------------------------------------------------- */

function Panel({
  icon,
  title,
  right,
  className = '',
  children,
}: {
  icon: JSX.Element;
  title: string;
  right?: JSX.Element;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={`cc-panel p-4 ${className}`}>
      <span className="cc-corner cc-corner--tl" />
      <span className="cc-corner cc-corner--tr" />
      <span className="cc-corner cc-corner--bl" />
      <span className="cc-corner cc-corner--br" />
      <header className="cc-panel-title mb-4">
        {icon}
        <span className="cc-tt">{title}</span>
        {right && <span className="ml-auto flex items-center gap-2">{right}</span>}
      </header>
      {children}
    </section>
  );
}

function StatTile({
  icon,
  label,
  value,
  sub,
  color,
}: {
  icon: JSX.Element;
  label: string;
  value: number;
  sub: string;
  color: string;
}) {
  return (
    <div className="cc-stat" style={{ color }}>
      <span className="cc-corner cc-corner--tl" />
      <span className="cc-corner cc-corner--br" />
      <div className="flex items-center justify-between">
        <span>{icon}</span>
        <span className="text-[10px] tracking-[0.2em] uppercase" style={{ color: 'var(--cc-muted)' }}>
          {label}
        </span>
      </div>
      <Counter value={value} className="cc-stat-value text-3xl mt-3 cc-glow block" />
      <div className="text-[10px] mt-1.5 tracking-wide" style={{ color: 'var(--cc-muted)' }}>
        {sub}
      </div>
      <span className="cc-stat-bar" />
    </div>
  );
}

function PostureRing({ score, color, label }: { score: number; color: string; label: string }) {
  const v = useCountUp(score, 1300);
  const pct = Math.round(v);
  return (
    <div
      className="cc-ring"
      style={{ width: 212, height: 212, ['--cc-pct' as string]: pct, ['--cc-ring' as string]: color } as React.CSSProperties}
    >
      <div className="cc-ring__ticks" />
      <div className="cc-ring__track" />
      <div className="cc-ring__radar" />
      <div className="cc-ring__core">
        <div className="text-5xl font-extrabold cc-glow leading-none" style={{ color }}>
          {pct}
        </div>
        <div className="text-[10px] tracking-[0.35em] uppercase mt-1" style={{ color: 'var(--cc-muted)' }}>
          Posture
        </div>
        <div className="text-[13px] font-bold tracking-[0.22em] mt-1" style={{ color }}>
          {label}
        </div>
      </div>
    </div>
  );
}

function MiniReadout({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-lg py-2 px-2 text-center" style={{ border: '1px solid var(--cc-line)', background: 'rgba(8,15,30,0.45)' }}>
      <div className="text-sm font-bold font-mono" style={{ color }}>
        {value}
      </div>
      <div className="text-[9px] uppercase tracking-[0.16em] mt-0.5" style={{ color: 'var(--cc-muted)' }}>
        {label}
      </div>
    </div>
  );
}

/* --- Page ----------------------------------------------------------------- */

export default function CommandCenter() {
  const now = useClock(1000);

  // Security-fabric data sources — distinct from the operational dashboard.
  const { data: blocklist } = useQuery({
    queryKey: ['cc-blocklist'],
    queryFn: () => api.get<BlocklistEntry[]>('/api/v1/blocklist'),
    refetchInterval: 20000,
  });
  const { data: rpzRules } = useQuery({
    queryKey: ['cc-rpz'],
    queryFn: () => api.get<RpzRule[]>('/api/v1/rpz/rules'),
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
  const { data: info } = useQuery({
    queryKey: ['cc-info'],
    queryFn: () => api.get<{ version: string; config_version: number }>('/api/v1/system/info'),
    refetchInterval: 10000,
  });
  const liveEvents = useEventStream(28);

  const clock = useMemo(() => {
    const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const date = now.toLocaleDateString([], { weekday: 'short', year: 'numeric', month: 'short', day: '2-digit' });
    let zone = 'LOCAL';
    try {
      zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch {
      /* keep LOCAL */
    }
    return { time, date, zone };
  }, [now]);

  /* --- Derived security metrics ----------------------------------------- */
  // Memoised so their identity stays stable for the analytics useMemo deps.
  const rpzList = useMemo(() => rpzRules ?? [], [rpzRules]);
  const tfList = useMemo(() => threatFeeds ?? [], [threatFeeds]);
  const feedList = useMemo(() => feeds ?? [], [feeds]);
  const assetList = useMemo(() => assets ?? [], [assets]);
  const intList = useMemo(() => integrations ?? [], [integrations]);
  const autoList = useMemo(() => automation ?? [], [automation]);

  const blockCount = blocklist?.length ?? 0;
  const rpzActive = rpzList.filter((r) => r.enabled).length;
  const tfIocs = tfList.reduce((sum, f) => sum + (f.entry_count ?? 0), 0);
  const feedEntries = feedList.reduce((sum, f) => sum + (f.entry_count ?? 0), 0);
  const indicatorsBlocked = blockCount + tfIocs + feedEntries;

  const criticalAssets = assetList.filter((a) => a.criticality === 'critical' || a.criticality === 'high').length;
  const sourcesOnline = intList.filter((i) => i.enabled && !isFailed(i.last_status)).length;
  const playbooksArmed = autoList.filter((a) => a.enabled).length;

  // Composite defense-posture score (0–100): protection coverage + feed/source
  // operability + automation readiness.
  const posture = useMemo(() => {
    const coverage = ((blockCount > 0 ? 1 : 0) + (rpzActive > 0 ? 1 : 0) + (tfList.length > 0 ? 1 : 0)) / 3;
    const feedHealth = tfList.length ? tfList.filter((f) => f.enabled && !isFailed(f.last_status)).length / tfList.length : 0;
    const sourceHealth = intList.length ? sourcesOnline / intList.length : 0;
    const autoHealth = autoList.length ? playbooksArmed / autoList.length : 0;
    const score = Math.round(100 * (0.34 * coverage + 0.24 * feedHealth + 0.24 * sourceHealth + 0.18 * autoHealth));
    const { color, label } =
      score >= 80
        ? { color: 'var(--cc-green)', label: 'FORTIFIED' }
        : score >= 60
          ? { color: 'var(--cc-teal)', label: 'GUARDED' }
          : score >= 40
            ? { color: 'var(--cc-amber)', label: 'ELEVATED' }
            : { color: 'var(--cc-red)', label: 'EXPOSED' };
    return { score, color, label, coverage, feedHealth, sourceHealth };
  }, [blockCount, rpzActive, tfList, intList, sourcesOnline, autoList, playbooksArmed]);

  // Severity triage + attack-vector (category) breakdown from the event log.
  const sev = useMemo(() => {
    const evs = events ?? [];
    let error = 0;
    let warning = 0;
    let info2 = 0;
    for (const e of evs) {
      if (e.severity === 'error') error += 1;
      else if (e.severity === 'warning') warning += 1;
      else info2 += 1;
    }
    return { error, warning, info: info2, total: evs.length };
  }, [events]);

  const vectors = useMemo(() => {
    const map = new Map<string, number>();
    for (const e of events ?? []) map.set(e.category, (map.get(e.category) ?? 0) + 1);
    const sorted = [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
    const max = Math.max(1, ...sorted.map(([, c]) => c));
    return { sorted, max };
  }, [events]);

  // Threat-activity timeline: events bucketed across their time span.
  const timeline = useMemo(() => {
    const N = 34;
    const empty = { error: 0, warning: 0, info: 0, total: 0 };
    const bins = Array.from({ length: N }, () => ({ ...empty }));
    const evs = events ?? [];
    const times = evs.map((e) => new Date(e.ts).getTime()).filter(Number.isFinite);
    if (times.length === 0) return { bins, max: 0, start: null as number | null, end: null as number | null };
    const end = Date.now();
    const start = Math.min(...times);
    const width = Math.max(end - start, N * 1000) / N;
    for (const e of evs) {
      const t = new Date(e.ts).getTime();
      if (!Number.isFinite(t)) continue;
      let idx = Math.floor((t - start) / width);
      idx = Math.max(0, Math.min(N - 1, idx));
      const k = e.severity === 'error' ? 'error' : e.severity === 'warning' ? 'warning' : 'info';
      bins[idx][k] += 1;
      bins[idx].total += 1;
    }
    return { bins, max: Math.max(1, ...bins.map((b) => b.total)), start, end };
  }, [events]);

  // Unified threat-intelligence list (RPZ threat feeds + distribution feeds).
  const intel = useMemo(() => {
    const tf = tfList.map((f) => ({
      key: `tf-${f.id}`,
      name: f.name,
      entries: f.entry_count ?? 0,
      color: !f.enabled ? 'var(--cc-muted)' : isFailed(f.last_status) ? 'var(--cc-red)' : isHealthy(f.last_status) ? 'var(--cc-green)' : 'var(--cc-amber)',
      sub: `${f.action} · ${relTime(f.last_synced)}`,
      kind: 'INTEL',
    }));
    const df = feedList.map((f) => ({
      key: `df-${f.id}`,
      name: f.name,
      entries: f.entry_count ?? 0,
      color: f.enabled ? 'var(--cc-cyan)' : 'var(--cc-muted)',
      sub: `${f.kind} distribution feed`,
      kind: 'FEED',
    }));
    const all = [...tf, ...df].sort((a, b) => b.entries - a.entries);
    return { all, max: Math.max(1, ...all.map((a) => a.entries)) };
  }, [tfList, feedList]);

  const tiles = [
    { icon: <ShieldAlert size={18} />, label: 'Indicators Blocked', value: indicatorsBlocked, sub: `${blockCount} blocklist · ${tfIocs} IOC`, color: 'var(--cc-cyan)' },
    { icon: <ShieldOff size={18} />, label: 'DNS Firewall', value: rpzList.length, sub: `${rpzActive} active rules`, color: 'var(--cc-violet)' },
    { icon: <Radar size={18} />, label: 'Intel Feeds', value: tfList.length + feedList.length, sub: `${tfIocs.toLocaleString()} IOCs tracked`, color: 'var(--cc-teal)' },
    { icon: <Boxes size={18} />, label: 'Protected Assets', value: assetList.length, sub: `${criticalAssets} critical`, color: 'var(--cc-green)' },
    { icon: <Plug size={18} />, label: 'Data Sources', value: intList.length, sub: `${sourcesOnline} online`, color: 'var(--cc-amber)' },
    { icon: <Workflow size={18} />, label: 'Playbooks', value: autoList.length, sub: `${playbooksArmed} armed`, color: 'var(--cc-pink)' },
  ];

  const fmtClock = (ms: number | null) => (ms ? new Date(ms).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—');

  return (
    <div className="cc-root p-5 md:p-6 space-y-5">
      {/* Hero ------------------------------------------------------------ */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="cc-kicker flex items-center gap-2 text-[11px] tracking-[0.3em] uppercase" style={{ color: 'var(--cc-muted)' }}>
            <Signal size={13} className="cc-pulse" style={{ color: 'var(--cc-green)' }} /> M-Eyes · Security Operations
          </div>
          <h1 className="cc-title text-4xl md:text-5xl mt-1">THREAT DEFENSE COMMAND</h1>
          <div className="flex items-center gap-3 mt-2 text-xs flex-wrap" style={{ color: 'var(--cc-muted)' }}>
            <span className="inline-flex items-center gap-1.5">
              <span className="cc-dot cc-ping cc-pulse" style={{ background: posture.color, color: posture.color }} />
              Defense posture <span style={{ color: posture.color, fontWeight: 600 }}>{posture.label}</span>
            </span>
            <span>·</span>
            <span className="inline-flex items-center gap-1.5">
              <Crosshair size={12} /> <Counter value={indicatorsBlocked} className="font-mono" style={{ color: 'var(--cc-text)' }} /> indicators enforced
            </span>
            <span>·</span>
            <span className="font-mono">v{info?.version ?? '…'} · cfg v{info?.config_version ?? 0}</span>
          </div>
        </div>

        {/* Live clock */}
        <div className="cc-panel px-5 py-3 text-right">
          <span className="cc-corner cc-corner--tl" />
          <span className="cc-corner cc-corner--br" />
          <div className="text-4xl md:text-5xl font-bold tracking-widest font-mono cc-glow" style={{ color: 'var(--cc-cyan)' }}>
            {clock.time}
          </div>
          <div className="text-[11px] tracking-wider mt-1" style={{ color: 'var(--cc-muted)' }}>
            {clock.date} · {clock.zone}
          </div>
        </div>
      </div>

      {/* Stat strip ------------------------------------------------------ */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {tiles.map((t) => (
          <StatTile key={t.label} {...t} />
        ))}
      </div>

      {/* Posture + threat-activity timeline ------------------------------ */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <Panel icon={<Shield size={14} style={{ color: 'var(--cc-teal)' }} />} title="Defense Posture">
          <div className="flex flex-col items-center">
            <PostureRing score={posture.score} color={posture.color} label={posture.label} />
            <div className="grid grid-cols-3 gap-2 w-full mt-5">
              <MiniReadout label="Coverage" value={`${Math.round(posture.coverage * 100)}%`} color="var(--cc-cyan)" />
              <MiniReadout label="Feeds OK" value={`${Math.round(posture.feedHealth * 100)}%`} color="var(--cc-green)" />
              <MiniReadout label="Sources" value={`${sourcesOnline}/${intList.length}`} color="var(--cc-amber)" />
            </div>
          </div>
        </Panel>

        <Panel
          icon={<Activity size={14} style={{ color: 'var(--cc-cyan)' }} />}
          title="Threat Activity Timeline"
          right={
            <span className="text-[10px] tracking-wider font-mono" style={{ color: 'var(--cc-muted)' }}>
              {sev.total} events
            </span>
          }
          className="xl:col-span-2"
        >
          <div className="cc-bars">
            {timeline.bins.map((b, i) => (
              <div className="cc-bar" key={i} title={`${b.total} event${b.total === 1 ? '' : 's'}`}>
                {b.total === 0 ? (
                  <span className="cc-bar__idle" />
                ) : (
                  <>
                    <span className="cc-bar__seg" style={{ height: `${(b.error / timeline.max) * 100}%`, background: 'var(--cc-red)', color: 'var(--cc-red)' }} />
                    <span className="cc-bar__seg" style={{ height: `${(b.warning / timeline.max) * 100}%`, background: 'var(--cc-amber)', color: 'var(--cc-amber)' }} />
                    <span className="cc-bar__seg" style={{ height: `${(b.info / timeline.max) * 100}%`, background: 'var(--cc-cyan)', color: 'var(--cc-cyan)' }} />
                  </>
                )}
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between mt-3 text-[10px]" style={{ color: 'var(--cc-muted)' }}>
            <span className="font-mono">{fmtClock(timeline.start)}</span>
            <div className="flex items-center gap-3">
              {(['error', 'warning', 'info'] as const).map((k) => (
                <span key={k} className="inline-flex items-center gap-1.5">
                  <span className="cc-dot" style={{ background: SEV_COLOR[k], color: SEV_COLOR[k] }} /> {SEV_LABEL[k]}
                </span>
              ))}
            </div>
            <span className="font-mono">now</span>
          </div>
        </Panel>
      </div>

      {/* Intel · data sources · triage ----------------------------------- */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <Panel icon={<Radar size={14} style={{ color: 'var(--cc-teal)' }} />} title="Threat Intelligence">
          <div className="space-y-3 cc-scroll overflow-y-auto" style={{ maxHeight: 256 }}>
            {intel.all.length === 0 && (
              <div className="text-xs" style={{ color: 'var(--cc-muted)' }}>
                No intel feeds configured yet
              </div>
            )}
            {intel.all.map((f) => (
              <div key={f.key}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="inline-flex items-center gap-2 min-w-0">
                    <span className="cc-dot cc-pulse shrink-0" style={{ background: f.color, color: f.color }} />
                    <span className="truncate" style={{ color: 'var(--cc-text)' }}>
                      {f.name}
                    </span>
                  </span>
                  <span className="font-mono shrink-0" style={{ color: f.color }}>
                    {f.entries.toLocaleString()}
                  </span>
                </div>
                <div className="cc-track">
                  <span style={{ width: `${(f.entries / intel.max) * 100}%`, background: f.color, boxShadow: `0 0 10px ${f.color}` }} />
                </div>
                <div className="text-[10px] mt-0.5" style={{ color: 'var(--cc-muted)' }}>
                  {f.kind} · {f.sub}
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel
          icon={<Waypoints size={14} style={{ color: 'var(--cc-cyan)' }} />}
          title="Security Fabric"
          right={<span className="cc-dot cc-pulse" style={{ background: 'var(--cc-green)', color: 'var(--cc-green)' }} />}
        >
          <div className="cc-bus">
            <div className="cc-node flex items-center gap-3 py-2">
              <span className="cc-dot cc-pulse" style={{ background: 'var(--cc-green)', color: 'var(--cc-green)' }} />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold" style={{ color: 'var(--cc-text)' }}>
                  M-Eyes Core
                </div>
                <div className="text-[11px]" style={{ color: 'var(--cc-muted)' }}>
                  DDI control plane · cfg v{info?.config_version ?? 0}
                </div>
              </div>
              <span className="text-[10px] uppercase tracking-wider font-mono" style={{ color: 'var(--cc-green)' }}>
                online
              </span>
            </div>
            {intList.length === 0 && (
              <div className="cc-node text-xs py-2" style={{ color: 'var(--cc-muted)' }}>
                No connectors linked — add in Integrations
              </div>
            )}
            {intList.map((i) => {
              const color = !i.enabled ? 'var(--cc-muted)' : isFailed(i.last_status) ? 'var(--cc-red)' : isHealthy(i.last_status) ? 'var(--cc-green)' : 'var(--cc-amber)';
              const statusText = !i.enabled ? 'paused' : isFailed(i.last_status) ? 'fault' : isHealthy(i.last_status) ? 'online' : 'idle';
              return (
                <div key={i.id} className="cc-node flex items-center gap-3 py-2">
                  <span className="cc-dot cc-pulse" style={{ background: color, color }} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold truncate" style={{ color: 'var(--cc-text)' }}>
                      {i.name}
                    </div>
                    <div className="text-[11px] truncate" style={{ color: 'var(--cc-muted)' }}>
                      {i.kind} · synced {relTime(i.last_sync_at)}
                    </div>
                  </div>
                  <span className="text-[10px] uppercase tracking-wider font-mono shrink-0" style={{ color }}>
                    {statusText}
                  </span>
                </div>
              );
            })}
          </div>
        </Panel>

        <Panel icon={<Flame size={14} style={{ color: 'var(--cc-red)' }} />} title="Threat Triage">
          <div className="space-y-3">
            {(['error', 'warning', 'info'] as const).map((k) => {
              const count = sev[k];
              const pct = sev.total ? (count / sev.total) * 100 : 0;
              return (
                <div key={k}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="inline-flex items-center gap-1.5" style={{ color: 'var(--cc-text)' }}>
                      <span className="cc-dot" style={{ background: SEV_COLOR[k], color: SEV_COLOR[k] }} /> {SEV_LABEL[k]}
                    </span>
                    <span className="font-mono" style={{ color: SEV_COLOR[k] }}>
                      {count}
                    </span>
                  </div>
                  <div className="cc-meter">
                    <span style={{ width: `${pct}%`, background: SEV_COLOR[k], color: SEV_COLOR[k] }} />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 pt-3" style={{ borderTop: '1px solid var(--cc-line)' }}>
            <div className="text-[10px] uppercase tracking-[0.18em] mb-2" style={{ color: 'var(--cc-muted)' }}>
              <Bug size={11} className="inline mr-1" style={{ color: 'var(--cc-violet)' }} /> Attack Vectors
            </div>
            <div className="space-y-2">
              {vectors.sorted.length === 0 && (
                <div className="text-xs" style={{ color: 'var(--cc-muted)' }}>
                  No activity recorded
                </div>
              )}
              {vectors.sorted.map(([cat, count]) => (
                <div key={cat} className="flex items-center gap-2">
                  <span className="text-[11px] w-20 shrink-0 uppercase tracking-wide" style={{ color: 'var(--cc-muted)' }}>
                    {cat}
                  </span>
                  <div className="cc-track flex-1">
                    <span style={{ width: `${(count / vectors.max) * 100}%`, background: 'var(--cc-violet)', boxShadow: '0 0 8px var(--cc-violet)' }} />
                  </div>
                  <span className="text-[11px] font-mono w-6 text-right" style={{ color: 'var(--cc-text)' }}>
                    {count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </div>

      {/* Live stream + orchestration ------------------------------------- */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <Panel
          icon={<Radio size={14} style={{ color: 'var(--cc-green)' }} />}
          title="Live Threat Stream"
          right={<span className="cc-dot cc-ping cc-pulse" style={{ background: 'var(--cc-green)', color: 'var(--cc-green)' }} />}
          className="xl:col-span-2"
        >
          <div className="cc-feed cc-scroll space-y-0.5 overflow-y-auto" style={{ maxHeight: 300 }}>
            {liveEvents.length === 0 && <div style={{ color: 'var(--cc-muted)' }}>// awaiting telemetry…</div>}
            {liveEvents.map((e) => {
              const color = SEV_COLOR[e.severity] ?? 'var(--cc-cyan)';
              return (
                <div key={e.id} className="cc-feed-row">
                  <span className="cc-dot mt-1 shrink-0" style={{ background: color, color }} />
                  <span className="shrink-0" style={{ color: 'var(--cc-muted)' }}>
                    {new Date(e.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                  <span className="cc-tag shrink-0" style={{ color }}>
                    {e.category}
                  </span>
                  <span style={{ color: 'var(--cc-text)' }}>{e.message}</span>
                </div>
              );
            })}
          </div>
        </Panel>

        <Panel icon={<ScanLine size={14} style={{ color: 'var(--cc-violet)' }} />} title="Orchestration">
          <div className="space-y-2.5 cc-scroll overflow-y-auto" style={{ maxHeight: 300 }}>
            {autoList.length === 0 && (
              <div className="text-xs" style={{ color: 'var(--cc-muted)' }}>
                No playbooks defined — configure in Automation
              </div>
            )}
            {autoList.map((a) => {
              const color = !a.enabled ? 'var(--cc-muted)' : isFailed(a.last_status) ? 'var(--cc-red)' : isHealthy(a.last_status) ? 'var(--cc-green)' : 'var(--cc-cyan)';
              return (
                <div
                  key={a.id}
                  className="flex items-center gap-3 p-3 rounded-lg"
                  style={{ border: '1px solid var(--cc-line)', background: 'rgba(8,15,30,0.5)' }}
                >
                  <span className="cc-dot cc-pulse" style={{ background: color, color }} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold truncate" style={{ color: 'var(--cc-text)' }}>
                      {a.name}
                    </div>
                    <div className="text-[11px] truncate" style={{ color: 'var(--cc-muted)' }}>
                      {a.kind} · {a.enabled ? `next ${relTime(a.next_run_at)}` : 'disarmed'}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-[10px] uppercase tracking-wider font-mono" style={{ color }}>
                      {a.enabled ? 'armed' : 'idle'}
                    </div>
                    <div className="text-[10px] font-mono" style={{ color: 'var(--cc-muted)' }}>
                      {a.run_count} runs
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      </div>

      {/* Footer HUD line ------------------------------------------------- */}
      <div className="flex items-center justify-between text-[10px] tracking-[0.2em] uppercase pt-1" style={{ color: 'var(--cc-muted)' }}>
        <span className="inline-flex items-center gap-2">
          <Server size={11} /> M-Eyes DDI · Threat Defense Grid
        </span>
        <span className="inline-flex items-center gap-2">
          {posture.score < 40 && <AlertTriangle size={11} style={{ color: 'var(--cc-amber)' }} />}
          Live · refreshed {clock.time}
        </span>
      </div>
    </div>
  );
}
