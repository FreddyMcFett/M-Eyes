import { Cpu, Gauge as GaugeIcon, HardDrive, MemoryStick } from 'lucide-react';
import { SystemResources } from '../api/types';
import { formatBytes, formatDuration } from '../lib/format';

function barColor(percent: number): string {
  return percent > 90 ? 'var(--danger)' : percent > 75 ? 'var(--warning)' : 'var(--accent)';
}

function Bar({ icon, label, percent, detail }: { icon: JSX.Element; label: string; percent: number | null; detail: string }) {
  const value = percent === null ? 0 : Math.min(100, Math.max(0, percent));
  const color = barColor(value);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="flex items-center gap-1.5 text-table font-medium text-slate-600">
          <span className="text-accent">{icon}</span> {label}
        </span>
        <span className="text-xs text-muted">
          {percent === null ? 'n/a' : `${value.toFixed(0)}%`} · {detail}
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
        <div
          className="h-full rounded-full transition-[width] duration-500"
          style={{ width: `${value}%`, background: color }}
        />
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
