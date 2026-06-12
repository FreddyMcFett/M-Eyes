import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Trash2, UploadCloud } from 'lucide-react';
import { api } from '../../api/client';
import { DnsView, Network, Zone } from '../../api/types';
import DataTable from '../../components/DataTable';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import SlideOver from '../../components/SlideOver';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../components/Toast';

export default function Zones() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [deleting, setDeleting] = useState<Zone | null>(null);
  const [form, setForm] = useState({ name: '', kind: 'forward', network_id: '', view_id: '', dnssec: false });

  const { data: zones = [], refetch } = useQuery({
    queryKey: ['zones'],
    queryFn: () => api.get<Zone[]>('/api/v1/zones'),
  });
  const { data: networks = [] } = useQuery({
    queryKey: ['networks'],
    queryFn: () => api.get<Network[]>('/api/v1/networks'),
  });
  const { data: views = [] } = useQuery({
    queryKey: ['dns-views'],
    queryFn: () => api.get<DnsView[]>('/api/v1/views'),
  });

  const create = useMutation({
    mutationFn: () =>
      api.post('/api/v1/zones', {
        name: form.name || undefined,
        kind: form.kind,
        network_id: form.kind === 'reverse' && form.network_id ? Number(form.network_id) : undefined,
        view_id: form.view_id ? Number(form.view_id) : undefined,
        dnssec_enabled: form.dnssec,
      }),
    onSuccess: () => {
      toast('success', 'Zone created');
      setEditorOpen(false);
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (zone: Zone) => api.delete(`/api/v1/zones/${zone.id}`),
    onSuccess: () => {
      toast('success', 'Zone deleted');
      setDeleting(null);
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const deployBind = useMutation({
    mutationFn: () => api.post<{ status: string; detail: string }>('/api/v1/deploy/bind'),
    onSuccess: (result) =>
      toast(result.status === 'success' ? 'success' : 'error', `BIND: ${result.detail}`),
    onError: (err: Error) => toast('error', err.message),
  });

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">DNS — Zones</h1>
      <DataTable
        columns={[
          {
            header: 'Zone',
            searchText: (z: Zone) => z.name,
            render: (z) => (
              <Link to={`/dns/${z.id}`} className="text-info hover:underline font-mono">
                {z.name}
              </Link>
            ),
          },
          { header: 'Kind', searchText: (z: Zone) => z.kind, render: (z) => <StatusBadge value={z.kind} /> },
          {
            header: 'View',
            searchText: (z: Zone) => z.view_name ?? 'default',
            render: (z) => <span className="font-mono">{z.view_name ?? 'default'}</span>,
          },
          { header: 'DNSSEC', render: (z) => (z.dnssec_enabled ? <StatusBadge value="signed" /> : <span className="text-muted">—</span>) },
          { header: 'Serial', render: (z) => <span className="font-mono">{z.serial}</span> },
          { header: 'Records', render: (z) => <span>{z.record_count}</span> },
          { header: 'TTL', render: (z) => <span>{z.default_ttl}</span> },
          {
            header: 'Actions',
            render: (z) => (
              <button onClick={() => setDeleting(z)} className="text-danger hover:opacity-70" title="Delete">
                <Trash2 size={14} />
              </button>
            ),
          },
        ]}
        rows={zones}
        rowKey={(z) => z.id}
        onCreate={() => {
          setForm({ name: '', kind: 'forward', network_id: '', view_id: '', dnssec: false });
          setEditorOpen(true);
        }}
        createLabel="Create Zone"
        onRefresh={() => refetch()}
        toolbar={
          <button className="f-btn-secondary" disabled={deployBind.isPending} onClick={() => deployBind.mutate()}>
            <UploadCloud size={14} /> Deploy to BIND
          </button>
        }
      />

      <SlideOver title="Create Zone" open={editorOpen} onClose={() => setEditorOpen(false)}>
        <FormField label="Kind">
          <select className="f-input" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
            <option value="forward">forward</option>
            <option value="reverse">reverse</option>
          </select>
        </FormField>
        {form.kind === 'reverse' && (
          <FormField label="Derive from network" hint="Optional: name is computed from the network CIDR (/8, /16, /24)">
            <select
              className="f-input"
              value={form.network_id}
              onChange={(e) => setForm({ ...form, network_id: e.target.value })}
            >
              <option value="">— manual name —</option>
              {networks
                .filter((n) => !n.is_container)
                .map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.cidr} {n.name && `(${n.name})`}
                  </option>
                ))}
            </select>
          </FormField>
        )}
        <FormField
          label="Zone name"
          hint={form.kind === 'reverse' ? 'e.g. 1.10.10.in-addr.arpa (leave empty when deriving from a network)' : 'e.g. corp.example.com'}
        >
          <input className="f-input font-mono" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </FormField>
        <FormField label="DNS view" hint="Split-horizon: the zone is only served to clients matching the view">
          <select className="f-input" value={form.view_id} onChange={(e) => setForm({ ...form, view_id: e.target.value })}>
            <option value="">default (all clients)</option>
            {views.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} ({v.match_clients})
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="DNSSEC" hint="Sign the zone with BIND's default dnssec-policy">
          <label className="flex items-center gap-2 text-table">
            <input type="checkbox" checked={form.dnssec} onChange={(e) => setForm({ ...form, dnssec: e.target.checked })} />
            Enable inline signing
          </label>
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditorOpen(false)}>
            Cancel
          </button>
          <button
            className="f-btn-primary"
            disabled={create.isPending || (!form.name && !(form.kind === 'reverse' && form.network_id))}
            onClick={() => create.mutate()}
          >
            Create
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Delete zone"
        message={`Delete zone ${deleting?.name} and all its records?`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
