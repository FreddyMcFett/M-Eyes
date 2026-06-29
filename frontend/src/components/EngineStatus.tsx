import { AlertTriangle, CheckCircle2, CloudOff, Loader2, RefreshCw } from 'lucide-react';
import { EngineState, EngineTarget, EngineView, useEngineSync } from '../hooks/useEngineSync';

/* Native service-health chips for DNS (BIND) and DHCP (Kea). The header pills
   double as the always-mounted driver for background auto-apply. */

interface Meta {
  dot: string; // tailwind bg-* for the status dot
  badge: string; // tailwind classes for the page badge pill
  label: string;
  Icon: typeof CheckCircle2;
  spin?: boolean;
}

const META: Record<EngineState, Meta> = {
  live: { dot: 'bg-accent', badge: 'bg-accent/10 text-accent-dark border-accent/40', label: 'Live', Icon: CheckCircle2 },
  applying: { dot: 'bg-info', badge: 'bg-info/10 text-info border-info/40', label: 'Applying…', Icon: Loader2, spin: true },
  pending: { dot: 'bg-warning', badge: 'bg-warning/10 text-warning border-warning/50', label: 'Sync pending', Icon: CloudOff },
  attention: { dot: 'bg-danger', badge: 'bg-danger/10 text-danger border-danger/50', label: 'Needs attention', Icon: AlertTriangle },
  idle: { dot: 'bg-slate-400', badge: 'bg-slate-100 text-slate-500 border-line', label: 'Ready', Icon: CheckCircle2 },
};

function tip(e: EngineView): string {
  const versions =
    e.deployedVersion !== null
      ? `config v${e.configVersion}, applied v${e.deployedVersion}`
      : `config v${e.configVersion}`;
  const base = `${e.label} service · ${META[e.state].label} (${versions})`;
  return e.lastMessage ? `${base}\n${e.lastMessage}` : base;
}

/** Compact DNS + DHCP service pills for the top bar (dark background). */
export function EngineStatusPills() {
  const sync = useEngineSync();
  return (
    <div className="flex items-center gap-3.5">
      {[sync.bind, sync.kea].map((e) => {
        const m = META[e.state];
        return (
          <span key={e.target} title={tip(e)} className="flex items-center gap-1.5 text-xs text-slate-300">
            {e.state === 'applying' ? (
              <Loader2 size={11} className="animate-spin text-info" />
            ) : (
              <span className={`w-2 h-2 rounded-full ${m.dot} ${e.state === 'live' ? 'animate-pulse' : ''}`} />
            )}
            {e.label}
          </span>
        );
      })}
    </div>
  );
}

/** Inline service-state badge for a page toolbar; offers a manual re-apply when
    the engine needs attention. Replaces the old manual "Deploy" button. */
export function EngineSyncBadge({ target }: { target: EngineTarget }) {
  const sync = useEngineSync();
  const e = sync[target];
  const m = META[e.state];
  const needsAction = e.state === 'pending' || e.state === 'attention';

  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded border text-xs font-medium ${m.badge}`}
        title={tip(e)}
      >
        <m.Icon size={13} className={m.spin ? 'animate-spin' : ''} />
        {e.label} {m.label}
        {e.deployedVersion !== null && <span className="font-mono opacity-60">v{e.deployedVersion}</span>}
      </span>
      {needsAction && (
        <button className="f-btn-secondary" onClick={() => sync.reapply(target)} title="Re-apply now">
          <RefreshCw size={13} /> Apply now
        </button>
      )}
    </div>
  );
}
