import { Cpu, Gauge as GaugeIcon, HardDrive, MemoryStick } from 'lucide-react';
import { SystemResources } from '../api/types';
import { formatBytes, formatDuration } from '../lib/format';

function barGradient(percent: number): string {
  if (percent > 90) return 'linear-gradient(90deg, #fb7185, #ef4444)';
  if (percent > 75) return 'linear-gradient(90deg, #fbbf24, #f59e0b)';
  return 'linear-gradient(90deg, #34d399, #06b6d4)';
}
function glowColor(percent: number): string {
  return percent > 90 ? '#ef4444' : percent > 75 ? '#f59e0b' : '#10b981';
}

function Bar({ icon, label, percent, detail }: { icon: JSX.Element; label: string; percent: number | null; detail: string }) {
  const value = percent === null ? 0 : Math.min(100, Math.max(0, percent));
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="flex items-center gap-1.5 text-table font-semibold text-slate-600">
          <span className="text-accent">{icon}</span> {label}
        </span>
        <span className="text-xs text-muted tabular-nums">
          <b className="text-slate-700 font-semibold">{percent === null ? 'n/a' : `${value.toFixed(0)}%`}</b> · {detail}
        </span>
      </div>
      <div className="relative h-2.5 rounded-full bg-slate-100 overflow-hidden ring-1 ring-slate-200/60">
        <div
          className="relative h-full rounded-full transition-[width] duration-700 ease-out overflow-hidden"
          style={{ width: `${value}%`, background: barGradient(value), boxShadow: `0 0 10px -1px ${glowColor(value)}88` }}
        >
          <span className="absolute inset-y-0 -left-1/3 w-1/3 bg-white/40 blur-[2px] animate-shimmer" />
        </div>
      </div>
    </div>
  );
}

/** Light, FortiOS-styled host resource monitor for the operational dashboard. */
export default function ResourceMonitor({ resources }: { resources?: SystemResources }) {
  const mem = resources?.memory;
  const disk = resources?.disk;
  const load = resources?.load_average;
  const loadPerCore = load && resources?.cpu_count ? load[0] / resources.cpu_count : null;

  return (
    <div className="f-card p-4">
      <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
        <GaugeIcon size={16} className="text-accent" /> Resource Monitor
      </h3>
      <div className="space-y-3">
        <Bar
          icon={<Cpu size={14} />}
          label="CPU"
          percent={resources?.cpu_percent ?? null}
          detail={`${resources?.cpu_count ?? '—'} cores`}
        />
        <Bar
          icon={<MemoryStick size={14} />}
          label="Memory"
          percent={mem?.percent ?? null}
          detail={mem ? `${formatBytes(mem.used)} / ${formatBytes(mem.total)}` : 'unavailable'}
        />
        <Bar
          icon={<HardDrive size={14} />}
          label="Disk"
          percent={disk?.percent ?? null}
          detail={disk ? `${formatBytes(disk.used)} / ${formatBytes(disk.total)}` : 'unavailable'}
        />
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-4 pt-3 border-t border-line text-xs">
        <div className="flex justify-between">
          <span className="text-muted">Load avg</span>
          <span className="font-mono" style={loadPerCore && loadPerCore > 1 ? { color: 'var(--warning)' } : undefined}>
            {load ? load.map((l) => l.toFixed(2)).join(' / ') : '—'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted">Host uptime</span>
          <span className="font-mono">{formatDuration(resources?.host_uptime_seconds)}</span>
        </div>
      </div>
    </div>
  );
}
