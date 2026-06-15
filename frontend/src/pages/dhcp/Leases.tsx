import { useQuery } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { api } from '../../api/client';
import { DhcpLease, LeasesResponse } from '../../api/types';
import DataTable from '../../components/DataTable';
import StatusBadge from '../../components/StatusBadge';

export default function Leases() {
  const { data, refetch } = useQuery({
    queryKey: ['dhcp-leases'],
    queryFn: () => api.get<LeasesResponse>('/api/v1/dhcp/leases'),
    refetchInterval: 15000,
  });

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">DHCP — Leases</h1>
      <p className="text-table text-muted mb-3 max-w-3xl">
        Live lease table read from the DHCP engine; refreshes automatically every 15 seconds.
      </p>
      {data && !data.reachable && (
        <div className="flex items-center gap-2 mb-3 px-3 py-2 rounded border border-warning/50 bg-warning/10 text-table">
          <AlertTriangle size={15} className="text-warning shrink-0" />
          {data.detail} — start the DHCP engine to see live leases.
        </div>
      )}
      <DataTable
        columns={[
          { header: 'IP Address', searchText: (l: DhcpLease) => l.ip, render: (l) => <span className="font-mono">{l.ip}</span> },
          { header: 'MAC', searchText: (l: DhcpLease) => l.mac, render: (l) => <span className="font-mono">{l.mac || '—'}</span> },
          { header: 'Hostname', searchText: (l: DhcpLease) => l.hostname, render: (l) => <span>{l.hostname || '—'}</span> },
          { header: 'State', searchText: (l: DhcpLease) => l.state, render: (l) => <StatusBadge value={l.state} /> },
          { header: 'Subnet', searchText: (l: DhcpLease) => l.subnet ?? '', render: (l) => <span className="font-mono">{l.subnet ?? '—'}</span> },
          { header: 'Expires', render: (l) => <span>{l.expires_at ? new Date(l.expires_at).toLocaleString() : '—'}</span> },
        ]}
        rows={data?.leases ?? []}
        rowKey={(l) => l.ip}
        onRefresh={() => refetch()}
        emptyText={data?.reachable ? 'No active leases' : 'DHCP engine not reachable'}
      />
    </>
  );
}
