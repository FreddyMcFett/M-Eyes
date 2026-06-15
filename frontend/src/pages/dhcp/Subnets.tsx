import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Trash2, UploadCloud } from 'lucide-react';
import { api } from '../../api/client';
import { DhcpSubnet, Network } from '../../api/types';
import DataTable from '../../components/DataTable';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import SlideOver from '../../components/SlideOver';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../components/Toast';

export default function Subnets() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [networkId, setNetworkId] = useState('');
  const [deleting, setDeleting] = useState<DhcpSubnet | null>(null);

  const { data: subnets = [], refetch } = useQuery({
    queryKey: ['dhcp-subnets'],
    queryFn: () => api.get<DhcpSubnet[]>('/api/v1/dhcp/subnets'),
  });
  const { data: networks = [] } = useQuery({
    queryKey: ['networks'],
    queryFn: () => api.get<Network[]>('/api/v1/networks'),
  });

  const enabledNetworkIds = new Set(subnets.map((s) => s.network_id));
  const candidates = networks.filter((n) => !n.is_container && !enabledNetworkIds.has(n.id));

  const create = useMutation({
    mutationFn: () => api.post('/api/v1/dhcp/subnets', { network_id: Number(networkId) }),
    onSuccess: () => {
      toast('success', 'DHCP scope created');
      setEditorOpen(false);
      queryClient.invalidateQueries({ queryKey: ['dhcp-subnets'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (subnet: DhcpSubnet) => api.delete(`/api/v1/dhcp/subnets/${subnet.id}`),
    onSuccess: () => {
      toast('success', 'DHCP scope removed');
      setDeleting(null);
      queryClient.invalidateQueries({ queryKey: ['dhcp-subnets'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const deployDhcp = useMutation({
    mutationFn: () => api.post<{ status: string; detail: string }>('/api/v1/deploy/kea'),
    onSuccess: (result) =>
      toast(result.status === 'success' ? 'success' : 'error', `DHCP: ${result.detail}`),
    onError: (err: Error) => toast('error', err.message),
  });

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">DHCP — Scopes</h1>
      <DataTable
        columns={[
          {
            header: 'Subnet',
            searchText: (s: DhcpSubnet) => s.cidr,
            render: (s) => (
              <Link to={`/dhcp/${s.id}`} className="text-info hover:underline font-mono">
                {s.cidr}
              </Link>
            ),
          },
          {
            header: 'Status',
            render: (s) => <StatusBadge value={s.enabled ? 'success' : 'failed'} />,
          },
          {
            header: 'Ranges',
            render: (s) => (
              <span className="font-mono text-xs">
                {s.ranges.map((r) => `${r.start_ip}-${r.end_ip}`).join(', ') || '—'}
              </span>
            ),
          },
          { header: 'Reservations', render: (s) => <span>{s.reservations.length}</span> },
          { header: 'Options', render: (s) => <span>{s.options.length}</span> },
          {
            header: 'Actions',
            render: (s) => (
              <button onClick={() => setDeleting(s)} className="text-danger hover:opacity-70" title="Delete">
                <Trash2 size={14} />
              </button>
            ),
          },
        ]}
        rows={subnets}
        rowKey={(s) => s.id}
        onCreate={() => {
          setNetworkId('');
          setEditorOpen(true);
        }}
        createLabel="Enable DHCP on network"
        onRefresh={() => refetch()}
        toolbar={
          <button className="f-btn-secondary" disabled={deployDhcp.isPending} onClick={() => deployDhcp.mutate()}>
            <UploadCloud size={14} /> Deploy DHCP
          </button>
        }
      />

      <SlideOver title="Enable DHCP" open={editorOpen} onClose={() => setEditorOpen(false)}>
        <FormField label="IPAM network">
          <select className="f-input" value={networkId} onChange={(e) => setNetworkId(e.target.value)}>
            <option value="">— select a network —</option>
            {candidates.map((n) => (
              <option key={n.id} value={n.id}>
                {n.cidr} {n.name && `(${n.name})`}
              </option>
            ))}
          </select>
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditorOpen(false)}>Cancel</button>
          <button className="f-btn-primary" disabled={!networkId || create.isPending} onClick={() => create.mutate()}>
            Enable
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Remove DHCP scope"
        message={`Remove the DHCP scope on ${deleting?.cidr}? Ranges, reservations and options will be deleted.`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
