import { useQuery } from '@tanstack/react-query';
import { Activity, Globe, List, Rss, Server } from 'lucide-react';
import { api } from '../api/client';
import { DashboardStats, SystemStatus } from '../api/types';
import Donut from '../components/Donut';
import { EngineSyncBadge } from '../components/EngineStatus';
import ResourceMonitor from '../components/ResourceMonitor';
import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';
import SystemStatusCard from '../components/SystemStatusCard';
import { useEventStream } from '../hooks/useEventStream';

export default function Dashboard() {
  const { data: stats } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get<DashboardStats>('/api/v1/dashboard/stats'),
    refetchInterval: 5000,
  });
  const { data: systemStatus } = useQuery({
    queryKey: ['system-status'],
    queryFn: () => api.get<SystemStatus>('/api/v1/system/status'),
    refetchInterval: 3000,
  });
  const liveEvents = useEventStream(12);

  const counts = stats?.counts ?? {};

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <StatCard label="Networks" value={counts.networks ?? '…'} icon={<List size={22} />} accent to="/ipam" />
        <StatCard label="IP Addresses" value={counts.ip_addresses ?? '…'} icon={<Activity size={22} />} to="/ipam" />
        <StatCard label="DNS Zones" value={counts.zones ?? '…'} icon={<Globe size={22} />} to="/dns" />
        <StatCard label="Records" value={counts.records ?? '…'} icon={<Globe size={22} />} to="/dns" />
        <StatCard label="DHCP Scopes" value={counts.dhcp_subnets ?? '…'} icon={<Server size={22} />} to="/dhcp" />
        <StatCard label="Feeds" value={counts.feeds ?? '…'} icon={<Rss size={22} />} to="/feeds" />
      </div>

      {/* System status + resource monitor */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        <SystemStatusCard status={systemStatus} />
        <ResourceMonitor resources={systemStatus?.resources} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Utilization */}
        <div className="f-card p-4">
          <h3 className="font-semibold text-sm mb-3">Network Utilization</h3>
          <div className="flex flex-wrap gap-4 justify-around">
            {(stats?.top_networks ?? []).map((network) => (
              <Donut key={network.id} percent={network.percent} label={`${network.cidr}`} />
            ))}
            {(stats?.top_networks ?? []).length === 0 && (
              <p className="text-muted text-table">No subnets yet</p>
            )}
          </div>
        </div>

        {/* DNS & DHCP services — native, auto-applied; no manual deploy. */}
        <div className="f-card p-4">
          <h3 className="font-semibold text-sm mb-3">DNS &amp; DHCP Services</h3>
          {(['bind', 'kea'] as const).map((target) => (
            <div key={target} className="flex items-center justify-between py-2.5 border-b border-line last:border-0">
              <div className="flex items-center gap-2 font-medium text-table">
                {target === 'bind' ? <Globe size={15} className="text-accent" /> : <Server size={15} className="text-accent" />}
                {target === 'bind' ? 'DNS' : 'DHCP'}
              </div>
              <EngineSyncBadge target={target} />
            </div>
          ))}
          <p className="text-xs text-muted mt-3">
            Configuration changes apply to the running services automatically.
          </p>
        </div>

        {/* Live events */}
        <div className="f-card p-4">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
            Live Events
            <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          </h3>
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            {liveEvents.length === 0 && <p className="text-muted text-table">Waiting for events…</p>}
            {liveEvents.map((event) => (
              <div key={event.id} className="flex items-start gap-2 text-xs">
                <StatusBadge value={event.severity} />
                <span className="text-slate-700">{event.message}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent changes */}
      <div className="f-card">
        <h3 className="font-semibold text-sm px-4 py-3 border-b border-line">Recent Configuration Changes</h3>
        <table className="f-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Time</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Object</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {(stats?.recent_changes ?? []).map((change) => (
              <tr key={change.id}>
                <td className="font-mono text-xs">v{change.id}</td>
                <td className="whitespace-nowrap">{new Date(change.ts).toLocaleString()}</td>
                <td>{change.actor}</td>
                <td>
                  <StatusBadge value={change.action} />
                </td>
                <td>{change.object_type}</td>
                <td>{change.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
