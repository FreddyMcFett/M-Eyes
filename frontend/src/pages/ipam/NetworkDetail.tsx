import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Trash2, Wand2 } from 'lucide-react';
import { api } from '../../api/client';
import { IPAddress, Network } from '../../api/types';
import DataTable from '../../components/DataTable';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import SlideOver from '../../components/SlideOver';
import StatusBadge from '../../components/StatusBadge';
import StatCard from '../../components/StatCard';
import { useToast } from '../../components/Toast';

interface IpForm {
  ip: string;
  status: string;
  hostname: string;
  mac: string;
  description: string;
}

const EMPTY: IpForm = { ip: '', status: 'used', hostname: '', mac: '', description: '' };

export default function NetworkDetail() {
  const { id } = useParams();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [form, setForm] = useState<IpForm>(EMPTY);
  const [deleting, setDeleting] = useState<IPAddress | null>(null);

  const { data: network } = useQuery({
    queryKey: ['network', id],
    queryFn: () => api.get<Network>(`/api/v1/networks/${id}`),
  });
  const { data: addresses = [], refetch } = useQuery({
    queryKey: ['addresses', id],
    queryFn: () => api.get<IPAddress[]>(`/api/v1/networks/${id}/addresses`),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['addresses', id] });
    queryClient.invalidateQueries({ queryKey: ['network', id] });
  };

  const create = useMutation({
    mutationFn: () =>
      api.post(`/api/v1/networks/${id}/addresses`, { ...form, ip: form.ip || null }),
    onSuccess: () => {
      toast('success', 'Address allocated');
      setEditorOpen(false);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (address: IPAddress) => api.delete(`/api/v1/addresses/${address.id}`),
    onSuccess: () => {
      toast('success', 'Address released');
      setDeleting(null);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const suggestIp = async () => {
    try {
      const result = await api.get<{ ip: string }>(`/api/v1/networks/${id}/next-ip`);
      setForm((f) => ({ ...f, ip: result.ip }));
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'No free IP');
    }
  };

  const util = network?.utilization;

  return (
    <>
      <div className="flex items-center gap-3 mb-3">
        <Link to="/ipam" className="text-info hover:underline flex items-center gap-1 text-table">
          <ArrowLeft size={14} /> Networks
        </Link>
        <h1 className="text-lg font-semibold font-mono">{network?.cidr}</h1>
        <span className="text-muted">{network?.name}</span>
      </div>

      {util && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <StatCard label="Total usable" value={util.total} />
          <StatCard label="Allocated" value={util.used} accent />
          <StatCard label="In DHCP ranges" value={util.dhcp_range} />
          <StatCard label="Free" value={util.free} />
        </div>
      )}

      <DataTable
        columns={[
          {
            header: 'IP Address',
            searchText: (a: IPAddress) => a.ip,
            render: (a) => <span className="font-mono">{a.ip}</span>,
          },
          { header: 'Status', searchText: (a: IPAddress) => a.status, render: (a) => <StatusBadge value={a.status} /> },
          { header: 'Hostname', searchText: (a: IPAddress) => a.hostname, render: (a) => <span>{a.hostname || '—'}</span> },
          { header: 'MAC', searchText: (a: IPAddress) => a.mac, render: (a) => <span className="font-mono">{a.mac || '—'}</span> },
          { header: 'Description', searchText: (a: IPAddress) => a.description, render: (a) => <span>{a.description || '—'}</span> },
          {
            header: 'Actions',
            render: (a) => (
              <button onClick={() => setDeleting(a)} className="text-danger hover:opacity-70" title="Release">
                <Trash2 size={14} />
              </button>
            ),
          },
        ]}
        rows={addresses}
        rowKey={(a) => a.id}
        onCreate={() => {
          setForm(EMPTY);
          setEditorOpen(true);
        }}
        createLabel="Allocate IP"
        onRefresh={() => refetch()}
        emptyText="No addresses allocated in this network"
      />

      <SlideOver title="Allocate IP address" open={editorOpen} onClose={() => setEditorOpen(false)}>
        <FormField label="IP address" hint="Leave empty to auto-allocate the next free address">
          <div className="flex gap-2">
            <input
              className="f-input font-mono"
              value={form.ip}
              onChange={(e) => setForm({ ...form, ip: e.target.value })}
              placeholder="auto"
            />
            <button className="f-btn-secondary shrink-0" onClick={suggestIp} title="Suggest next free IP">
              <Wand2 size={14} /> Next free
            </button>
          </div>
        </FormField>
        <FormField label="Status">
          <select className="f-input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            <option value="used">used</option>
            <option value="reserved">reserved</option>
            <option value="dhcp">dhcp</option>
          </select>
        </FormField>
        <FormField label="Hostname">
          <input className="f-input" value={form.hostname} onChange={(e) => setForm({ ...form, hostname: e.target.value })} />
        </FormField>
        <FormField label="MAC address">
          <input className="f-input font-mono" value={form.mac} onChange={(e) => setForm({ ...form, mac: e.target.value })} />
        </FormField>
        <FormField label="Description">
          <input className="f-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditorOpen(false)}>
            Cancel
          </button>
          <button className="f-btn-primary" disabled={create.isPending} onClick={() => create.mutate()}>
            Allocate
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Release IP"
        message={`Release ${deleting?.ip}?`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
